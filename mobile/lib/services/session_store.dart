import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Where the credentials live between launches.
///
/// The guest key is the reason this uses the keychain rather than plain
/// preferences: for an anonymous account it *is* the account. Lose it and the
/// profile, the answers and the unlocked levels are gone, because there is no
/// email to recover them with.
class SessionStore {
  const SessionStore({FlutterSecureStorage storage = const FlutterSecureStorage()})
      : _storage = storage;

  final FlutterSecureStorage _storage;

  static const _accessToken = 'pkfam.access_token';
  static const _refreshToken = 'pkfam.refresh_token';
  static const _displayName = 'pkfam.display_name';
  static const _guestKey = 'pkfam.guest_key';

  Future<String?> readGuestKey() => _storage.read(key: _guestKey);
  Future<String?> readAccessToken() => _storage.read(key: _accessToken);
  Future<String?> readDisplayName() => _storage.read(key: _displayName);

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
    required String displayName,
  }) async {
    await _storage.write(key: _accessToken, value: accessToken);
    await _storage.write(key: _refreshToken, value: refreshToken);
    await _storage.write(key: _displayName, value: displayName);
  }

  Future<void> saveGuestKey(String key) =>
      _storage.write(key: _guestKey, value: key);

  /// Sign out without throwing the account away.
  ///
  /// The guest key deliberately survives: for an anonymous account, deleting
  /// it is not a sign-out, it is a deletion — and it would be silent.
  Future<void> clearTokens() async {
    await _storage.delete(key: _accessToken);
    await _storage.delete(key: _refreshToken);
    await _storage.delete(key: _displayName);
  }

  /// Forget the anonymous account for good.
  Future<void> forgetGuest() async {
    await clearTokens();
    await _storage.delete(key: _guestKey);
  }
}
