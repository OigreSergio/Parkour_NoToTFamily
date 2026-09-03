import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/models/spot.dart';
import 'package:parkour_notot/screens/spot_detail_screen.dart';

Spot _spot({List<String> photos = const [], bool community = false}) => Spot(
      id: 'gmaps-1',
      name: 'Spot Náfplio 1',
      description: 'Dalla lista community Google Maps.',
      location: const GeoPoint(lat: 37.5645, lng: 22.7946),
      photoUrls: photos,
      difficulty: 3,
      status: community ? 'community' : 'verified',
      submittedBy: null,
      verifiedAt: null,
      createdAt: DateTime(2026, 1, 1),
    );

Future<void> _pump(WidgetTester tester, Spot spot) async {
  await tester.pumpWidget(MaterialApp(home: SpotDetailScreen(spot: spot)));
  await tester.pump();
}

void main() {
  testWidgets('an unverified spot gets a satellite view and says so',
      (tester) async {
    await _pump(tester, _spot(community: true));

    expect(find.textContaining('Satellite view'), findsOneWidget);
    expect(find.textContaining('Not verified'), findsOneWidget);
    expect(find.textContaining('Esri'), findsOneWidget);
  });

  testWidgets('a spot with photos shows them, with no satellite caption',
      (tester) async {
    await _pump(tester, _spot(photos: const ['https://photos.example/a.jpg']));

    expect(find.textContaining('Satellite view'), findsNothing);
    expect(find.textContaining('Not verified'), findsNothing);
    expect(find.byType(Image), findsWidgets);
  });

  testWidgets('a verified spot without photos still gets the satellite view, '
      'but is not flagged as unverified', (tester) async {
    await _pump(tester, _spot());

    expect(find.textContaining('Satellite view'), findsOneWidget);
    expect(find.textContaining('Not verified'), findsNothing);
  });
}
