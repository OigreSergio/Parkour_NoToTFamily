import 'package:supabase_flutter/supabase_flutter.dart';

/// Cosa si sta segnalando.
///
/// Le categorie non sono decorative: l'art. 16 DSA chiede che una segnalazione
/// sia abbastanza precisa da poter essere trattata, e «contenuto illecito» e
/// «spam» richiedono a chi modera due reazioni molto diverse.
enum ReportKind {
  spot('spot_id'),
  message('message_id'),
  comment('comment_id'),
  post('post_id'),
  profile('profile_id');

  const ReportKind(this.column);

  final String column;
}

/// Una motivazione di moderazione ricevuta.
///
/// È lo *statement of reasons* dell'art. 17 DSA: quando un contenuto viene
/// rimosso o rifiutato, chi l'ha scritto ha diritto di sapere perché. Non basta
/// annotarlo in un registro interno — deve arrivargli.
class ModerationNotice {
  const ModerationNotice({
    required this.id,
    required this.targetKind,
    required this.action,
    required this.reason,
    this.createdAt,
    this.readAt,
  });

  final String id;
  final String targetKind;
  final String action;
  final String reason;
  final DateTime? createdAt;
  final DateTime? readAt;

  bool get isUnread => readAt == null;

  String get label => switch (action) {
    'rifiutato' => 'Proposta rifiutata',
    'rimosso' => 'Contenuto rimosso',
    'sospeso' => 'Account sospeso',
    'riattivato' => 'Sospensione revocata',
    'bannato' => 'Account bloccato',
    'sbannato' => 'Blocco revocato',
    'ruolo' => 'Ruolo aggiornato',
    _ => 'Decisione di moderazione',
  };

  factory ModerationNotice.fromJson(Map<String, dynamic> json) =>
      ModerationNotice(
        id: json['id'] as String,
        targetKind: (json['target_kind'] as String?) ?? '',
        action: (json['action'] as String?) ?? '',
        reason: (json['reason'] as String?) ?? '',
        createdAt: _date(json['created_at']),
        readAt: _date(json['read_at']),
      );

  static DateTime? _date(Object? v) =>
      v is String ? DateTime.tryParse(v) : null;
}

/// Segnalazioni e motivazioni ricevute.
class ModerationRepository {
  const ModerationRepository(this._db);

  final SupabaseClient _db;

  /// Segnala un contenuto ai moderatori.
  ///
  /// Chi viene segnalato non lo saprà, e non saprà da chi: la policy sulla
  /// tabella `reports` lascia leggere una segnalazione solo a chi l'ha fatta e
  /// ai moderatori. Senza quella garanzia nessuno segnalerebbe, e il
  /// meccanismo dell'art. 16 DSA sarebbe una casella vuota.
  Future<void> report({
    required ReportKind kind,
    required String targetId,
    required String reason,
  }) async {
    final me = _db.auth.currentUser?.id;
    if (me == null) {
      throw const ModerationException('Serve un account per segnalare.');
    }

    final text = reason.trim();
    if (text.isEmpty) {
      throw const ModerationException('Dì cosa non va: serve a chi modera.');
    }

    try {
      await _db.from('reports').insert({
        'reporter_id': me,
        kind.column: targetId,
        'reason': text,
        'status': 'aperta',
      });
    } on PostgrestException catch (e) {
      if (e.code == '23514') {
        // Il vincolo `reports_needs_target` rifiuta le segnalazioni senza
        // bersaglio, e quelle di sé stessi.
        throw const ModerationException('Segnalazione non valida.');
      }
      throw ModerationException(e.message);
    }
  }

  /// Le motivazioni che mi riguardano, dalla più recente.
  Future<List<ModerationNotice>> myNotices() async {
    final me = _db.auth.currentUser?.id;
    if (me == null) return const [];

    try {
      final rows = await _db
          .from('moderation_notices')
          .select('id, target_kind, action, reason, created_at, read_at')
          .order('created_at', ascending: false)
          .limit(50);

      return rows
          .whereType<Map<String, dynamic>>()
          .map(ModerationNotice.fromJson)
          .toList(growable: false);
    } catch (_) {
      // La tabella arriva con la migration 0009. Finché non è applicata, il
      // profilo non deve rompersi: semplicemente non c'è niente da mostrare.
      return const [];
    }
  }

  Future<void> markRead(String noticeId) async {
    await _db
        .from('moderation_notices')
        .update({'read_at': DateTime.now().toIso8601String()})
        .eq('id', noticeId);
  }
}

class ModerationException implements Exception {
  const ModerationException(this.message);
  final String message;

  @override
  String toString() => message;
}
