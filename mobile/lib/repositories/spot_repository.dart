import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart' show MediaType;

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
  static const String _photosPath = '/api/v1/spots/photos';

  /// A report without photos cannot be checked by a moderator, so the app asks
  /// for at least this many before it will send one.
  static const int minPhotos = 3;

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

  /// Upload the photos of a report and get back the URLs to send with it.
  ///
  /// Throws [ArgumentError] below [minPhotos]: the check also lives in the UI,
  /// but the repository is the last place that can stop a useless report.
  Future<List<String>> uploadPhotos(
    List<SpotPhotoUpload> photos, {
    required String accessToken,
  }) async {
    if (photos.length < minPhotos) {
      throw ArgumentError('A spot report needs at least $minPhotos photos.');
    }

    final request = http.MultipartRequest(
      'POST',
      Uri.parse('${_api.baseUrl}$_photosPath'),
    )..headers['Authorization'] = 'Bearer $accessToken';

    for (final photo in photos) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'files',
          photo.bytes,
          filename: photo.filename,
          contentType: MediaType.parse(photo.contentType),
        ),
      );
    }

    final body = await _api.sendJson(request) as Map<String, dynamic>;
    return ((body['photo_urls'] as List<dynamic>?) ?? const [])
        .map((e) => e as String)
        .toList(growable: false);
  }

  /// Submit a spot for moderation (`status = pending`).
  Future<Spot> submitSpot({
    required String name,
    required String description,
    required double lat,
    required double lng,
    required List<String> photoUrls,
    required String accessToken,
  }) async {
    final data = await _api.postJson(
      _spotsPath,
      accessToken: accessToken,
      body: {
        'name': name,
        'description': description,
        'location': {'lat': lat, 'lng': lng},
        'photo_urls': photoUrls,
      },
    );
    return Spot.fromJson(data as Map<String, dynamic>);
  }
}

/// The photos a member picked for a spot they are reporting.
class SpotPhotoUpload {
  const SpotPhotoUpload({
    required this.bytes,
    required this.filename,
    required this.contentType,
  });

  final Uint8List bytes;
  final String filename;

  /// e.g. `image/jpeg` — the backend accepts jpeg, png, webp and heic.
  final String contentType;
}
