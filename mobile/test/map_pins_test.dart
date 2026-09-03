import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';

import 'package:parkour_notot/models/spot.dart';
import 'package:parkour_notot/services/map_pins.dart';

Spot _spot(String id, double lat, double lng, {bool community = false}) => Spot(
      id: id,
      name: id,
      description: '',
      location: GeoPoint(lat: lat, lng: lng),
      photoUrls: const [],
      difficulty: 3,
      status: community ? 'community' : 'verified',
      submittedBy: null,
      verifiedAt: null,
      createdAt: DateTime(2026, 1, 1),
    );

final _world = LatLngBounds(
  const LatLng(-85, -180),
  const LatLng(85, 180),
);

void main() {
  group('MapPins.visible', () {
    test('keeps every spot when they are far enough apart on screen', () {
      final spots = [
        _spot('a', 41.90, 12.49),
        _spot('b', 41.91, 12.50),
        _spot('c', 41.92, 12.51),
      ];

      final pins = MapPins.visible(spots, bounds: _world, zoom: 16);

      expect(pins.length, 3);
    });

    test('collapses spots that would land on the same pixels', () {
      // Three spots a few metres apart, seen from country zoom.
      final spots = [
        _spot('a', 41.9000, 12.4900),
        _spot('b', 41.9001, 12.4901),
        _spot('c', 41.9002, 12.4902),
      ];

      final pins = MapPins.visible(spots, bounds: _world, zoom: 6);

      expect(pins.length, 1);
    });

    test('a verified spot wins the cell over a community one', () {
      final spots = [
        _spot('community', 41.9000, 12.4900, community: true),
        _spot('family', 41.9001, 12.4901),
      ];

      final pins = MapPins.visible(spots, bounds: _world, zoom: 6);

      expect(pins.single.id, 'family');
    });

    test('spots outside the view are not built at all', () {
      final spots = [
        _spot('rome', 41.90, 12.49),
        _spot('tokyo', 35.68, 139.69),
      ];
      final aroundRome = LatLngBounds(
        const LatLng(41.5, 12.0),
        const LatLng(42.3, 13.0),
      );

      final pins = MapPins.visible(spots, bounds: aroundRome, zoom: 10);

      expect(pins.single.id, 'rome');
    });

    test('never builds more pins than the ceiling, whatever the zoom', () {
      final spots = [
        for (var i = 0; i < 1706; i++)
          _spot('s$i', -80 + (i % 160), -179 + (i % 359), community: true),
      ];

      final pins = MapPins.visible(spots, bounds: _world, zoom: 3, maxPins: 50);

      expect(pins.length, lessThanOrEqualTo(50));
    });

    test('the grid cell shrinks as the map zooms in', () {
      expect(
        MapPins.cellSizeDegrees(4),
        greaterThan(MapPins.cellSizeDegrees(12)),
      );
      // ~44 px at zoom 0 is about a sixth of the world.
      expect(MapPins.cellSizeDegrees(0), closeTo(61.9, 0.5));
    });
  });
}
