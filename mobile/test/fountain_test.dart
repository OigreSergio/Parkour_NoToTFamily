import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/models/fountain.dart';
import 'package:parkour_notot/repositories/fountain_repository.dart';

const _sampleDataset = {
  'meta': {
    'city': 'Roma',
    'attribution': ['© OpenStreetMap contributors (ODbL)', 'Wikidata (CC0)'],
  },
  'fountains': [
    {
      'id': 'rf-0001',
      'lat': 41.8948845,
      'lon': 12.4908938,
      'name': 'Fontana di piazza della Madonna dei Monti',
      'kind': 'nasone',
      'sources': ['osm_drinking_water', 'wikidata'],
      'refs': ['osm:node/246574150', 'wikidata:Q3747443'],
      'confidence': 2,
      'wheelchair': null,
      'bottle': null,
    },
    {
      'id': 'rf-1000',
      'lat': 41.9,
      'lon': 12.5,
      'name': null,
      'kind': 'drinking_water',
      'sources': ['osm_drinking_water'],
      'refs': ['osm:node/1'],
      'confidence': 1,
      'wheelchair': 'yes',
      'bottle': 'yes',
    },
  ],
};

/// Serves [_sampleDataset] for any asset key.
class _FakeBundle extends CachingAssetBundle {
  @override
  Future<ByteData> load(String key) async =>
      ByteData.sublistView(utf8.encode(jsonEncode(_sampleDataset)));
}

void main() {
  test('Fountain.fromJson parses a merged record', () {
    final json =
        (_sampleDataset['fountains'] as List).first as Map<String, dynamic>;
    final fountain = Fountain.fromJson(json);

    expect(fountain.id, 'rf-0001');
    expect(fountain.displayName, 'Fontana di piazza della Madonna dei Monti');
    expect(fountain.kind, 'nasone');
    expect(fountain.kindLabel, 'Nasone');
    expect(fountain.sources, ['osm_drinking_water', 'wikidata']);
    expect(fountain.confidence, 2);
    expect(fountain.toLatLng().latitude, closeTo(41.8948845, 1e-9));
  });

  test('unnamed fountains fall back to the kind label', () {
    final json =
        (_sampleDataset['fountains'] as List).last as Map<String, dynamic>;
    final fountain = Fountain.fromJson(json);

    expect(fountain.name, isNull);
    expect(fountain.displayName, 'Drinking fountain');
    expect(fountain.wheelchair, 'yes');
  });

  test('FountainRepository loads and parses the bundled asset', () async {
    final repo = FountainRepository(bundle: _FakeBundle());
    final dataset = await repo.loadFountains();

    expect(dataset.fountains, hasLength(2));
    expect(dataset.attribution, contains('Wikidata (CC0)'));
    expect(dataset.fountains.first.kind, 'nasone');
  });
}
