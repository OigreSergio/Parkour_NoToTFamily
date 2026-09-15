"""Anonymous accounts: same questions, no identity, their own key."""

import re
from datetime import date
from uuid import uuid4

import pytest

from app.core.exceptions import Forbidden, ValidationFailed
from app.data import guest_names
from app.legal import LIABILITY_WAIVER
from app.models.profile import ExperienceBand, PractitionerType, UserProfile
from app.models.user import User
from app.schemas.auth import GuestLoginRequest
from app.schemas.legal import AcceptedDocument
from app.schemas.onboarding import OnboardingStep
from app.services import auth_service, onboarding_service

ADULT = date(1998, 4, 12)
MINOR = date(2012, 4, 12)


class _Session:
    """Stand-in for the DB. `next_step` only reads the last dossier."""

    certification = None


@pytest.fixture(autouse=True)
def _stub_repo(monkeypatch):
    async def latest_certification(session, _user_id):
        return session.certification

    monkeypatch.setattr(
        onboarding_service.profiles_repo, "latest_certification", latest_certification
    )


def _guest(**kwargs) -> User:
    return User(id=uuid4(), email=None, display_name="Muretto-7K4Q", is_guest=True, **kwargs)


def _member() -> User:
    return User(id=uuid4(), email="a@b.c", display_name="T", is_guest=False)


def _profile(**kwargs) -> UserProfile:
    return UserProfile(user_id=uuid4(), **kwargs)


# --- the generated name ------------------------------------------------------


def test_generated_names_read_like_a_name() -> None:
    for _ in range(50):
        name = guest_names.generate()
        assert re.fullmatch(r"[A-Za-z]+-[2-9A-HJ-NP-Z]{4}", name), name
        # No 0/O or 1/I: these get read aloud at a spot and typed by hand.
        assert not set("01OI") & set(name.split("-")[1])


def test_generated_names_rarely_collide() -> None:
    names = {guest_names.generate() for _ in range(3000)}
    assert len(names) > 2950  # 20 words x 32^4 leaves plenty of room


def test_a_longer_suffix_is_available_when_the_short_one_is_crowded() -> None:
    assert re.fullmatch(r"[A-Za-z]+-[2-9A-HJ-NP-Z]{8}", guest_names.generate(suffix_length=8))


# --- the key that makes progress survive -------------------------------------


def test_every_guest_key_is_distinct_and_recognisable() -> None:
    keys = {auth_service.generate_guest_key() for _ in range(500)}
    assert len(keys) == 500
    assert all(k.startswith(auth_service.GUEST_KEY_PREFIX) for k in keys)


def test_only_a_digest_of_the_key_is_stored() -> None:
    key = auth_service.generate_guest_key()
    digest = auth_service.hash_guest_key(key)
    assert key not in digest
    assert len(digest) == 64
    assert auth_service.hash_guest_key(key) == digest  # deterministic: it is the lookup


def test_two_guests_can_never_share_an_account() -> None:
    a, b = auth_service.generate_guest_key(), auth_service.generate_guest_key()
    assert auth_service.hash_guest_key(a) != auth_service.hash_guest_key(b)


async def test_a_guest_account_needs_the_risk_notice_too() -> None:
    # A guest sees the same spots and the same tutorials, so they take the same
    # risk. The check runs before anything touches the database.
    with pytest.raises(ValidationFailed):
        await auth_service.login_guest(None, GuestLoginRequest())


def test_the_notice_a_guest_has_to_accept_is_the_same_one() -> None:
    from app.legal import required_document_ids
    from app.services import legal_service

    # Not a guest-specific waiver: literally the same document, at the same
    # version, that a registered account has to accept.
    assert required_document_ids(is_minor=False) == (LIABILITY_WAIVER.id,)
    accepted = [AcceptedDocument(id=LIABILITY_WAIVER.id, version=LIABILITY_WAIVER.version)]
    assert legal_service.missing_required(accepted, is_minor=False) == ()


# --- the questions -----------------------------------------------------------


async def test_a_guest_is_asked_the_date_of_birth_like_everyone_else() -> None:
    step = await onboarding_service.next_step(_Session(), _guest(), _profile())
    assert step is OnboardingStep.birth_date


async def test_an_adult_guest_is_never_asked_athlete_or_instructor() -> None:
    guest = _guest()
    profile = _profile(birth_date=ADULT, practitioner_type=PractitionerType.athlete)
    assert await onboarding_service.next_step(_Session(), guest, profile) is (
        OnboardingStep.experience
    )

    # ...while the same profile on a registered account does get asked.
    member_profile = _profile(birth_date=ADULT)
    assert await onboarding_service.next_step(_Session(), _member(), member_profile) is (
        OnboardingStep.practitioner_type
    )


async def test_a_guest_with_no_type_on_file_still_skips_the_question() -> None:
    # Guest rows created before the key migration have no practitioner_type.
    step = await onboarding_service.next_step(_Session(), _guest(), _profile(birth_date=ADULT))
    assert step is OnboardingStep.experience


async def test_guests_walk_the_experience_and_the_game_like_everyone_else() -> None:
    session, guest = _Session(), _guest()
    profile = _profile(birth_date=ADULT, practitioner_type=PractitionerType.athlete)

    assert await onboarding_service.next_step(session, guest, profile) is (
        OnboardingStep.experience
    )
    profile.experience_band = ExperienceBand.couple_years
    assert await onboarding_service.next_step(session, guest, profile) is (
        OnboardingStep.experience_quiz
    )
    profile.verified_band = ExperienceBand.couple_years
    assert await onboarding_service.next_step(session, guest, profile) is OnboardingStep.done


async def test_an_adult_and_a_minor_guest_see_the_same_screens() -> None:
    session, guest = _Session(), _guest()
    adult = _profile(birth_date=ADULT, practitioner_type=PractitionerType.athlete)
    minor = _profile(birth_date=MINOR, practitioner_type=PractitionerType.athlete)
    assert await onboarding_service.next_step(session, guest, adult) is (
        await onboarding_service.next_step(session, guest, minor)
    )


# --- the branch a guest cannot take ------------------------------------------


async def test_a_guest_cannot_declare_themselves_an_instructor(monkeypatch) -> None:
    profile = _profile(birth_date=ADULT)

    async def get_or_create(_session, _user_id):
        return profile

    monkeypatch.setattr(onboarding_service.profiles_repo, "get_or_create", get_or_create)
    with pytest.raises(Forbidden):
        await onboarding_service.set_practitioner_type(
            _Session(), _guest(), practitioner_type=PractitionerType.instructor
        )
    # Not even as an athlete: the question does not exist for a guest.
    with pytest.raises(Forbidden):
        await onboarding_service.set_practitioner_type(
            _Session(), _guest(), practitioner_type=PractitionerType.athlete
        )
    assert profile.practitioner_type is None


async def test_a_guest_cannot_submit_a_certificate(monkeypatch) -> None:
    profile = _profile(birth_date=ADULT, practitioner_type=PractitionerType.instructor)

    async def get_or_create(_session, _user_id):
        return profile

    monkeypatch.setattr(onboarding_service.profiles_repo, "get_or_create", get_or_create)
    with pytest.raises(Forbidden):
        await onboarding_service.submit_instructor_certificate(
            _Session(),
            _guest(),
            issuing_body="FIGeST",
            certificate_filename="c.pdf",
            certificate_content=b"%PDF",
            certificate_content_type="application/pdf",
            identity_filename="d.pdf",
            identity_content=b"%PDF",
            identity_content_type="application/pdf",
        )
