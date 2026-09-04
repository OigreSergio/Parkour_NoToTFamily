import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/models/spot.dart';
import 'package:parkour_notot/services/spot_directions.dart';

Spot _spot() => Spot(
      id: 's1',
      name: 'Colle Oppio Park',
      description: '',
      location: const GeoPoint(lat: 41.8925, lng: 12.4966),
      photoUrls: const [],
      status: 'verified',
      submittedBy: null,
      verifiedAt: null,
      createdAt: DateTime(2026, 1, 1),
    );

void main() {
  group('SpotDirections hands the spot to the phone, not to one brand', () {
    test('Android gets the geo: intent, so every maps app can answer', () {
      final uris = SpotDirections.candidatesFor(
        _spot(),
        isWeb: false,
        operatingSystem: 'android',
      );

      expect(uris.first.scheme, 'geo');
      expect(uris.first.toString(), contains('41.8925,12.4966'));
      expect(uris.first.toString(), contains('Colle%20Oppio%20Park'));
      expect(uris.last.host, 'www.google.com', reason: 'web fallback last');
    });

    test('iOS opens Apple Maps first', () {
      final uris = SpotDirections.candidatesFor(
        _spot(),
        isWeb: false,
        operatingSystem: 'ios',
      );

      expect(uris.first.scheme, 'maps');
      expect(uris[1].host, 'maps.apple.com');
    });

    test('on the web there is only the browser map', () {
      final uris = SpotDirections.candidatesFor(_spot(), isWeb: true);

      expect(uris, hasLength(1));
      expect(uris.single.toString(), contains('destination=41.8925,12.4966'));
    });

    test('an unknown platform still gets somewhere', () {
      final uris = SpotDirections.candidatesFor(
        _spot(),
        isWeb: false,
        operatingSystem: 'fuchsia',
      );

      expect(uris, hasLength(1));
      expect(uris.single.scheme, 'https');
    });
  });
}
