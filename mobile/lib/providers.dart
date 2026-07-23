import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import 'models/spot.dart';
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
