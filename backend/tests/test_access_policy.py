from datetime import date
from itertools import pairwise
from uuid import uuid4

from app.models.profile import ExperienceBand, PractitionerType, UserProfile
from app.models.video import TrickCategory, Video, VideoCategory, VideoLevel
from app.services import access_policy
from app.services.access_policy import BAND_ORDER, LEVEL_ORDER, ContentAccess

TODAY = date(2026, 9, 6)


def _profile(
    *,
    birth_date: date | None = None,
    band: ExperienceBand | None = None,
    verified: ExperienceBand | None = None,
    practitioner: PractitionerType | None = None,
) -> UserProfile:
    return UserProfile(
        user_id=uuid4(),
        birth_date=birth_date,
        experience_band=band,
        verified_band=verified,
        practitioner_type=practitioner,
    )


def _video(level: VideoLevel, difficulty: int) -> Video:
    return Video(
        id=uuid4(),
        title="Kong",
        description="",
        url="https://videos.example/kong.mp4",
        category=VideoCategory.practice,
        level=level,
        trick_category=TrickCategory.vaults,
        difficulty=difficulty,
        duration_seconds=90,
    )


# --- age ---------------------------------------------------------------------


def test_age_counts_completed_years() -> None:
    assert access_policy.age_on(date(2008, 9, 6), TODAY) == 18
    assert access_policy.age_on(date(2008, 9, 7), TODAY) == 17  # birthday tomorrow
    assert access_policy.age_on(date(2008, 9, 5), TODAY) == 18


def test_adulthood_starts_on_the_eighteenth_birthday() -> None:
    assert not access_policy.is_minor(date(2008, 9, 6), TODAY)
    assert access_policy.is_minor(date(2008, 9, 7), TODAY)


# --- ceilings ----------------------------------------------------------------


def test_no_minor_ceiling_ever_reaches_advanced() -> None:
    for age in range(5, 18):
        assert access_policy.minor_ceiling(age).max_level is not VideoLevel.advanced


def test_minor_ceilings_do_not_go_down_with_age() -> None:
    ceilings = [access_policy.minor_ceiling(age) for age in range(5, 18)]
    for a, b in pairwise(ceilings):
        assert LEVEL_ORDER.index(a.max_level) <= LEVEL_ORDER.index(b.max_level)
        assert a.max_difficulty <= b.max_difficulty


def test_band_ceilings_never_go_down_with_experience() -> None:
    ladder = [access_policy.band_access(b) for b in BAND_ORDER]
    for a, b in pairwise(ladder):
        assert LEVEL_ORDER.index(a.max_level) <= LEVEL_ORDER.index(b.max_level)
        assert a.max_difficulty <= b.max_difficulty


def test_experience_opens_harder_levels() -> None:
    beginner = access_policy.band_access(ExperienceBand.less_than_month)
    veteran = access_policy.band_access(ExperienceBand.over_5_years)
    assert not beginner.allows(level=VideoLevel.advanced, difficulty=9)
    assert veteran.allows(level=VideoLevel.advanced, difficulty=10)


# --- how the two combine -----------------------------------------------------


def test_age_ceiling_wins_over_any_claim() -> None:
    # A 15-year-old who says they have trained for ten years still does not get
    # advanced content: the age ceiling is not negotiable by answering.
    access = access_policy.access_for(
        _profile(birth_date=date(2011, 1, 1), band=ExperienceBand.over_10_years),
        today=TODAY,
    )
    assert access.max_level is VideoLevel.intermediate
    assert access.max_difficulty == 4


def test_adult_athlete_gets_the_band_ceiling() -> None:
    access = access_policy.access_for(
        _profile(birth_date=date(1998, 1, 1), band=ExperienceBand.couple_years),
        today=TODAY,
    )
    assert access == ContentAccess(VideoLevel.advanced, 8)


def test_quiz_result_overrides_the_declaration() -> None:
    profile = _profile(
        birth_date=date(1998, 1, 1),
        band=ExperienceBand.over_10_years,
        verified=ExperienceBand.six_months,
    )
    assert access_policy.effective_band(profile) is ExperienceBand.six_months
    assert access_policy.access_for(profile, today=TODAY).max_level is VideoLevel.intermediate


def test_approved_instructor_has_no_experience_ceiling() -> None:
    profile = _profile(birth_date=date(1990, 1, 1), practitioner=PractitionerType.instructor)
    assert (
        access_policy.access_for(profile, today=TODAY, instructor_approved=True)
        == access_policy.FULL_ACCESS
    )
    # Claiming it is not enough — the certificate has to have been approved.
    assert (
        access_policy.access_for(profile, today=TODAY, instructor_approved=False)
        == access_policy.DEFAULT_ACCESS
    )


def test_no_profile_falls_back_to_the_safest_default() -> None:
    assert access_policy.access_for(None, today=TODAY) == access_policy.DEFAULT_ACCESS


def test_is_within_filters_on_both_level_and_difficulty() -> None:
    access = ContentAccess(VideoLevel.intermediate, 4)
    assert access_policy.is_within(_video(VideoLevel.beginner, 3), access)
    assert access_policy.is_within(_video(VideoLevel.intermediate, 4), access)
    # Right level, too hard.
    assert not access_policy.is_within(_video(VideoLevel.intermediate, 7), access)
    # Easy for its level, but the level itself is out of reach.
    assert not access_policy.is_within(_video(VideoLevel.advanced, 1), access)
