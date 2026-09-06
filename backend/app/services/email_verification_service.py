"""Sign-in by emailed code.

There is no password in this flow. The account *is* the address: the app asks
for it, a six-digit code is generated on the spot and mailed from the no-reply
sender, and typing it back proves control of the mailbox. A correct code on an
unknown address creates the account and its profile row; on a known one it
signs the member in. Same two endpoints either way, and the responses give away
nothing about which case it was — otherwise the endpoint would double as a way
to find out who has an account here.

What protects it:

- codes live ``EMAIL_CODE_TTL_MINUTES`` (10 by default) and once only;
- five wrong guesses burn the code, so 10⁶ combinations cannot be walked;
- an address may request ``EMAIL_CODE_MAX_PER_HOUR`` codes, no faster than one
  per ``EMAIL_CODE_MIN_INTERVAL_SECONDS`` — mailbox flooding costs the sender
  nothing, so the limit lives here rather than only at the HTTP edge;
- only an HMAC of the code is stored, keyed with the server secret.
"""

from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import Forbidden, RateLimited, Unauthorized, ValidationFailed
from app.core.logging import log
from app.models.verification import EmailVerificationCode, VerificationPurpose
from app.repositories import profiles as profiles_repo
from app.repositories import users as users_repo
from app.repositories import verification as codes_repo
from app.schemas.auth import EmailCodeSent, EmailCodeVerifyRequest, TokenPair
from app.schemas.legal import AcceptedDocument
from app.schemas.onboarding import OnboardingStep
from app.services import auth_service, legal_service, mailer
from app.services.mailer import Email

CODE_DIGITS = 6


def generate_code() -> str:
    """A fresh code, drawn now, from the OS CSPRNG."""
    return f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"


def hash_code(email: str, code: str) -> str:
    """HMAC the code with the server secret, bound to the address.

    Binding to the address means a code leaked for one mailbox cannot be
    replayed against another, and the digest of a six-digit number is not
    brute-forceable from a database dump without the secret.
    """
    settings = get_settings()
    return hmac.new(
        settings.jwt_secret.encode(),
        f"{email.lower()}:{code}".encode(),
        sha256,
    ).hexdigest()


def matches(stored_hash: str, email: str, code: str) -> bool:
    return hmac.compare_digest(stored_hash, hash_code(email, code))


def _body(code: str, ttl_minutes: int) -> str:
    settings = get_settings()
    mailbox = settings.review_mailbox or "il supporto della piattaforma"
    return f"""Ciao,

il tuo codice di accesso a PkFAMILY è:

    {code}

Scade tra {ttl_minutes} minuti e vale una sola volta.

Se non hai richiesto tu questo codice, ignora questo messaggio: senza il
codice nessuno può entrare, e non è stato creato nessun account.

Un promemoria, perché conta: PkFAMILY è un servizio informativo gratuito.
Mette a disposizione spot segnalati dalla community e contenuti didattici,
ma non organizza né supervisiona alcun allenamento. Chi si allena lo fa
sotto la propria esclusiva responsabilità.

--
Questo messaggio è generato automaticamente da un indirizzo che non viene
letto: non rispondere. Per scrivere a una persona usa {mailbox}.
"""


