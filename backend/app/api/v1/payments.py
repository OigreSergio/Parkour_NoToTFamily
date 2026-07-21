from fastapi import APIRouter

from app.core.config import get_settings
from app.core.exceptions import NotFound
from app.schemas.payment import BankDetailsOut

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/bank-details", response_model=BankDetailsOut)
async def get_bank_details() -> BankDetailsOut:
    """Bank-transfer coordinates for supporting the project.

    Sourced from PAYMENTS_* environment variables so the IBAN never lives in
    the codebase. 404 until the deployment configures them.
    """
    settings = get_settings()
    if not settings.payments_iban or not settings.payments_beneficiary:
        raise NotFound("Bank transfer details are not configured")
    return BankDetailsOut(
        beneficiary=settings.payments_beneficiary,
        iban=settings.payments_iban.replace(" ", "").upper(),
        bic=settings.payments_bic,
        transfer_note=settings.payments_transfer_note,
    )
