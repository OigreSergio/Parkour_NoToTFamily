import enum
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.profile import CertificationStatus, ExperienceBand, PractitionerType
from app.schemas.legal import LegalDocumentOut


class OnboardingStep(str, enum.Enum):
    """The next question the app has to ask.

    The order is the same for everyone. The one branch is the instructor
    question, which only an adult account is asked (a certificate issued by a
    national body to a minor is not a thing, and mailing a minor's identity
    document to a review inbox is not something worth building).
    """

    birth_date = "birth_date"
    practitioner_type = "practitioner_type"
    experience = "experience"
    instructor_certificate = "instructor_certificate"
    experience_quiz = "experience_quiz"
    done = "done"


class Option(BaseModel):
    """A choice, labelled by the server so clients never hardcode the wording."""

    value: str
    label: str


class BirthDateRequest(BaseModel):
    birth_date: date


class PractitionerTypeRequest(BaseModel):
    practitioner_type: PractitionerType


class ExperienceRequest(BaseModel):
    experience_band: ExperienceBand


class OnboardingState(BaseModel):
    """Everything the client needs to draw the current onboarding screen."""

    next_step: OnboardingStep
    completed: bool
    #: Options for `practitioner_type`, empty when the step does not apply.
    practitioner_options: list[Option] = []
    #: Options for `experience`, in the order they must be shown.
    experience_options: list[Option] = []
    #: Notices this account still has to accept, at their current version.
    pending_documents: list[LegalDocumentOut] = []


class ProfileOut(BaseModel):
    """The profile as the app is allowed to see it.

    Deliberately absent: ``birth_date``, anything derived from it, and the
    content ceiling itself. A client that cannot know a member is a minor
    cannot draw a "safe mode" badge, grey out a section, or word an empty
    state differently — which is the whole point. The filtering happens
    server-side, in ``app.services.access_policy``.
    """

    model_config = ConfigDict(from_attributes=True)

    display_name: str
    email: str | None
    practitioner_type: PractitionerType | None = None
    experience_band: ExperienceBand | None = None
    #: Set once the vault game has been played.
    verified_band: ExperienceBand | None = None
    instructor_status: CertificationStatus | None = None
    onboarding_completed: bool = False


class InstructorCertificationOut(BaseModel):
    id: UUID
    issuing_body: str
    status: CertificationStatus
    submitted_at: datetime
    rejection_reason: str | None = None
    #: Mailbox the dossier was forwarded to, so the member knows where it went.
    forwarded_to: str | None = None


# --- vault mini-game ---------------------------------------------------------


class QuizQuestionOut(BaseModel):
    #: Position in the run; answers are sent back in this order.
    index: int
    clue: str
    media_url: str | None = None
    options: list[str]


class QuizOut(BaseModel):
    attempt_id: UUID
    title: str
    intro: str
    questions: list[QuizQuestionOut]
    #: Share of correct answers needed to confirm the declared experience.
    pass_ratio: float


class QuizAnswersRequest(BaseModel):
    attempt_id: UUID
    #: One entry per question, in the order they were served. `null` = skipped.
    answers: list[int | None] = Field(max_length=50)


class QuizCorrection(BaseModel):
    index: int
    correct_answer: str
    given_answer: str | None
    is_correct: bool


class QuizResultOut(BaseModel):
    score: int
    total: int
    passed: bool
    #: The band that now applies. Lower than the declared one on a bad run.
    granted_band: ExperienceBand | None
    #: True when the run lowered what had been declared.
    adjusted: bool
    #: False on every run after the first: the level was settled then and does
    #: not move again. Later runs are played for their own sake.
    counts_towards_level: bool = True
    corrections: list[QuizCorrection]
    message: str
