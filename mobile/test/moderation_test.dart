import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/repositories/moderation_repository.dart';

void main() {
  group('ReportKind', () {
    test('ogni tipo scrive nella propria colonna', () {
      // Il vincolo `reports_needs_target` accetta esattamente un bersaglio: se
      // qui la colonna fosse sbagliata, la segnalazione verrebbe rifiutata dal
      // database e chi segnala non capirebbe perché.
      expect(ReportKind.spot.column, 'spot_id');
      expect(ReportKind.message.column, 'message_id');
      expect(ReportKind.comment.column, 'comment_id');
      expect(ReportKind.post.column, 'post_id');
      expect(ReportKind.profile.column, 'profile_id');
    });

    test('si può segnalare anche uno spot e una persona', () {
      // Prima della migration 0009 `reports` non aveva né spot_id né
      // profile_id: uno spot pericoloso non era segnalabile, e un utente
      // molesto lo si poteva segnalare solo attraverso un suo messaggio.
      final kinds = ReportKind.values.map((k) => k.name).toSet();
      expect(kinds, containsAll(['spot', 'profile']));
    });
  });

  group('ModerationNotice', () {
    test('legge una motivazione ricevuta', () {
      final n = ModerationNotice.fromJson({
        'id': 'n1',
        'target_kind': 'spot',
        'action': 'rifiutato',
        'reason': 'Lo spot è su proprietà privata.',
        'created_at': '2026-08-27T10:00:00Z',
      });

      expect(n.label, 'Proposta rifiutata');
      expect(n.reason, contains('proprietà privata'));
      expect(n.isUnread, isTrue);
    });

    test('una già letta non risulta da leggere', () {
      final n = ModerationNotice.fromJson({
        'id': 'n2',
        'action': 'rimosso',
        'reason': 'x',
        'read_at': '2026-08-27T11:00:00Z',
      });
      expect(n.isUnread, isFalse);
      expect(n.label, 'Contenuto rimosso');
    });

    test('un\'azione sconosciuta non lascia l\'etichetta vuota', () {
      // Se un domani il database introduce un\'azione nuova, l\'utente deve
      // comunque leggere qualcosa di sensato.
      final n = ModerationNotice.fromJson({
        'id': 'n3',
        'action': 'qualcosa_di_nuovo',
        'reason': 'y',
      });
      expect(n.label, 'Decisione di moderazione');
    });

    test('regge una riga incompleta', () {
      final n = ModerationNotice.fromJson({'id': 'n4'});
      expect(n.reason, '');
      expect(n.action, '');
      expect(n.createdAt, isNull);
    });
  });
}
