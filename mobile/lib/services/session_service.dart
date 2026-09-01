import 'dart:convert';

import '../models/account.dart';
import '../repositories/auth_repository.dart';
import 'local_store.dart';

/// Persists the signed-in session (tokens + the account they belong to) so the
/// app comes back signed in after a restart.
///
/// Tokens are secrets: they go through a [LocalStore] backed by
/// `flutter_secure_storage`. The cached account is only there so the account
/// menu can render before `GET /api/v1/users/me` answers.
class SessionService {
  const SessionService(this._store);

  final LocalStore _store;

  static const String accessTokenKey = 'auth.access_token';
  static const String refreshTokenKey = 'auth.refresh_token';
  static const String accountKey = 'auth.account';

  /// The stored session, or `null` when nobody is signed in on this device.
  Future<StoredSession?> read() async {
    final accessToken = await _store.read(accessTokenKey);
    if (accessToken == null || accessToken.isEmpty) return null;
    return StoredSession(
      tokens: AuthTokens(
        accessToken: accessToken,
        refreshToken: await _store.read(refreshTokenKey) ?? '',
      ),
      account: _decodeAccount(await _store.read(accountKey)),
    );
  }

  Future<void> saveTokens(AuthTokens tokens) async {
    await _store.write(accessTokenKey, tokens.accessToken);
    await _store.write(refreshTokenKey, tokens.refreshToken);
  }

  Future<void> saveAccount(Account account) =>
      _store.write(accountKey, jsonEncode(account.toJson()));

  /// Drop every trace of the session from the device.
  Future<void> clear() async {
    await _store.delete(accessTokenKey);
    await _store.delete(refreshTokenKey);
    await _store.delete(accountKey);
  }

  Account? _decodeAccount(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    try {
      return Account.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      // A blob written by an incompatible build: ignore it, /users/me refreshes.
      return null;
    }
  }
}

/// What [SessionService.read] found on the device.
class StoredSession {
  const StoredSession({required this.tokens, this.account});

  final AuthTokens tokens;
  final Account? account;
}
