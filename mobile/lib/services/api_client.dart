import 'dart:convert';

import 'package:http/http.dart' as http;

/// Thin HTTP client around the NoToT Family Python backend (FastAPI).
///
/// The base URL defaults to `http://10.0.2.2:8000` — on the Android emulator
/// `10.0.2.2` is an alias for the developer machine's `localhost`. Override it
/// for the iOS simulator (`http://localhost:8000`), a physical device, or
/// production either by passing [baseUrl] or with
/// `--dart-define=API_BASE_URL=https://api.example.com`.
class ApiClient {
  ApiClient({String? baseUrl, http.Client? httpClient})
      : baseUrl = baseUrl ?? defaultBaseUrl,
        _http = httpClient ?? http.Client();

  /// Configurable default backend base URL.
  static const String defaultBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  final String baseUrl;
  final http.Client _http;

  /// `GET` [path] (relative to [baseUrl]) with optional query parameters and
  /// return the decoded JSON body.
  ///
  /// Pass [accessToken] to authenticate the call with `Authorization: Bearer`.
  Future<dynamic> getJson(
    String path, {
    Map<String, dynamic>? query,
    String? accessToken,
  }) async {
    final uri = Uri.parse('$baseUrl$path').replace(
      queryParameters: query?.map((k, v) => MapEntry(k, '$v')),
    );
    final res = await _http.get(uri, headers: _headers(accessToken));
    return _decode(res, uri);
  }

  /// `POST` [body] (encoded as JSON) to [path] and return the decoded JSON
  /// body, or `null` when the backend answers `204 No Content` — which is what
  /// `POST /api/v1/auth/logout` does.
  ///
  /// Pass [accessToken] to authenticate the call with `Authorization: Bearer`.
  Future<dynamic> postJson(
    String path, {
    Object? body,
    String? accessToken,
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    final res = await _http.post(
      uri,
      headers: {..._headers(accessToken), 'Content-Type': 'application/json'},
      body: jsonEncode(body ?? const <String, dynamic>{}),
    );
    return _decode(res, uri);
  }

  /// Send a prepared request — multipart photo uploads go through here — and
  /// return its decoded JSON body.
  Future<dynamic> sendJson(http.BaseRequest request) async {
    final res = await http.Response.fromStream(await _http.send(request));
    return _decode(res, request.url);
  }

  Map<String, String> _headers(String? accessToken) => {
        'Accept': 'application/json',
        if (accessToken != null && accessToken.isNotEmpty)
          'Authorization': 'Bearer $accessToken',
      };

  /// Throw on a non-2xx response, otherwise decode the body (`null` when it is
  /// empty, e.g. `204 No Content`).
  ///
  /// The bytes are read as UTF-8 rather than through `response.body`: without a
  /// `charset` in the content type — which FastAPI does not send — `http`
  /// falls back to latin-1 and every accent in a message the user is meant to
  /// read ("Questo nome non è ammesso") comes out broken.
  dynamic _decode(http.Response res, Uri uri) {
    final body = res.bodyBytes.isEmpty ? '' : utf8.decode(res.bodyBytes, allowMalformed: true);
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(res.statusCode, body, uri);
    }
    return body.isEmpty ? null : jsonDecode(body);
  }

  /// Release the underlying connection pool.
  void close() => _http.close();
}

/// Raised when the backend returns a non-2xx response.
class ApiException implements Exception {
  ApiException(this.statusCode, this.body, this.uri);

  final int statusCode;
  final String body;
  final Uri uri;

  /// The message meant for the person using the app.
  ///
  /// The API answers `{"error": {"code": ..., "message": ...}}`; when it does,
  /// that message is already written for them (the display-name policy relies
  /// on this), so it is shown as it is instead of a status code.
  String get userMessage {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        final error = decoded['error'];
        if (error is Map<String, dynamic>) {
          final message = error['message'] ?? error['detail'];
          if (message is String && message.isNotEmpty) return message;
        }
        if (error is String && error.isNotEmpty) return error;
        final detail = decoded['detail'];
        if (detail is String && detail.isNotEmpty) return detail;
      }
    } catch (_) {
      // Body that is not JSON: fall through to the generic message.
    }
    return switch (statusCode) {
      401 => 'Email or password not recognised.',
      409 => 'That email is already registered.',
      >= 500 => 'The server is having trouble. Try again in a moment.',
      _ => 'Something went wrong ($statusCode).',
    };
  }

  @override
  String toString() => 'ApiException($statusCode) for $uri: $body';
}
