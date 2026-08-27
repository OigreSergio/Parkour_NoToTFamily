import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/chat.dart';

/// Le conversazioni: private a due e di gruppo.
///
/// Un avvertimento che vale più di ogni dettaglio tecnico: **non c'è cifratura
/// end-to-end**. I messaggi sono in chiaro nel database, e chi amministra il
/// progetto può tecnicamente leggerli. Va detto agli utenti, non nascosto —
/// promettere una riservatezza che non c'è sarebbe una dichiarazione falsa, e
/// su una chat che ospita anche minori è la cosa peggiore da fare.
///
/// Quello che è davvero garantito è che **gli altri utenti** non li leggono:
/// lo impongono le policy RLS, non questo codice.
class ChatRepository {
  const ChatRepository(this._db);

  final SupabaseClient _db;

  String? get _me => _db.auth.currentUser?.id;

  // ---------------------------------------------------------------------------
  // Lettura
  // ---------------------------------------------------------------------------

  /// Le conversazioni di cui faccio parte, con l'ultimo messaggio.
  Future<List<Chat>> myChats() async {
    final me = _me;
    if (me == null) return const [];

    final rows = await _db
        .from('chats')
        .select(
          'id, name, is_group, created_by, created_at, '
          'chat_members(user_id, joined_at, profiles(username))',
        )
        .order('created_at', ascending: false);

    final chats =
        rows.whereType<Map<String, dynamic>>().map(Chat.fromJson).toList();

    // Un'anteprima per ciascuna. Sono poche conversazioni per utente: una query
    // per chat costa meno di una vista da mantenere, e resta leggibile.
    final withPreview = <Chat>[];
    for (final chat in chats) {
      withPreview.add(chat.copyWith(lastMessage: await _lastMessage(chat.id)));
    }

    withPreview.sort((a, b) {
      final ta = a.lastMessage?.createdAt ?? a.createdAt;
      final tb = b.lastMessage?.createdAt ?? b.createdAt;
      if (ta == null || tb == null) return 0;
      return tb.compareTo(ta);
    });

    return withPreview;
  }

  Future<ChatMessage?> _lastMessage(String chatId) async {
    final row =
        await _db
            .from('messages')
            .select(
              'id, chat_id, body, sender_id, created_at, profiles(username)',
            )
            .eq('chat_id', chatId)
            .order('created_at', ascending: false)
            .limit(1)
            .maybeSingle();
    return row == null ? null : ChatMessage.fromJson(row);
  }

  Future<List<ChatMessage>> messages(String chatId, {int limit = 200}) async {
    final rows = await _db
        .from('messages')
        .select('id, chat_id, body, sender_id, created_at, profiles(username)')
        .eq('chat_id', chatId)
        .order('created_at')
        .limit(limit);

    return rows
        .whereType<Map<String, dynamic>>()
        .map(ChatMessage.fromJson)
        .toList(growable: false);
  }

  /// I messaggi in tempo reale.
  ///
  /// Realtime consegna la riga grezza, senza la join su `profiles`: il nome
  /// dell'autore non c'è. Chi consuma lo stream lo risolve dai membri della
  /// conversazione, che ha già in mano — meglio di una query per messaggio.
  Stream<List<ChatMessage>> watch(String chatId) => _db
      .from('messages')
      .stream(primaryKey: ['id'])
      .eq('chat_id', chatId)
      .order('created_at')
      .map((rows) => rows.map(ChatMessage.fromJson).toList(growable: false));

  // ---------------------------------------------------------------------------
  // Scrittura
  // ---------------------------------------------------------------------------

  /// Invia un messaggio.
  ///
  /// Può fallire per ragioni che il database impone e il client non decide:
  /// email non confermata, blocco fra i due utenti, limite di frequenza,
  /// account supervisionato con la chat spenta. [ChatException] li traduce in
  /// qualcosa di leggibile invece di mostrare un codice Postgres.
  Future<void> send({required String chatId, required String body}) async {
    final me = _me;
    if (me == null) throw const ChatException('Serve un account per scrivere.');

    final text = body.trim();
    if (text.isEmpty) return;
    if (text.length > 4000) {
      throw const ChatException(
        'Messaggio troppo lungo (massimo 4000 caratteri).',
      );
    }

    try {
      await _db.from('messages').insert({
        'chat_id': chatId,
        'sender_id': me,
        'body': text,
      });
    } on PostgrestException catch (e) {
      throw ChatException(_explain(e));
    }
  }

