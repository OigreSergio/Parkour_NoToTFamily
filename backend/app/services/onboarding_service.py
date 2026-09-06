"""The questions asked after the code is verified, and what they unlock.

Order of the flow:

1. **Date of birth.** Everything downstream hangs off it. Under 18 the account
   gets the age ceiling of ``access_policy`` — the "safe version". It is not a
   separate app and not a visible mode: the same screens, the same wording, the
   same absence of any badge; only the exercises behind them differ. A minor is
   also asked to confirm a guardian's consent, because that is the one place
   where the law does not let the experience be identical.
2. **Athlete or instructor** — adults only.
3a. **Instructor**: a certificate from a nationally recognised body plus an
    identity document proving the certificate is theirs. Both are forwarded to
    the mailbox that already reviews spots, and are *not* kept on the servers.
    The badge is granted by a human, through the existing admin endpoint.
3b. **Athlete**: how long they have been training. The answer opens the
    matching levels straight away.
4. **The vault game** verifies that answer (``quiz_service``).

Minors go through 3b as well: it is what tells the app which exercises suit a
14-year-old who has trained for three years versus one who started last week —
inside the ceiling their age sets, which nothing here can lift.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import Conflict, Forbidden, NotFound, ValidationFailed
from app.legal import Trigger, documents_for
from app.models.profile import (
    CertificationStatus,
    ExperienceBand,
    ExperienceQuizAttempt,
    InstructorCertification,
    PractitionerType,
    UserProfile,
)
from app.models.user import User
from app.repositories import profiles as profiles_repo
from app.schemas.legal import AcceptedDocument, LegalDocumentOut
from app.schemas.onboarding import (
    InstructorCertificationOut,
    OnboardingState,
    OnboardingStep,
    Option,
    ProfileOut,
    QuizCorrection,
    QuizOut,
    QuizQuestionOut,
    QuizResultOut,
)
from app.services import legal_service, mailer, quiz_service
from app.services.access_policy import ADULT_AGE, BAND_ORDER, age_on
from app.services.mailer import Attachment, Email

#: Wording of the options, served by the API so no client hardcodes them.
PRACTITIONER_LABELS: dict[PractitionerType, str] = {
    PractitionerType.athlete: "Sono un atleta: pratico parkour",
    PractitionerType.instructor: "Sono un istruttore di parkour",
}

EXPERIENCE_LABELS: dict[ExperienceBand, str] = {
    ExperienceBand.less_than_month: "Meno di un mese",
    ExperienceBand.few_months: "Un paio di mesi",
    ExperienceBand.six_months: "Sei mesi",
    ExperienceBand.one_year: "Un anno",
    ExperienceBand.couple_years: "Un paio d'anni",
    ExperienceBand.over_5_years: "Più di 5 anni",
    ExperienceBand.over_10_years: "Più di 10 anni",
}

#: Sanity bounds on a declared birth date.
MAX_AGE = 100
MIN_PLAUSIBLE_AGE = 5

ALLOWED_UPLOAD_TYPES = frozenset(
    {"application/pdf", "image/jpeg", "image/png", "image/heic", "image/heif"}
)
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def practitioner_options() -> list[Option]:
    return [Option(value=t.value, label=PRACTITIONER_LABELS[t]) for t in PractitionerType]


def experience_options() -> list[Option]:
    return [Option(value=b.value, label=EXPERIENCE_LABELS[b]) for b in BAND_ORDER]


def _today() -> date:
    return datetime.now(timezone.utc).date()


def is_adult(profile: UserProfile, *, today: date | None = None) -> bool:
    if profile.birth_date is None:
        return False
    return age_on(profile.birth_date, today or _today()) >= ADULT_AGE


async def next_step(
    session: AsyncSession, user: User, profile: UserProfile | None
) -> OnboardingStep:
    if profile is None or profile.birth_date is None:
        return OnboardingStep.birth_date

    adult = is_adult(profile)
    if adult and profile.practitioner_type is None:
        return OnboardingStep.practitioner_type

    if profile.practitioner_type is PractitionerType.instructor:
        cert = await profiles_repo.latest_certification(session, user.id)
        if cert is None or cert.status is CertificationStatus.rejected:
            return OnboardingStep.instructor_certificate
        return OnboardingStep.done

    if profile.experience_band is None:
        return OnboardingStep.experience
    if profile.verified_band is None:
        return OnboardingStep.experience_quiz
    return OnboardingStep.done


async def state(session: AsyncSession, user: User) -> OnboardingState:
    profile = await profiles_repo.get(session, user.id)
    step = await next_step(session, user, profile)
    acceptances = await profiles_repo.list_acceptances(session, user.id)
    pending = [
        LegalDocumentOut.of(d)
        for d in legal_service.pending_documents(acceptances)
        # The guardian notice only makes sense once the age is known, and only
        # for the accounts it applies to.
        if not (
            d.trigger is Trigger.signup_minor
            and (profile is None or profile.birth_date is None or is_adult(profile))
        )
    ]
    return OnboardingState(
        next_step=step,
        completed=step is OnboardingStep.done,
        practitioner_options=(
            practitioner_options() if step is OnboardingStep.practitioner_type else []
        ),
        experience_options=experience_options() if step is OnboardingStep.experience else [],
        pending_documents=pending,
    )


async def profile_out(session: AsyncSession, user: User) -> ProfileOut:
    profile = await profiles_repo.get(session, user.id)
    cert = await profiles_repo.latest_certification(session, user.id)
    step = await next_step(session, user, profile)
    return ProfileOut(
        display_name=user.display_name,
        email=user.email,
        practitioner_type=profile.practitioner_type if profile else None,
        experience_band=profile.experience_band if profile else None,
        verified_band=profile.verified_band if profile else None,
        instructor_status=cert.status if cert else None,
        onboarding_completed=step is OnboardingStep.done,
    )


# --- steps -------------------------------------------------------------------


async def set_birth_date(
    session: AsyncSession,
    user: User,
    *,
    birth_date: date,
    accepted_documents: list[AcceptedDocument],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> OnboardingState:
    today = _today()
    if birth_date > today:
        raise ValidationFailed("birth date is in the future")
    age = age_on(birth_date, today)
    if age > MAX_AGE or age < MIN_PLAUSIBLE_AGE:
        raise ValidationFailed("birth date is not plausible")

    minor = age < ADULT_AGE
    if minor:
        missing = legal_service.missing_required(accepted_documents, is_minor=True)
        # The signup notice is already accepted at this point; what can still
        # be missing here is the guardian consent.
        missing = tuple(
            m for m in missing if m in {d.id for d in documents_for(Trigger.signup_minor)}
        )
        if missing:
            raise ValidationFailed(
                "guardian consent is required for accounts under 18: " + ", ".join(missing)
            )

    profile = await profiles_repo.get_or_create(session, user.id)
    if profile.birth_date is not None and profile.birth_date != birth_date:
        # Changing it would move the ceiling, which is exactly what someone
        # who mistyped their age on purpose would try. Support can fix it.
        raise Conflict("birth date is already set")
    profile.birth_date = birth_date

    if accepted_documents:
        await legal_service.record(
            session,
            user_id=user.id,
            documents=accepted_documents,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    await session.commit()
    return await state(session, user)


async def set_practitioner_type(
    session: AsyncSession, user: User, *, practitioner_type: PractitionerType
) -> OnboardingState:
    profile = await profiles_repo.get_or_create(session, user.id)
    if profile.birth_date is None:
        raise ValidationFailed("answer the date of birth first")
    if not is_adult(profile):
        # Not a judgement about the member: a certificate from a national body
        # is issued to adults, and an under-18's identity document has no
        # business being mailed to a review inbox.
        raise Forbidden("this question does not apply to this account")
    profile.practitioner_type = practitioner_type
    await session.commit()
    return await state(session, user)


async def set_experience(
    session: AsyncSession, user: User, *, band: ExperienceBand
) -> OnboardingState:
    profile = await profiles_repo.get_or_create(session, user.id)
    if profile.birth_date is None:
        raise ValidationFailed("answer the date of birth first")
    if profile.practitioner_type is PractitionerType.instructor:
        raise ValidationFailed("instructors submit a certificate instead")
    profile.experience_band = band
    # A new declaration has to be re-earned in the game.
    profile.verified_band = None
    await session.commit()
    return await state(session, user)


def _check_upload(filename: str, content: bytes, content_type: str, label: str) -> None:
    if not content:
        raise ValidationFailed(f"{label} is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationFailed(f"{label} is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    if content_type not in ALLOWED_UPLOAD_TYPES:
        raise ValidationFailed(f"{label} must be a PDF or a photo (got {content_type})")
    if not filename:
        raise ValidationFailed(f"{label} has no filename")


def _dossier_body(user: User, issuing_body: str) -> str:
    return f"""Nuova richiesta di qualifica ISTRUTTORE.