async def request_code(
    session: AsyncSession,
    *,
    email: str,
    purpose: VerificationPurpose = VerificationPurpose.email_login,
) -> EmailCodeSent:
    settings = get_settings()
    address = email.lower()
    now = datetime.now(timezone.utc)

    recent = await codes_repo.count_since(session, email=address, since=now - timedelta(hours=1))
    if recent >= settings.email_code_max_per_hour:
        raise RateLimited("too many codes requested for this address, try again later")

    last = await codes_repo.latest_any(session, email=address)
    if last is not None:
        age = (now - last.created_at).total_seconds()
        if age < settings.email_code_min_interval_seconds:
            raise RateLimited(
                f"wait {int(settings.email_code_min_interval_seconds - age)}s "
                "before requesting another code"
            )
        # A new code supersedes the previous one: only one may ever be live.
        if last.consumed_at is None:
            last.consumed_at = now

    code = generate_code()
    ttl = settings.email_code_ttl_minutes
    await codes_repo.create(
        session,
        email=address,
        code_hash=hash_code(address, code),
        purpose=purpose,
        expires_at=now + timedelta(minutes=ttl),
    )
    await session.commit()

    await mailer.send(
        Email(
            to=address,
            subject=f"{code} — il tuo codice di accesso a PkFAMILY",
            text=_body(code, ttl),
        )
    )
    log.info("auth.code_requested", email_domain=address.rpartition("@")[2])

    return EmailCodeSent(
        sent=True,
        expires_in_seconds=ttl * 60,
        # Never in production: the validator on `env` guarantees a real mail
        # backend there, so nobody needs the code echoed back.
        debug_code=code if settings.env != "production" else None,
    )


def _burn(row: EmailVerificationCode) -> None:
    row.consumed_at = datetime.now(timezone.utc)


async def _consume(
    session: AsyncSession, *, email: str, code: str, purpose: VerificationPurpose
) -> None:
    """Validate ``code`` and mark it used, or raise."""
    settings = get_settings()
    address = email.lower()
    row = await codes_repo.latest_open(session, email=address, purpose=purpose)
    now = datetime.now(timezone.utc)

    if row is None or row.expires_at < now:
        # Same error for "never asked", "already used" and "expired": the
        # caller learns nothing about the state of the address.
        raise Unauthorized("invalid or expired code")

    row.attempts += 1
    if row.attempts > settings.email_code_max_attempts:
        _burn(row)
        await session.commit()
        raise Unauthorized("invalid or expired code")

    if not matches(row.code_hash, address, code):
        await session.commit()
        raise Unauthorized("invalid or expired code")

    _burn(row)


def _display_name_from(email: str, given: str | None) -> str:
    if given:
        return given
    local = email.split("@", 1)[0]
    cleaned = "".join(c for c in local if c.isalnum() or c in "._-").strip("._-")
    return (cleaned or "Traceur")[:80].ljust(2, "_")


async def verify_code(
    session: AsyncSession,
    data: EmailCodeVerifyRequest,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[TokenPair, bool, OnboardingStep]:
    """Check the code; sign in, or create the account and its profile.

    Returns ``(tokens, created, next_step)``.
    """
    address = str(data.email).lower()
    await _consume(session, email=address, code=data.code, purpose=VerificationPurpose.email_login)

    user = await users_repo.get_by_email(session, address)
    created = False

    if user is None:
        # Creating the account is what the notices gate: no acceptance, no
        # profile. Only the signup notice is required here — the guardian
        # consent is asked at the birth-date step, which is where the app
        # first knows the age.
        missing = legal_service.missing_required(data.accepted_documents, is_minor=False)
        if missing:
            raise ValidationFailed(
                "these notices must be accepted before the account can be created: "
                + ", ".join(missing)
            )
        user = await users_repo.create(
            session,
            email=address,
            password_hash=None,
            display_name=_display_name_from(address, data.display_name),
            is_email_verified=True,
        )
        await profiles_repo.get_or_create(session, user.id)
        created = True
    else:
        if not user.is_active:
            raise Forbidden("account disabled")
        user.is_email_verified = True
        await profiles_repo.get_or_create(session, user.id)

    accepted: list[AcceptedDocument] = list(data.accepted_documents)
    if accepted:
        await legal_service.record(
            session,
            user_id=user.id,
            documents=accepted,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    await session.commit()
    tokens = await auth_service.issue_tokens(session, user)
    log.info("auth.code_verified", created=created)

    # Imported here to keep the module import graph acyclic.
    from app.services import onboarding_service

    profile = await profiles_repo.get(session, user.id)
    next_step = await onboarding_service.next_step(session, user, profile)
    return tokens, created, next_step
