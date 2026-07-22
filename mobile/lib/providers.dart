import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import 'models/auth_tokens.dart';
import 'models/bank_details.dart';
import 'models/spot.dart';
import 'repositories/auth_repository.dart';
import 'repositories/payment_repository.dart';
import 'repositories/spot_repository.dart';
import 'services/api_client.dart';
import 'services/location_service.dart';

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

/// Auth endpoints (register/login).
final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(ref.watch(apiClientProvider)),
);

/// The logged-in user's JWT pair, or `null` when signed out. Held in memory
/// only — enough for submitting spots; persistent sessions come later.
final authTokensProvider = StateProvider<AuthTokens?>((ref) => null);

/// Payment data source.
final paymentRepositoryProvider = Provider<PaymentRepository>(
  (ref) => PaymentRepository(ref.watch(apiClientProvider)),
);

/// Bank-transfer details for the Support screen (`null` until the backend
/// deployment configures them).
final bankDetailsProvider = FutureProvider<BankDetails?>(
  (ref) => ref.watch(paymentRepositoryProvider).fetchBankDetails(),
);
