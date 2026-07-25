/// A tutorial/training video.
///
/// Matches the backend `VideoOut` schema (`backend/app/schemas/video.py`).
/// Access tiers are decided by the backend: `beginner` videos are free for
/// everyone (including guests signed in without an email), higher levels come
/// back with `locked == true` and `url == null` until the user subscribes.
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
    this.isPremium = false,
    this.locked = false,
    this.landed = false,
    required this.createdAt,
  });

  final String id;
  final String title;
  final String description;

  /// Playback URL — `null` when [locked] (the backend hides it).
  final String? url;

  final String? thumbnailUrl;

  /// `recovery` | `practice` | `conditioning`.
  final String category;

  /// `beginner` | `intermediate` | `advanced`.
  final String level;

  /// Tutorial grid grouping: `flips` | `basics` | `vaults` | `wall_tricks` |
  /// `bar_tricks` | `ground_tricks` | `other`. `null` for non-tutorial videos.
  final String? trickCategory;

  /// 1–10, where 10 is the hardest. Drives the difficulty gauge.
  final int difficulty;

  final int durationSeconds;

  /// True for videos above beginner level (subscription required to watch).
  final bool isPremium;

  /// True when the current viewer cannot watch this video yet.
  final bool locked;

  /// Whether the current user has landed this trick. Client-side field;
  /// defaults to `false` until the backend persists it (see roadmap).
  final bool landed;

  final DateTime createdAt;

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
        isPremium: isPremium,
        locked: locked,
        landed: landed ?? this.landed,
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
        isPremium: (json['is_premium'] as bool?) ?? false,
        locked: (json['locked'] as bool?) ?? false,
        landed: (json['landed'] as bool?) ?? false,
        createdAt: json['created_at'] == null
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
        'is_premium': isPremium,
        'locked': locked,
        'landed': landed,
        'created_at': createdAt.toIso8601String(),
      };
}
