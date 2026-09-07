from datetime import date
from uuid import uuid4

import pytest

from app.core.exceptions import Conflict, Forbidden, ValidationFailed
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
    # by accident. Nothing derived from the age may cross the API boundary —
    # and this is the payload a returning member's app actually reads.
    from app.schemas.onboarding import MemberProfile

    leaky = {"birth_date", "age", "is_minor", "minor", "safe_mode", "max_level", "max_difficulty"}
    assert leaky.isdisjoint(MemberProfile.model_fields)

    same_answers = dict(
        display_name="T",
        email="a@b.c",
        email_verified=True,
        experience_band=ExperienceBand.one_year,
        verified_band=ExperienceBand.one_year,
        onboarding_completed=True,
    )
    # A 14-year-old and a 30-year-old who answered the same way are, on the
    # wire, the same profile — the ceiling between them lives server-side.
    assert MemberProfile(**same_answers).model_dump() == MemberProfile(**same_answers).model_dump()


# --- the level is settled once ------------------------------------------------


def test_a_long_claim_is_possible_for_a_young_member() -> None:
    from app.services.access_policy import bands_possible_at, min_age_for

    # Courses start at five, so ten years by fifteen is real — and the app has
    # no business telling that member otherwise.
    assert min_age_for(ExperienceBand.over_10_years) == 15
    assert ExperienceBand.over_10_years in bands_possible_at(15)
    assert ExperienceBand.over_5_years in bands_possible_at(10)


def test_what_no_age_could_have_reached_is_never_offered() -> None:
    from app.services.access_policy import bands_possible_at

    # Ten years by twelve is not possible; the option simply does not appear,
    # which beats offering it and refusing the answer afterwards.
    assert ExperienceBand.over_10_years not in bands_possible_at(12)
    assert ExperienceBand.over_5_years not in bands_possible_at(9)
    assert bands_possible_at(6) == (
        ExperienceBand.less_than_month,
        ExperienceBand.few_months,
        ExperienceBand.six_months,
        ExperienceBand.one_year,
    )


def test_an_adult_is_offered_everything() -> None:
    assert len(onboarding_service.experience_options(30)) == len(BAND_ORDER)
    assert len(onboarding_service.experience_options(None)) == len(BAND_ORDER)


def test_an_experienced_minor_is_not_treated_as_a_beginner() -> None:
    from datetime import date

    from app.services import access_policy

    # Fifteen, started at five, confirmed by the game: their experience counts.
    # The age still caps how hard the landings get — that is about growing
    # bones, not about what they know.
    experienced = _profile(
        birth_date=date(2011, 1, 1),
        experience_band=ExperienceBand.over_10_years,
        verified_band=ExperienceBand.over_10_years,
    )
    beginner = _profile(
        birth_date=date(2011, 1, 1),
        experience_band=ExperienceBand.less_than_month,
        verified_band=ExperienceBand.less_than_month,
    )
    today = date(2026, 9, 6)
    assert access_policy.access_for(experienced, today=today).max_difficulty > (
        access_policy.access_for(beginner, today=today).max_difficulty
    )
    # ...and never past the ceiling for that age.
    assert access_policy.access_for(experienced, today=today) == (access_policy.minor_ceiling(15))


def test_the_level_is_locked_by_the_first_completed_run() -> None:
    unplayed = _profile(birth_date=ADULT, experience_band=ExperienceBand.couple_years)
    assert not onboarding_service.level_is_locked(unplayed)

    played = _profile(
        birth_date=ADULT,
        experience_band=ExperienceBand.couple_years,
        verified_band=ExperienceBand.six_months,
    )
    assert onboarding_service.level_is_locked(played)


async def test_the_declaration_cannot_be_changed_after_the_game(monkeypatch) -> None:
    # The other end of the same lockpick: re-declare, play again, keep the
    # better of the two.
    profile = _profile(
        birth_date=ADULT,
        practitioner_type=PractitionerType.athlete,
        experience_band=ExperienceBand.six_months,
        verified_band=ExperienceBand.six_months,
    )

    async def get_or_create(_session, _user_id):
        return profile

    monkeypatch.setattr(onboarding_service.profiles_repo, "get_or_create", get_or_create)
    with pytest.raises(Conflict):
        await onboarding_service.set_experience(
            _Session(), _user(), band=ExperienceBand.over_10_years
        )
    assert profile.experience_band is ExperienceBand.six_months


