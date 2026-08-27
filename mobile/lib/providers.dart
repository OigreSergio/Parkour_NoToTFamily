import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'models/profile.dart';
import 'models/spot.dart';
import 'models/video.dart';
import 'repositories/account_repository.dart';
import 'repositories/parent_access_repository.dart';
import 'repositories/safety_repository.dart';
import 'repositories/spot_repository.dart';
import 'repositories/video_repository.dart';
import 'services/location_service.dart';
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

final locationServiceProvider = Provider<LocationService>(
  (ref) => const LocationService(),
);

/// Il centro della mappa: la posizione GPS, o un ripiego.
final currentLocationProvider = FutureProvider<LatLng>(
  (ref) => ref.watch(locationServiceProvider).currentLatLng(),
);

/// Gli spot intorno alla posizione corrente.
///
/// Torna una lista vuota finché l'avviso di sicurezza non è accettato. Non è
/// solo cortesia dell'interfaccia: la policy RESTRICTIVE sulla tabella `spots`
/// li nega comunque lato server, e questo evita una chiamata che tornerebbe
/// vuota per forza.
final spotsProvider = FutureProvider<List<Spot>>((ref) async {
  final accepted = await ref.watch(safetyAcceptedProvider.future);
  if (!accepted) return const [];

  final center = await ref.watch(currentLocationProvider.future);
  return ref
      .watch(spotRepositoryProvider)
      .fetchSpots(lat: center.latitude, lng: center.longitude);
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
