import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import 'models/onboarding.dart';
import 'models/risk_notice.dart';
import 'models/spot.dart';
import 'models/video.dart';
import 'repositories/auth_repository.dart';
import 'repositories/legal_repository.dart';
import 'repositories/onboarding_repository.dart';
import 'repositories/spot_repository.dart';
import 'repositories/video_repository.dart';
import 'services/api_client.dart';
import 'services/location_service.dart';
import 'services/session_store.dart';

/// Backend HTTP client (disposed with the [ProviderScope]).
final apiClientProvider = Provider<ApiClient>((ref) {
  final client = ApiClient();
  ref.onDispose(client.close);
  return client;
});

/// Spot data source.
final spotRepositoryProvider = Provider<SpotRepository>(
  (ref) => SpotRepository(ref.watch(apiClientProvider)),
);

/// Device location helper.
final locationServiceProvider =
    Provider<LocationService>((ref) => const LocationService());

/// The map / search centre — the user's GPS position, or a fallback.
final currentLocationProvider = FutureProvider<LatLng>(
  (ref) => ref.watch(locationServiceProvider).currentLatLng(),
);

/// Verified spots near the current location.
final spotsProvider = FutureProvider<List<Spot>>((ref) async {
  final center = await ref.watch(currentLocationProvider.future);
  return ref.watch(spotRepositoryProvider).fetchSpots(
        lat: center.latitude,
        lng: center.longitude,
      );
});

/// Tutorial video data source.
final videoRepositoryProvider = Provider<VideoRepository>(
  (ref) => VideoRepository(ref.watch(apiClientProvider)),
);

/// All tutorial videos. The backend marks premium ones as `locked` for
/// viewers without a subscription; beginner tutorials are open to everyone,
/// including guests signed in without an email.
final tutorialsProvider = FutureProvider<List<TutorialVideo>>(
  (ref) => ref.watch(videoRepositoryProvider).fetchTutorials(),
);

/// IDs of the tricks the user marked as landed. Client-side stub (kept in
/// memory) until the backend persists per-user progress — same pattern as
/// spot likes.
class LandedTricksNotifier extends StateNotifier<Set<String>> {
  LandedTricksNotifier() : super(const {});

  void toggle(String videoId) {
    final next = Set<String>.of(state);
    if (!next.add(videoId)) {
      next.remove(videoId);
    }
    state = next;
  }
}

final landedTricksProvider =
    StateNotifierProvider<LandedTricksNotifier, Set<String>>(
  (ref) => LandedTricksNotifier(),
);

/// Risk notices (`GET /api/v1/legal/documents`).
final legalRepositoryProvider = Provider<LegalRepository>(
  (ref) => LegalRepository(ref.watch(apiClientProvider)),
);

/// Notices accepted in this session.
///
/// Per session on purpose: the trigger for the spot and tutorial notices is
/// "the first time, each time the app is opened". The durable record is the
/// one the backend keeps in `legal_acceptances` — this is only what stops the
/// same dialog from appearing on every tap.
class AcceptedNoticesNotifier extends StateNotifier<Set<String>> {
  AcceptedNoticesNotifier() : super(const {});

  void accept(String noticeId) => state = {...state, noticeId};
}

final acceptedNoticesProvider =
    StateNotifierProvider<AcceptedNoticesNotifier, Set<String>>(
  (ref) => AcceptedNoticesNotifier(),
);

/// Credentials on the device.
final sessionStoreProvider = Provider<SessionStore>((ref) => const SessionStore());

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(
    ref.watch(apiClientProvider),
    ref.watch(sessionStoreProvider),
  ),
);

final onboardingRepositoryProvider = Provider<OnboardingRepository>(
  (ref) => OnboardingRepository(ref.watch(apiClientProvider)),
);

/// Who is signed in: `null` once we know nobody is.
///
/// Starts in [AsyncValue.loading] because the answer lives in the keychain: on
/// launch the app tries the stored guest key before showing anything, so an
/// anonymous member does not get asked to sign in again on every cold start.
class AuthController extends StateNotifier<AsyncValue<AppSession?>> {
  AuthController(this._repo) : super(const AsyncValue.loading()) {
    restore();
  }

  final AuthRepository _repo;

  Future<void> restore() async {
    state = const AsyncValue.loading();
    try {
      state = AsyncValue.data(await _repo.resumeGuest());
    } catch (error, stack) {
      state = AsyncValue.error(error, stack);
    }
  }

  /// Create an anonymous account. [accepted] is the notice that was shown.
  Future<AppSession> signInAsGuest(List<RiskNotice> accepted) async {
    final session = await _repo.signInAsGuest(accepted: accepted);
    state = AsyncValue.data(session);
    return session;
  }

  /// Note the step the server says comes next, without re-fetching the session.
  void updateStep(String nextStep) {
    final current = state.value;
    if (current == null) return;
    state = AsyncValue.data(
      AppSession(
        accessToken: current.accessToken,
        refreshToken: current.refreshToken,
        displayName: current.displayName,
        isGuest: current.isGuest,
        nextStep: nextStep,
      ),
    );
  }

  Future<void> signOut() async {
    await _repo.signOut();
    state = const AsyncValue.data(null);
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AsyncValue<AppSession?>>(
  (ref) => AuthController(ref.watch(authRepositoryProvider)),
);
