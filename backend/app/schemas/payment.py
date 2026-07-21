from pydantic import BaseModel


class BankDetailsOut(BaseModel):
    """Bank-transfer coordinates the client shows on the Support screen."""

    beneficiary: str
    iban: str
    bic: str | None = None
    transfer_note: str | None = None
