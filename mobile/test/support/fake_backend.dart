import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// Records every request the app makes, e.g. `POST /api/v1/auth/logout`.
class RecordedCall {
  RecordedCall(this.method, this.path, this.headers);

  final String method;
  final String path;
  final Map<String, String> headers;

  @override
  String toString() => '$method $path';
}

/// Stubs the handful of endpoints the account menu talks to.
///
/// Guest sign-in returns a token pair, `/users/me` the matching account, and
/// logout answers `204 No Content` like the real backend.
class FakeBackend {
  FakeBackend({this.logoutStatus = 204});

  /// Status code returned by `POST /api/v1/auth/logout` — set it to something
  /// other than 204 to exercise the "the server could not be reached" path.
  final int logoutStatus;

  final List<RecordedCall> calls = [];

  static const Map<String, dynamic> account = {
    'id': 'a1b2c3',
    'email': null,
    'display_name': 'Guest-9f2c',
    'role': 'user',
    'is_email_verified': false,
    'is_guest': true,
    'is_subscribed': false,
    'created_at': '2026-01-01T00:00:00Z',
  };

  http.Client get client => MockClient((request) async {
        calls.add(
          RecordedCall(request.method, request.url.path, request.headers),
        );
        return switch (request.url.path) {
          '/api/v1/auth/guest' => http.Response(
              jsonEncode({
                'access_token': 'access-123',
                'refresh_token': 'refresh-456',
                'token_type': 'Bearer',
              }),
              201,
            ),
          '/api/v1/users/me' => http.Response(jsonEncode(account), 200),
          '/api/v1/auth/logout' => http.Response('', logoutStatus),
          // Spots and tutorials: an empty list keeps the screens quiet.
          _ => http.Response(jsonEncode(const []), 200),
        };
      });

  bool called(String method, String path) =>
      calls.any((c) => c.method == method && c.path == path);

  RecordedCall? lastCall(String path) {
    for (final call in calls.reversed) {
      if (call.path == path) return call;
    }
    return null;
  }
}
