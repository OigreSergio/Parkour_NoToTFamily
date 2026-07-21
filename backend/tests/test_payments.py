from app.core.config import get_settings

# Example IBAN from the official IBAN registry docs — not a real account.
EXAMPLE_IBAN = "IT60X0542811101000000123456"


async def test_bank_details_404_when_not_configured(client) -> None:
    res = await client.get("/api/v1/payments/bank-details")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


async def test_bank_details_returned_when_configured(client, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "payments_beneficiary", "Mario Rossi")
    monkeypatch.setattr(settings, "payments_iban", "it60 x054 2811 1010 0000 0123 456")
    monkeypatch.setattr(settings, "payments_bic", "BPMOIT22")
    monkeypatch.setattr(settings, "payments_transfer_note", "Support the project")

    res = await client.get("/api/v1/payments/bank-details")
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "beneficiary": "Mario Rossi",
        "iban": EXAMPLE_IBAN,
        "bic": "BPMOIT22",
        "transfer_note": "Support the project",
    }
