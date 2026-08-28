/// Un video del catalogo.
///
/// Colonne reali di `videos` dopo le migration 0006 e 0008: `id, title, url,
/// category, level, created_at, is_starter, order_index, description,
/// safety_note, author, source, stage`.
///
/// **Non c'è più nessun gating.** Il servizio è gratuito e ogni video è
/// accessibile a chiunque, anche senza account: `is_premium` e `locked` non
/// esistono più, né qui né nelle policy. Il vecchio bundle li forzava a `false`
/// nel JavaScript mentre il database continuava a rifiutare — l'utente vedeva
/// un'interfaccia sbloccata e riceveva errori silenziosi.
class TutorialVideo {
  const TutorialVideo({
    required this.id,
    required this.title,
    required this.description,
    required this.url,
    required this.thumbnailUrl,
    required this.category,
    required this.level,
    this.trickCategory,
    this.difficulty = 1,
    this.durationSeconds = 0,
    this.landed = false,
    this.isStarter = false,
    this.orderIndex,
    this.stage,
    this.safetyNote,
    this.author,
    required this.createdAt,
  });

  final String id;
  final String title;
  final String description;

  /// Dove si guarda. **null quando la tappa del percorso non ha ancora un
  /// video**: la descrizione e la nota di sicurezza valgono già da sole, e
  /// mostrare «in arrivo» è meglio che far sparire la tappa.
  final String? url;

  final String? thumbnailUrl;

  /// `recovery` | `practice` | `conditioning`.
  final String category;

  /// `beginner` | `intermediate` | `advanced`.
  final String level;

  /// Il livello come lo legge una persona.
  ///
  /// `level` resta il valore del database (`beginner|intermediate|advanced`):
  /// è un dato, e tradurlo alla fonte romperebbe i filtri. Quello che si
  /// mostra però è italiano, come tutto il resto dell'app.
  String get livelloLeggibile => switch (level) {
    'beginner' => 'Principiante',
    'intermediate' => 'Intermedio',
    'advanced' => 'Avanzato',
    // Un valore che non conosciamo si mostra com'è: meglio una parola strana
    // che una etichetta sbagliata messa lì per non lasciare un buco.
    _ => level,
  };

  /// Tutorial grid grouping: `flips` | `basics` | `vaults` | `wall_tricks` |
  /// `bar_tricks` | `ground_tricks` | `other`. `null` for non-tutorial videos.
  final String? trickCategory;

  /// 1–10, where 10 is the hardest. Drives the difficulty gauge.
  final int difficulty;

  final int durationSeconds;

  /// Whether the current user has landed this trick. Client-side field;
  /// defaults to `false` until the backend persists it (see roadmap).
  final bool landed;

  /// Fa parte del percorso «Inizia da qui»?
  final bool isStarter;

  /// La posizione nel percorso. Un percorso senza ordine non è un percorso.
  final int? orderIndex;

  /// `riscaldamento` | `atterraggio` | `quadrupedia` | `precision` | `vault` |
  /// `progressione` | `recupero`. Null per i video fuori dal percorso.
  final String? stage;

  /// L'avvertenza specifica di questa tappa.
  ///
  /// Non è la stessa per tutti, ed è il motivo per cui sta sul singolo video e
  /// non in un banner generico: quello che serve sapere prima di una rullata
  /// non è quello che serve prima di un salto di precisione.
  final String? safetyNote;

  /// Chi ha fatto il video, verificato via oEmbed al momento del seed.
  final String? author;

  final DateTime createdAt;

  bool get hasVideo => url != null && url!.isNotEmpty;

  /// Returns a copy with the landed state flipped — optimistic UI update.
  TutorialVideo toggleLanded() => copyWith(landed: !landed);

  TutorialVideo copyWith({bool? landed}) => TutorialVideo(
    id: id,
    title: title,
    description: description,
    url: url,
    thumbnailUrl: thumbnailUrl,
    category: category,
    level: level,
    trickCategory: trickCategory,
    difficulty: difficulty,
    durationSeconds: durationSeconds,
    landed: landed ?? this.landed,
    isStarter: isStarter,
    orderIndex: orderIndex,
    stage: stage,
    safetyNote: safetyNote,
    author: author,
    createdAt: createdAt,
  );

  factory TutorialVideo.fromJson(Map<String, dynamic> json) => TutorialVideo(
    id: json['id'] as String,
    title: (json['title'] as String?) ?? '',
    description: (json['description'] as String?) ?? '',
    url: json['url'] as String?,
    thumbnailUrl: json['thumbnail_url'] as String?,
    category: (json['category'] as String?) ?? 'practice',
    level: (json['level'] as String?) ?? 'beginner',
    trickCategory: json['trick_category'] as String?,
    difficulty: (json['difficulty'] as num?)?.toInt() ?? 1,
    durationSeconds: (json['duration_seconds'] as num?)?.toInt() ?? 0,
    landed: (json['landed'] as bool?) ?? false,
    isStarter: (json['is_starter'] as bool?) ?? false,
    orderIndex: (json['order_index'] as num?)?.toInt(),
    stage: json['stage'] as String?,
    safetyNote: json['safety_note'] as String?,
    author: json['author'] as String?,
    createdAt:
        json['created_at'] == null
            ? DateTime.fromMillisecondsSinceEpoch(0)
            : DateTime.parse(json['created_at'] as String),
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'description': description,
    'url': url,
    'thumbnail_url': thumbnailUrl,
    'category': category,
    'level': level,
    'trick_category': trickCategory,
    'difficulty': difficulty,
    'duration_seconds': durationSeconds,
    'landed': landed,
    'is_starter': isStarter,
    'order_index': orderIndex,
    'stage': stage,
    'safety_note': safetyNote,
    'author': author,
    'created_at': createdAt.toIso8601String(),
  };
}
