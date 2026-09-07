"""What a member is allowed to be shown, and why.

Two independent things narrow the catalogue, and the narrower of the two wins:

1. **Age.** An account whose declared birth date is under 18 gets a ceiling
   that no answer, claim or quiz score can lift. This is the "safe version" —
   and it is deliberately *not a mode*: there is no banner, no badge, no
   "locked because you are 15", no second app. The catalogue simply contains
   the exercises that suit the member, exactly as it does for everyone else.
   Nothing in any API response names the ceiling or the age that produced it
   (see ``app.schemas.onboarding.ProfileOut``), so no client can render a
   difference even by accident.

2. **Experience.** An adult athlete declares how long they have been training
   and gets the matching ceiling straight away. The vault-naming game then
   *verifies* that claim: passing keeps the ceiling, failing lowers it to what
   the score supports. An instructor whose certificate has been approved has
   no experience ceiling at all.

Everything here is a pure function of a profile and a date, so the rules can be
read, tested and argued about without a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.models.profile import ExperienceBand, PractitionerType, UserProfile
from app.models.video import Video, VideoLevel

#: Ascending. Used to compare and to take the minimum of two ceilings.
LEVEL_ORDER: tuple[VideoLevel, ...] = (
    VideoLevel.beginner,
    VideoLevel.intermediate,
    VideoLevel.advanced,
)

#: Ascending. The options offered in the app, in the order they are shown.
BAND_ORDER: tuple[ExperienceBand, ...] = (
    ExperienceBand.less_than_month,
    ExperienceBand.few_months,
    ExperienceBand.six_months,
    ExperienceBand.one_year,
    ExperienceBand.couple_years,
    ExperienceBand.over_5_years,
    ExperienceBand.over_10_years,
)

ADULT_AGE = 18

#: The age the youngest courses start at. It is what makes a long claim from a
#: young member plausible instead of suspicious: someone who began at five is
#: ten years in by fifteen, and telling them otherwise would be both wrong and
#: insulting.
MIN_START_AGE = 5

#: Years of practice each band implies at minimum. Used to work out which
#: bands a given age could honestly have reached.
BAND_MIN_YEARS: dict[ExperienceBand, int] = {
    ExperienceBand.less_than_month: 0,
    ExperienceBand.few_months: 0,
    ExperienceBand.six_months: 0,
    ExperienceBand.one_year: 1,
    ExperienceBand.couple_years: 2,
    ExperienceBand.over_5_years: 5,
    ExperienceBand.over_10_years: 10,
}


def min_age_for(band: ExperienceBand) -> int:
    """The youngest someone declaring ``band`` could be."""
    return MIN_START_AGE + BAND_MIN_YEARS[band]


def bands_possible_at(age: int | None) -> tuple[ExperienceBand, ...]:
    """The bands that age could have reached, in order.

    Offering the impossible ones and then refusing them would be a worse
    experience than not offering them: nobody enjoys being told their answer
    was wrong after picking it from a list somebody else wrote.
    """
    if age is None:
        return BAND_ORDER
    return tuple(b for b in BAND_ORDER if min_age_for(b) <= age)


@dataclass(frozen=True)
class ContentAccess:
    """A ceiling: the hardest level and difficulty a member may be offered."""

    max_level: VideoLevel
    #: On the 1-10 scale of ``Video.difficulty``.
    max_difficulty: int

    def narrower_of(self, other: ContentAccess) -> ContentAccess:
        return ContentAccess(
            max_level=min(self.max_level, other.max_level, key=LEVEL_ORDER.index),
            max_difficulty=min(self.max_difficulty, other.max_difficulty),
        )

    def allows(self, *, level: VideoLevel, difficulty: int) -> bool:
        return (
            LEVEL_ORDER.index(level) <= LEVEL_ORDER.index(self.max_level)
            and difficulty <= self.max_difficulty
        )


FULL_ACCESS = ContentAccess(VideoLevel.advanced, 10)

#: Where someone lands before they have answered anything.
DEFAULT_ACCESS = ContentAccess(VideoLevel.beginner, 3)

BAND_ACCESS: dict[ExperienceBand, ContentAccess] = {
    ExperienceBand.less_than_month: ContentAccess(VideoLevel.beginner, 2),
    ExperienceBand.few_months: ContentAccess(VideoLevel.beginner, 3),
    ExperienceBand.six_months: ContentAccess(VideoLevel.intermediate, 5),
    ExperienceBand.one_year: ContentAccess(VideoLevel.intermediate, 6),
    ExperienceBand.couple_years: ContentAccess(VideoLevel.advanced, 8),
    ExperienceBand.over_5_years: ContentAccess(VideoLevel.advanced, 10),
    ExperienceBand.over_10_years: ContentAccess(VideoLevel.advanced, 10),
}

#: Age ceilings. Growth plates, not ability, set these: the impact loads of
#: advanced parkour are not something a body still growing should be pushed
#: into by an app that has never met the person.
#:
#: They are a ceiling, not a verdict on the member. A fifteen-year-old who
#: started at five has trained longer than most adults on the platform, and
#: their experience still counts — it just counts up to here. What the age
#: decides is how hard the landings get, not whether the person knows what
#: they are doing.
_MINOR_CEILINGS: tuple[tuple[int, ContentAccess], ...] = (
    # (max age this row applies to, ceiling)
    (11, ContentAccess(VideoLevel.beginner, 3)),
    (13, ContentAccess(VideoLevel.intermediate, 4)),
    (15, ContentAccess(VideoLevel.intermediate, 6)),
    (17, ContentAccess(VideoLevel.advanced, 8)),
)


def age_on(birth_date: date, today: date) -> int:
    """Completed years of age on ``today``."""
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def is_minor(birth_date: date, today: date) -> bool:
    return age_on(birth_date, today) < ADULT_AGE


def minor_ceiling(age: int) -> ContentAccess:
    for max_age, ceiling in _MINOR_CEILINGS:
        if age <= max_age:
            return ceiling
    return FULL_ACCESS


def band_access(band: ExperienceBand | None) -> ContentAccess:
    if band is None:
        return DEFAULT_ACCESS
    return BAND_ACCESS[band]


def effective_band(profile: UserProfile) -> ExperienceBand | None:
    """The band that counts: the verified one once the game has been played.

    Before the game, the declared band applies — the member gets the harder
    levels straight away, and the game confirms or corrects that afterwards.
    """
    return profile.verified_band or profile.experience_band


def access_for(
    profile: UserProfile | None,
    *,
    today: date,
    instructor_approved: bool = False,
) -> ContentAccess:
    """The ceiling for ``profile``. ``None`` (no onboarding yet) is the default."""
    if profile is None:
        return DEFAULT_ACCESS

    if profile.practitioner_type is PractitionerType.instructor and instructor_approved:
        access = FULL_ACCESS
    else:
        access = band_access(effective_band(profile))

    if profile.birth_date is not None:
        age = age_on(profile.birth_date, today)
        if age < ADULT_AGE:
            access = access.narrower_of(minor_ceiling(age))
    return access


def is_within(video: Video, access: ContentAccess) -> bool:
    return access.allows(level=video.level, difficulty=video.difficulty)
