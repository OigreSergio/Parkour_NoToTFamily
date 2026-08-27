import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/profile.dart';

/// Registrazione, accesso, profilo e diritti dell'interessato.
///
/// Tutto passa da Supabase Auth e dalle policy RLS: qui non c'è nessun
/// controllo di sicurezza, solo la traduzione fra UI e database. Quello che un
/// utente può fare lo decide il database.
class AccountRepository {
  const AccountRepository(this._db);

  final SupabaseClient _db;

  User? get currentUser => _db.auth.currentUser;

  /// True quando c'è una sessione, ma anonima: nessun account vero.
  bool get isAnonymous => _db.auth.currentUser?.isAnonymous ?? true;

  bool get isSignedIn => currentUser != null && !isAnonymous;

  Stream<AuthState> get authChanges => _db.auth.onAuthStateChange;

  /// Apre una sessione anonima se non c'è già una sessione.
  ///
  /// Serve a dare un'identità anche a chi non si registra, perché la presa
  /// d'atto del gate di sicurezza possa essere registrata lato server e le
  /// policy RLS possano applicarla davvero. Senza, il gate sarebbe un
  /// suggerimento aggirabile disattivando JavaScript.
  ///
  /// Ha un costo di privacy da dichiarare nell'informativa: è un identificativo
  /// per visitatore, che va trattato come un identificativo di sessione e
  /// ripulito periodicamente. Va abilitato in Dashboard → Authentication →
  /// Anonymous sign-ins; se è disattivato questa chiamata fallisce e l'app
  /// resta utilizzabile senza spot.
  Future<void> ensureSession() async {
    if (_db.auth.currentUser != null) return;
    await _db.auth.signInAnonymously();
  }

  /// Registrazione con conferma email obbligatoria.
  ///
  /// [birthDate] non viene conservata: serve solo a calcolare la soglia, e
  /// quello che resta è `age_confirmed_at`. Tenere la data di nascita di tutti
  /// per un controllo fatto una volta sola sarebbe raccolta eccessiva.
  Future<void> signUp({
    required String email,
    required String password,
    required String username,
    required DateTime birthDate,
  }) async {
    if (AgeCheck.of(birthDate) != AgeCheck.ok) {
      throw const AccountException(
        'Per aprire un account servono almeno ${AgeCheck.minimumAge} anni.',
      );
    }

    final res = await _db.auth.signUp(
      email: email,
      password: password,
      data: {'username': username},
    );

    // Con la conferma email attiva la sessione non parte subito: è voluto,
    // impedisce di iscriversi con l'indirizzo di qualcun altro.
    if (res.user == null) {
      throw const AccountException('Registrazione non riuscita.');
    }

    await _markAgeConfirmed(res.user!.id);
  }

  Future<void> signIn({required String email, required String password}) async {
    await _db.auth.signInWithPassword(email: email, password: password);
  }

  Future<void> sendPasswordReset(String email) async {
    await _db.auth.resetPasswordForEmail(email);
  }

  Future<void> signOut() async {
    await _db.auth.signOut();
  }

  Future<Profile?> currentProfile() async {
    final id = currentUser?.id;
    if (id == null || isAnonymous) return null;

    final row =
        await _db
            .from('profiles')
            .select(
              'id, username, avatar_url, role, banned, age_confirmed_at, '
              'supervised, supervisor_confirmed_at, chat_enabled, '
              'deletion_requested_at, created_at',
            )
            .eq('id', id)
            .maybeSingle();

    return row == null ? null : Profile.fromJson(row);
  }

  Future<void> updateUsername(String username) async {
    final id = currentUser?.id;
    if (id == null) throw const AccountException('Nessun account connesso.');
    await _db.from('profiles').update({'username': username}).eq('id', id);
  }

  /// Attiva o disattiva la chat sul proprio account.
  ///
  /// È l'interruttore che un genitore usa su un account supervisionato. Il
  /// vincolo vero è nelle policy RLS (`can_use_chat()`): questo aggiorna il
  /// flag, non concede niente da solo.
  Future<void> setChatEnabled(bool enabled) async {
    final id = currentUser?.id;
    if (id == null) throw const AccountException('Nessun account connesso.');
    await _db.from('profiles').update({'chat_enabled': enabled}).eq('id', id);
  }

  /// Tutti i dati dell'utente, per l'esercizio degli artt. 15 e 20 GDPR.
  ///
  /// Le RLS fanno già il filtro: quello che torna è per definizione ciò a cui
  /// l'utente ha diritto di accedere. Le tabelle che non esistono ancora
  /// vengono saltate invece di far fallire l'export — un diritto che si
  /// esercita solo a schema completo non è un diritto.
  Future<Map<String, dynamic>> exportMyData() async {
    final id = currentUser?.id;
    if (id == null) throw const AccountException('Nessun account connesso.');

    final export = <String, dynamic>{
      'esportato_il': DateTime.now().toIso8601String(),
      'account': {'id': id, 'email': currentUser?.email},
    };

    Future<void> add(String table, String column) async {
      try {
        export[table] = await _db.from(table).select().eq(column, id);
      } catch (_) {
        // Tabella assente o non leggibile: si annota e si va avanti.
        export[table] = {'non_disponibile': true};
      }
    }

    await add('profiles', 'id');
    await add('spots', 'author_id');
    await add('comments', 'author_id');
    await add('messages', 'author_id');
    await add('ratings', 'user_id');
    await add('safety_acknowledgements', 'user_id');

    return export;
  }

  /// Richiede la cancellazione dell'account (art. 17 GDPR).
  ///
  /// Segna l'inizio dei 30 giorni di grazia. La cancellazione vera la esegue un
  /// processo server-side: deve rimuovere il profilo e i contenuti personali e
  /// **pseudonimizzare** i messaggi già inviati — non rimuoverli dalle
  /// conversazioni altrui, dove gli altri partecipanti hanno un interesse
  /// legittimo alla propria conversazione.
  ///
  /// Il client non può cancellare un utente da `auth.users`: serve la secret
  /// key, che qui non c'è e non deve esserci.
  Future<void> requestDeletion() async {
    final id = currentUser?.id;
    if (id == null) throw const AccountException('Nessun account connesso.');
    await _db
        .from('profiles')
        .update({'deletion_requested_at': DateTime.now().toIso8601String()})
        .eq('id', id);
  }

  /// Annulla la richiesta, se si è ancora nei 30 giorni.
  Future<void> cancelDeletion() async {
    final id = currentUser?.id;
    if (id == null) throw const AccountException('Nessun account connesso.');
    await _db
        .from('profiles')
        .update({'deletion_requested_at': null})
        .eq('id', id);
  }

  Future<void> _markAgeConfirmed(String userId) async {
    try {
      await _db
          .from('profiles')
          .update({'age_confirmed_at': DateTime.now().toIso8601String()})
          .eq('id', userId);
    } catch (_) {
      // Con la conferma email attiva il profilo può non essere ancora
      // scrivibile: non è un motivo per far fallire una registrazione riuscita.
      // Il valore si riscrive al primo accesso.
    }
  }
}

class AccountException implements Exception {
  const AccountException(this.message);
  final String message;

  @override
  String toString() => message;
}
