"""The questions asked once the email code has been verified.

The flow is driven by the server: the client asks for `state`, draws the screen
for `next_step` with the options it is handed, posts the answer, and repeats
until `done`. Clients therefore never hold a copy of the rules, and the safe
experience for under-18 accounts cannot be defeated by an old build.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.models.user import User
from app.schemas.legal import AcceptedDocument
from app.schemas.onboarding import (
    BirthDateRequest,
    ExperienceRequest,
    InstructorCertificationOut,
    OnboardingState,
    PractitionerTypeRequest,
    ProfileOut,
    QuizAnswersRequest,
    QuizOut,
    QuizResultOut,
)
from app.services import onboarding_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/state", response_model=OnboardingState)
async def state(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> OnboardingState:
    return await onboarding_service.state(session, user)


@router.get("/profile", response_model=ProfileOut)
async def profile(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> ProfileOut:
    """The profile as the app may see it — no age, no ceiling. See `ProfileOut`."""
    return await onboarding_service.profile_out(session, user)


class _BirthDateBody(BirthDateRequest):
    #: The guardian-consent notice, when the date turns out to be under 18.
    accepted_documents: list[AcceptedDocument] = Field(default_factory=list)


@router.post("/birth-date", response_model=OnboardingState)
async def set_birth_date(
    data: _BirthDateBody,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> OnboardingState:
    """Save the date of birth: the answer everything else hangs off.

    Under 18 the guardian-consent notice must come with it, and the account
    picks up the age ceiling of `app.services.access_policy`.
    """
    return await onboarding_service.set_birth_date(
        session,
        user,
        birth_date=data.birth_date,
        accepted_documents=data.accepted_documents,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/practitioner-type", response_model=OnboardingState)
async def set_practitioner_type(
    data: PractitionerTypeRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> OnboardingState:
    """Athlete or instructor. Asked of adult accounts only."""
    return await onboarding_service.set_practitioner_type(
        session, user, practitioner_type=data.practitioner_type
    )


@router.post("/experience", response_model=OnboardingState)
async def set_experience(
    data: ExperienceRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> OnboardingState:
    """How long they have been training. Opens the matching levels at once.

    The declaration stands until the vault game either confirms it or brings
    it down to what the score supports.
    """
    return await onboarding_service.set_experience(session, user, band=data.experience_band)


@router.post("/instructor-certificate", response_model=InstructorCertificationOut)
async def submit_instructor_certificate(
    issuing_body: str = Form(..., min_length=2, max_length=160),
    certificate: UploadFile = File(...),
    identity_document: UploadFile = File(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> InstructorCertificationOut:
    """Send the dossier to the mailbox that reviews spots.

    Two files, both required: the certificate from a nationally recognised
    body, and an identity document showing the certificate belongs to the
    person signed in. Neither is stored — they are mailed and dropped, and
    only a SHA-256 digest stays behind. The instructor badge is then granted
    by a human through the admin endpoint, never automatically.
    """
    return await onboarding_service.submit_instructor_certificate(
        session,
        user,
        issuing_body=issuing_body,
        certificate_filename=certificate.filename or "",
        certificate_content=await certificate.read(),
        certificate_content_type=certificate.content_type or "",
        identity_filename=identity_document.filename or "",
        identity_content=await identity_document.read(),
        identity_content_type=identity_document.content_type or "",
    )


@router.post("/quiz", response_model=QuizOut)
async def start_quiz(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> QuizOut:
    """Deal a fresh run of the vault-naming game. Answers stay server-side."""
    return await onboarding_service.start_quiz(session, user)


@router.post("/quiz/answers", response_model=QuizResultOut)
async def submit_quiz(
    data: QuizAnswersRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> QuizResultOut:
    """Score a run and settle the experience band it supports."""
    return await onboarding_service.submit_quiz(
        session, user, attempt_id=UUID(str(data.attempt_id)), answers=data.answers
    )
