/// The account behind the current session.
///
/// Mirrors the backend `UserOut` schema (see `backend/app/schemas/user.py`).
/// Parsing is deliberately tolerant: a missing or unexpected field falls back
/// to a default instead of throwing, so an older client keeps working against
/// a newer API.
class Account {
  const Account({
    required this.id,
    required this.displayName,
    this.email,
    this.role = 'user',
    this.isGuest = false,
    this.isSubscribed = false,
    this.isEmailVerified = false,
  });

  final String id;
  final String displayName;

  /// `null` for guest accounts — they sign in without an email.
  final String? email;

  /// `user` (everyone), `instructor` (granted by an admin) or `admin`.
  final String role;
  final bool isGuest;
  final bool isSubscribed;
  final bool isEmailVerified;

  bool get isInstructor => role == 'instructor';
  bool get isAdmin => role == 'admin';

  /// First letter of the display name, for the avatar.
  String get initial =>
      displayName.isEmpty ? '?' : displayName.substring(0, 1).toUpperCase();

  factory Account.fromJson(Map<String, dynamic> json) {
    final name = (json['display_name'] as String?)?.trim();
    final email = (json['email'] as String?)?.trim();
    return Account(
      id: '${json['id'] ?? ''}',
      displayName: (name == null || name.isEmpty) ? 'Traceur' : name,
      email: (email == null || email.isEmpty) ? null : email,
      role: (json['role'] as String?) ?? 'user',
      isGuest: json['is_guest'] as bool? ?? false,
      isSubscribed: json['is_subscribed'] as bool? ?? false,
      isEmailVerified: json['is_email_verified'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'display_name': displayName,
        'email': email,
        'role': role,
        'is_guest': isGuest,
        'is_subscribed': isSubscribed,
        'is_email_verified': isEmailVerified,
      };
}
