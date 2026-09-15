from datetime import datetime

from pydantic import BaseModel, Field

from app.legal import LegalDocument, Trigger


class LegalDocumentOut(BaseModel):
    """A notice, ready to be rendered as a pop-up."""

    id: str
    version: int
    title: str
    summary: str
    #: Short points — what a pop-up shows without scrolling.
    bullets: list[str]
    #: The binding text (Markdown), behind "Leggi tutto".
    body: str
    trigger: Trigger
    blocking: bool
    accept_label: str
    decline_label: str

    @classmethod
    def of(cls, doc: LegalDocument) -> "LegalDocumentOut":
        return cls(
            id=doc.id,
            version=doc.version,
            title=doc.title,
            summary=doc.summary,
            bullets=list(doc.bullets),
            body=doc.body.strip(),
            trigger=doc.trigger,
            blocking=doc.blocking,
            accept_label=doc.accept_label,
            decline_label=doc.decline_label,
        )


class AcceptedDocument(BaseModel):
    """A notice the user says they have read, at the version they were shown."""

    id: str = Field(max_length=64)
    version: int = Field(ge=1)


class LegalAcceptRequest(BaseModel):
    documents: list[AcceptedDocument] = Field(min_length=1)


class LegalAcceptanceOut(BaseModel):
    document_id: str
    document_version: int
    accepted_at: datetime


class LegalStatusOut(BaseModel):
    """Which notices are settled and which still have to be shown."""

    accepted: list[LegalAcceptanceOut]
    #: Documents whose current version this account has not accepted yet.
    pending: list[LegalDocumentOut]
