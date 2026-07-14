import '../models/user.dart';
import '../services/api_client.dart';
import '../services/token_store.dart';

/// Login / register / session restore against `POST /api/v1/auth/*`.
///
/// Tokens live in [TokenStore] (secure storage); [ApiClient] reads them from
/// there and refreshes transparently, so this repository only orchestrates.
class AuthRepository {
  AuthRepository(this._api, this._tokens);

  final ApiClient _api;
  final TokenStore _tokens;

  static const _authPath = '/api/v1/auth';
  static const _mePath = '/api/v1/users/me';

  /// Exchange credentials for a token pair, store it and return the account.
  Future<AppUser> login({required String email, required String password}) async {
    final data = await _api.postJson(
      '$_authPath/login',
      body: {'email': email, 'password': password},
    ) as Map<String, dynamic>;
    await _tokens.save(
      access: data['access_token'] as String,
      refresh: data['refresh_token'] as String,
    );
    return fetchMe();
  }

  /// Create an account, then log straight in.
  Future<AppUser> register({
    required String email,
    required String password,
    required String displayName,
  }) async {
    await _api.postJson(
      '$_authPath/register',
      body: {'email': email, 'password': password, 'display_name': displayName},
    );
    return login(email: email, password: password);
  }

  /// The current account, or throws [ApiException] when not authenticated.
  Future<AppUser> fetchMe() async {
    final data = await _api.getJson(_mePath, auth: true) as Map<String, dynamic>;
    return AppUser.fromJson(data);
  }

  /// Restore a previous session from stored tokens. Returns `null` when
  /// there is no session or it can no longer be refreshed.
  Future<AppUser?> restoreSession() async {
    if (await _tokens.refreshToken() == null) return null;
    try {
      return await fetchMe();
    } on ApiException {
      await _tokens.clear();
      return null;
    }
  }

  /// Revoke all refresh tokens server-side (best effort) and forget the
  /// local session.
  Future<void> logout() async {
    try {
      await _api.postJson('$_authPath/logout', auth: true);
    } on ApiException {
      // Already invalid server-side — still clear locally.
    } finally {
      await _tokens.clear();
    }
  }
}
