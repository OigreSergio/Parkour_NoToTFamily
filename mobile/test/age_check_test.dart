import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/models/profile.dart';

void main() {
  // Data fissa: un test sull'età che dipende da "oggi" comincia a fallire da
  // solo il giorno del compleanno di qualcuno.
  final oggi = DateTime(2026, 8, 27);

  group('AgeCheck', () {
    test('sedici anni compiuti: può aprire un account', () {
      expect(AgeCheck.of(DateTime(2010, 8, 27), now: oggi), AgeCheck.ok);
      expect(AgeCheck.of(DateTime(1990, 1, 1), now: oggi), AgeCheck.ok);
    });

    test(
      'il giorno prima del sedicesimo compleanno è ancora troppo presto',
      () {
        expect(
          AgeCheck.of(DateTime(2010, 8, 28), now: oggi),
          AgeCheck.tooYoung,
        );
      },
    );

    test('il compleanno stesso conta', () {
      // Compiere gli anni oggi basta: non si aspetta il giorno dopo.
      expect(AgeCheck.of(DateTime(2010, 8, 27), now: oggi), AgeCheck.ok);
    });

    test('sotto soglia: strada del genitore, non un muro', () {
      expect(AgeCheck.of(DateTime(2014, 3, 10), now: oggi), AgeCheck.tooYoung);
    });

    test('date impossibili sono invalide, non "troppo giovane"', () {
      expect(AgeCheck.of(null, now: oggi), AgeCheck.invalid);
      // Nel futuro.
      expect(AgeCheck.of(DateTime(2030, 1, 1), now: oggi), AgeCheck.invalid);
      // Oltre i 120 anni: più probabile un errore di battitura.
      expect(AgeCheck.of(DateTime(1850, 1, 1), now: oggi), AgeCheck.invalid);
    });

    test('la soglia è 16, come l\'art. 8 GDPR', () {
      // Se qualcuno la abbassa, deve essere una decisione consapevole: sotto
      // soglia serve il consenso verificabile di un genitore, e verificarlo
      // davvero è il problema che questa soglia evita.
      expect(AgeCheck.minimumAge, 16);
    });
  });

  group('Profile', () {
    test('legge una riga con le colonne della migration 0005', () {
      final p = Profile.fromJson({
        'id': 'u1',
        'username': 'sergio',
        'role': 'admin',
        'banned': false,
        'age_confirmed_at': '2026-08-27T10:00:00Z',
        'supervised': true,
        'supervisor_confirmed_at': '2026-08-27T10:00:00Z',
        'chat_enabled': false,
        'created_at': '2026-07-19T13:05:29Z',
      });

      expect(p.isAdmin, isTrue);
      expect(p.supervised, isTrue);
      expect(p.chatEnabled, isFalse);
      expect(p.canUseChat, isFalse);
      expect(p.isPendingDeletion, isFalse);
    });

    test('resta tollerante se la migration 0005 non è ancora applicata', () {
      // Nessuna delle colonne nuove è presente: l'app deve funzionare comunque.
      final p = Profile.fromJson({'id': 'u2', 'username': 'ospite'});

      expect(p.supervised, isFalse);
      expect(p.chatEnabled, isTrue);
      expect(p.ageConfirmedAt, isNull);
      expect(p.role, 'user');
    });

    test('un utente bannato non può usare la chat', () {
      final p = Profile.fromJson({
        'id': 'u3',
        'username': 'x',
        'banned': true,
        'chat_enabled': true,
      });
      expect(p.canUseChat, isFalse);
    });
  });
}
