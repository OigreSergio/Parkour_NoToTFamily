import 'dart:convert';

import 'package:flutter/services.dart' show AssetBundle, rootBundle;

import '../models/fountain.dart';

/// Reads the merged Rome drinking-fountain dataset bundled with the app.
///
/// The asset is produced offline by `backend/scripts/build_fountains_dataset.py`,
/// which cross-references OpenStreetMap (Overpass) and Wikidata and merges
/// duplicate records by proximity. Bundling it keeps the fountains map fully
/// offline and avoids hammering the public Overpass API from every client.
class FountainRepository {
  FountainRepository({AssetBundle? bundle}) : _bundle = bundle ?? rootBundle;

  final AssetBundle _bundle;

  static const String assetPath = 'assets/data/fountains_roma.json';

  Future<FountainDataset> loadFountains() async {
    final raw = await _bundle.loadString(assetPath);
    return FountainDataset.fromJson(jsonDecode(raw) as Map<String, dynamic>);
  }
}
