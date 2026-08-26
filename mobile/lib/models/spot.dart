import 'package:latlong2/latlong.dart';

/// A geographic point as returned by the backend (`{ "lat": .., "lng": .. }`).
///
/// Mirrors `Point` in `backend/app/schemas/spot.py`.
class GeoPoint {
  const GeoPoint({required this.lat, required this.lng});

  final double lat;
  final double lng;

  factory GeoPoint.fromJson(Map<String, dynamic> json) => GeoPoint(
        lat: (json['lat'] as num).toDouble(),
        lng: (json['lng'] as num).toDouble(),
      );

  Map<String, dynamic> toJson() => {'lat': lat, 'lng': lng};

  /// Convert to a `flutter_map` / `latlong2` coordinate.
  LatLng toLatLng() => LatLng(lat, lng);
}

/// A spot photo together with the attribution that must be shown next to it.
///
/// Mirrors `SpotPhoto` in `backend/app/schemas/spot.py`. Photos shot by the
/// crew carry no licence; photos reused from a free archive (Wikimedia
/// Commons) carry author, licence and a link to the original, which CC BY /
/// CC BY-SA require to be displayed wherever the image appears.
class SpotPhoto {
  const SpotPhoto({
    required this.url,
    this.kind = 'area',
    this.caption = '',
    this.author = '',
    this.license = '',
    this.licenseUrl = '',
    this.source = '',
    this.sourceUrl = '',
    this.date = '',
  });

  final String url;

  /// `spot` when the photo shows the obstacles themselves, `area` when it only
  /// shows the surrounding place — the app labels the two differently so a
  /// context shot is never mistaken for the spot.
  final String kind;

  final String caption;
  final String author;
  final String license;
  final String licenseUrl;
  final String source;
  final String sourceUrl;
  final String date;

  /// One-line credit, empty when there is nothing to attribute.
  String get credit {
    if (author.isEmpty && license.isEmpty) return '';
    return [
      if (author.isNotEmpty) author,
      if (license.isNotEmpty) license,
    ].join(' · ');
  }

  factory SpotPhoto.fromJson(Map<String, dynamic> json) => SpotPhoto(
        url: json['url'] as String,
        kind: (json['kind'] as String?) ?? 'area',
        caption: (json['caption'] as String?) ?? '',
        author: (json['author'] as String?) ?? '',
        license: (json['license'] as String?) ?? '',
        licenseUrl: (json['license_url'] as String?) ?? '',
        source: (json['source'] as String?) ?? '',
        sourceUrl: (json['source_url'] as String?) ?? '',
        date: (json['date'] as String?) ?? '',
      );

  Map<String, dynamic> toJson() => {
        'url': url,
        'kind': kind,
        'caption': caption,
        'author': author,
        'license': license,
        'license_url': licenseUrl,
        'source': source,
        'source_url': sourceUrl,
        'date': date,
      };
}

/// A parkour spot.
///
/// Matches the backend `SpotOut` schema (see `docs/DATA_MODEL.md` and
/// `backend/app/schemas/spot.py`). Only spots with `status == "verified"` are
/// returned by `GET /api/v1/spots`.
class Spot {
  const Spot({
    required this.id,
    required this.name,
    required this.description,
    required this.location,
    required this.photoUrls,
    this.photos = const [],
    required this.difficulty,
    this.surveyed = true,
    required this.status,
    this.water = false,
    required this.submittedBy,
    this.likes = 0,
    this.liked = false,
    required this.verifiedAt,
    required this.createdAt,
  });

  final String id;
  final String name;
  final String description;
  final GeoPoint location;
  final List<String> photoUrls;

  /// Same photos as [photoUrls], with their credits. Empty on older
  /// backends, which is why [photoUrls] is still the source of truth for
  /// what to display.
  final List<SpotPhoto> photos;

  /// 1–5, where 5 is the hardest.
  final int difficulty;

  /// `pending` | `verified` | `rejected`.
  final String status;

  /// False when the spot is on the map but nobody has surveyed its
  /// obstacles on site yet — the app says so instead of pretending the
  /// description is complete.
  final bool surveyed;

  /// Whether there is a drinking-water source (fountain, tap) at or near the
  /// spot. Client-side field; defaults to `false` until the backend exposes it.
  final bool water;

  final String? submittedBy;

  /// Total number of likes the spot has received.
  final int likes;

  /// Whether the current user has liked this spot. Toggle with [toggleLike].
  final bool liked;

  final DateTime? verifiedAt;
  final DateTime createdAt;

  /// Returns a copy with the like state flipped and the [likes] count adjusted
  /// accordingly — used for optimistic UI updates before the backend confirms.
  Spot toggleLike() => copyWith(
        liked: !liked,
        likes: liked ? likes - 1 : likes + 1,
      );

  Spot copyWith({
    bool? water,
    int? likes,
    bool? liked,
  }) =>
      Spot(
        id: id,
        name: name,
        description: description,
        location: location,
        photoUrls: photoUrls,
        photos: photos,
        difficulty: difficulty,
        surveyed: surveyed,
        status: status,
        water: water ?? this.water,
        submittedBy: submittedBy,
        likes: likes ?? this.likes,
        liked: liked ?? this.liked,
        verifiedAt: verifiedAt,
        createdAt: createdAt,
      );

  factory Spot.fromJson(Map<String, dynamic> json) => Spot(
        id: json['id'] as String,
        name: json['name'] as String,
        description: (json['description'] as String?) ?? '',
        location: GeoPoint.fromJson(json['location'] as Map<String, dynamic>),
        photoUrls: (json['photo_urls'] as List<dynamic>? ?? const [])
            .map((e) => e as String)
            .toList(growable: false),
        photos: (json['photos'] as List<dynamic>? ?? const [])
            .map((e) => SpotPhoto.fromJson(e as Map<String, dynamic>))
            .toList(growable: false),
        difficulty: (json['difficulty'] as num?)?.toInt() ?? 1,
        surveyed: (json['surveyed'] as bool?) ?? true,
        status: (json['status'] as String?) ?? 'verified',
        water: (json['water'] as bool?) ?? false,
        submittedBy: json['submitted_by'] as String?,
        likes: (json['likes'] as num?)?.toInt() ?? 0,
        liked: (json['liked'] as bool?) ?? false,
        verifiedAt: json['verified_at'] == null
            ? null
            : DateTime.parse(json['verified_at'] as String),
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'description': description,
        'location': location.toJson(),
        'photo_urls': photoUrls,
        'photos': photos.map((p) => p.toJson()).toList(),
        'difficulty': difficulty,
        'surveyed': surveyed,
        'status': status,
        'water': water,
        'submitted_by': submittedBy,
        'likes': likes,
        'liked': liked,
        'verified_at': verifiedAt?.toIso8601String(),
        'created_at': createdAt.toIso8601String(),
      };
}
