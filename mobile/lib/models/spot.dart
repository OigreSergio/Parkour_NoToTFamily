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
    required this.difficulty,
    required this.status,
    required this.submittedBy,
    required this.verifiedAt,
    required this.createdAt,
  });

  final String id;
  final String name;
  final String description;
  final GeoPoint location;
  final List<String> photoUrls;

  /// 1–5, where 5 is the hardest.
  final int difficulty;

  /// `pending` | `verified` | `rejected`.
  final String status;
  final String? submittedBy;
  final DateTime? verifiedAt;
  final DateTime createdAt;

  factory Spot.fromJson(Map<String, dynamic> json) => Spot(
        id: json['id'] as String,
        name: json['name'] as String,
        description: (json['description'] as String?) ?? '',
        location: GeoPoint.fromJson(json['location'] as Map<String, dynamic>),
        photoUrls: (json['photo_urls'] as List<dynamic>? ?? const [])
            .map((e) => e as String)
            .toList(growable: false),
        difficulty: (json['difficulty'] as num?)?.toInt() ?? 1,
        status: (json['status'] as String?) ?? 'verified',
        submittedBy: json['submitted_by'] as String?,
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
        'difficulty': difficulty,
        'status': status,
        'submitted_by': submittedBy,
        'verified_at': verifiedAt?.toIso8601String(),
        'created_at': createdAt.toIso8601String(),
      };
}
