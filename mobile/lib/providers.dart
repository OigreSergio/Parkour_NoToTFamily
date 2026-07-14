import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import 'models/spot.dart';
import 'models/user.dart';
import 'repositories/auth_repository.dart';
import 'repositories/spot_repository.dart';
import 'services/api_client.dart';
import 'services/location_service.dart';
import 'services/token_store.dart';

/// Secure storage for the JWT access/refresh pair.
final tokenStoreProvider = Provider<TokenStore>((ref) => const TokenStore());

/// Backend HTTP client (disposed with the [ProviderScope]).
final apiClientProvider = Provider<ApiClient>((ref) {
  final client = ApiClient(tokenStore: ref.watch(tokenStoreProvider));
  ref.onDispose(client.close);
  return client;
});

/// Auth data source (login / register / session restore).
final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(
    ref.watch(apiClientProvider),
    ref.watch(tokenStoreProvider),
  ),
);

/// The signed-in account, or `null` when browsing anonymously.
///
/// Anonymous users can still see the map and verified spots — login is only
/// needed to submit a spot. Publishing spots stays admin-only server-side.
final authControllerProvider =
    AsyncNotifierProvider<AuthController, AppUser?>(AuthController.new);

class AuthController extends AsyncNotifier<AppUser?> {
  @override
  Future<AppUser?> build() =>
      ref.watch(authRepositoryProvider).restoreSession();

  Future<void> login({required String email, required String password}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(authRepositoryProvider).login(email: email, password: password),
    );
  }

  Future<void> register({
    required String email,
    required String password,
    required String displayName,
  }) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(authRepositoryProvider).register(
            email: email,
            password: password,
            displayName: displayName,
          ),
    );
  }

  Future<void> logout() async {
    await ref.read(authRepositoryProvider).logout();
    state = const AsyncData(null);
  }
}

/// The caller's own submissions (pending, verified and rejected).
final mySpotsProvider = FutureProvider<List<Spot>>(
  (ref) async {
    // Re-fetch whenever the session changes.
    final user = await ref.watch(authControllerProvider.future);
    if (user == null) return const [];
    return ref.watch(spotRepositoryProvider).fetchMySpots();
  },
);

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
