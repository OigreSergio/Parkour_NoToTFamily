import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;
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
  WaterRepository({
    http.Client? httpClient,
    List<String>? endpoints,
    Future<String> Function(String key)? loadAsset,
  })  : _http = httpClient ?? http.Client(),
        _endpoints = endpoints ?? defaultEndpoints,
        _loadAsset = loadAsset ?? rootBundle.loadString;

  final http.Client _http;
  final List<String> _endpoints;
  final Future<String> Function(String key) _loadAsset;

  /// Fountains harvested from OpenStreetMap, area by area — Rome first, then
  /// Italy, Europe and the rest (`scripts/fetch_water_points.py`). Shipped
  /// with the app so the answer is instant and works with no signal. It does
  /// not cover every spot yet: whatever it has not seen goes to Overpass.
  static const String bundledAsset = 'assets/water/spot_water.json';

  Map<String, List<dynamic>>? _bundled;

  /// Public Overpass mirrors, tried in order: they rate-limit, and one being
  /// busy should not cost the user the answer.
  ///
  /// All of them serve the whole planet. Some public mirrors only hold one
  /// country (overpass.osm.ch is Switzerland) and answer "nothing here" for
  /// everywhere else — which would read as "no water near this spot".
  static const List<String> defaultEndpoints = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.openstreetmap.fr/api/interpreter',
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

    // The bundled harvest answers first: no wait, no network. Where it has
    // nothing to say the live lookup below takes over.
    final harvested = await _fromBundle(spot);
    if (harvested != null) return harvested;

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

  /// What the harvest knows about this spot, or `null` when it never saw it
  /// (a spot somebody just reported, for instance) so the live lookup runs.
  Future<List<WaterPoint>?> _fromBundle(Spot spot) async {
    try {
      final bundle = _bundled ??= (jsonDecode(await _loadAsset(bundledAsset))
              as Map<String, dynamic>)
          .map((key, value) => MapEntry(key, value as List<dynamic>));
      final points = bundle[spot.id];
      if (points == null) return null;
      return points
          .map((e) => _pointFromBundle(e as Map<String, dynamic>))
          .toList(growable: false);
    } catch (_) {
      // No asset in this build, or a blob we cannot read: ask Overpass.
      return null;
    }
  }

  WaterPoint _pointFromBundle(Map<String, dynamic> json) => WaterPoint(
        id: (json['osm_id'] as num?)?.toInt() ?? 0,
        lat: (json['lat'] as num).toDouble(),
        lng: (json['lng'] as num).toDouble(),
        kind: (json['kind'] as String?) ?? 'drinking_water',
        distanceMeters: (json['distance_m'] as num?)?.toDouble() ?? 0,
        name: json['name'] as String?,
      );

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