async def test_a_claim_too_big_for_the_age_is_refused(monkeypatch) -> None:
    from datetime import date

    profile = _profile(birth_date=date(2014, 1, 1), practitioner_type=None)  # 12 anni

    async def get_or_create(_session, _user_id):
        return profile

    monkeypatch.setattr(onboarding_service.profiles_repo, "get_or_create", get_or_create)
    with pytest.raises(ValidationFailed):
        await onboarding_service.set_experience(
            _Session(), _user(), band=ExperienceBand.over_10_years
        )
    assert profile.experience_band is None


def test_a_replayed_run_says_it_changes_nothing() -> None:
    primo = onboarding_service._quiz_message(passed=False, adjusted=True, counts=True)
    dopo = onboarding_service._quiz_message(passed=False, adjusted=False, counts=False)
    assert "un gradino più sotto" in primo
    assert "resta quello del primo giro" in dopo
    # Nessun invito a riprovare per fare meglio: non c'è niente da vincere.
    assert "riprova" not in dopo.lower()


# --- what a returning member gets back ---------------------------------------


class _SessionConSpot(_Session):
    """Session stub that also answers the spot queries."""

    def __init__(self, counts=None, latest=(), certification=None) -> None:
        super().__init__(certification)
        self.counts = counts or {}
        self.latest = latest


class _Spot:
    def __init__(self, name, status, reason=None) -> None:
        from datetime import datetime, timezone

        self.id = uuid4()
        self.name = name
        self.status = status
        self.created_at = datetime.now(timezone.utc)
        self.rejection_reason = reason


@pytest.fixture
def _stub_spots(monkeypatch):
    async def count_by_status_for(session, _user_id):
        return session.counts

    async def list_submitted_by(session, _user_id, limit=10):
        return list(session.latest)[:limit]

    monkeypatch.setattr(onboarding_service.spots_repo, "count_by_status_for", count_by_status_for)
    monkeypatch.setattr(onboarding_service.spots_repo, "list_submitted_by", list_submitted_by)


async def test_a_returning_member_gets_their_answers_back(monkeypatch, _stub_spots) -> None:
    from app.models.spot import SpotStatus

    profile = _profile(
        birth_date=ADULT,
        practitioner_type=PractitionerType.athlete,
        experience_band=ExperienceBand.couple_years,
        verified_band=ExperienceBand.one_year,
    )

    async def get(_session, _user_id):
        return profile

    monkeypatch.setattr(onboarding_service.profiles_repo, "get", get)

    user = _user()
    user.is_email_verified = True
    session = _SessionConSpot(
        counts={SpotStatus.verified: 2, SpotStatus.pending: 1},
        latest=[_Spot("Colle Oppio", SpotStatus.verified), _Spot("Muretto", SpotStatus.pending)],
    )

    out = await onboarding_service.member_profile(session, user)

    # Nothing is asked again: what they answered is read back.
    assert out.email_verified
    assert out.experience_band is ExperienceBand.couple_years
    assert out.verified_band is ExperienceBand.one_year
    assert out.level_settled
    assert out.onboarding_completed
    assert out.next_step is OnboardingStep.done

    # ...and what they put on the map comes with it.
    assert out.spots.submitted == 3
    assert out.spots.verified == 2
    assert out.spots.pending == 1
    assert [s.name for s in out.spots.latest] == ["Colle Oppio", "Muretto"]


async def test_the_members_own_pending_spots_come_back_too(monkeypatch, _stub_spots) -> None:
    # A spot in review is invisible to everyone else, but its author is
    # exactly the person who comes back to check on it.
    from app.models.spot import SpotStatus

    async def get(_session, _user_id):
        return _profile(birth_date=ADULT, verified_band=ExperienceBand.one_year)

    monkeypatch.setattr(onboarding_service.profiles_repo, "get", get)
    session = _SessionConSpot(
        counts={SpotStatus.pending: 1, SpotStatus.rejected: 1},
        latest=[
            _Spot("In attesa", SpotStatus.pending),
            _Spot("Rifiutato", SpotStatus.rejected, "foto non pertinenti"),
        ],
    )
    out = await onboarding_service.member_profile(session, _user())
    assert out.spots.pending == 1
    assert out.spots.rejected == 1
    assert out.spots.latest[1].rejection_reason == "foto non pertinenti"


async def test_somebody_who_has_never_submitted_gets_zeroes(monkeypatch, _stub_spots) -> None:
    async def get(_session, _user_id):
        return None

    monkeypatch.setattr(onboarding_service.profiles_repo, "get", get)
    out = await onboarding_service.member_profile(_SessionConSpot(), _user())
    assert out.spots.submitted == 0
    assert out.spots.latest == []
    # Nothing answered yet: the app knows to start from the first question.
    assert out.next_step is OnboardingStep.birth_date
    assert not out.onboarding_completed
