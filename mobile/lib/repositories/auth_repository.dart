import '../models/account.dart';
import '../services/api_client.dart';

/// Talks to `POST /api/v1/auth/*` and `GET /api/v1/users/me`.
///
/// Only the calls the account menu needs are implemented: sign in without an
/// email (guest), read the signed-in account, and log out. Email login and
/// registration land with the full auth flow (roadmap milestone 3).
class AuthRepository {
  AuthRepository(this._api);

  final ApiClient _api;

  static const String _registerPath = '/api/v1/auth/register';
  static const String _loginPath = '/api/v1/auth/login';
  static const String _guestPath = '/api/v1/auth/guest';
  static const String _logoutPath = '/api/v1/auth/logout';
  static const String _mePath = '/api/v1/users/me';

  /// Create an account with an email, a password and a chosen name.
  ///
  /// The name goes through the server's public-name policy, which refuses
  /// slurs, calls to hatred and staff impersonation; when it does, the message
  /// it sends back is meant to be shown to the person as it is.
  Future<Account> register({
    required String email,
    required String password,
    required String displayName,
  }) async {
    final data = await _api.postJson(_registerPath, body: {
      'email': email,
      'password': password,
      'display_name': displayName,
    });
    return Account.fromJson(data as Map<String, dynamic>);
  }

  /// Sign in with email and password.
  Future<AuthTokens> login({
    required String email,
    required String password,
  }) async {
    final data = await _api.postJson(_loginPath, body: {
      'email': email,
      'password': password,
    });
    return AuthTokens.fromJson(data as Map<String, dynamic>);
  }

  /// Create a device-only account (no email) and return its token pair.
  Future<AuthTokens> loginAsGuest({String? displayName}) async {
    final data = await _api.postJson(
      _guestPath,
      body: {if (displayName != null) 'display_name': displayName},
    );
    return AuthTokens.fromJson(data as Map<String, dynamic>);
  }

  /// The account behind [accessToken].
  Future<Account> me(String accessToken) async {
    final data = await _api.getJson(_mePath, accessToken: accessToken);
    return Account.fromJson(data as Map<String, dynamic>);
  }

  /// Revoke every refresh token of the signed-in user, server-side.
  ///
  /// The caller still has to drop the local tokens — see
  /// `SessionService.clear()`.
  Future<void> logout(String accessToken) =>
      _api.postJson(_logoutPath, accessToken: accessToken);
}

/// Access + refresh token pair, mirroring the backend `TokenPair` schema.
class AuthTokens {
  const AuthTokens({required this.accessToken, required this.refreshToken});

  final String accessToken;
  final String refreshToken;

  factory AuthTokens.fromJson(Map<String, dynamic> json) => AuthTokens(
        accessToken: (json['access_token'] as String?) ?? '',
        refreshToken: (json['refresh_token'] as String?) ?? '',
      );
}
