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

  /// Fetch verified spots near ([lat], [lng]) within [radiusMeters].
  ///
  /// The backend requires a search centre, so callers pass the user's GPS
  /// position (or a sensible fallback when location is unavailable). Defaults
  /// use the widest radius the API allows (the whole planet), so the map is
  /// populated even without a precise fix.
  Future<List<Spot>> fetchSpots({
    required double lat,
    required double lng,
    int radiusMeters = 20000000,
    int limit = 2000,
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
