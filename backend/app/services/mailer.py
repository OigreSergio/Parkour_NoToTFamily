"""Outbound email.

Every message the platform sends is automated and comes from a **no-reply**
address: nobody reads the mailbox behind ``MAIL_FROM``. The body therefore
always names the mailbox that *is* read (the one that reviews spots and
instructor dossiers), and the headers tell well-behaved mail systems not to
generate autoresponders or out-of-office replies against it.

Four backends, chosen with ``MAIL_BACKEND``:

- ``console`` — prints the message (development default);
- ``memory`` — appends to :data:`OUTBOX` (tests assert against it);
- ``smtp`` — sends over SMTP;
- ``api`` — sends through a provider's HTTPS API (Resend or Brevo).

``api`` is the one to reach for first. SMTP ports are the first thing blocked —
by office networks, by proxies, by most free hosting tiers — and a send that
fails there fails silently late, at the worst moment. An HTTPS call goes
through anything that can already reach the internet, and every provider with
a free plan offers one.

SMTP is blocking ``smtplib`` pushed onto a worker thread, so the event loop
never waits on the conversation; the HTTPS path is async already.
"""

from __future__ import annotations

import base64
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

import anyio
import httpx

from app.core.config import get_settings
from app.core.logging import log

#: Headers that mark the message as machine-generated, so mail systems do not
#: fire autoresponders at a mailbox nobody reads.
NO_REPLY_HEADERS = {
    "Auto-Submitted": "auto-generated",
    "X-Auto-Response-Suppress": "All",
}

_API_ENDPOINTS = {
    "resend": "https://api.resend.com",
    "brevo": "https://api.brevo.com",
}


@dataclass
class Attachment:
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass
class Email:
    to: str
    subject: str
    text: str
    attachments: list[Attachment] = field(default_factory=list)


#: Messages captured by the ``memory`` backend. Cleared by tests.
OUTBOX: list[Email] = []


def build_message(email: Email) -> EmailMessage:
    settings = get_settings()
    msg = EmailMessage()
    msg["From"] = formataddr((settings.mail_from_name, settings.mail_from))
    msg["To"] = email.to
    msg["Subject"] = email.subject
    msg["Message-ID"] = make_msgid()
    # No-reply hygiene: discourage autoresponders and make the intent explicit
    # to mail clients that surface it.
    for header, value in NO_REPLY_HEADERS.items():
        msg[header] = value
    msg.set_content(email.text)
    for att in email.attachments:
        maintype, _, subtype = att.content_type.partition("/")
        msg.add_attachment(
            att.content,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=att.filename,
        )
    return msg


def _send_smtp(msg: EmailMessage) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        raise RuntimeError("SMTP_HOST is not configured but MAIL_BACKEND=smtp")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


class MailDeliveryError(RuntimeError):
    """The provider refused the message.

    Carries the provider's own words: "domain not verified", "sender not
    allowed", an expired key. Those are the failures that actually happen, and
    guessing at them from a generic error wastes an afternoon.
    """


def _api_payload(email: Email, provider: str) -> tuple[str, dict[str, str], dict]:
    """(path, headers, json body) for the provider's send endpoint."""
    settings = get_settings()
    key = settings.mail_api_key or ""
    sender_name, sender_addr = settings.mail_from_name, settings.mail_from

    if provider == "resend":
        body: dict = {
            "from": formataddr((sender_name, sender_addr)),
            "to": [email.to],
            "subject": email.subject,
            "text": email.text,
            "headers": dict(NO_REPLY_HEADERS),
        }
        if email.attachments:
            body["attachments"] = [
                {
                    "filename": a.filename,
                    "content": base64.b64encode(a.content).decode(),
                }
                for a in email.attachments
            ]
        return "/emails", {"Authorization": f"Bearer {key}"}, body

    body = {
        "sender": {"name": sender_name, "email": sender_addr},
        "to": [{"email": email.to}],
        "subject": email.subject,
        "textContent": email.text,
        "headers": dict(NO_REPLY_HEADERS),
    }
    if email.attachments:
        body["attachment"] = [
            {"name": a.filename, "content": base64.b64encode(a.content).decode()}
            for a in email.attachments
        ]
    return "/v3/smtp/email", {"api-key": key}, body


async def _send_api(email: Email) -> None:
    settings = get_settings()
    provider = settings.mail_api_provider
    if not settings.mail_api_key:
        raise MailDeliveryError("MAIL_API_KEY is not set but MAIL_BACKEND=api")

    base = settings.mail_api_base_url or _API_ENDPOINTS[provider]
    path, headers, body = _api_payload(email, provider)
    headers["Content-Type"] = "application/json"

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(base.rstrip("/") + path, headers=headers, json=body)

    if response.status_code >= 400:
        raise MailDeliveryError(
            f"{provider} refused the message ({response.status_code}): {response.text[:400]}"
        )


async def send(email: Email) -> None:
    """Deliver ``email`` through the configured backend."""
    settings = get_settings()
    backend = settings.mail_backend
    if backend == "memory":
        OUTBOX.append(email)
        return
    if backend == "console":
        log.info(
            "mail.console",
            to=email.to,
            subject=email.subject,
            attachments=[a.filename for a in email.attachments],
        )
        print(f"\n--- mail to {email.to} ---\n{email.subject}\n\n{email.text}\n---\n")
        return
    if backend == "api":
        await _send_api(email)
    else:
        await anyio.to_thread.run_sync(_send_smtp, build_message(email))
    log.info("mail.sent", backend=backend, to=email.to, subject=email.subject)
