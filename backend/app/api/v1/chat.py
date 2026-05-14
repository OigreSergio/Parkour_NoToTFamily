from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.core.exceptions import Forbidden
from app.models.user import User
from app.repositories import chat as chat_repo
from app.schemas.chat import CreateConversationRequest, MessageOut, SendMessageRequest
from app.services.chat_service import manager

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: CreateConversationRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> dict[str, UUID]:
    member_ids = list({*data.member_ids, user.id})
    convo = await chat_repo.create_conversation(session, member_ids=member_ids, title=data.title)
    await session.commit()
    return {"id": convo.id}


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> list[MessageOut]:
    if not await chat_repo.is_member(session, conversation_id=conversation_id, user_id=user.id):
        raise Forbidden("not a member of this conversation")
    msgs = await chat_repo.list_messages(session, conversation_id)
    return [MessageOut.model_validate(m) for m in msgs]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: UUID,
    data: SendMessageRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> MessageOut:
    if not await chat_repo.is_member(session, conversation_id=conversation_id, user_id=user.id):
        raise Forbidden("not a member of this conversation")
    msg = await chat_repo.add_message(
        session, conversation_id=conversation_id, author_id=user.id, body=data.body
    )
    await session.commit()
    out = MessageOut.model_validate(msg)
    # Best-effort fan-out to live WS subscribers (single-worker dev only).
    await manager.publish(
        recipient_ids=[user.id], payload={"type": "message", "data": out.model_dump(mode="json")}
    )
    return out
