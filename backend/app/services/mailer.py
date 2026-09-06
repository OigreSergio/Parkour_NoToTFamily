"""Outbound email.

Every message the platform sends is automated and comes from a **no-reply**
address: nobody reads the mailbox behind ``MAIL_FROM``. The body therefore
always names the mailbox that *is* read (the one that reviews spots and
instructor dossiers), and the headers tell well-behaved mail systems not to
generate autoresponders or out-of-office replies against it.

Three backends, chosen with ``MAIL_BACKEND``:

- ``console`` — prints the message (development default);
- ``memory`` — appends to :data:`OUTBOX` (tests assert against it);
- ``smtp`` — sends for real. Required in production.

Sending is blocking ``smtplib`` pushed onto a worker thread, so the event loop
never waits on the SMTP conversation.
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

import anyio

from app.core.config import get_settings
from app.core.logging import log


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
    msg["Auto-Submitted"] = "auto-generated"
    msg["X-Auto-Response-Suppress"] = "All"
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
    msg = build_message(email)
    await anyio.to_thread.run_sync(_send_smtp, msg)
    log.info("mail.sent", to=email.to, subject=email.subject)
