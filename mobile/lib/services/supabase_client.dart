import 'package:supabase_flutter/supabase_flutter.dart';

/// Configurazione e avvio del client Supabase.
///
/// Supabase è il backend di produzione: `backend/` (FastAPI) resta nel repo
/// come riferimento di dominio ma non è deployato, e nessun percorso di codice
/// ci arriva più.
///
/// URL e chiave arrivano da `--dart-define`, mai dal sorgente:
///
/// ```sh
/// flutter run -d chrome \
///   --dart-define=SUPABASE_URL=https://<ref>.supabase.co \
///   --dart-define=SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
/// ```
///
/// La **publishable key** è pubblica per definizione: finisce nel bundle e
/// chiunque può leggerla. Non è un segreto, ma questo significa che le policy
/// RLS sono l'unica difesa del database — vedi `scripts/audit_rls.mjs`.
/// La **secret key** non deve mai comparire in un client: bypassa ogni RLS.
class SupabaseConfig {
  const SupabaseConfig._();

  static const String url = String.fromEnvironment('SUPABASE_URL');

  static const String publishableKey = String.fromEnvironment(
    'SUPABASE_PUBLISHABLE_KEY',
  );

  /// True quando entrambi i valori sono stati passati al build.
  static bool get isConfigured => url.isNotEmpty && publishableKey.isNotEmpty;

  /// Messaggio mostrato quando il build è partito senza configurazione: meglio
  /// una schermata che spiega cosa manca di una pila di errori di rete.
  static const String missingConfigMessage =
      'Configurazione Supabase assente. Rilancia il build con '
      '--dart-define=SUPABASE_URL=... e '
      '--dart-define=SUPABASE_PUBLISHABLE_KEY=...';
}

/// Inizializza Supabase. Da chiamare una sola volta, prima di `runApp`.
///
/// Non solleva se la configurazione manca: l'app parte comunque e mostra
/// [SupabaseConfig.missingConfigMessage]. Un crash all'avvio in produzione per
/// una variabile dimenticata sarebbe peggio di una schermata che lo dice.
Future<void> initSupabase() async {
  if (!SupabaseConfig.isConfigured) return;
  await Supabase.initialize(
    url: SupabaseConfig.url,
    publishableKey: SupabaseConfig.publishableKey,
  );
}

/// Il client, dopo [initSupabase].
SupabaseClient get supabase => Supabase.instance.client;
