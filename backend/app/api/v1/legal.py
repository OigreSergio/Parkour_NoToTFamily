"""The notices, and the record of who accepted what.

The documents themselves are public: anyone can read what they would be
agreeing to before creating an account, which is the point of a notice.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.core.exceptions import NotFound
from app.legal import DOCUMENTS, Trigger, documents_for, get_document
from app.models.user import User
from app.repositories import profiles as profiles_repo
from app.schemas.legal import (
    LegalAcceptanceOut,
    LegalAcceptRequest,
    LegalDocumentOut,
    LegalStatusOut,
)
from app.services import legal_service

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/documents", response_model=list[LegalDocumentOut])
async def list_documents(trigger: Trigger | None = None) -> list[LegalDocumentOut]:
    """Every notice, or only the ones shown at a given moment.

    Clients call this once at startup and cache it: `trigger` tells them when
    to put each one on screen (`signup`, `spot_open`, `tutorial_open`).
    """
    docs = documents_for(trigger) if trigger is not None else DOCUMENTS
    return [LegalDocumentOut.of(d) for d in docs]


@router.get("/documents/{document_id}", response_model=LegalDocumentOut)
async def read_document(document_id: str) -> LegalDocumentOut:
    doc = get_document(document_id)
    if doc is None:
        raise NotFound("legal document not found")
    return LegalDocumentOut.of(doc)


async def _status(session: AsyncSession, user: User) -> LegalStatusOut:
    acceptances = await profiles_repo.list_acceptances(session, user.id)
    return LegalStatusOut(
        accepted=[
            LegalAcceptanceOut(
                document_id=a.document_id,
                document_version=a.document_version,
                accepted_at=a.accepted_at,
            )
            for a in acceptances
        ],
        pending=[LegalDocumentOut.of(d) for d in legal_service.pending_documents(acceptances)],
    )


@router.get("/status", response_model=LegalStatusOut)
async def status(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> LegalStatusOut:
    return await _status(session, user)


@router.post("/accept", response_model=LegalStatusOut)
async def accept(
    data: LegalAcceptRequest,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> LegalStatusOut:
    """Record acceptance of one or more notices, at the version shown.

    A version that is no longer current is refused: it would mean the user
    accepted something other than what is in force.
    """
    await legal_service.record(
        session,
        user_id=user.id,
        documents=data.documents,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return await _status(session, user)
