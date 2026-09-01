import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/providers.dart';
import 'package:parkour_notot/screens/settings_screen.dart';
import 'package:parkour_notot/services/api_client.dart';
import 'package:parkour_notot/services/local_store.dart';
import 'package:parkour_notot/services/session_service.dart';
import 'package:parkour_notot/widgets/account_menu.dart';

import 'support/fake_backend.dart';

/// A bare screen carrying the same app bar action as the app shell, so the
/// menu can be exercised without the map and its network tiles.
Widget _host() => const MaterialApp(
      home: Scaffold(
        body: Center(child: AccountMenuButton()),
      ),
    );

void main() {
  late FakeBackend backend;
  late InMemoryLocalStore store;
  late ProviderContainer container;

  ProviderContainer buildContainer({int logoutStatus = 204}) {
    backend = FakeBackend(logoutStatus: logoutStatus);
    store = InMemoryLocalStore();
    return ProviderContainer(
      overrides: [
        localStoreProvider.overrideWithValue(store),
        apiClientProvider.overrideWithValue(
          ApiClient(baseUrl: 'http://backend.test', httpClient: backend.client),
        ),
      ],
    );
  }

  Future<void> pumpMenu(WidgetTester tester) async {
    await tester.pumpWidget(
      UncontrolledProviderScope(container: container, child: _host()),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byType(AccountMenuButton));
    await tester.pumpAndSettle();
  }

  setUp(() {
    container = buildContainer();
    addTearDown(container.dispose);
  });

  testWidgets('the menu offers settings and guest sign-in when signed out',
      (tester) async {
    await pumpMenu(tester);

    expect(find.text('Not signed in'), findsOneWidget);
    expect(find.text('Settings'), findsOneWidget);
    expect(find.text('Sign in as a guest'), findsOneWidget);
    expect(find.text('Log out'), findsNothing);
  });

  testWidgets('Settings opens the settings screen', (tester) async {
    await pumpMenu(tester);

    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();

    expect(find.byType(SettingsScreen), findsOneWidget);
    expect(find.text('Appearance'), findsOneWidget);
    expect(find.text('Spot search'), findsOneWidget);
  });

  testWidgets('signing in as a guest shows the account, then logging out '
      'revokes and clears it', (tester) async {
    await pumpMenu(tester);

    await tester.tap(find.text('Sign in as a guest'));
    await tester.pumpAndSettle();

    expect(backend.called('POST', '/api/v1/auth/guest'), isTrue);
    expect(container.read(sessionProvider).account?.displayName, 'Guest-9f2c');
    expect(await store.read(SessionService.accessTokenKey), 'access-123');

    // Reopen the menu: it now names the account and offers the log out.
    await tester.tap(find.byType(AccountMenuButton));
    await tester.pumpAndSettle();
    expect(find.text('Guest-9f2c'), findsOneWidget);
    expect(find.text('Guest account — no email'), findsOneWidget);

    await tester.tap(find.text('Log out'));
    await tester.pumpAndSettle();

    // The confirmation dialog holds the log out back until it is accepted.
    expect(find.text('Log out?'), findsOneWidget);
    expect(backend.called('POST', '/api/v1/auth/logout'), isFalse);

    await tester.tap(find.widgetWithText(FilledButton, 'Log out'));
    await tester.pumpAndSettle();

    expect(backend.called('POST', '/api/v1/auth/logout'), isTrue);
    expect(
      backend.lastCall('/api/v1/auth/logout')?.headers['authorization'],
      'Bearer access-123',
    );
    expect(container.read(sessionProvider).isSignedIn, isFalse);
    expect(await store.read(SessionService.accessTokenKey), isNull);
    expect(find.text('Logged out.'), findsOneWidget);
  });

  testWidgets('cancelling the confirmation keeps the session', (tester) async {
    await pumpMenu(tester);
    await tester.tap(find.text('Sign in as a guest'));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(AccountMenuButton));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Log out'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(TextButton, 'Cancel'));
    await tester.pumpAndSettle();

    expect(backend.called('POST', '/api/v1/auth/logout'), isFalse);
    expect(container.read(sessionProvider).isSignedIn, isTrue);
  });

  testWidgets('an unreachable server still clears the local session',
      (tester) async {
    container = buildContainer(logoutStatus: 500);
    addTearDown(container.dispose);

    await pumpMenu(tester);
    await tester.tap(find.text('Sign in as a guest'));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(AccountMenuButton));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Log out'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Log out'));
    await tester.pumpAndSettle();

    expect(container.read(sessionProvider).isSignedIn, isFalse);
    expect(await store.read(SessionService.accessTokenKey), isNull);
    expect(
      find.textContaining('still open there'),
      findsOneWidget,
      reason: 'the user must know the tokens were not revoked server-side',
    );
  });

  testWidgets('a session saved on the device comes back signed in',
      (tester) async {
    store = InMemoryLocalStore({SessionService.accessTokenKey: 'access-123'});
    backend = FakeBackend();
    container = ProviderContainer(
      overrides: [
        localStoreProvider.overrideWithValue(store),
        apiClientProvider.overrideWithValue(
          ApiClient(baseUrl: 'http://backend.test', httpClient: backend.client),
        ),
      ],
    );
    addTearDown(container.dispose);

    await pumpMenu(tester);

    expect(find.text('Guest-9f2c'), findsOneWidget);
    expect(find.text('Log out'), findsOneWidget);
  });
}
