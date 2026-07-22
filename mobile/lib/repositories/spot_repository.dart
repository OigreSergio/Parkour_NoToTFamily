import '../models/spot.dart';
import '../services/api_client.dart';

/// Reads parkour spots from the backend.
///
/// `GET /api/v1/spots` only ever returns spots that have been verified by an
/// admin — moderation is enforced server-side.
class SpotRepository {
  SpotRepository(this._api);

  final ApiClient _api;

  static const String _spotsPath = '/api/v1/spots';

  /// Submit a new spot for review. Requires a logged-in user's [accessToken];
  /// the backend stores it with `status = "pending"` until an admin verifies
  /// it, so it will NOT appear in [fetchSpots] right away.
  Future<Spot> submitSpot({
    required String name,
    String description = '',
    required double lat,
    required double lng,
    int difficulty = 1,
    required String accessToken,
  }) async {
    final data = await _api.postJson(
      _spotsPath,
      bearerToken: accessToken,
      body: {
        'name': name,
        'description': description,
        'location': {'lat': lat, 'lng': lng},
        'difficulty': difficulty,
      },
    );
    return Spot.fromJson(data as Map<String, dynamic>);
  }

  /// Fetch verified spots near ([lat], [lng]) within [radiusMeters].
  ///
  /// The backend requires a search centre, so callers pass the user's GPS
  /// position (or a sensible fallback when location is unavailable). Defaults
  /// use the widest radius the API allows so the list/map are populated even
  /// without a precise fix.
  Future<List<Spot>> fetchSpots({
    required double lat,
    required double lng,
    int radiusMeters = 50000,
    int limit = 500,
  }) async {
    final data = await _api.getJson(
      _spotsPath,
      query: {
        'lat': lat,
        'lng': lng,
        'radius_m': radiusMeters,
        'limit': limit,
      },
    );
    final list = data as List<dynamic>;
    return list
        .map((e) => Spot.fromJson(e as Map<String, dynamic>))
        .toList(growable: false);
  }
}