  /// Apre (o riapre) la conversazione a due con [otherUserId].
  ///
  /// Se ne esiste già una la riusa: due persone non devono ritrovarsi con tre
  /// conversazioni parallele perché hanno toccato il pulsante tre volte.
  Future<String> openDirect(String otherUserId) async {
    final me = _me;
    if (me == null) throw const ChatException('Serve un account.');
    if (me == otherUserId) {
      throw const ChatException('Non puoi aprire una chat con te stessə.');
    }

    final existing = await _findDirect(me, otherUserId);
    if (existing != null) return existing;

    try {
      final chat =
          await _db
              .from('chats')
              .insert({'is_group': false, 'created_by': me})
              .select('id')
              .single();

      final chatId = chat['id'] as String;
      await _db.from('chat_members').insert([
        {'chat_id': chatId, 'user_id': me},
        {'chat_id': chatId, 'user_id': otherUserId},
      ]);
      return chatId;
    } on PostgrestException catch (e) {
      throw ChatException(_explain(e));
    }
  }

  Future<String?> _findDirect(String me, String other) async {
    final mine = await _db
        .from('chat_members')
        .select('chat_id, chats!inner(is_group)')
        .eq('user_id', me)
        .eq('chats.is_group', false);

    final ids =
        mine
            .whereType<Map<String, dynamic>>()
            .map((r) => r['chat_id'] as String)
            .toList();
    if (ids.isEmpty) return null;

    final shared =
        await _db
            .from('chat_members')
            .select('chat_id')
            .eq('user_id', other)
            .inFilter('chat_id', ids)
            .limit(1)
            .maybeSingle();

    return shared?['chat_id'] as String?;
  }

  Future<String> createGroup({
    required String name,
    required List<String> memberIds,
  }) async {
    final me = _me;
    if (me == null) throw const ChatException('Serve un account.');
    if (name.trim().isEmpty) {
      throw const ChatException('Dai un nome al gruppo.');
    }

    try {
      final chat =
          await _db
              .from('chats')
              .insert({'is_group': true, 'name': name.trim(), 'created_by': me})
              .select('id')
              .single();

      final chatId = chat['id'] as String;
      await _db.from('chat_members').insert([
        {'chat_id': chatId, 'user_id': me},
        for (final id in memberIds.where((id) => id != me))
          {'chat_id': chatId, 'user_id': id},
      ]);
      return chatId;
    } on PostgrestException catch (e) {
      throw ChatException(_explain(e));
    }
  }

  /// Esce da una conversazione. I messaggi già scritti restano.
  Future<void> leave(String chatId) async {
    final me = _me;
    if (me == null) return;
    await _db
        .from('chat_members')
        .delete()
        .eq('chat_id', chatId)
        .eq('user_id', me);
  }

  /// Cancella un proprio messaggio.
  Future<void> deleteMessage(String messageId) async {
    await _db.from('messages').delete().eq('id', messageId);
  }

  // ---------------------------------------------------------------------------
  // Blocco e segnalazione
  // ---------------------------------------------------------------------------

  Future<void> block(String userId) async {
    final me = _me;
    if (me == null) return;
    await _db.from('blocked_users').upsert({
      'blocker_id': me,
      'blocked_id': userId,
    }, onConflict: 'blocker_id,blocked_id');
  }

  Future<void> unblock(String userId) async {
    final me = _me;
    if (me == null) return;
    await _db
        .from('blocked_users')
        .delete()
        .eq('blocker_id', me)
        .eq('blocked_id', userId);
  }

  Future<Set<String>> blockedIds() async {
    final me = _me;
    if (me == null) return {};
    final rows = await _db
        .from('blocked_users')
        .select('blocked_id')
        .eq('blocker_id', me);
    return rows
        .whereType<Map<String, dynamic>>()
        .map((r) => r['blocked_id'] as String)
        .toSet();
  }

  /// Segnala un messaggio ai moderatori.
  ///
  /// Obbligo DSA: deve esistere un modo per segnalare contenuti illeciti, e chi
  /// segnala deve poterlo fare senza passare da un'email.
  Future<void> reportMessage({
    required String messageId,
    required String reason,
  }) async {
    final me = _me;
    if (me == null) {
      throw const ChatException('Serve un account per segnalare.');
    }
    if (reason.trim().isEmpty) {
      throw const ChatException('Dì cosa non va: serve a chi modera.');
    }

    await _db.from('reports').insert({
      'reporter_id': me,
      'message_id': messageId,
      'reason': reason.trim(),
      'status': 'aperta',
    });
  }

  /// Traduce gli errori del database in frasi che abbiano senso per chi legge.
  static String _explain(PostgrestException e) {
    // Sollevato dal trigger `enforce_message_rate_limit`.
    if (e.code == '53400') {
      return 'Vai troppo veloce: aspetta qualche secondo.';
    }

    // 42501 = la policy RLS ha rifiutato. Le ragioni possibili sono quelle
    // imposte dalla 0005 e dalla 0007, e non sono distinguibili dal codice.
    if (e.code == '42501') {
      return 'Non puoi scrivere qui. Può dipendere da un blocco fra voi, '
          'dall\'email non ancora confermata, o dalla chat disattivata su '
          'questo account.';
    }
    return e.message;
  }
}

class ChatException implements Exception {
  const ChatException(this.message);
  final String message;

  @override
  String toString() => message;
}
