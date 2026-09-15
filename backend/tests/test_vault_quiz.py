import random

from app.data.vaults import BY_SLUG, VAULTS
from app.models.profile import ExperienceBand
from app.services import quiz_service
from app.services.access_policy import BAND_ORDER


def _rng() -> random.Random:
    # Seeded on purpose: the game must be reproducible in a test.
    return random.Random(20260906)  # noqa: S311


def _answer_all(questions: list[quiz_service.Question], correct: int) -> list[int | None]:
    """Answer the first ``correct`` questions right and the rest wrong."""
    answers: list[int | None] = []
    for i, q in enumerate(questions):
        right = q.answer_index
        answers.append(right if i < correct else (right + 1) % len(q.options))
    return answers


def test_catalogue_is_coherent() -> None:
    assert len({v.slug for v in VAULTS}) == len(VAULTS)
    assert len({v.name for v in VAULTS}) == len(VAULTS)  # options must be distinguishable
    assert {v.tier for v in VAULTS} == {1, 2, 3}
    assert all(v.clue.strip() for v in VAULTS)


def test_every_question_has_four_distinct_options_and_one_right_answer() -> None:
    questions = quiz_service.build_questions(ExperienceBand.over_5_years, rng=_rng())
    assert len(questions) == quiz_service.QUESTION_COUNT
    for q in questions:
        assert len(q.options) == quiz_service.OPTIONS_PER_QUESTION
        assert len(set(q.options)) == len(q.options)
        assert BY_SLUG[q.slug].name in q.options


def test_beginners_are_only_asked_the_first_vocabulary() -> None:
    questions = quiz_service.build_questions(ExperienceBand.less_than_month, rng=_rng())
    assert all(BY_SLUG[q.slug].tier == 1 for q in questions)


def test_a_long_claim_is_always_probed_at_the_deepest_tier() -> None:
    # Otherwise a ten-year claim could be confirmed on safety vaults alone.
    for seed in range(20):
        questions = quiz_service.build_questions(
            ExperienceBand.over_10_years,
            rng=random.Random(seed),  # noqa: S311
        )
        assert any(BY_SLUG[q.slug].tier == 3 for q in questions)


def test_grading_counts_only_right_answers() -> None:
    questions = quiz_service.build_questions(ExperienceBand.one_year, rng=_rng())
    assert quiz_service.grade(questions, _answer_all(questions, len(questions))) == len(questions)
    assert quiz_service.grade(questions, _answer_all(questions, 0)) == 0
    # Skipped and out-of-range answers are wrong, not crashes.
    assert quiz_service.grade(questions, []) == 0
    assert quiz_service.grade(questions, [None] * len(questions)) == 0
    assert quiz_service.grade(questions, [99] * len(questions)) == 0


def test_a_clean_run_confirms_the_declared_experience() -> None:
    claimed = ExperienceBand.over_5_years
    assert quiz_service.resolve_band(claimed, 6, 6) is claimed
    assert quiz_service.resolve_band(claimed, 5, 6) is claimed  # 83% >= 70%


def test_a_failed_run_always_costs_at_least_one_band() -> None:
    claimed = ExperienceBand.over_10_years
    granted = quiz_service.resolve_band(claimed, 4, 6)  # 67%, just short
    assert granted is not None
    assert BAND_ORDER.index(granted) < BAND_ORDER.index(claimed)


def test_a_failed_run_never_drops_below_the_first_band() -> None:
    for claimed in BAND_ORDER:
        granted = quiz_service.resolve_band(claimed, 0, 6)
        assert granted in BAND_ORDER
        assert BAND_ORDER.index(granted) >= 0
    assert quiz_service.resolve_band(BAND_ORDER[0], 0, 6) is BAND_ORDER[0]


def test_without_a_declaration_the_game_alone_cannot_unlock_the_top() -> None:
    granted = quiz_service.resolve_band(None, 6, 6)
    assert granted is ExperienceBand.one_year
    assert quiz_service.resolve_band(None, 0, 6) is ExperienceBand.less_than_month


def test_answer_key_survives_a_round_trip_through_the_database() -> None:
    questions = quiz_service.build_questions(ExperienceBand.couple_years, rng=_rng())
    restored = quiz_service.from_payload(quiz_service.to_payload(questions))
    assert [q.slug for q in restored] == [q.slug for q in questions]
    assert [q.options for q in restored] == [q.options for q in questions]
    assert [q.answer_index for q in restored] == [q.answer_index for q in questions]
