import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';

import 'package:parkour_notot/models/spot.dart';
import 'package:parkour_notot/services/spot_distance.dart';
import 'package:parkour_notot/services/spot_imagery.dart';
import 'package:parkour_notot/widgets/spot_rating.dart';

Spot _spot({
  int? difficulty,
  double? rating,
  int ratingCount = 0,
  List<String> photos = const [],
  String? streetView,
}) =>
    Spot(
      id: 's1',
      name: 'Spot Monti 1',
      description: '',
      location: const GeoPoint(lat: 41.8925, lng: 12.4966),
      photoUrls: photos,
      streetViewUrl: streetView,
      difficulty: difficulty,
      rating: rating,
      ratingCount: ratingCount,
      status: 'community',
      submittedBy: null,
      verifiedAt: null,
      createdAt: DateTime(2026, 1, 1),
    );

void main() {
  group('ratings are never invented', () {
    test('an imported spot carries no difficulty and no rating', () {
      final spot = Spot.fromJson({
        'id': 'gmaps-1',
        'name': 'Spot Náfplio 1',
        'location': {'lat': 37.5, 'lng': 22.7},
        'status': 'community',
        'created_at': '2026-01-01T00:00:00Z',
      });

      expect(spot.difficulty, isNull);
      expect(spot.rating, isNull);
      expect(spot.ratingCount, 0);
      expect(spot.isRated, isFalse);
    });

    test('a spot counts as rated only once people have voted', () {
      expect(_spot(rating: 4.5).isRated, isFalse, reason: 'no votes behind it');
      expect(_spot(ratingCount: 3).isRated, isFalse, reason: 'no average yet');
      expect(_spot(rating: 4.5, ratingCount: 3).isRated, isTrue);
    });

    testWidgets('an unrated spot says so instead of showing stars',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(home: Scaffold(body: SpotRating(spot: _spot()))),
      );

      expect(find.textContaining('Not rated'), findsOneWidget);
      expect(find.byIcon(Icons.star), findsNothing);
    });

    testWidgets('a rated spot shows the average and how many voted',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SpotRating(spot: _spot(rating: 4.2, ratingCount: 7)),
          ),
        ),
      );

      expect(find.text('4.2 (7)'), findsOneWidget);
      expect(find.byIcon(Icons.star), findsNWidgets(4));
    });
  });

  group('SpotDistance', () {
    test('says nothing without a position', () {
      expect(SpotDistance.labelFor(_spot(), null), isNull);
    });

    test('measures from where you are', () {
      // ~1.2 km north of the spot.
      final label = SpotDistance.labelFor(_spot(), const LatLng(41.9035, 12.4966));
      expect(label, '1.2 km');
    });

    test('reads in metres under a kilometre', () {
      expect(SpotDistance.format(320), '320 m');
      expect(SpotDistance.format(4700), '4.7 km');
      expect(SpotDistance.format(1204000), '1204 km');
    });
  });

  group('SpotImagery picks the closest thing to a photo', () {
    test('a real photo wins', () {
      final spot = _spot(
        photos: const ['https://photos.example/a.jpg'],
        streetView: 'https://streetviewpixels-pa.googleapis.com/v1/thumbnail?x',
      );
      expect(SpotImagery.coverUrl(spot), 'https://photos.example/a.jpg');
      expect(SpotImagery.onlyAerial(spot), isFalse);
    });

    test('Street View comes before the satellite', () {
      final spot = _spot(streetView: 'https://streetviewpixels-pa.googleapis.com/v1/x');
      expect(SpotImagery.coverUrl(spot), contains('streetviewpixels'));
      expect(SpotImagery.onlyAerial(spot), isFalse);
    });

    test('the satellite is the last resort', () {
      final spot = _spot();
      expect(SpotImagery.coverUrl(spot), contains('World_Imagery'));
      expect(SpotImagery.onlyAerial(spot), isTrue);
    });
  });
}
