from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Conversation, ConversationKind, ConversationMember, Message


async def create_conversation(
    session: AsyncSession, *, member_ids: list[UUID], title: str | None = None
) -> Conversation:
    kind = ConversationKind.direct if len(member_ids) == 2 else ConversationKind.group
    convo = Conversation(kind=kind, title=title)
    session.add(convo)
    await session.flush()
    for uid in member_ids:
        session.add(ConversationMember(conversation_id=convo.id, user_id=uid))
    await session.flush()
    return convo


async def is_member(session: AsyncSession, *, conversation_id: UUID, user_id: UUID) -> bool:
    stmt = select(ConversationMember.id).where(
        ConversationMember.conversation_id == conversation_id,
        ConversationMember.user_id == user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def list_for_user(session: AsyncSession, user_id: UUID) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
        .where(ConversationMember.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list((await session.execute(stmt)).scalars())


async def add_message(
    session: AsyncSession, *, conversation_id: UUID, author_id: UUID, body: str
) -> Message:
    msg = Message(conversation_id=conversation_id, author_id=author_id, body=body)
    session.add(msg)
    await session.flush()
    return msg


async def list_messages(
    session: AsyncSession, conversation_id: UUID, *, limit: int = 50
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return list(reversed(list((await session.execute(stmt)).scalars())))
