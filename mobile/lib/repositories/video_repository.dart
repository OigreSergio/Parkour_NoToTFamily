import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/video.dart';

/// Legge i video da Supabase.
///
/// La tabella `videos` è leggibile da tutti, anche senza account e senza aver
/// accettato il gate di sicurezza: il servizio è gratuito, i video sono la
/// porta d'ingresso per chi non ha mai fatto parkour, e guardarne uno non
/// comporta nessun rischio da segnalare.
///
/// `is_premium` e `locked` non esistono più, né come colonne né nel modello.
class VideoRepository {
  const VideoRepository(this._db);

  final SupabaseClient _db;

  static const String _table = 'videos';

  /// Le colonne che esistono dopo le migration 0006 e 0008.
  ///
  /// `thumbnail_url`, `trick_category` e `difficulty` non ci sono: il modello
  /// le tratta come opzionali, così l'app funziona anche prima che vengano
  /// aggiunte. Nessuna miniatura remota è un bene, non un limite — vedi
  /// `VideoOpener`.
  static const String _columns =
      'id, title, url, category, level, created_at, '
      'is_starter, order_index, stage, description, safety_note, author';

  Future<List<TutorialVideo>> fetchTutorials({
    String? category,
    String? level,
    int limit = 200,
  }) async {
    var query = _db.from(_table).select(_columns);
    if (category != null) query = query.eq('category', category);
    if (level != null) query = query.eq('level', level);

    final rows = await query.order('created_at').limit(limit);

    return rows
        .whereType<Map<String, dynamic>>()
        .map(TutorialVideo.fromJson)
        .toList(growable: false);
  }

  /// Le tappe del percorso «Inizia da qui», nell'ordine giusto.
  ///
  /// L'ordine viene dal database (`order_index`), non dall'ordine di
  /// inserimento: in un percorso didattico è la sostanza, non un dettaglio di
  /// presentazione.
  Future<List<TutorialVideo>> starterPath() async {
    final rows = await _db
        .from(_table)
        .select(_columns)
        .eq('is_starter', true)
        .order('order_index');

    return rows
        .whereType<Map<String, dynamic>>()
        .map(TutorialVideo.fromJson)
        .toList(growable: false);
  }
}
