import 'package:supabase_flutter/supabase_flutter.dart';

/// La richiesta di accesso che un minore manda a un genitore.
///
/// Passa da una **Edge Function**, non da un insert diretto, per tre motivi che
/// non sono negoziabili:
///
/// * la tabella `parent_access_requests` ha RLS attiva **senza policy**: dal
///   client è inaccessibile, in lettura e in scrittura. Contiene l'email di un
///   terzo, fornita da un minore;
/// * l'invio dell'email richiede una chiave che nel client non può stare;
/// * è un canale di invio email pilotato da un input utente. Senza rate limit
///   server-side diventa uno strumento di molestia — chiunque potrebbe far
///   arrivare messaggi a un indirizzo arbitrario.
///
/// La funzione lato server (`supabase/functions/parent-access-request/`) deve:
/// limitare le richieste per IP e per indirizzo, generare un token, salvarne
/// solo l'hash, inviare **una** email, e cancellare le richieste non completate
/// dopo 7 giorni (`purge_expired_parent_requests()`).
class ParentAccessRepository {
  const ParentAccessRepository(this._db);

  final SupabaseClient _db;

  static const String _function = 'parent-access-request';

  Future<void> requestAccess({required String parentEmail}) async {
    final email = parentEmail.trim();
    if (!email.contains('@')) {
      throw const ParentAccessException('Indirizzo email non valido.');
    }

    try {
      final res = await _db.functions.invoke(
        _function,
        body: {'parent_email': email},
      );

      if (res.status != 200) {
        throw ParentAccessException(
          _messageFor(res.status) ?? 'Invio non riuscito (${res.status}).',
        );
      }
    } on FunctionException catch (e) {
      throw ParentAccessException(
        _messageFor(e.status) ??
            'Invio non riuscito. Riprova più tardi, oppure chiedi a un adulto '
                'di registrarsi direttamente.',
      );
    }
  }

  String? _messageFor(int status) => switch (status) {
    429 =>
      'Troppe richieste da questo dispositivo. Riprova più tardi: il limite '
          'serve a evitare che qualcuno usi questa funzione per infastidire '
          'un indirizzo.',
    404 =>
      'Il servizio di richiesta non è ancora attivo. Nel frattempo un adulto '
          'può registrarsi direttamente.',
    _ => null,
  };
}

class ParentAccessException implements Exception {
  const ParentAccessException(this.message);
  final String message;

  @override
  String toString() => message;
}
