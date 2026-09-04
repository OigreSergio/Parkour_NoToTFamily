import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:parkour_notot/services/api_client.dart';

void main() {
  test('accented messages from the API arrive readable', () async {
    // FastAPI answers `application/json` with no charset; `http` would then
    // read the bytes as latin-1 and mangle every accent.
    final client = ApiClient(
      baseUrl: 'http://backend.test',
      httpClient: MockClient(
        (_) async => http.Response.bytes(
          utf8.encode(
            jsonEncode({
              'error': {
                'code': 'validation_failed',
                'message': 'Questo nome non è ammesso: scegline un altro.',
              },
            }),
          ),
          422,
          headers: const {'content-type': 'application/json'},
        ),
      ),
    );

    try {
      await client.postJson('/api/v1/auth/register', body: const {});
      fail('a 422 should have thrown');
    } on ApiException catch (error) {
      expect(error.userMessage, 'Questo nome non è ammesso: scegline un altro.');
    }
  });

  test('a body that is not JSON still gets a sentence', () async {
    final client = ApiClient(
      baseUrl: 'http://backend.test',
      httpClient: MockClient((_) async => http.Response('gateway down', 502)),
    );

    try {
      await client.getJson('/api/v1/spots');
      fail('a 502 should have thrown');
    } on ApiException catch (error) {
      expect(error.userMessage, contains('server'));
      expect(error.userMessage, isNot(contains('gateway down')));
    }
  });

  test('unauthorised is said in words, not as a status code', () async {
    final client = ApiClient(
      baseUrl: 'http://backend.test',
      httpClient: MockClient((_) async => http.Response('', 401)),
    );

    try {
      await client.postJson('/api/v1/auth/login', body: const {});
      fail('a 401 should have thrown');
    } on ApiException catch (error) {
      expect(error.userMessage, contains('password'));
    }
  });
}
