/// Il profilo pubblico di un membro, dalla tabella `profiles`.
///
/// Colonne reali: `id, username, avatar_url, role, banned, created_at`, più
/// quelle aggiunte dalla migration `0005`: `age_confirmed_at`, `supervised`,
/// `supervisor_confirmed_at`, `chat_enabled`, `deletion_requested_at`.
///
/// Tollerante per costruzione: se una colonna non c'è ancora — perché la
/// migration non è stata applicata — il modello usa un default invece di
/// lanciare.
class Profile {
  const Profile({
    required this.id,
    required this.username,
    this.avatarUrl,
    this.role = 'user',
    this.banned = false,
    this.ageConfirmedAt,
    this.supervised = false,
    this.supervisorConfirmedAt,
    this.chatEnabled = true,
    this.deletionRequestedAt,
    this.createdAt,
  });

  final String id;
  final String username;
  final String? avatarUrl;

  /// `user` | `instructor` | `admin`.
  ///
  /// `instructor` è un riconoscimento concesso da un admin, non un livello a
  /// pagamento; `admin` si assegna solo a livello di database.
  final String role;

  final bool banned;

  /// Quando l'utente ha dichiarato di avere almeno 16 anni.
  final DateTime? ageConfirmedAt;

  /// Account aperto da un adulto per un minore che lo usa sotto la sua
  /// supervisione. Il titolare resta l'adulto.
  final bool supervised;

  final DateTime? supervisorConfirmedAt;

  /// Sugli account supervisionati nasce `false`. Il vincolo è applicato anche
  /// nelle policy del database: spegnerlo qui non basterebbe.
  final bool chatEnabled;

  /// Inizio dei 30 giorni di grazia prima della cancellazione definitiva.
  final DateTime? deletionRequestedAt;

  final DateTime? createdAt;

  bool get isAdmin => role == 'admin';
  bool get isInstructor => role == 'instructor';
  bool get isPendingDeletion => deletionRequestedAt != null;

  /// Può scrivere in chat? La risposta vera la dà il database
  /// (`can_use_chat()`); qui serve solo a non mostrare una UI che fallirebbe.
  bool get canUseChat => chatEnabled && !banned;

  factory Profile.fromJson(Map<String, dynamic> json) => Profile(
    id: json['id'] as String,
    username: (json['username'] as String?) ?? '',
    avatarUrl: json['avatar_url'] as String?,
    role: (json['role'] as String?) ?? 'user',
    banned: (json['banned'] as bool?) ?? false,
    ageConfirmedAt: _date(json['age_confirmed_at']),
    supervised: (json['supervised'] as bool?) ?? false,
    supervisorConfirmedAt: _date(json['supervisor_confirmed_at']),
    chatEnabled: (json['chat_enabled'] as bool?) ?? true,
    deletionRequestedAt: _date(json['deletion_requested_at']),
    createdAt: _date(json['created_at']),
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'username': username,
    'avatar_url': avatarUrl,
    'role': role,
    'banned': banned,
    'age_confirmed_at': ageConfirmedAt?.toIso8601String(),
    'supervised': supervised,
    'supervisor_confirmed_at': supervisorConfirmedAt?.toIso8601String(),
    'chat_enabled': chatEnabled,
    'deletion_requested_at': deletionRequestedAt?.toIso8601String(),
    'created_at': createdAt?.toIso8601String(),
  };

  static DateTime? _date(Object? v) =>
      v is String ? DateTime.tryParse(v) : null;
}

/// Esito del controllo di età in fase di registrazione.
enum AgeCheck {
  /// 16 anni compiuti: può aprire un account proprio.
  ok,

  /// Sotto i 16: niente account proprio, ma può chiedere a un genitore.
  tooYoung,

  /// Data non plausibile o non inserita.
  invalid;

  /// Soglia dell'art. 8 GDPR.
  ///
  /// Il regolamento fissa 16 anni per il consenso diretto dei minori e lascia
  /// agli Stati la facoltà di abbassarla; l'Italia è a 14. Sotto soglia serve
  /// il consenso **verificabile** di chi esercita la responsabilità
  /// genitoriale, e per un servizio gratuito gestito da una persona sola non
  /// c'è modo realistico di verificarlo. Fissando 16 il problema non si pone.
  static const int minimumAge = 16;

  static AgeCheck of(DateTime? birthDate, {DateTime? now}) {
    if (birthDate == null) return AgeCheck.invalid;

    final today = now ?? DateTime.now();
    if (birthDate.isAfter(today)) return AgeCheck.invalid;
    // Oltre i 120 anni è più probabile un errore di battitura che un record.
    if (today.difference(birthDate).inDays > 120 * 366) return AgeCheck.invalid;

    var age = today.year - birthDate.year;
    final hasHadBirthday =
        today.month > birthDate.month ||
        (today.month == birthDate.month && today.day >= birthDate.day);
    if (!hasHadBirthday) age--;

    return age >= minimumAge ? AgeCheck.ok : AgeCheck.tooYoung;
  }
}
