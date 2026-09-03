import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/models/spot.dart';
import 'package:parkour_notot/services/spot_imagery.dart';

Spot _spot({List<String> photos = const []}) => Spot(
      id: 's1',
      name: 'Colle Oppio Park',
      description: '',
      location: const GeoPoint(lat: 41.8925, lng: 12.4966),
      photoUrls: photos,
      difficulty: 2,
      status: 'verified',
      submittedBy: null,
      verifiedAt: null,
      createdAt: DateTime(2026, 1, 1),
    );

void main() {
  group('SpotImagery', () {
    test('a spot with a photo keeps its photo as the cover', () {
      final spot = _spot(photos: const ['https://photos.example/oppio.jpg']);
      expect(SpotImagery.coverUrl(spot), 'https://photos.example/oppio.jpg');
    });

    test('a spot without photos falls back to the aerial view', () {
      final url = SpotImagery.coverUrl(_spot());
      expect(url, contains('World_Imagery'));
      expect(url, contains('f=image'));
    });

    test('the aerial view is framed on the coordinates', () {
      final url = SpotImagery.aerialUrl(
        const GeoPoint(lat: 41.8925, lng: 12.4966),
        width: 640,
        height: 360,
      );
      final bbox = Uri.parse(url).queryParameters['bbox']!.split(',');
      final west = double.parse(bbox[0]);
      final south = double.parse(bbox[1]);
      final east = double.parse(bbox[2]);
      final north = double.parse(bbox[3]);

      expect(west, lessThan(12.4966));
      expect(east, greaterThan(12.4966));
      expect(south, lessThan(41.8925));
      expect(north, greaterThan(41.8925));
      expect(Uri.parse(url).queryParameters['size'], '640,360');
    });
  });

  group('Spot.isCommunity', () {
    test('tells the community list apart from the family map', () {
      expect(_spot().isCommunity, isFalse);
      final community = Spot.fromJson({
        'id': 'gmaps-1',
        'name': 'Spot Náfplio 1',
        'location': {'lat': 37.5, 'lng': 22.7},
        'status': 'community',
        'created_at': '2026-01-01T00:00:00Z',
      });
      expect(community.isCommunity, isTrue);
    });
  });
}
