import 'package:supabase_flutter/supabase_flutter.dart';

import '../services/safety_notice.dart';

/// Registra e verifica la presa d'atto dell'avviso di sicurezza.
///
/// Senza registrazione il gate in giudizio vale zero: quello che serve provare
/// è *quale testo esatto* è stato mostrato e *quando*. Da qui version + hash,
/// scritti insieme all'accettazione.
class SafetyRepository {
  const SafetyRepository(this._db);

  final SupabaseClient _db;

  static const String _table = 'safety_acknowledgements';

  /// L'utente corrente ha accettato la versione corrente dell'avviso?
  ///
  /// In caso di errore risponde `false`: davanti a un dubbio si mostra il gate,
  /// non si aprono gli spot.
  Future<bool> hasAccepted() async {
    final userId = _db.auth.currentUser?.id;
    if (userId == null) return false;

    try {
      final row =
          await _db
              .from(_table)
              .select('accepted_at, revoked_at')
              .eq('user_id', userId)
              .eq('version', SafetyNotice.currentVersion)
              .maybeSingle();

      return row != null && row['revoked_at'] == null;
    } catch (_) {
      return false;
    }
  }

  /// Registra l'accettazione del testo effettivamente mostrato.
  ///
  /// [notice] arriva da `SafetyNotice.load()`, che calcola l'hash dal file
  /// caricato: così l'impronta registrata è per costruzione quella del testo
  /// che l'utente ha davanti, non di una versione che il codice crede di
  /// mostrare.
  Future<void> accept(SafetyNotice notice) async {
    final userId = _db.auth.currentUser?.id;
    if (userId == null) {
      throw StateError(
        'Nessuna sessione: la presa d\'atto non sarebbe registrabile. '
        'Chiama AccountRepository.ensureSession() prima di mostrare il gate.',
      );
    }

    await _db.from(_table).upsert({
      'user_id': userId,
      'version': notice.version,
      'text_sha256': notice.sha256,
      'accepted_at': DateTime.now().toIso8601String(),
      'revoked_at': null,
    }, onConflict: 'user_id,version');
  }

  /// Revoca: la mappa torna senza spot.
  ///
  /// La riga resta e si marca `revoked_at`. Cancellarla distruggerebbe la prova
  /// che a suo tempo il testo era stato accettato — che è esattamente ciò che
  /// serve conservare se un giorno qualcuno contesta di non essere stato
  /// informato.
  Future<void> revoke() async {
    final userId = _db.auth.currentUser?.id;
    if (userId == null) return;

    await _db
        .from(_table)
        .update({'revoked_at': DateTime.now().toIso8601String()})
        .eq('user_id', userId)
        .eq('version', SafetyNotice.currentVersion);
  }
}
