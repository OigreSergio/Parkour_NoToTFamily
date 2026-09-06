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

  /// Bearer token sent with every request once someone is signed in.
  ///
  /// Held here rather than passed at every call site: the app has exactly one
  /// signed-in account at a time, and threading it through would mean every
  /// repository knowing about sessions.
  String? authToken;

  Map<String, String> _headers({bool json = false}) => {
        'Accept': 'application/json',
        if (json) 'Content-Type': 'application/json',
        if (authToken != null) 'Authorization': 'Bearer $authToken',
      };

  /// `GET` [path] (relative to [baseUrl]) with optional query parameters and
  /// return the decoded JSON body.
  Future<dynamic> getJson(String path, {Map<String, dynamic>? query}) async {
    final uri = Uri.parse('$baseUrl$path').replace(
      queryParameters: query?.map((k, v) => MapEntry(k, '$v')),
    );
    final res = await _http.get(uri, headers: _headers());
    return _decode(res, uri);
  }

  /// `POST` [body] as JSON to [path] and return the decoded JSON body.
  Future<dynamic> postJson(String path, {Object? body}) async {
    final uri = Uri.parse('$baseUrl$path');
    final res = await _http.post(
      uri,
      headers: _headers(json: true),
      body: jsonEncode(body ?? const <String, dynamic>{}),
    );
    return _decode(res, uri);
  }

  dynamic _decode(http.Response res, Uri uri) {
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(res.statusCode, res.body, uri);
    }
    if (res.body.isEmpty) return null;
    return jsonDecode(res.body);
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

  /// The `message` the API puts inside `{"error": {...}}`, when there is one.
  String? get detail {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map && decoded['error'] is Map) {
        final message = (decoded['error'] as Map)['message'];
        if (message is String) return message;
      }
    } catch (_) {
      // Not JSON, or not shaped like an API error: fall through.
    }
    return null;
  }

  @override
  String toString() => 'ApiException($statusCode) for $uri: $body';
}
