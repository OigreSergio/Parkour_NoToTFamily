import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:parkour_notot/models/spot.dart';
import 'package:parkour_notot/providers.dart';
import 'package:parkour_notot/repositories/water_repository.dart';
import 'package:parkour_notot/screens/spot_detail_screen.dart';

Spot _spot({
  List<String> photos = const [],
  String? streetView,
  bool community = false,
}) =>
    Spot(
      id: 'gmaps-1',
      name: 'Spot Náfplio 1',
      description: 'Dalla lista community Google Maps.',
      location: const GeoPoint(lat: 37.5645, lng: 22.7946),
      photoUrls: photos,
      streetViewUrl: streetView,
      status: community ? 'community' : 'verified',
      submittedBy: null,
      verifiedAt: null,
      createdAt: DateTime(2026, 1, 1),
    );

/// A build without the harvested dataset: these tests are about the screen,
/// so the lookup goes straight to the (stubbed) live one.
Future<String> _noBundle(String key) async => throw Exception('no asset');

/// Water lookup that answers "nothing mapped here".
WaterRepository _noWater() => WaterRepository(
      loadAsset: _noBundle,
      httpClient: MockClient(
        (_) async => http.Response('{"elements": []}', 200),
      ),
    );

Future<void> _pump(WidgetTester tester, Spot spot) async {
  // Tall viewport: the detail is a ListView, and what is off-screen is not
  // built at all.
  tester.view.physicalSize = const Size(1000, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [waterRepositoryProvider.overrideWithValue(_noWater())],
      child: MaterialApp(home: SpotDetailScreen(spot: spot)),
    ),
  );
  await tester.pumpAndSettle();
  // The water lookup resolves after the first settle.
  await tester.pump(const Duration(milliseconds: 50));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('a spot with a Street View shot opens on the ground view',
      (tester) async {
    await _pump(
      tester,
      _spot(
        community: true,
        streetView: 'https://streetviewpixels-pa.googleapis.com/v1/thumbnail?x',
      ),
    );

    expect(find.textContaining('Street View pointed at the spot'), findsOneWidget);
    expect(find.textContaining('Not verified'), findsOneWidget);
  });

  testWidgets('with no photo and no Street View it falls back to satellite',
      (tester) async {
    await _pump(tester, _spot(community: true));

    expect(find.textContaining('Satellite view'), findsOneWidget);
    expect(find.textContaining('Esri'), findsOneWidget);
  });

  testWidgets('a spot with photos shows them and no imagery caption',
      (tester) async {
    await _pump(tester, _spot(photos: const ['https://photos.example/a.jpg']));

    expect(find.textContaining('Satellite view'), findsNothing);
    expect(find.textContaining('Street View'), findsNothing);
    expect(find.textContaining('Not verified'), findsNothing);
  });

  testWidgets('every spot reads as not rated until people vote', (tester) async {
    await _pump(tester, _spot());

    expect(find.textContaining('Not rated'), findsOneWidget);
    expect(find.byIcon(Icons.star), findsNothing);
  });

  testWidgets('it says when no drinking water is mapped nearby', (tester) async {
    await _pump(tester, _spot());

    expect(find.textContaining('No drinking water mapped'), findsOneWidget);
    expect(find.textContaining('OpenStreetMap'), findsNothing);
  });

  testWidgets('it names the nearest fountain when there is one', (tester) async {
    tester.view.physicalSize = const Size(1000, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          waterRepositoryProvider.overrideWithValue(
            WaterRepository(
              loadAsset: _noBundle,
              httpClient: MockClient(
                (_) async => http.Response(
                  '{"elements": [{"id": 1, "lat": 37.5646, "lon": 22.7947, '
                  '"tags": {"amenity": "drinking_water", "name": "Krini"}}]}',
                  200,
                ),
              ),
            ),
          ),
        ],
        child: MaterialApp(home: SpotDetailScreen(spot: _spot())),
      ),
    );
    await tester.pumpAndSettle();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pumpAndSettle();

    expect(find.textContaining('Krini'), findsOneWidget);
    expect(find.textContaining('OpenStreetMap'), findsOneWidget);
  });
}
