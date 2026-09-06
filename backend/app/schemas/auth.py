from pydantic import BaseModel, EmailStr, Field

from app.schemas.legal import AcceptedDocument
from app.schemas.onboarding import OnboardingStep


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class GuestLoginRequest(BaseModel):
    """Sign in without saying who you are.

    Nothing is asked: no email, no chosen handle. The name is generated, and
    the notices are the only thing that gates the account — the same gate the
    email flow has, because a guest gets the same spots and the same tutorials
    and therefore takes the same risk.
    """

    accepted_documents: list[AcceptedDocument] = Field(default_factory=list)


class GuestResumeRequest(BaseModel):
    """Come back to a guest account with the key handed out at sign-up."""

    guest_key: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class GuestSession(BaseModel):
    tokens: TokenPair
    #: The name the app generated. Nothing about it is a claim of identity.
    display_name: str
    #: Shown **once**, at creation: it is the only way back to this account and
    #: to the progress on it. `None` when resuming — the key already exists.
    guest_key: str | None = None
    created: bool = False
    next_step: OnboardingStep


# --- email code sign-in ------------------------------------------------------


class EmailCodeRequest(BaseModel):
    """Ask for a fresh code. Works the same for a new and an existing address."""

    email: EmailStr


class EmailCodeSent(BaseModel):
    """Deliberately says nothing about whether the address has an account.

    Answering "that email is unknown" would turn the endpoint into a way to
    enumerate members, so the response is identical either way.
    """

    sent: bool = True
    expires_in_seconds: int
    #: Only ever populated outside production, so a developer can sign in
    #: without a mail server. `None` in production.
    debug_code: str | None = None


class EmailCodeVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)
    #: Used only when the code creates the account.
    display_name: str | None = Field(default=None, min_length=2, max_length=80)
    #: The notices shown before the account is created. Signup is refused
    #: unless the required ones are here at their current version.
    accepted_documents: list[AcceptedDocument] = []


class EmailCodeResult(BaseModel):
    tokens: TokenPair
    #: True when this call created the account (and its profile row).
    created: bool
    #: What the app has to ask next.
    next_step: OnboardingStep
