import pytest

from app.core.exceptions import ValidationFailed
from app.legal import LIABILITY_WAIVER
from app.schemas.auth import EmailCodeVerifyRequest
from app.schemas.legal import AcceptedDocument
from app.services import email_verification_service as codes
from app.services import legal_service, mailer
from app.services.mailer import Email

EMAIL = "traceur@example.com"


def test_code_is_six_digits_drawn_fresh() -> None:
    codes_seen = {codes.generate_code() for _ in range(200)}
    assert all(len(c) == codes.CODE_DIGITS and c.isdigit() for c in codes_seen)
    # Not a constant, and not a counter.
    assert len(codes_seen) > 100


def test_only_the_hmac_is_ever_stored() -> None:
    code = "123456"
    digest = codes.hash_code(EMAIL, code)
    assert code not in digest
    assert len(digest) == 64
    assert codes.hash_code(EMAIL, code) == digest  # deterministic


def test_a_code_is_bound_to_the_address_it_was_mailed_to() -> None:
    code = "123456"
    digest = codes.hash_code(EMAIL, code)
    assert codes.matches(digest, EMAIL, code)
    assert codes.matches(digest, EMAIL.upper(), code)  # case-insensitive address
    assert not codes.matches(digest, "someone.else@example.com", code)
    assert not codes.matches(digest, EMAIL, "123457")


def test_display_name_falls_back_to_the_local_part() -> None:
    assert codes._display_name_from("mario.rossi@example.com", None) == "mario.rossi"
    assert codes._display_name_from("mario.rossi@example.com", "Mario") == "Mario"
    # Never shorter than the 2 characters the schema requires.
    assert len(codes._display_name_from("a@example.com", None)) >= 2


def test_the_mail_never_invites_a_reply_and_says_who_carries_the_risk() -> None:
    body = codes._body("123456", 10)
    assert "123456" in body
    assert "non rispondere" in body
    assert "responsabilità" in body


def test_no_reply_headers_are_set() -> None:
    msg = mailer.build_message(Email(to=EMAIL, subject="s", text="t"))
    assert msg["Auto-Submitted"] == "auto-generated"
    assert msg["X-Auto-Response-Suppress"] == "All"
    assert "noreply@" in msg["From"]
    assert msg["Reply-To"] is None


# --- what has to be accepted before an account exists ------------------------


def test_signup_requires_the_liability_notice_at_its_current_version() -> None:
    assert legal_service.missing_required([], is_minor=False) == (LIABILITY_WAIVER.id,)
    accepted = [AcceptedDocument(id=LIABILITY_WAIVER.id, version=LIABILITY_WAIVER.version)]
    assert legal_service.missing_required(accepted, is_minor=False) == ()


def test_accepting_an_outdated_version_does_not_count() -> None:
    stale = [AcceptedDocument(id=LIABILITY_WAIVER.id, version=LIABILITY_WAIVER.version + 1)]
    assert legal_service.missing_required(stale, is_minor=False) == (LIABILITY_WAIVER.id,)


def test_minors_additionally_need_guardian_consent() -> None:
    accepted = [AcceptedDocument(id=LIABILITY_WAIVER.id, version=LIABILITY_WAIVER.version)]
    assert legal_service.missing_required(accepted, is_minor=True) == ("minor_guardian",)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("82.60.14.77", "82.60.14.0/24"),
        ("82.60.14.77, 10.0.0.1", "82.60.14.0/24"),
        ("not-an-ip", None),
        (None, None),
    ],
)
def test_stored_addresses_are_truncated(raw: str | None, expected: str | None) -> None:
    assert legal_service.anonymise_ip(raw) == expected


async def test_a_refused_notice_does_not_burn_the_code() -> None:
    """The notice is checked before the code is spent, and before any query.

    Passing `None` for the session is the assertion: if the check ran after
    `_consume`, this would fail on the missing database rather than raise.
    Someone who declines the notice and changes their mind must not be sent
    back to the start, a minute of rate limiting and a second email later.
    """
    with pytest.raises(ValidationFailed):
        await codes.verify_code(
            None,
            EmailCodeVerifyRequest(email=EMAIL, code="123456", accepted_documents=[]),
        )


async def test_the_notice_is_required_whether_or_not_the_account_exists() -> None:
    # Asking for it only on sign-up would make the two cases answer
    # differently, and that difference is exactly "does this address have an
    # account here" — which is what the whole flow is careful not to say.
    import inspect

    source = inspect.getsource(codes.verify_code)
    check = source.index("missing_required")
    consume = source.index("_consume(")
    assert check < consume, "the notice check must come before the code is spent"
    assert "if user is None" not in source[:check], (
        "the notice check must not sit inside the new-account branch"
    )
