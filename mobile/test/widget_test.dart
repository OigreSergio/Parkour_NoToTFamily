import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/main.dart';

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues(<String, String>{}));

  testWidgets('with nobody signed in, the app opens on the way in', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: ParkourApp()));
    await tester.pumpAndSettle();

    expect(find.text('Continua senza account'), findsOneWidget);
    // Nothing is asked of a guest: no email field, no name field.
    expect(find.byType(TextField), findsNothing);
  });

  testWidgets('a guest key that no longer works does not lock the app out',
      (tester) async {
    // Tests have no network, so resuming fails exactly as it would against a
    // wiped database. The app has to fall back to the welcome screen rather
    // than get stuck on a spinner or an error.
    FlutterSecureStorage.setMockInitialValues(
      <String, String>{'pkfam.guest_key': 'pkg_stale'},
    );

    await tester.pumpWidget(const ProviderScope(child: ParkourApp()));
    await tester.pumpAndSettle();

    expect(find.text('Continua senza account'), findsOneWidget);
  });

  testWidgets('the shell still has the Map/List/Tutorials tabs', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: MaterialApp(home: HomeScreen())),
    );
    await tester.pump();

    expect(find.text('Map'), findsWidgets);
    expect(find.text('List'), findsWidgets);
    expect(find.text('Tutorials'), findsWidgets);
  });
}
