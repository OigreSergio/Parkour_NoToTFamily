import 'package:flutter_map/flutter_map.dart' show LatLngBounds;
import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';

import 'package:parkour_notot/models/spot.dart';
import 'package:parkour_notot/services/spot_clustering.dart';
import 'package:parkour_notot/services/spot_filter.dart';

Spot _spot({
  required String id,
  required double lat,
  required double lng,
  String? skill,
  bool? water,
  SpotCompleteness completeness = SpotCompleteness.daCompletare,
}) => Spot(
  id: id,
  name: 'Spot $id',
  description: '',
  location: GeoPoint(lat: lat, lng: lng),
  skillLevel: skill,
  hasFountain: water,
  completeness: completeness,
);

/// Roma, all'incirca.
final _roma = LatLngBounds(
  const LatLng(41.80, 12.35),
  const LatLng(42.00, 12.65),
);

void main() {
  group('SpotClustering', () {
    test('scarta quello che è fuori dal viewport', () {
      final clusters = SpotClustering.clusterize(
        spots: [
          _spot(id: 'dentro', lat: 41.90, lng: 12.49),
          _spot(id: 'berlino', lat: 52.52, lng: 13.40),
          _spot(id: 'tokyo', lat: 35.68, lng: 139.69),
        ],
        bounds: _roma,
        zoom: 16,
      );

      expect(clusters.length, 1);
      expect(clusters.first.single.id, 'dentro');
    });

    test('tiene un margine attorno al viewport', () {
      // Poco fuori dal bordo: deve restare, altrimenti i marker comparirebbero
      // di scatto mentre si trascina la mappa.
      final clusters = SpotClustering.clusterize(
        spots: [_spot(id: 'appena-fuori', lat: 42.01, lng: 12.50)],
        bounds: _roma,
        zoom: 16,
      );
      expect(clusters.length, 1);
    });

    test('sopra lo zoom di dettaglio non raggruppa', () {
      final spots = [
        for (var i = 0; i < 40; i++)
          _spot(id: '$i', lat: 41.900 + i * 0.0001, lng: 12.490),
      ];

      final clusters = SpotClustering.clusterize(
        spots: spots,
        bounds: _roma,
        zoom: SpotClustering.detailZoom,
      );

      expect(clusters.length, 40);
      expect(clusters.every((c) => c.isSingle), isTrue);
    });

    test('a zoom basso raggruppa, senza perdere nessuno spot', () {
      final spots = [
        for (var i = 0; i < 400; i++)
          _spot(
            id: '$i',
            lat: 41.85 + (i % 20) * 0.005,
            lng: 12.40 + (i ~/ 20) * 0.005,
          ),
      ];

      final clusters = SpotClustering.clusterize(
        spots: spots,
        bounds: _roma,
        zoom: 10,
      );

      expect(clusters.length, lessThan(spots.length));
      // Nessuno spot deve sparire: raggruppare non è filtrare.
      final total = clusters.fold(0, (sum, c) => sum + c.count);
      expect(total, spots.length);
    });

    test('sotto la trentina mostra i singoli anche a zoom basso', () {
      final spots = [
        for (var i = 0; i < 12; i++)
          _spot(id: '$i', lat: 41.90 + i * 0.001, lng: 12.49),
      ];

      final clusters = SpotClustering.clusterize(
        spots: spots,
        bounds: _roma,
        zoom: 8,
      );
      expect(clusters.every((c) => c.isSingle), isTrue);
    });

    test('il viewport a cavallo dell\'antimeridiano non svuota la mappa', () {
      // west > east: succede sul Pacifico, e senza gestirlo la mappa lì si
      // svuota di colpo.
      final pacifico = LatLngBounds(
        const LatLng(-20, 170),
        const LatLng(20, -170),
      );

      final clusters = SpotClustering.clusterize(
        spots: [
          _spot(id: 'fiji', lat: -17.7, lng: 178.0),
          _spot(id: 'samoa', lat: -13.8, lng: -172.0),
          _spot(id: 'roma', lat: 41.9, lng: 12.5),
        ],
        bounds: pacifico,
        zoom: 16,
      );

      final ids = clusters.map((c) => c.single.id).toSet();
      expect(ids, {'fiji', 'samoa'});
    });

    test('un gruppo indica quello più raccontato e se ha contenuto', () {
      final cluster = SpotCluster(const LatLng(41.9, 12.5), [
        _spot(id: 'vuoto', lat: 41.9, lng: 12.5),
        _spot(
          id: 'buono',
          lat: 41.9,
          lng: 12.5,
          completeness: SpotCompleteness.verificato,
        ),
      ]);

      expect(cluster.best.id, 'buono');
      expect(cluster.hasContent, isTrue);
    });
  });

  group('SpotFilter', () {
    final spots = [
      _spot(id: 'segnaposto', lat: 41.9, lng: 12.5),
      _spot(
        id: 'raccontato',
        lat: 41.9,
        lng: 12.5,
        skill: 'principiante',
        water: true,
        completeness: SpotCompleteness.verificato,
      ),
      _spot(
        id: 'senza-acqua',
        lat: 41.9,
        lng: 12.5,
        skill: 'avanzato',
        water: false,
        completeness: SpotCompleteness.arricchito,
      ),
    ];

    test('senza filtri passa tutto', () {
      expect(const SpotFilter().apply(spots).length, 3);
      expect(const SpotFilter().isActive, isFalse);
    });

    test('«solo raccontati» nasconde i segnaposto', () {
      final out = const SpotFilter(onlyWithContent: true).apply(spots);
      expect(out.map((s) => s.id), ['raccontato', 'senza-acqua']);
    });

    test('«con acqua» esclude anche chi non lo sa', () {
      // hasFountain == null non passa: "non lo sappiamo" non è "sì". Chi filtra
      // per l'acqua parte con la borraccia mezza vuota, e un forse non aiuta.
      final out = const SpotFilter(onlyWithWater: true).apply(spots);
      expect(out.map((s) => s.id), ['raccontato']);
    });

    test('filtrare per livello esclude i non valutati', () {
      final out = const SpotFilter(levels: {'principiante'}).apply(spots);
      expect(out.map((s) => s.id), ['raccontato']);
    });

    test('i filtri si sommano', () {
      final out = const SpotFilter(
        onlyWithContent: true,
        levels: {'avanzato'},
      ).apply(spots);
      expect(out.map((s) => s.id), ['senza-acqua']);
    });
  });
}
