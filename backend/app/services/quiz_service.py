"""The vault-naming game that verifies a declared experience.

Someone says they have been training for five years, and the app immediately
opens the harder levels for them — that is the point of asking. The game is
what keeps the claim honest: a handful of movements described the way a traceur
would describe them, four names each, one right. Knowing that vocabulary is a
decent proxy for time actually spent in the discipline, and a poor one for
anything else — it cannot be gamed by watching a single video, and it does not
ask anyone to jump off anything to prove a point.

Failing is not a punishment: the ceiling simply drops to the band the score
supports, and the game can be played again later.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.data.vaults import BY_SLUG, VAULTS, Vault
from app.models.profile import ExperienceBand
from app.services.access_policy import BAND_ORDER

#: Questions per run.
QUESTION_COUNT = 6
OPTIONS_PER_QUESTION = 4
#: Share of correct answers needed to keep the declared band.
PASS_RATIO = 0.7

#: How deep into the vocabulary the questions go, per declared band.
_MAX_TIER: dict[ExperienceBand, int] = {
    ExperienceBand.less_than_month: 1,
    ExperienceBand.few_months: 1,
    ExperienceBand.six_months: 2,
    ExperienceBand.one_year: 2,
    ExperienceBand.couple_years: 3,
    ExperienceBand.over_5_years: 3,
    ExperienceBand.over_10_years: 3,
}

#: Band awarded from the score alone, when nothing was declared.
_SCORE_BAND_FLOOR = ExperienceBand.less_than_month
_SCORE_BAND_CEILING = ExperienceBand.one_year


@dataclass(frozen=True)
class Question:
    slug: str
    clue: str
    media_url: str | None
    #: Shuffled; the client answers with an index into this list.
    options: tuple[str, ...]

    @property
    def answer_index(self) -> int:
        return self.options.index(BY_SLUG[self.slug].name)


def max_tier_for(band: ExperienceBand | None) -> int:
    if band is None:
        return 2
    return _MAX_TIER[band]


def _distractors(target: Vault, pool: list[Vault], rng: random.Random) -> list[str]:
    """Plausible wrong names: same tier first, then whatever is left."""
    same_tier = [v for v in pool if v.slug != target.slug and v.tier == target.tier]
    others = [v for v in pool if v.slug != target.slug and v.tier != target.tier]
    rng.shuffle(same_tier)
    rng.shuffle(others)
    picked = (same_tier + others)[: OPTIONS_PER_QUESTION - 1]
    if len(picked) < OPTIONS_PER_QUESTION - 1:
        # Tiny pools (only possible if the catalogue shrinks) fall back to all.
        rest = [v for v in VAULTS if v.slug != target.slug and v not in picked]
        rng.shuffle(rest)
        picked += rest[: OPTIONS_PER_QUESTION - 1 - len(picked)]
    return [v.name for v in picked]


def build_questions(
    band: ExperienceBand | None,
    *,
    count: int = QUESTION_COUNT,
    rng: random.Random | None = None,
) -> list[Question]:
    """Draw ``count`` questions suited to ``band``.

    Higher claims draw from a deeper pool *and* are guaranteed at least one
    question from the deepest tier they claim — otherwise a five-year claim
    could be confirmed on nothing but safety vaults.
    """
    # Not a secret: which six vaults get asked does not need a CSPRNG, and a
    # seedable Random is what makes the game reproducible in tests.
    rng = rng or random.Random()  # noqa: S311
    max_tier = max_tier_for(band)
    pool = [v for v in VAULTS if v.tier <= max_tier]
    top = [v for v in pool if v.tier == max_tier]

    chosen: list[Vault] = []
    if top and max_tier > 1:
        chosen.append(rng.choice(top))
    remaining = [v for v in pool if v not in chosen]
    rng.shuffle(remaining)
    chosen += remaining[: max(0, count - len(chosen))]
    rng.shuffle(chosen)

    questions: list[Question] = []
    for vault in chosen[:count]:
        options = [vault.name, *_distractors(vault, pool, rng)]
        rng.shuffle(options)
        questions.append(
            Question(
                slug=vault.slug,
                clue=vault.clue,
                media_url=vault.media_url,
                options=tuple(options),
            )
        )
    return questions


def grade(questions: list[Question], answers: list[int | None]) -> int:
    """Number of correct answers. Missing or out-of-range answers count as wrong."""
    score = 0
    for i, question in enumerate(questions):
        answer = answers[i] if i < len(answers) else None
        if answer is not None and 0 <= answer < len(question.options):
            if question.options[answer] == BY_SLUG[question.slug].name:
                score += 1
    return score


def passed(score: int, total: int) -> bool:
    return total > 0 and score / total >= PASS_RATIO


def resolve_band(claimed: ExperienceBand | None, score: int, total: int) -> ExperienceBand | None:
    """The band the result actually supports.

    - Pass → the claim stands.
    - Fail → step down proportionally to the score, never below the first band.
    - No claim → the score alone can grant up to ``one_year``; beyond that the
      app needs a declaration to compare against.
    """
    if total <= 0:
        return claimed
    ratio = score / total

    if claimed is None:
        ceiling = BAND_ORDER.index(_SCORE_BAND_CEILING)
        index = min(ceiling, int(ratio * (ceiling + 1)))
        return BAND_ORDER[max(BAND_ORDER.index(_SCORE_BAND_FLOOR), index)]

    if passed(score, total):
        return claimed

    claimed_index = BAND_ORDER.index(claimed)
    # Scale the claim by how far short the run fell, and always drop at least
    # one band: a failed run never leaves the ceiling where it was.
    scaled = int(claimed_index * (ratio / PASS_RATIO))
    return BAND_ORDER[max(0, min(scaled, claimed_index - 1))]


def to_payload(questions: list[Question]) -> list[dict]:
    """Answer key for the database (never returned to a client)."""
    return [{"slug": q.slug, "options": list(q.options)} for q in questions]


def from_payload(payload: list[dict]) -> list[Question]:
    out: list[Question] = []
    for item in payload:
        vault = BY_SLUG[item["slug"]]
        out.append(
            Question(
                slug=vault.slug,
                clue=vault.clue,
                media_url=vault.media_url,
                options=tuple(item["options"]),
            )
        )
    return out
