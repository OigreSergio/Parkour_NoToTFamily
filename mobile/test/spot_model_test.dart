import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/models/spot.dart';

void main() {
  group('Spot.fromJson', () {
    test('legge una riga reale della tabella spots', () {
      final spot = Spot.fromJson({
        'id': 'a1',
        'name': 'Foro Italico — Stadio dei Marmi',
        'lat': 41.9339,
        'lng': 12.4547,
        'description': 'Gradonate in marmo e muri alti.',
        'skill_level': 'avanzato',
        'crowd_level': 'tranquillo',
        'has_fountain': false,
        'status': 'verified',
        'author_id': 'u1',
        'created_at': '2026-07-19T13:05:29.823809+00:00',
        'verified_at': '2026-07-20T10:00:00+00:00',
      });

      expect(spot.name, 'Foro Italico — Stadio dei Marmi');
      expect(spot.location.lat, closeTo(41.9339, 1e-9));
      expect(spot.skillLabel, 'Avanzato');
      expect(spot.crowdLabel, 'Tranquillo');
      expect(spot.hasFountain, isFalse);
      expect(spot.isRated, isTrue);
      expect(spot.createdAt, isNotNull);
    });

    test('un attributo assente resta sconosciuto, non diventa un default', () {
      // È la regola che tiene onesta la mappa: i 1.680 spot importati non
      // hanno una valutazione, e inventarne una è peggio che ammetterlo.
      final spot = Spot.fromJson({
        'id': 'b2',
        'name': 'Spot Athens 3',
        'lat': 37.99,
        'lng': 23.73,
        'status': 'community',
      });

      expect(spot.skillLevel, isNull);
      expect(spot.skillLabel, isNull);
      expect(spot.crowdLabel, isNull);
      expect(spot.isRated, isFalse);
      // null ≠ false: "non sappiamo se c'è acqua" non è "non c'è acqua".
      expect(spot.hasFountain, isNull);
      expect(spot.completeness, SpotCompleteness.daCompletare);
    });

    test('non lancia su un payload malformato', () {
      // I modelli devono restare tolleranti: docs/PROJECT_RULES_AND_ROADMAP.md §3.
      final spot = Spot.fromJson({
        'id': 'c3',
        'lat': '45.07',
        'lng': null,
        'skill_level': '',
        'created_at': 'non-una-data',
      });

      expect(spot.name, 'Spot senza nome');
      expect(spot.location.lat, closeTo(45.07, 1e-9));
      expect(spot.location.lng, 0);
      expect(spot.skillLevel, isNull);
      expect(spot.createdAt, isNull);
    });
  });

  group('SpotPhoto', () {
    test('espone i crediti quando autore e licenza ci sono', () {
      final photo = SpotPhoto.fromJson({
        'url': 'https://images.mapillary.com/x.jpg',
        'author': 'mario',
        'license': 'CC-BY-SA 4.0',
        'source': 'mapillary',
      });

      expect(photo.credit, 'mario · CC-BY-SA 4.0');
    });

    test('nessun credito da mostrare per una foto della community', () {
      final photo = SpotPhoto.fromJson({'url': 'https://x/y.jpg'});
      expect(photo.credit, isNull);
    });
  });

  group('Spot.toggleLike', () {
    test('aggiorna conteggio e stato in modo ottimistico', () {
      const spot = Spot(
        id: 'a1',
        name: 'x',
        description: '',
        location: GeoPoint(lat: 0, lng: 0),
        likes: 3,
      );

      final liked = spot.toggleLike();
      expect(liked.liked, isTrue);
      expect(liked.likes, 4);
      expect(liked.toggleLike().likes, 3);
    });
  });
}
