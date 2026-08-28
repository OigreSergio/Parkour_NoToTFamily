import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'models/chat.dart';
import 'models/profile.dart';
import 'models/spot.dart';
import 'models/video.dart';
import 'repositories/account_repository.dart';
import 'repositories/chat_repository.dart';
import 'repositories/parent_access_repository.dart';
import 'repositories/safety_repository.dart';
import 'repositories/spot_repository.dart';
import 'repositories/video_repository.dart';
import 'services/location_service.dart';
import 'services/spot_filter.dart';
import 'services/safety_notice.dart';
import 'services/supabase_client.dart';

/// Il client Supabase, già inizializzato da `initSupabase()` in `main`.
final supabaseClientProvider = Provider((ref) => supabase);

// ---------------------------------------------------------------------------
// Account
// ---------------------------------------------------------------------------

final accountRepositoryProvider = Provider<AccountRepository>(
  (ref) => AccountRepository(ref.watch(supabaseClientProvider)),
);

final parentAccessRepositoryProvider = Provider<ParentAccessRepository>(
  (ref) => ParentAccessRepository(ref.watch(supabaseClientProvider)),
);

/// Cambi di stato dell'autenticazione: login, logout, refresh del token.
///
/// Tutto ciò che dipende dall'identità lo osserva, così un logout non lascia
/// in giro dati dell'utente precedente.
final authStateProvider = StreamProvider<AuthState>(
  (ref) => ref.watch(accountRepositoryProvider).authChanges,
);

/// C'è una sessione con un account vero (non anonima)?
///
/// I widget guardano questo, non il repository: così lo stato si aggiorna da
/// solo a ogni login o logout, e nei test si sostituisce senza costruire un
/// client Supabase — che avvia timer di refresh e non muore con il test.
final isSignedInProvider = Provider<bool>((ref) {
  ref.watch(authStateProvider);
  return ref.watch(accountRepositoryProvider).isSignedIn;
});

/// L'id dell'utente corrente, o null.
final currentUserIdProvider = Provider<String?>((ref) {
  ref.watch(authStateProvider);
  return ref.watch(accountRepositoryProvider).currentUser?.id;
});

final currentProfileProvider = FutureProvider<Profile?>((ref) async {
  ref.watch(authStateProvider);
  return ref.watch(accountRepositoryProvider).currentProfile();
});

// ---------------------------------------------------------------------------
// Gate di sicurezza
// ---------------------------------------------------------------------------

final safetyRepositoryProvider = Provider<SafetyRepository>(
  (ref) => SafetyRepository(ref.watch(supabaseClientProvider)),
);

/// Il testo dell'avviso e il suo hash, caricati dagli asset.
final safetyNoticeProvider = FutureProvider<SafetyNotice>(
  (ref) => SafetyNotice.load(),
);

/// L'utente ha accettato la versione corrente dell'avviso?
final safetyAcceptedProvider = FutureProvider<bool>((ref) async {
  ref.watch(authStateProvider);
  return ref.watch(safetyRepositoryProvider).hasAccepted();
});

/// L'utente ha rifiutato in questa sessione.
///
/// Volutamente non persistito: chi rifiuta non lascia una traccia in più, e al
/// prossimo avvio l'avviso ricompare. Un rifiuto non è una preferenza da
/// ricordare, è l'assenza di un'accettazione.
final safetyDeclinedProvider = StateProvider<bool>((ref) => false);

// ---------------------------------------------------------------------------
// Spot
// ---------------------------------------------------------------------------

final spotRepositoryProvider = Provider<SpotRepository>(
  (ref) => SpotRepository(ref.watch(supabaseClientProvider)),
);

final spotWriteRepositoryProvider = Provider<SpotWriteRepository>(
  (ref) => SpotWriteRepository(ref.watch(supabaseClientProvider)),
);

final locationServiceProvider = Provider<LocationService>(
  (ref) => const LocationService(),
);

/// La posizione del dispositivo, **su richiesta esplicita**.
///
/// `autoDispose` di proposito: la posizione non resta in memoria dopo l'uso.
/// Chiederla di nuovo significa una nuova lettura, non un valore riesumato da
/// una cache — coerente con l'informativa, che dichiara conservazione «nessuna».
///
/// Nessun provider la osserva all'avvio: si legge solo quando l'utente tocca
/// «dove sono» o «percorso».
final locationRequestProvider = FutureProvider.autoDispose<LocationResult>(
  (ref) => ref.watch(locationServiceProvider).request(),
);

