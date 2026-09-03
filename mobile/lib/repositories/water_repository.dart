import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';

import '../models/spot.dart';
import '../models/water_point.dart';

/// Finds drinking water around a spot in OpenStreetMap, through Overpass.
///
/// OSM is where the drinking-water apps get their fountains, so asking it
/// directly means the answer is as fresh as the map itself — no copy of the
/// data to keep up to date, and user-submitted spots are covered too.
class WaterRepository {
  WaterRepository({http.Client? httpClient, List<String>? endpoints})
      : _http = httpClient ?? http.Client(),
        _endpoints = endpoints ?? defaultEndpoints;

  final http.Client _http;
  final List<String> _endpoints;

  /// Public Overpass mirrors, tried in order: they rate-limit, and one being
  /// busy should not cost the user the answer.
  static const List<String> defaultEndpoints = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
  ];

  static const Distance _distance = Distance();

  /// How far around the spot to look. Beyond this you are not "at the spot"
  /// any more, you are going for a walk.
  static const int defaultRadiusMeters = 400;

  /// Drinking water within [radiusMeters] of [spot], nearest first.
  ///
  /// Returns an empty list when the area has none mapped; throws only when no
  /// mirror answered, so the UI can tell "none nearby" from "could not ask".
  Future<List<WaterPoint>> nearSpot(
    Spot spot, {
    int radiusMeters = defaultRadiusMeters,
  }) async {
    final lat = spot.location.lat;
    final lng = spot.location.lng;
    final query = '''
[out:json][timeout:25];
(
  node(around:$radiusMeters,$lat,$lng)["amenity"="drinking_water"];
  node(around:$radiusMeters,$lat,$lng)["man_made"="water_tap"];
  node(around:$radiusMeters,$lat,$lng)["natural"="spring"]["drinking_water"="yes"];
  node(around:$radiusMeters,$lat,$lng)["amenity"="fountain"]["drinking_water"="yes"];
);
out body;''';

    Object? lastError;
    for (final endpoint in _endpoints) {
      try {
        final uri = Uri.parse(endpoint).replace(queryParameters: {'data': query});
        final res = await _http.get(uri).timeout(const Duration(seconds: 25));
        if (res.statusCode != 200) {
          lastError = 'HTTP ${res.statusCode}';
          continue;
        }
        return _parse(res.body, LatLng(lat, lng));
      } catch (error) {
        lastError = error;
      }
    }
    throw WaterLookupException('$lastError');
  }

  List<WaterPoint> _parse(String body, LatLng spot) {
    final elements =
        (jsonDecode(body) as Map<String, dynamic>)['elements'] as List<dynamic>? ??
            const [];
    final points = <WaterPoint>[];

    for (final element in elements) {
      final node = element as Map<String, dynamic>;
      final lat = (node['lat'] as num?)?.toDouble();
      final lng = (node['lon'] as num?)?.toDouble();
      if (lat == null || lng == null) continue;

      final tags = (node['tags'] as Map<String, dynamic>?) ?? const {};
      if (tags['drinking_water'] == 'no') continue;

      points.add(
        WaterPoint(
          id: (node['id'] as num?)?.toInt() ?? 0,
          lat: lat,
          lng: lng,
          kind: (tags['man_made'] as String?) ??
              (tags['natural'] as String?) ??
              (tags['amenity'] as String?) ??
              'drinking_water',
          distanceMeters:
              _distance.as(LengthUnit.Meter, spot, LatLng(lat, lng)).toDouble(),
          name: tags['name'] as String?,
        ),
      );
    }

    points.sort((a, b) => a.distanceMeters.compareTo(b.distanceMeters));
    return points;
  }

  void close() => _http.close();
}

/// Raised when no Overpass mirror could answer.
class WaterLookupException implements Exception {
  const WaterLookupException(this.message);

  final String message;

  @override
  String toString() => 'WaterLookupException: $message';
}
