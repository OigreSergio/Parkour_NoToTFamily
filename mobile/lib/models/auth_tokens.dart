/// JWT pair returned by `POST /api/v1/auth/login`.
///
/// Mirrors `TokenPair` in `backend/app/schemas/auth.py`.
class AuthTokens {
  const AuthTokens({required this.accessToken, required this.refreshToken});

  final String accessToken;
  final String refreshToken;

  factory AuthTokens.fromJson(Map<String, dynamic> json) => AuthTokens(
        accessToken: json['access_token'] as String,
        refreshToken: json['refresh_token'] as String,
      );
}