Account:      {user.display_name}
Email:        {user.email}
User ID:      {user.id}
Ente dichiarato: {issuing_body}

In allegato:
  1. il certificato rilasciato dall'ente;
  2. un documento di identità, per verificare che il certificato sia
     intestato alla stessa persona che ha effettuato l'accesso.

Da controllare prima di approvare:
  - il nome sul certificato coincide con quello sul documento;
  - l'ente è riconosciuto a livello nazionale;
  - il certificato è in corso di validità.

La qualifica non è automatica: si concede a mano con
POST /api/v1/admin/users/{user.id}/role  →  {{"role": "instructor"}}

Gli allegati non sono conservati sui server della piattaforma: questa mail è
l'unica copia. Trattala di conseguenza e cancellala quando la verifica è
conclusa.

--
Messaggio generato automaticamente da un indirizzo che non viene letto.
"""


async def submit_instructor_certificate(
    session: AsyncSession,
    user: User,
    *,
    issuing_body: str,
    certificate_filename: str,
    certificate_content: bytes,
    certificate_content_type: str,
    identity_filename: str,
    identity_content: bytes,
    identity_content_type: str,
) -> InstructorCertificationOut:
    settings = get_settings()
    profile = await profiles_repo.get_or_create(session, user.id)
    if not is_adult(profile):
        raise Forbidden("this question does not apply to this account")
    if profile.practitioner_type is not PractitionerType.instructor:
        raise ValidationFailed("answer the athlete/instructor question first")

    existing = await profiles_repo.latest_certification(session, user.id)
    if existing is not None and existing.status is CertificationStatus.pending:
        raise Conflict("a dossier is already under review")
    if existing is not None and existing.status is CertificationStatus.approved:
        raise Conflict("this account is already qualified")

    _check_upload(
        certificate_filename, certificate_content, certificate_content_type, "the certificate"
    )
    _check_upload(
        identity_filename, identity_content, identity_content_type, "the identity document"
    )

    mailbox = settings.review_mailbox
    if not mailbox:
        raise ValidationFailed("no review mailbox is configured on this deployment")

    row = InstructorCertification(
        user_id=user.id,
        issuing_body=issuing_body.strip()[:160],
        certificate_filename=certificate_filename[:255],
        certificate_sha256=sha256(certificate_content).hexdigest(),
        identity_filename=identity_filename[:255],
        identity_sha256=sha256(identity_content).hexdigest(),
        status=CertificationStatus.pending,
    )
    session.add(row)
    await session.flush()

    await mailer.send(
        Email(
            to=mailbox,
            subject=f"[PkFAMILY] Qualifica istruttore — {user.email}",
            text=_dossier_body(user, row.issuing_body),
            attachments=[
                Attachment(
                    filename=certificate_filename,
                    content=certificate_content,
                    content_type=certificate_content_type,
                ),
                Attachment(
                    filename=identity_filename,
                    content=identity_content,
                    content_type=identity_content_type,
                ),
            ],
        )
    )
    await session.commit()

    return InstructorCertificationOut(
        id=row.id,
        issuing_body=row.issuing_body,
        status=row.status,
        submitted_at=row.created_at,
        rejection_reason=None,
        forwarded_to=mailbox,
    )


# --- the vault game ----------------------------------------------------------

QUIZ_TITLE = "Come si chiama questo scavalcamento?"
QUIZ_INTRO = (
    "Sei movimenti, quattro nomi per ognuno. Serve a capire con che livello "
    "partire: non c'è niente da saltare e niente da dimostrare a nessuno."
)


async def start_quiz(session: AsyncSession, user: User) -> QuizOut:
    profile = await profiles_repo.get_or_create(session, user.id)
    questions = quiz_service.build_questions(profile.experience_band)
    attempt = ExperienceQuizAttempt(
        user_id=user.id,
        claimed_band=profile.experience_band,
        questions=quiz_service.to_payload(questions),
        total=len(questions),
    )
    session.add(attempt)
    await session.commit()

    return QuizOut(
        attempt_id=attempt.id,
        title=QUIZ_TITLE,
        intro=QUIZ_INTRO,
        pass_ratio=quiz_service.PASS_RATIO,
        questions=[
            QuizQuestionOut(
                index=i,
                clue=q.clue,
                media_url=q.media_url,
                options=list(q.options),
            )
            for i, q in enumerate(questions)
        ],
    )


def _quiz_message(*, passed: bool, adjusted: bool) -> str:
    if passed:
        return "Nomi giusti: il livello che hai indicato resta com'è."
    if adjusted:
        return (
            "Qualche nome è scappato. Si riparte da un gradino più sotto — "
            "puoi rifare il gioco quando vuoi e recuperarlo."
        )
    return "Rifallo pure quando vuoi: si può ripetere senza limiti."


async def submit_quiz(
    session: AsyncSession, user: User, *, attempt_id: UUID, answers: list[int | None]
) -> QuizResultOut:
    attempt = await session.get(ExperienceQuizAttempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise NotFound("quiz attempt not found")
    if attempt.completed_at is not None:
        raise Conflict("this run has already been submitted")

    questions = quiz_service.from_payload(attempt.questions)
    score = quiz_service.grade(questions, answers)
    total = len(questions)
    ok = quiz_service.passed(score, total)
    granted = quiz_service.resolve_band(attempt.claimed_band, score, total)

    attempt.score = score
    attempt.total = total
    attempt.passed = ok
    attempt.granted_band = granted
    attempt.completed_at = datetime.now(timezone.utc)

    profile = await profiles_repo.get_or_create(session, user.id)
    profile.quiz_attempts += 1
    profile.verified_band = granted
    if ok:
        profile.quiz_passed_at = attempt.completed_at
    if profile.onboarding_completed_at is None:
        profile.onboarding_completed_at = attempt.completed_at
    await session.commit()

    corrections = []
    for i, question in enumerate(questions):
        given_index = answers[i] if i < len(answers) else None
        given = (
            question.options[given_index]
            if given_index is not None and 0 <= given_index < len(question.options)
            else None
        )
        correct = question.options[question.answer_index]
        corrections.append(
            QuizCorrection(
                index=i,
                correct_answer=correct,
                given_answer=given,
                is_correct=given == correct,
            )
        )

    adjusted = granted != attempt.claimed_band
    return QuizResultOut(
        score=score,
        total=total,
        passed=ok,
        granted_band=granted,
        adjusted=adjusted,
        corrections=corrections,
        message=_quiz_message(passed=ok, adjusted=adjusted),
    )
