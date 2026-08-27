import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/models/chat.dart';

void main() {
  group('Chat.fromJson', () {
    test('legge una riga reale con la join sui membri', () {
      final chat = Chat.fromJson({
        'id': 'c1',
        // In produzione è un booleano `is_group`, non un `kind` testuale: la
        // migration storica 0001 descriveva tutt'altro.
        'is_group': true,
        'name': 'Roma nord',
        'created_by': 'u1',
        'created_at': '2026-08-27T10:00:00Z',
        'chat_members': [
          {
            'user_id': 'u1',
            'joined_at': '2026-08-27T10:00:00Z',
            'profiles': {'username': 'sergio'},
          },
          {
            'user_id': 'u2',
            'profiles': {'username': 'giulia'},
          },
        ],
      });

      expect(chat.isGroup, isTrue);
      expect(chat.members.length, 2);
      expect(chat.members.first.displayName, 'sergio');
      expect(chat.titleFor('u1'), 'Roma nord');
    });

    test('una chat a due prende il nome dall\'altra persona', () {
      final chat = Chat.fromJson({
        'id': 'c2',
        'is_group': false,
        'chat_members': [
          {
            'user_id': 'io',
            'profiles': {'username': 'sergio'},
          },
          {
            'user_id': 'altro',
            'profiles': {'username': 'giulia'},
          },
        ],
      });

      // Il punto: senza sapere chi guarda, mostreremmo il nome di chi guarda.
      expect(chat.titleFor('io'), 'giulia');
      expect(chat.titleFor('altro'), 'sergio');
    });

    test('un gruppo senza nome non resta senza titolo', () {
      final chat = Chat.fromJson({'id': 'c3', 'is_group': true, 'name': '  '});
      expect(chat.titleFor('io'), 'Gruppo');
    });

    test('regge una riga senza join e senza campi opzionali', () {
      final chat = Chat.fromJson({'id': 'c4'});
      expect(chat.isGroup, isFalse);
      expect(chat.members, isEmpty);
      expect(chat.titleFor('io'), 'Conversazione');
    });
  });

  group('ChatMessage', () {
    test('legge una riga reale', () {
      final m = ChatMessage.fromJson({
        'id': 'm1',
        'chat_id': 'c1',
        'body': 'ci vediamo all\'EUR',
        // `sender_id`, non `author_id`: verificato sondando la produzione.
        'sender_id': 'u2',
        'created_at': '2026-08-27T11:00:00Z',
        'profiles': {'username': 'giulia'},
      });

      expect(m.body, 'ci vediamo all\'EUR');
      expect(m.displayName, 'giulia');
      expect(m.isMine('u2'), isTrue);
      expect(m.isMine('u1'), isFalse);
      expect(m.isFromDeletedAccount, isFalse);
    });

    test('un account eliminato lascia il messaggio senza autore', () {
      // Alla cancellazione i messaggi vengono pseudonimizzati, non rimossi:
      // toglierli lascerebbe a metà la conversazione degli altri, che non
      // hanno chiesto niente.
      final m = ChatMessage.fromJson({
        'id': 'm2',
        'chat_id': 'c1',
        'body': 'resta qui',
        'sender_id': null,
      });

      expect(m.isFromDeletedAccount, isTrue);
      expect(m.displayName, 'Utente eliminato');
      // Nessuno può rivendicare un messaggio senza autore, nemmeno per sbaglio.
      expect(m.isMine(null), isFalse);
      expect(m.isMine('u1'), isFalse);
    });

    test('senza join sul profilo usa un nome generico', () {
      // È il caso dei messaggi che arrivano da Realtime: la riga è grezza.
      final m = ChatMessage.fromJson({
        'id': 'm3',
        'chat_id': 'c1',
        'body': 'x',
        'sender_id': 'u9',
      });
      expect(m.displayName, 'Traceur');
    });
  });

  group('ChatMember', () {
    test('un nome vuoto non lascia una riga vuota', () {
      final m = ChatMember.fromJson({
        'user_id': 'u1',
        'profiles': {'username': '   '},
      });
      expect(m.displayName, 'Traceur');
    });
  });
}
