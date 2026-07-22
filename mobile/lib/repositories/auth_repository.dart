import '../models/auth_tokens.dart';
import '../services/api_client.dart';

/// Register/login against the backend auth endpoints.
class AuthRepository {
  AuthRepository(this._api);

  final ApiClient _api;

  static const String _authPath = '/api/v1/auth';

  /// Create a new account. The backend returns the user profile, not tokens —
  /// call [login] afterwards to obtain a [AuthTokens] pair.
  Future<void> register({
    required String email,
    required String password,
    required String displayName,
  }) async {
    await _api.postJson('$_authPath/register', body: {
      'email': email,
      'password': password,
      'display_name': displayName,
    });
  }

  /// Exchange credentials for a JWT pair.
  Future<AuthTokens> login({
    required String email,
    required String password,
  }) async {
    final data = await _api.postJson('$_authPath/login', body: {
      'email': email,
      'password': password,
    });
    return AuthTokens.fromJson(data as Map<String, dynamic>);
  }
}
