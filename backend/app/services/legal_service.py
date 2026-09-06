"""Recording that a notice was actually put in front of someone.

Acceptance is stored per (user, document, version). Bumping a document's
version in ``app.legal`` therefore invalidates nothing retroactively — it just
means the pop-up comes back, and the new acceptance is a new row. The old row
stays: it is the evidence of what that person agreed to, at the time.
"""

from __future__ import annotations

import ipaddress
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationFailed
from app.legal import DOCUMENTS, LegalDocument, get_document, required_document_ids
from app.models.profile import LegalAcceptance
from app.repositories import profiles as profiles_repo
from app.schemas.legal import AcceptedDocument

#: Truncation applied before an address is stored: enough to corroborate an
#: acceptance, not enough to track anyone around.
_IPV4_PREFIX = 24
_IPV6_PREFIX = 48


def anonymise_ip(raw: str | None) -> str | None:
    if not raw:
        return None
    candidate = raw.split(",")[0].strip()
    try:
        addr = ipaddress.ip_address(candidate)
    except ValueError:
        return None
    prefix = _IPV4_PREFIX if addr.version == 4 else _IPV6_PREFIX
    return str(ipaddress.ip_network(f"{addr}/{prefix}", strict=False))


def missing_required(accepted: list[AcceptedDocument], *, is_minor: bool) -> tuple[str, ...]:
    """Required notices that are absent, or offered at the wrong version."""
    seen = {a.id: a.version for a in accepted}
    missing = []
    for doc_id in required_document_ids(is_minor=is_minor):
        doc = get_document(doc_id)
        if doc is None:
            continue
        if seen.get(doc_id) != doc.version:
            missing.append(doc_id)
    return tuple(missing)


def pending_documents(acceptances: list[LegalAcceptance]) -> list[LegalDocument]:
    """Current-version notices this account has not accepted."""
    seen = {(a.document_id, a.document_version) for a in acceptances}
    return [d for d in DOCUMENTS if (d.id, d.version) not in seen]


async def record(
    session: AsyncSession,
    *,
    user_id: UUID,
    documents: list[AcceptedDocument],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> list[LegalAcceptance]:
    """Store acceptances, refusing anything that is not a current notice."""
    existing = {
        (a.document_id, a.document_version)
        for a in await profiles_repo.list_acceptances(session, user_id)
    }
    now = datetime.now(timezone.utc)
    written: list[LegalAcceptance] = []
    for item in documents:
        doc = get_document(item.id)
        if doc is None:
            raise ValidationFailed(f"unknown legal document: {item.id}")
        if item.version != doc.version:
            raise ValidationFailed(
                f"{item.id} was accepted at version {item.version}, "
                f"current version is {doc.version}"
            )
        if (doc.id, doc.version) in existing:
            continue
        row = LegalAcceptance(
            user_id=user_id,
            document_id=doc.id,
            document_version=doc.version,
            accepted_at=now,
            ip_address=anonymise_ip(ip_address),
            user_agent=(user_agent or None) and user_agent[:255],
        )
        session.add(row)
        written.append(row)
    await session.flush()
    return written
