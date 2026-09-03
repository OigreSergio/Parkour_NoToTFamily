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
  dynamic _decode(http.Response res, Uri uri) {
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
