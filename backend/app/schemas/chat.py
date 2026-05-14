from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    author_id: UUID | None
    body: str
    created_at: datetime


class SendMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class CreateConversationRequest(BaseModel):
    member_ids: list[UUID] = Field(min_length=1, max_length=50)
    title: str | None = Field(default=None, max_length=120)
