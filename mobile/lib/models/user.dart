/// The authenticated account, as returned by `GET /api/v1/users/me`.
///
/// Mirrors `UserOut` in `backend/app/schemas/user.py`. Kept tolerant:
/// unknown/missing fields default, never throw.
class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.displayName,
    this.role = 'user',
    this.isEmailVerified = false,
  });

  final String id;
  final String email;
  final String displayName;

  /// `user` | `admin`. Regular users can only browse the map and submit
  /// spots for review; publishing (verifying) spots is admin-only and
  /// enforced server-side — this flag exists purely to adapt the UI.
  final String role;

  final bool isEmailVerified;

  bool get isAdmin => role == 'admin';

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'] as String,
        email: (json['email'] as String?) ?? '',
        displayName: (json['display_name'] as String?) ?? '',
        role: (json['role'] as String?) ?? 'user',
        isEmailVerified: (json['is_email_verified'] as bool?) ?? false,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'email': email,
        'display_name': displayName,
        'role': role,
        'is_email_verified': isEmailVerified,
      };
}
