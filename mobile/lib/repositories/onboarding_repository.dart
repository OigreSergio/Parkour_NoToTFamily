import '../models/onboarding.dart';
import '../models/risk_notice.dart';
import '../services/api_client.dart';

/// The questions asked after signing in.
///
/// Every method returns the *next* state rather than a success flag: the flow
/// is the server's to decide, so the app asks what to draw instead of working
/// it out. That is also what keeps an old build from skipping a step.
class OnboardingRepository {
  OnboardingRepository(this._api);

  final ApiClient _api;

  Future<OnboardingState> state() async => OnboardingState.fromJson(
        await _api.getJson('/api/v1/onboarding/state') as Map<String, dynamic>,
      );

  /// Save the date of birth, with the guardian consent when it is needed.
  ///
  /// Under 18 the backend refuses the call without `minor_guardian`, so the
  /// app shows that notice before getting here.
  Future<OnboardingState> setBirthDate(
    DateTime birthDate, {
    List<RiskNotice> accepted = const [],
  }) async {
    final iso = '${birthDate.year.toString().padLeft(4, '0')}-'
        '${birthDate.month.toString().padLeft(2, '0')}-'
        '${birthDate.day.toString().padLeft(2, '0')}';
    return OnboardingState.fromJson(
      await _api.postJson('/api/v1/onboarding/birth-date', body: {
        'birth_date': iso,
        'accepted_documents': [
          for (final notice in accepted) {'id': notice.id, 'version': notice.version},
        ],
      }) as Map<String, dynamic>,
    );
  }

  Future<OnboardingState> setPractitionerType(String value) async =>
      OnboardingState.fromJson(
        await _api.postJson(
          '/api/v1/onboarding/practitioner-type',
          body: {'practitioner_type': value},
        ) as Map<String, dynamic>,
      );

  Future<OnboardingState> setExperience(String band) async =>
      OnboardingState.fromJson(
        await _api.postJson(
          '/api/v1/onboarding/experience',
          body: {'experience_band': band},
        ) as Map<String, dynamic>,
      );

  Future<Quiz> startQuiz() async => Quiz.fromJson(
        await _api.postJson('/api/v1/onboarding/quiz') as Map<String, dynamic>,
      );

  Future<QuizResult> submitQuiz(String attemptId, List<int?> answers) async =>
      QuizResult.fromJson(
        await _api.postJson('/api/v1/onboarding/quiz/answers', body: {
          'attempt_id': attemptId,
          'answers': answers,
        }) as Map<String, dynamic>,
      );
}
