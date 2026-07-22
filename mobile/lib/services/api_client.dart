import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

/// Thin HTTP client around the NoToT Family Python backend (FastAPI).
///
/// The base URL defaults to `http://10.0.2.2:8000` — on the Android emulator
/// `10.0.2.2` is an alias for the developer machine's `localhost` — and to
/// `http://localhost:8000` when running as a web app. Override it for the iOS
/// simulator (`http://localhost:8000`), a physical device, or production
/// either by passing [baseUrl] or with
/// `--dart-define=API_BASE_URL=https://api.example.com`.
class ApiClient {
  ApiClient({String? baseUrl, http.Client? httpClient})
      : baseUrl = baseUrl ?? defaultBaseUrl,
        _http = httpClient ?? http.Client();

  /// Configurable default backend base URL.
  static const String _envBaseUrl = String.fromEnvironment('API_BASE_URL');

  static String get defaultBaseUrl {
    if (_envBaseUrl.isNotEmpty) return _envBaseUrl;
    return kIsWeb ? 'http://localhost:8000' : 'http://10.0.2.2:8000';
  }

  final String baseUrl;
  final http.Client _http;

  /// `GET` [path] (relative to [baseUrl]) with optional query parameters and
  /// return the decoded JSON body.
  Future<dynamic> getJson(String path, {Map<String, dynamic>? query}) async {
    final uri = Uri.parse('$baseUrl$path').replace(
      queryParameters: query?.map((k, v) => MapEntry(k, '$v')),
    );
    final res = await _http.get(uri, headers: const {
      'Accept': 'application/json',
    });
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(res.statusCode, res.body, uri);
    }
    return jsonDecode(res.body);
  }

  /// `POST` [body] as JSON to [path] (relative to [baseUrl]) and return the
  /// decoded JSON response body (or `null` for empty responses). Pass
  /// [bearerToken] for endpoints that require authentication.
  Future<dynamic> postJson(
    String path, {
    Object? body,
    String? bearerToken,
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    final res = await _http.post(
      uri,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        if (bearerToken != null) 'Authorization': 'Bearer $bearerToken',
      },
      body: jsonEncode(body ?? const <String, dynamic>{}),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(res.statusCode, res.body, uri);
    }
    return res.body.isEmpty ? null : jsonDecode(res.body);
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

  @override
  String toString() => 'ApiException($statusCode) for $uri: $body';
}
