import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/video.dart';

/// Legge i video da Supabase.
///
/// La tabella `videos` è leggibile da tutti, anche senza account: il servizio è
/// gratuito e i video sono la porta d'ingresso per chi non ha mai fatto
/// parkour. `is_premium` e `locked` non esistono più come colonne — il modello
/// li tiene a `false` per tolleranza, e nessun video risulta bloccato.
class VideoRepository {
  const VideoRepository(this._db);

  final SupabaseClient _db;

  static const String _table = 'videos';

  /// Colonne reali di `videos`. `description`, `thumbnail_url`,
  /// `trick_category` e `difficulty` non ci sono ancora: il modello le
  /// tratta come opzionali, così l'app funziona sia prima sia dopo la
  /// migration che le aggiunge.
  static const String _columns = 'id, title, url, category, level, created_at';

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
}
