"""Versioned legal notices shown by every client as blocking pop-ups.

The texts live in code (not in the database) so that a change is a reviewable
commit: each document carries a ``version`` that is bumped whenever the wording
changes, and acceptances are stored per (user, document_id, version). When a
document is bumped the client shows it again — an acceptance of v1 never counts
as an acceptance of v2.

Wording is Italian because that is the language of the audience and of the law
the platform operates under. See ``docs/LEGALE.md`` for the rationale, the
limits of what an exclusion clause can do under Italian law, and the note that
these texts are a drafted starting point to be reviewed by a lawyer before the
public launch.
"""

from app.legal.documents import (
    DOCUMENTS,
    LIABILITY_WAIVER,
    MINOR_GUARDIAN,
    SPOT_RISK,
    TUTORIAL_RISK,
    LegalDocument,
    Trigger,
    documents_for,
    get_document,
    latest_version,
    required_document_ids,
)

__all__ = [
    "DOCUMENTS",
    "LIABILITY_WAIVER",
    "MINOR_GUARDIAN",
    "SPOT_RISK",
    "TUTORIAL_RISK",
    "LegalDocument",
    "Trigger",
    "documents_for",
    "get_document",
    "latest_version",
    "required_document_ids",
]
