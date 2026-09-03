import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:latlong2/latlong.dart';

import 'package:parkour_notot/providers.dart';
import 'package:parkour_notot/repositories/spot_repository.dart';
import 'package:parkour_notot/screens/submit_spot_screen.dart';
import 'package:parkour_notot/services/api_client.dart';
import 'package:parkour_notot/services/local_store.dart';
import 'package:parkour_notot/services/session_service.dart';

import 'support/fake_backend.dart';

SpotPhotoUpload _photo(String name) => SpotPhotoUpload(
      bytes: Uint8List.fromList([1, 2, 3]),
      filename: name,
      contentType: 'image/jpeg',
    );

void main() {
  group('a report needs three photos', () {
    test('the repository refuses to send fewer', () async {
      final repository = SpotRepository(
        ApiClient(httpClient: MockClient((_) async => http.Response('{}', 200))),
      );

      expect(
        () => repository.uploadPhotos(
          [_photo('a.jpg'), _photo('b.jpg')],
          accessToken: 'token',
        ),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('three photos go up as multipart and come back as urls', () async {
      late http.Request sent;
      final repository = SpotRepository(
        ApiClient(
          baseUrl: 'http://backend.test',
          httpClient: MockClient((request) async {
            sent = request;
            return http.Response(
              jsonEncode({
                'photo_urls': ['/media/spots/a.jpg', '/media/spots/b.jpg', '/media/spots/c.jpg'],
              }),
              201,
            );
          }),
        ),
      );

      final urls = await repository.uploadPhotos(
        [_photo('a.jpg'), _photo('b.jpg'), _photo('c.jpg')],
        accessToken: 'access-123',
      );

      expect(urls.length, 3);
      expect(sent.url.path, '/api/v1/spots/photos');
      expect(sent.headers['authorization'], 'Bearer access-123');
      expect(sent.headers['content-type'], contains('multipart/form-data'));
    });
  });

  testWidgets('the send button stays off until the form is complete',
      (tester) async {
    final container = ProviderContainer(
      overrides: [
        localStoreProvider.overrideWithValue(
          InMemoryLocalStore({SessionService.accessTokenKey: 'access-123'}),
        ),
        apiClientProvider.overrideWithValue(
          ApiClient(
            baseUrl: 'http://backend.test',
            httpClient: FakeBackend().client,
          ),
        ),
      ],
    );
    addTearDown(container.dispose);

    // Tall viewport: the whole form is laid out, button included.
    tester.view.physicalSize = const Size(1000, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: SubmitSpotScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('0/3 minimum'), findsOneWidget);
    final button = tester.widget<ButtonStyleButton>(
      find.ancestor(
        of: find.text('Send for review'),
        // `FilledButton.icon` builds a private subclass, so match by type test.
        matching: find.byWidgetPredicate((w) => w is ButtonStyleButton),
      ),
    );
    expect(button.onPressed, isNull, reason: 'nothing has been filled in yet');
    expect(find.textContaining('At least 3 photos'), findsOneWidget);
    expect(find.textContaining('Reports are moderated'), findsOneWidget);
  });

  testWidgets('the form asks for a name and a description', (tester) async {
    final container = ProviderContainer(
      overrides: [
        localStoreProvider.overrideWithValue(InMemoryLocalStore()),
        apiClientProvider.overrideWithValue(
          ApiClient(httpClient: FakeBackend().client),
        ),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: SubmitSpotScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.widgetWithText(TextFormField, 'Name of the spot'), findsOneWidget);
    expect(find.widgetWithText(TextFormField, 'What is there'), findsOneWidget);
    expect(find.text('Use my position'), findsOneWidget);
    // Signed out: the form says why it cannot send.
    expect(find.textContaining('Sign in'), findsOneWidget);
  });

  test('submitting posts the spot with its photo urls', () async {
    final calls = <String>[];
    final container = ProviderContainer(
      overrides: [
        localStoreProvider.overrideWithValue(
          InMemoryLocalStore({SessionService.accessTokenKey: 'access-123'}),
        ),
        apiClientProvider.overrideWithValue(
          ApiClient(
            baseUrl: 'http://backend.test',
            httpClient: MockClient((request) async {
              calls.add('${request.method} ${request.url.path}');
              if (request.url.path == '/api/v1/spots/photos') {
                return http.Response(
                  jsonEncode({'photo_urls': ['/media/a.jpg', '/media/b.jpg', '/media/c.jpg']}),
                  201,
                );
              }
              if (request.url.path == '/api/v1/spots') {
                final body = jsonDecode(request.body) as Map<String, dynamic>;
                expect(body['photo_urls'], hasLength(3));
                expect(body['name'], 'Muretti di Testaccio');
                return http.Response(
                  jsonEncode({
                    'id': 'new-1',
                    'name': body['name'],
                    'description': body['description'],
                    'location': body['location'],
                    'photo_urls': body['photo_urls'],
                    'status': 'pending',
                    'created_at': '2026-09-03T10:00:00Z',
                  }),
                  201,
                );
              }
              return http.Response(jsonEncode(FakeBackend.account), 200);
            }),
          ),
        ),
      ],
    );
    addTearDown(container.dispose);

    // Let the session restore from the stored token.
    await container.read(sessionProvider.notifier).restore();

    final spot = await container.read(sessionProvider.notifier).submitSpot(
          name: 'Muretti di Testaccio',
          description: 'Muretti bassi e scalini, fondo in sampietrini.',
          position: const LatLng(41.8765, 12.4756),
          photos: [_photo('a.jpg'), _photo('b.jpg'), _photo('c.jpg')],
        );

    expect(spot.status, 'pending', reason: 'it goes to moderation, not the map');
    expect(calls, contains('POST /api/v1/spots/photos'));
    expect(calls, contains('POST /api/v1/spots'));
  });
}
