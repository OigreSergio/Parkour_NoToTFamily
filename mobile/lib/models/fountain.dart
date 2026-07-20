import 'package:latlong2/latlong.dart';

/// A public drinking fountain in Rome from the bundled merged dataset
/// (`assets/data/fountains_roma.json`).
///
/// Each record is the result of cross-referencing the open databases behind
/// the popular fountain apps — OpenStreetMap (used by WeTap, Fontanelle
/// d'Italia, …) and Wikidata — merged by proximity, so [sources] lists every
/// database that confirms this fountain and [confidence] counts them.
/// See `backend/scripts/build_fountains_dataset.py` for the pipeline.
class Fountain {
  const Fountain({
    required this.id,
    required this.lat,
    required this.lon,
    this.name,
    required this.kind,
    required this.sources,
    required this.refs,
    required this.confidence,
    this.wheelchair,
    this.bottle,
  });

  final String id;
  final double lat;
  final double lon;

  /// Proper name when one of the sources has it (e.g. "Fontana dei Libri").
  final String? name;

  /// `nasone` | `drinking_water` | `water_tap` | `fountain`.
  final String kind;

  /// Source datasets confirming this fountain
  /// (e.g. `osm_drinking_water`, `wikidata`).
  final List<String> sources;

  /// Upstream identifiers (e.g. `osm:node/123`, `wikidata:Q42`).
  final List<String> refs;

  /// Number of independent sources that confirm this fountain (>= 1).
  final int confidence;

  /// OSM `wheelchair` tag when present (`yes` | `no` | `limited`).
  final String? wheelchair;

  /// OSM `bottle` tag when present — whether a bottle can be refilled.
  final String? bottle;

  LatLng toLatLng() => LatLng(lat, lon);

  /// Display name: the proper name when known, otherwise a label for [kind].
  String get displayName => name ?? kindLabel;

  String get kindLabel => switch (kind) {
        'nasone' => 'Nasone',
        'water_tap' => 'Public tap',
        'fountain' => 'Drinkable fountain',
        _ => 'Drinking fountain',
      };

  factory Fountain.fromJson(Map<String, dynamic> json) => Fountain(
        id: json['id'] as String,
        lat: (json['lat'] as num).toDouble(),
        lon: (json['lon'] as num).toDouble(),
        name: json['name'] as String?,
        kind: (json['kind'] as String?) ?? 'drinking_water',
        sources: (json['sources'] as List<dynamic>? ?? const [])
            .map((e) => e as String)
            .toList(growable: false),
        refs: (json['refs'] as List<dynamic>? ?? const [])
            .map((e) => e as String)
            .toList(growable: false),
        confidence: (json['confidence'] as num?)?.toInt() ?? 1,
        wheelchair: json['wheelchair'] as String?,
        bottle: json['bottle'] as String?,
      );
}

/// The parsed dataset: fountains plus the attribution metadata that must be
/// shown in the UI (OSM data is ODbL-licensed).
class FountainDataset {
  const FountainDataset({required this.fountains, required this.attribution});

  final List<Fountain> fountains;
  final List<String> attribution;

  factory FountainDataset.fromJson(Map<String, dynamic> json) {
    final meta = json['meta'] as Map<String, dynamic>? ?? const {};
    return FountainDataset(
      fountains: (json['fountains'] as List<dynamic>? ?? const [])
          .map((e) => Fountain.fromJson(e as Map<String, dynamic>))
          .toList(growable: false),
      attribution: (meta['attribution'] as List<dynamic>? ?? const [])
          .map((e) => e as String)
          .toList(growable: false),
    );
  }
}