/// Filtri attivi sulla mappa e sulla lista.
final spotFilterProvider = NotifierProvider<SpotFilterNotifier, SpotFilter>(
  SpotFilterNotifier.new,
);

/// Gli spot da mostrare.
///
/// Torna una lista vuota finché l'avviso di sicurezza non è accettato. Non è
/// solo cortesia dell'interfaccia: la policy RESTRICTIVE sulla tabella `spots`
/// li nega comunque lato server, e questo evita una chiamata che tornerebbe
/// vuota per forza.
///
/// Il centro è Roma, non la posizione dell'utente: caricare gli spot non deve
/// dipendere da un permesso GPS che nessuno ha ancora concesso.
final spotsProvider = FutureProvider<List<Spot>>((ref) async {
  final accepted = await ref.watch(safetyAcceptedProvider.future);
  if (!accepted) return const [];

  const center = LocationService.fallbackCenter;
  return ref
      .watch(spotRepositoryProvider)
      .fetchSpots(
        lat: center.latitude,
        lng: center.longitude,
        radiusMeters: 2000000,
      );
});

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

final chatRepositoryProvider = Provider<ChatRepository>(
  (ref) => ChatRepository(ref.watch(supabaseClientProvider)),
);

/// Le mie conversazioni, con l'ultimo messaggio di ciascuna.
final myChatsProvider = FutureProvider<List<Chat>>((ref) async {
  ref.watch(authStateProvider);
  return ref.watch(chatRepositoryProvider).myChats();
});

/// I messaggi di una conversazione, in tempo reale.
///
/// `autoDispose`: chiusa la stanza, la sottoscrizione Realtime si chiude con
/// lei. Lasciarla aperta terrebbe un websocket per ogni chat mai visitata.
final chatMessagesProvider = StreamProvider.autoDispose
    .family<List<ChatMessage>, String>(
      (ref, chatId) => ref.watch(chatRepositoryProvider).watch(chatId),
    );

/// Chi ho bloccato.
final blockedIdsProvider = FutureProvider<Set<String>>((ref) async {
  ref.watch(authStateProvider);
  return ref.watch(chatRepositoryProvider).blockedIds();
});

/// Ricerca di persone per nome, per aprire una conversazione.
///
/// Sotto i due caratteri non cerca: una query su una lettera sola restituirebbe
/// mezza community, che è un elenco di iscritti che nessuno ha chiesto.
final userSearchProvider = FutureProvider.autoDispose
    .family<List<Profile>, String>((ref, query) async {
      final q = query.trim();
      if (q.length < 2) return const [];

      final rows = await ref
          .watch(supabaseClientProvider)
          .from('profiles')
          .select('id, username, avatar_url, role')
          .ilike('username', '%$q%')
          .limit(20);

      final me = ref.watch(accountRepositoryProvider).currentUser?.id;
      final blocked = await ref.watch(blockedIdsProvider.future);

      return rows
          .whereType<Map<String, dynamic>>()
          .map(Profile.fromJson)
          .where((p) => p.id != me && !blocked.contains(p.id))
          .toList(growable: false);
    });

// ---------------------------------------------------------------------------
// Video
// ---------------------------------------------------------------------------

final videoRepositoryProvider = Provider<VideoRepository>(
  (ref) => VideoRepository(ref.watch(supabaseClientProvider)),
);

/// Tutti i video. Il servizio è gratuito: nessun video è bloccato, e la
/// sezione è leggibile anche senza account e senza aver accettato il gate —
/// per chi inizia è la porta d'ingresso, e non c'è nessun rischio da segnalare
/// nel guardare un video.
final tutorialsProvider = FutureProvider<List<TutorialVideo>>(
  (ref) => ref.watch(videoRepositoryProvider).fetchTutorials(),
);

/// Il percorso «Inizia da qui».
final starterPathProvider = FutureProvider<List<TutorialVideo>>(
  (ref) => ref.watch(videoRepositoryProvider).starterPath(),
);

/// Trick segnati come "riusciti". Stub lato client finché il backend non
/// persiste il progresso per utente.
class LandedTricksNotifier extends StateNotifier<Set<String>> {
  LandedTricksNotifier() : super(const {});

  void toggle(String videoId) {
    final next = Set<String>.of(state);
    if (!next.add(videoId)) next.remove(videoId);
    state = next;
  }
}

final landedTricksProvider =
    StateNotifierProvider<LandedTricksNotifier, Set<String>>(
      (ref) => LandedTricksNotifier(),
    );
