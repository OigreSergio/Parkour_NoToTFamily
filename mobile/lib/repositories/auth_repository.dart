import '../models/onboarding.dart';
import '../models/risk_notice.dart';
import '../services/api_client.dart';
import '../services/session_store.dart';

/// Signing in, and staying signed in.
///
/// Only the anonymous path is implemented here: it is the one that needs the
/// app to hold something durable of its own. The email-code flow keeps its
/// state on the server, behind an address the user already has.
class AuthRepository {
  AuthRepository(this._api, this._store);

  final ApiClient _api;
  final SessionStore _store;

  /// Create an anonymous account.
  ///
  /// Nothing about the person is sent: no email, no chosen name. What *is*
  /// sent is the notice they were shown — the account is not created without
  /// it, exactly as for a registered member.
  Future<AppSession> signInAsGuest({required List<RiskNotice> accepted}) async {
    final data = await _api.postJson('/api/v1/auth/guest', body: {
      'accepted_documents': [
        for (final notice in accepted) {'id': notice.id, 'version': notice.version},
      ],
    }) as Map<String, dynamic>;

    final session = AppSession.guestFromJson(data);
    await _persist(session);
    // Shown once by the API and never again: if this write fails the account
    // is unreachable forever, so it happens before anything else can throw.
    final key = session.guestKey;
    if (key != null) await _store.saveGuestKey(key);
    return session;
  }

  /// Come back to the anonymous account stored on this device.
  ///
  /// Returns null when there is nothing to come back to, or when the key is no
  /// longer good — a wiped test database, an account removed. Either way the
  /// app falls back to the welcome screen instead of failing to start.
  Future<AppSession?> resumeGuest() async {
    final key = await _store.readGuestKey();
    if (key == null || key.isEmpty) return null;
    try {
      final data = await _api.postJson(
        '/api/v1/auth/guest/resume',
        body: {'guest_key': key},
      ) as Map<String, dynamic>;
      final session = AppSession.guestFromJson(data);
      await _persist(session);
      return session;
    } on ApiException {
      return null;
    }
  }

  Future<void> _persist(AppSession session) async {
    _api.authToken = session.accessToken;
    await _store.saveTokens(
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
      displayName: session.displayName,
    );
  }

  /// Sign out, keeping the anonymous account recoverable.
  Future<void> signOut() async {
    _api.authToken = null;
    await _store.clearTokens();
  }
}
