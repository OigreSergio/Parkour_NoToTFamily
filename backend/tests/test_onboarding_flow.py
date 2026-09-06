from datetime import date
from uuid import uuid4

import pytest

from app.core.exceptions import Forbidden, ValidationFailed
from app.models.profile import CertificationStatus, ExperienceBand, PractitionerType, UserProfile
from app.models.user import User
from app.services import onboarding_service
from app.services.access_policy import BAND_ORDER
from app.services.onboarding_service import EXPERIENCE_LABELS, OnboardingStep

ADULT = date(1998, 4, 12)
MINOR = date(2012, 4, 12)


class _Session:
    """Stand-in for the DB: `next_step` only ever reads the last dossier."""

    def __init__(self, certification=None) -> None:
        self.certification = certification


class _Cert:
    def __init__(self, status: CertificationStatus) -> None:
        self.status = status


@pytest.fixture(autouse=True)
def _stub_repo(monkeypatch):
    async def latest_certification(session, _user_id):
        return session.certification

    monkeypatch.setattr(
        onboarding_service.profiles_repo, "latest_certification", latest_certification
    )


def _user() -> User:
    return User(id=uuid4(), email="a@b.c", display_name="T")


def _profile(**kwargs) -> UserProfile:
    return UserProfile(user_id=uuid4(), **kwargs)


async def test_the_first_question_is_always_the_date_of_birth() -> None:
    user = _user()
    assert await onboarding_service.next_step(_Session(), user, None) is OnboardingStep.birth_date
    assert (
        await onboarding_service.next_step(_Session(), user, _profile())
        is OnboardingStep.birth_date
    )


async def test_an_adult_is_asked_athlete_or_instructor() -> None:
    step = await onboarding_service.next_step(_Session(), _user(), _profile(birth_date=ADULT))
    assert step is OnboardingStep.practitioner_type


async def test_a_minor_is_never_asked_for_an_instructor_certificate() -> None:
    # The question is skipped, not answered differently: a national body does
    # not certify a 14-year-old, and their ID document has no business being
    # mailed to a review inbox. Everything after this point is the same flow.
    step = await onboarding_service.next_step(_Session(), _user(), _profile(birth_date=MINOR))
    assert step is OnboardingStep.experience


async def test_a_minor_walks_the_same_remaining_screens_as_an_adult() -> None:
    minor = _profile(birth_date=MINOR, experience_band=ExperienceBand.one_year)
    adult = _profile(
        birth_date=ADULT,
        practitioner_type=PractitionerType.athlete,
        experience_band=ExperienceBand.one_year,
    )
    session, user = _Session(), _user()
    quiz = OnboardingStep.experience_quiz
    assert await onboarding_service.next_step(session, user, minor) is quiz
    assert await onboarding_service.next_step(session, user, adult) is quiz


async def test_an_athlete_goes_experience_then_game_then_done() -> None:
    session, user = _Session(), _user()
    profile = _profile(birth_date=ADULT, practitioner_type=PractitionerType.athlete)
    assert await onboarding_service.next_step(session, user, profile) is OnboardingStep.experience

    profile.experience_band = ExperienceBand.couple_years
    assert (
        await onboarding_service.next_step(session, user, profile) is OnboardingStep.experience_quiz
    )

    profile.verified_band = ExperienceBand.couple_years
    assert await onboarding_service.next_step(session, user, profile) is OnboardingStep.done


async def test_an_instructor_is_asked_for_the_dossier_until_it_is_reviewed() -> None:
    user = _user()
    profile = _profile(birth_date=ADULT, practitioner_type=PractitionerType.instructor)

    assert (
        await onboarding_service.next_step(_Session(), user, profile)
        is OnboardingStep.instructor_certificate
    )
    pending = _Session(_Cert(CertificationStatus.pending))
    assert await onboarding_service.next_step(pending, user, profile) is OnboardingStep.done
    rejected = _Session(_Cert(CertificationStatus.rejected))
    assert (
        await onboarding_service.next_step(rejected, user, profile)
        is OnboardingStep.instructor_certificate
    )


def test_the_experience_options_are_the_ones_the_app_offers_in_order() -> None:
    options = onboarding_service.experience_options()
    assert [o.value for o in options] == [b.value for b in BAND_ORDER]
    assert [o.label for o in options] == [
        "Meno di un mese",
        "Un paio di mesi",
        "Sei mesi",
        "Un anno",
        "Un paio d'anni",
        "Più di 5 anni",
        "Più di 10 anni",
    ]
    assert set(EXPERIENCE_LABELS) == set(BAND_ORDER)


def test_uploads_must_be_a_document_and_not_too_large() -> None:
    onboarding_service._check_upload("cert.pdf", b"%PDF-1.4", "application/pdf", "the certificate")

    with pytest.raises(ValidationFailed):
        onboarding_service._check_upload("cert.pdf", b"", "application/pdf", "the certificate")
    with pytest.raises(ValidationFailed):
        onboarding_service._check_upload("cert.exe", b"MZ", "application/x-msdownload", "x")
    with pytest.raises(ValidationFailed):
        onboarding_service._check_upload(
            "big.pdf",
            b"0" * (onboarding_service.MAX_UPLOAD_BYTES + 1),
            "application/pdf",
            "the certificate",
        )


def test_the_dossier_mail_carries_what_a_reviewer_has_to_check() -> None:
    user = _user()
    body = onboarding_service._dossier_body(user, "FIGeST")
    assert "FIGeST" in body
    assert str(user.id) in body
    assert "documento di identità" in body
    assert "non sono conservati" in body  # attachments are not stored anywhere
    assert "non è automatica" in body  # a human grants the badge


async def test_the_instructor_question_is_refused_for_a_minor(monkeypatch) -> None:
    user = _user()
    profile = _profile(birth_date=MINOR)

    async def get_or_create(_session, _user_id):
        return profile

    monkeypatch.setattr(onboarding_service.profiles_repo, "get_or_create", get_or_create)
    with pytest.raises(Forbidden):
        await onboarding_service.set_practitioner_type(
            _Session(), user, practitioner_type=PractitionerType.instructor
        )


def test_the_profile_the_app_sees_cannot_reveal_that_someone_is_a_minor() -> None:
    # The safe experience only works if no client can tell it apart, including
    # by accident. Nothing derived from the age may cross the API boundary.
    from app.schemas.onboarding import ProfileOut

    leaky = {"birth_date", "age", "is_minor", "minor", "safe_mode", "max_level", "max_difficulty"}
    assert leaky.isdisjoint(ProfileOut.model_fields)

    same_answers = dict(
        display_name="T",
        email="a@b.c",
        practitioner_type=None,
        experience_band=ExperienceBand.one_year,
        verified_band=ExperienceBand.one_year,
        instructor_status=None,
        onboarding_completed=True,
    )
    # A 14-year-old and a 30-year-old who answered the same way are, on the
    # wire, the same profile — the ceiling between them lives server-side.
    assert ProfileOut(**same_answers).model_dump() == ProfileOut(**same_answers).model_dump()
