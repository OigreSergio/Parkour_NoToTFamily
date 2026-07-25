from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr | None
    display_name: str
    role: UserRole
    is_email_verified: bool
    is_guest: bool = False
    is_subscribed: bool = False
    created_at: datetime
