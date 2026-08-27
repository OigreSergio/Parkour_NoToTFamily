import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import 'models/spot.dart';
import 'models/video.dart';
import 'repositories/spot_repository.dart';
import 'repositories/video_repository.dart';
import 'services/location_service.dart';
import 'services/supabase_client.dart';

/// Il client Supabase, già inizializzato da `initSupabase()` in `main`.
final supabaseClientProvider = Provider((ref) => supabase);

/// Spot data source.
final spotRepositoryProvider = Provider<SpotRepository>(
  (ref) => SpotRepository(ref.watch(supabaseClientProvider)),
);

/// Device location helper.
final locationServiceProvider = Provider<LocationService>(
  (ref) => const LocationService(),
);

/// The map / search centre — the user's GPS position, or a fallback.
final currentLocationProvider = FutureProvider<LatLng>(
  (ref) => ref.watch(locationServiceProvider).currentLatLng(),
);

/// Verified spots near the current location.
final spotsProvider = FutureProvider<List<Spot>>((ref) async {
  final center = await ref.watch(currentLocationProvider.future);
  return ref
      .watch(spotRepositoryProvider)
      .fetchSpots(lat: center.latitude, lng: center.longitude);
});

/// Tutorial video data source.
final videoRepositoryProvider = Provider<VideoRepository>(
  (ref) => VideoRepository(ref.watch(supabaseClientProvider)),
);

/// Tutti i video. Il servizio è gratuito: nessun video è bloccato, e la
/// sezione è leggibile anche senza account.
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
