import 'dart:convert';

import 'package:http/http.dart' as http;

import 'token_store.dart';

/// Thin HTTP client around the NoToT Family Python backend (FastAPI).
///
/// The base URL defaults to `http://10.0.2.2:8000` — on the Android emulator
/// `10.0.2.2` is an alias for the developer machine's `localhost`. Override it
/// for the iOS simulator (`http://localhost:8000`), a physical device, or
/// production either by passing [baseUrl] or with
/// `--dart-define=API_BASE_URL=https://api.example.com`.
///
/// Requests made with `auth: true` carry the stored `Authorization: Bearer`
/// access token; on a 401 the client rotates the refresh token once and
/// replays the request before giving up.
class ApiClient {
  ApiClient({String? baseUrl, http.Client? httpClient, TokenStore? tokenStore})
      : baseUrl = baseUrl ?? defaultBaseUrl,
        _http = httpClient ?? http.Client(),
        _tokens = tokenStore ?? const TokenStore();

  /// Configurable default backend base URL.
  static const String defaultBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  final String baseUrl;
  final http.Client _http;
  final TokenStore _tokens;

  /// `GET` [path] (relative to [baseUrl]) with optional query parameters and
  /// return the decoded JSON body.
  Future<dynamic> getJson(
    String path, {
    Map<String, dynamic>? query,
    bool auth = false,
  }) =>
      _send('GET', path, query: query, auth: auth);

  /// `POST` [body] as JSON to [path] and return the decoded JSON body
  /// (`null` for empty 204 responses).
  Future<dynamic> postJson(
    String path, {
    Object? body,
    bool auth = false,
  }) =>
      _send('POST', path, body: body, auth: auth);

  Future<dynamic> _send(
    String method,
    String path, {
    Map<String, dynamic>? query,
    Object? body,
    required bool auth,
    bool retryOnAuthFailure = true,
  }) async {
    final uri = Uri.parse('$baseUrl$path').replace(
      queryParameters: query?.map((k, v) => MapEntry(k, '$v')),
    );
    final headers = <String, String>{'Accept': 'application/json'};
    if (body != null) headers['Content-Type'] = 'application/json';
    if (auth) {
      final token = await _tokens.accessToken();
      if (token != null) headers['Authorization'] = 'Bearer $token';
    }

    final req = http.Request(method, uri)..headers.addAll(headers);
    if (body != null) req.body = jsonEncode(body);
    final res = await http.Response.fromStream(await _http.send(req));

    if (res.statusCode == 401 && auth && retryOnAuthFailure) {
      if (await _refreshTokens()) {
        return _send(
          method,
          path,
          query: query,
          body: body,
          auth: auth,
          retryOnAuthFailure: false,
        );
      }
    }
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(res.statusCode, res.body, uri);
    }
    if (res.body.isEmpty) return null;
    return jsonDecode(res.body);
  }

  /// Rotate the refresh token. Returns `true` when a new pair was stored.
  Future<bool> _refreshTokens() async {
    final refresh = await _tokens.refreshToken();
    if (refresh == null) return false;
    final uri = Uri.parse('$baseUrl/api/v1/auth/refresh');
    final res = await _http.post(
      uri,
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'refresh_token': refresh}),
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      await _tokens.clear();
      return false;
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    await _tokens.save(
      access: data['access_token'] as String,
      refresh: data['refresh_token'] as String,
    );
    return true;
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

  /// Human-readable message extracted from the backend's error envelope
  /// (`{"error": {"message": ...}}`), falling back to the status code.
  String get message {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        final error = decoded['error'];
        if (error is Map<String, dynamic> && error['message'] is String) {
          return error['message'] as String;
        }
        if (decoded['detail'] is String) return decoded['detail'] as String;
      }
    } on FormatException {
      // Not JSON — fall through to the generic message.
    }
    return 'Request failed ($statusCode)';
  }

  @override
  String toString() => 'ApiException($statusCode) for $uri: $body';
}
