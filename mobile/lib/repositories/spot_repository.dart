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

  /// Submit a new spot for review (requires login).
  ///
  /// Every user submission starts as `pending` — only an admin can make it
  /// public. The returned [Spot] therefore never shows on the map until it
  /// has been verified.
  Future<Spot> submitSpot({
    required String name,
    String description = '',
    required double lat,
    required double lng,
    int difficulty = 1,
    List<String> photoUrls = const [],
  }) async {
    final data = await _api.postJson(
      _spotsPath,
      auth: true,
      body: {
        'name': name,
        'description': description,
        'location': {'lat': lat, 'lng': lng},
        'difficulty': difficulty,
        'photo_urls': photoUrls,
      },
    );
    return Spot.fromJson(data as Map<String, dynamic>);
  }

  /// The caller's own submissions, whatever their moderation status
  /// (requires login).
  Future<List<Spot>> fetchMySpots() async {
    final data = await _api.getJson('$_spotsPath/mine', auth: true);
    final list = data as List<dynamic>;
    return list
        .map((e) => Spot.fromJson(e as Map<String, dynamic>))
        .toList(growable: false);
  }
}
