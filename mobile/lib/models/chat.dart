/// Una conversazione: privata a due, oppure di gruppo.
///
/// Colonne reali di `chats`: `id, created_by, created_at, name, is_group`.
/// Attenzione: `is_group` è un **booleano**, non un `kind` testuale — la
/// migration storica `0001_initial.sql` descriveva tutt'altro.
class Chat {
  const Chat({
    required this.id,
    required this.isGroup,
    this.name,
    this.createdBy,
    this.createdAt,
    this.members = const [],
    this.lastMessage,
  });

  final String id;
  final bool isGroup;

  /// Il nome del gruppo. Nelle chat a due è null: il titolo è l'altra persona.
  final String? name;

  final String? createdBy;
  final DateTime? createdAt;

  final List<ChatMember> members;
  final ChatMessage? lastMessage;

  /// Come chiamarla nell'elenco.
  ///
  /// Per una chat a due serve [me] per capire chi sia «l'altro»: senza,
  /// mostreremmo il nome di chi guarda.
  String titleFor(String? me) {
    if (isGroup) return name?.trim().isNotEmpty == true ? name! : 'Gruppo';
    final other = members.where((m) => m.userId != me).toList();
    return other.isEmpty ? 'Conversazione' : other.first.displayName;
  }

  factory Chat.fromJson(Map<String, dynamic> json) => Chat(
    id: json['id'] as String,
    isGroup: (json['is_group'] as bool?) ?? false,
    name: (json['name'] as String?)?.trim(),
    createdBy: json['created_by'] as String?,
    createdAt: _date(json['created_at']),
    members: (json['chat_members'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(ChatMember.fromJson)
        .toList(growable: false),
  );

  Chat copyWith({List<ChatMember>? members, ChatMessage? lastMessage}) => Chat(
    id: id,
    isGroup: isGroup,
    name: name,
    createdBy: createdBy,
    createdAt: createdAt,
    members: members ?? this.members,
    lastMessage: lastMessage ?? this.lastMessage,
  );

  static DateTime? _date(Object? v) =>
      v is String ? DateTime.tryParse(v) : null;
}

/// Un partecipante. Colonne reali: `chat_id, user_id, joined_at`.
class ChatMember {
  const ChatMember({required this.userId, this.username, this.joinedAt});

  final String userId;
  final String? username;
  final DateTime? joinedAt;

  String get displayName =>
      (username?.trim().isNotEmpty == true) ? username!.trim() : 'Traceur';

  factory ChatMember.fromJson(Map<String, dynamic> json) {
    // La join su `profiles` può arrivare come oggetto o mancare del tutto.
    final profile = json['profiles'];
    return ChatMember(
      userId: json['user_id'] as String,
      username:
          profile is Map<String, dynamic>
              ? profile['username'] as String?
              : json['username'] as String?,
      joinedAt: v(json['joined_at']),
    );
  }

  static DateTime? v(Object? x) => x is String ? DateTime.tryParse(x) : null;
}

/// Un messaggio. Colonne reali: `id, chat_id, body, created_at, sender_id`.
class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.chatId,
    required this.body,
    this.senderId,
    this.senderName,
    this.createdAt,
  });

  final String id;
  final String chatId;
  final String body;

  /// **null quando l'account è stato eliminato.**
  ///
  /// Il messaggio resta nella conversazione degli altri partecipanti, senza
  /// autore: cancellarlo toglierebbe a loro metà della conversazione, e loro
  /// non hanno chiesto niente.
  final String? senderId;

  final String? senderName;
  final DateTime? createdAt;

  bool get isFromDeletedAccount => senderId == null;

  String get displayName =>
      isFromDeletedAccount ? 'Utente eliminato' : (senderName ?? 'Traceur');

  bool isMine(String? me) => me != null && senderId == me;

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    final profile = json['profiles'];
    return ChatMessage(
      id: json['id'] as String,
      chatId: json['chat_id'] as String,
      body: (json['body'] as String?) ?? '',
      senderId: json['sender_id'] as String?,
      senderName:
          profile is Map<String, dynamic>
              ? profile['username'] as String?
              : json['sender_name'] as String?,
      createdAt:
          json['created_at'] is String
              ? DateTime.tryParse(json['created_at'] as String)
              : null,
    );
  }
}
