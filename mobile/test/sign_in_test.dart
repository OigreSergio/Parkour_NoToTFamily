import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:parkour_notot/providers.dart';
import 'package:parkour_notot/screens/sign_in_screen.dart';
import 'package:parkour_notot/services/api_client.dart';
import 'package:parkour_notot/services/local_store.dart';
import 'package:parkour_notot/services/session_service.dart';

import 'support/fake_backend.dart';

/// Backend that registers, signs in, and refuses one particular name the way
/// the server's policy does.
MockClient _authBackend(List<String> calls, {String? refuseName}) =>
    MockClient((request) async {
      calls.add('${request.method} ${request.url.path}');
      final body = request.body.isEmpty
          ? <String, dynamic>{}
          : jsonDecode(request.body) as Map<String, dynamic>;

      switch (request.url.path) {
        case '/api/v1/auth/register':
          if (refuseName != null && body['display_name'] == refuseName) {
            return http.Response(
              jsonEncode({
                'error': {
                  'code': 'validation_failed',
                  'message': 'That name contains a slur. Please pick another one.',
                },
              }),
              422,
            );
          }
          return http.Response(
            jsonEncode({
              ...FakeBackend.account,
              'display_name': body['display_name'],
              'email': body['email'],
              'is_guest': false,
            }),
            201,
          );
        case '/api/v1/auth/login':
          if (body['password'] == 'wrong-password') {
            return http.Response(
              jsonEncode({
                'error': {'code': 'unauthorized', 'message': 'invalid credentials'},
              }),
              401,
            );
          }
          return http.Response(
            jsonEncode({
              'access_token': 'access-123',
              'refresh_token': 'refresh-456',
              'token_type': 'Bearer',
            }),
            200,
          );
        case '/api/v1/users/me':
          return http.Response(
            jsonEncode({
              ...FakeBackend.account,
              'display_name': 'Sergio',
              'email': 'sergio@example.com',
              'is_guest': false,
            }),
            200,
          );
        default:
          return http.Response(jsonEncode(const []), 200);
      }
    });

ProviderContainer _container(MockClient client) {
  final container = ProviderContainer(
    overrides: [
      localStoreProvider.overrideWithValue(InMemoryLocalStore()),
      apiClientProvider.overrideWithValue(
        ApiClient(baseUrl: 'http://backend.test', httpClient: client),
      ),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

Future<void> _pump(WidgetTester tester, ProviderContainer container) async {
  tester.view.physicalSize = const Size(1000, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: SignInScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  group('registering with an email', () {
    test('creates the account with the chosen name, then signs in', () async {
      final calls = <String>[];
      final container = _container(_authBackend(calls));

      final ok = await container.read(sessionProvider.notifier).registerWithEmail(
            email: 'sergio@example.com',
            password: 'una-password-lunga',
            displayName: 'Sergio',
          );

      expect(ok, isTrue);
      expect(calls, containsAllInOrder([
        'POST /api/v1/auth/register',
        'POST /api/v1/auth/login',
      ]));
      final session = container.read(sessionProvider);
      expect(session.isSignedIn, isTrue);
      expect(session.account?.isGuest, isFalse);
      expect(session.account?.displayName, 'Sergio');
      expect(
        await container.read(localStoreProvider).read(SessionService.accessTokenKey),
        'access-123',
      );
    });

    test('a name the server refuses comes back as its own message', () async {
      final container = _container(
        _authBackend(<String>[], refuseName: 'frocio'),
      );

      final ok = await container.read(sessionProvider.notifier).registerWithEmail(
            email: 'x@example.com',
            password: 'una-password-lunga',
            displayName: 'frocio',
          );

      expect(ok, isFalse);
      expect(container.read(sessionProvider).isSignedIn, isFalse);
      expect(
        container.read(sessionProvider).error,
        contains('contains a slur'),
        reason: 'the reason from the policy is shown, not a status code',
      );
    });
  });

  group('signing in again', () {
    test('a known email and password get the session back', () async {
      final container = _container(_authBackend(<String>[]));

      final ok = await container.read(sessionProvider.notifier).signInWithEmail(
            email: 'sergio@example.com',
            password: 'una-password-lunga',
          );

      expect(ok, isTrue);
      expect(container.read(sessionProvider).account?.email, 'sergio@example.com');
    });

    test('a wrong password is said in plain words', () async {
      final container = _container(_authBackend(<String>[]));

      final ok = await container.read(sessionProvider.notifier).signInWithEmail(
            email: 'sergio@example.com',
            password: 'wrong-password',
          );

      expect(ok, isFalse);
      expect(container.read(sessionProvider).error, isNotNull);
      expect(container.read(sessionProvider).error, isNot(contains('401')));
    });
  });

  group('the screen', () {
    testWidgets('offers a name field when registering, and the guest way out',
        (tester) async {
      await _pump(tester, _container(_authBackend(<String>[])));

      expect(find.widgetWithText(TextFormField, 'Your name here'), findsOneWidget);
      expect(find.textContaining('except insults'), findsOneWidget);
      expect(find.text('Continue as a guest'), findsOneWidget);
      expect(find.textContaining('Rather not give an email?'), findsOneWidget);
    });

    testWidgets('switching to sign-in drops the name field', (tester) async {
      await _pump(tester, _container(_authBackend(<String>[])));

      await tester.tap(find.text('I already have an account'));
      await tester.pumpAndSettle();

      expect(find.widgetWithText(TextFormField, 'Your name here'), findsNothing);
      expect(find.widgetWithText(TextFormField, 'Email'), findsOneWidget);
    });

    testWidgets('it refuses a malformed email and a short password',
        (tester) async {
      final calls = <String>[];
      await _pump(tester, _container(_authBackend(calls)));

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Your name here'),
        'Sergio',
      );
      await tester.enterText(find.widgetWithText(TextFormField, 'Email'), 'nope');
      await tester.enterText(find.widgetWithText(TextFormField, 'Password'), 'short');
      await tester.tap(find.text('Create my account'));
      await tester.pumpAndSettle();

      expect(find.text('Write a valid email address'), findsOneWidget);
      expect(find.text('At least 8 characters'), findsOneWidget);
      expect(calls, isEmpty, reason: 'nothing is sent until the form is sound');
    });

    testWidgets('rewriting the name puts the refusal away', (tester) async {
      final container = _container(
        _authBackend(<String>[], refuseName: 'frocio'),
      );
      await _pump(tester, container);

      final nameField = find.widgetWithText(TextFormField, 'Your name here');
      await tester.enterText(nameField, 'frocio');
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Email'),
        'x@example.com',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Password'),
        'una-password-lunga',
      );
      await tester.tap(find.text('Create my account'));
      await tester.pumpAndSettle();

      expect(find.textContaining('contains a slur'), findsOneWidget);

      await tester.enterText(nameField, 'Sergio');
      await tester.pumpAndSettle();

      expect(
        find.textContaining('contains a slur'),
        findsNothing,
        reason: 'a refusal about a name that is no longer written only confuses',
      );
    });
  });
}
