import 'package:flutter/material.dart' show ThemeMode;
import 'package:flutter_map_vector_tiles/flutter_map_vector_tiles.dart' as vt;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import 'models/account.dart';
import 'models/app_settings.dart';
import 'models/spot.dart';
import 'models/water_point.dart';
import 'models/video.dart';
import 'repositories/auth_repository.dart';
import 'repositories/spot_repository.dart';
import 'repositories/water_repository.dart';
import 'repositories/video_repository.dart';
import 'services/api_client.dart';
import 'services/local_store.dart';
import 'services/location_service.dart';
import 'services/map_style.dart';
import 'services/session_service.dart';
import 'services/settings_store.dart';

/// Backend HTTP client (disposed with the [ProviderScope]).
final apiClientProvider = Provider<ApiClient>((ref) {
  final client = ApiClient();
  ref.onDispose(client.close);
  return client;
});

/// Device key/value storage for the session tokens and the preferences.
/// Overridden with an [InMemoryLocalStore] in tests.
final localStoreProvider = Provider<LocalStore>((ref) => SecureLocalStore());

/// Spot data source.
final spotRepositoryProvider = Provider<SpotRepository>(
  (ref) => SpotRepository(ref.watch(apiClientProvider)),
);

/// Device location helper.
final locationServiceProvider =
    Provider<LocationService>((ref) => const LocationService());

/// The map / search centre — the user's GPS position, or a fallback.
///
/// Honours the "use my location" preference: with it off the app stays on the
/// fallback centre and never asks the device for a fix.
final currentLocationProvider = FutureProvider<LatLng>((ref) {
  final useDeviceLocation =
      ref.watch(settingsProvider.select((s) => s.useDeviceLocation));
  if (!useDeviceLocation) {
    return Future.value(LocationService.fallbackCenter);
  }
  return ref.watch(locationServiceProvider).currentLatLng();
});

/// Verified spots near the current location, within the configured radius.
final spotsProvider = FutureProvider<List<Spot>>((ref) async {
  final center = await ref.watch(currentLocationProvider.future);
  final radius = ref.watch(settingsProvider.select((s) => s.searchRadiusMeters));
  return ref.watch(spotRepositoryProvider).fetchSpots(
        lat: center.latitude,
        lng: center.longitude,
        radiusMeters: radius,
        limit: AppSettings.spotsLimit,
      );
});

/// The embroidery map style, parsed once and kept for the app's lifetime.
final mapStyleProvider = FutureProvider<vt.Style>((ref) async {
  final style = await const MapStyleLoader().load();
  ref.onDispose(style.dispose);
  return style;
});

/// Drinking-water lookup (OpenStreetMap via Overpass).
final waterRepositoryProvider = Provider<WaterRepository>((ref) {
  final repository = WaterRepository();
  ref.onDispose(repository.close);
  return repository;
});

/// Drinking water around one spot, asked for only when its detail is open.
final waterNearSpotProvider =
    FutureProvider.autoDispose.family<List<WaterPoint>, Spot>(
  (ref, spot) => ref.watch(waterRepositoryProvider).nearSpot(spot),
);

/// Tutorial video data source.
final videoRepositoryProvider = Provider<VideoRepository>(
  (ref) => VideoRepository(ref.watch(apiClientProvider)),
);

/// All tutorial videos. The backend marks premium ones as `locked` for
/// viewers without a subscription; beginner tutorials are open to everyone,
/// including guests signed in without an email.
final tutorialsProvider = FutureProvider<List<TutorialVideo>>(
  (ref) => ref.watch(videoRepositoryProvider).fetchTutorials(),
);

/// IDs of the tricks the user marked as landed. Client-side stub (kept in
/// memory) until the backend persists per-user progress — same pattern as
/// spot likes.
class LandedTricksNotifier extends StateNotifier<Set<String>> {
  LandedTricksNotifier() : super(const {});

  void toggle(String videoId) {
    final next = Set<String>.of(state);
    if (!next.add(videoId)) {
      next.remove(videoId);
    }
    state = next;
  }
}

final landedTricksProvider =
    StateNotifierProvider<LandedTricksNotifier, Set<String>>(
  (ref) => LandedTricksNotifier(),
);

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

/// Preference persistence.
final settingsStoreProvider = Provider<SettingsStore>(
  (ref) => SettingsStore(ref.watch(localStoreProvider)),
);

/// Holds the current [AppSettings] and writes every change back to the device.
class SettingsController extends StateNotifier<AppSettings> {
  SettingsController(this._store) : super(const AppSettings()) {
    _restore();
  }

  final SettingsStore _store;

  Future<void> _restore() async {
    state = await _store.read();
  }

  Future<void> setThemeMode(ThemeMode mode) =>
      _update(state.copyWith(themeMode: mode));

  Future<void> setSearchRadiusMeters(int radiusMeters) =>
      _update(state.copyWith(searchRadiusMeters: radiusMeters));

  Future<void> setUseDeviceLocation(bool useDeviceLocation) =>
      _update(state.copyWith(useDeviceLocation: useDeviceLocation));

  /// Back to the out-of-the-box preferences.
  Future<void> reset() => _update(const AppSettings());

  Future<void> _update(AppSettings next) async {
    if (next == state) return;
    state = next;
    await _store.write(next);
  }
}

final settingsProvider =
    StateNotifierProvider<SettingsController, AppSettings>(
  (ref) => SettingsController(ref.watch(settingsStoreProvider)),
);

// ---------------------------------------------------------------------------
// Session
// ---------------------------------------------------------------------------

/// Auth endpoints.
final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(ref.watch(apiClientProvider)),
);

/// Session token persistence.
final sessionServiceProvider = Provider<SessionService>(
  (ref) => SessionService(ref.watch(localStoreProvider)),
);

/// Where the session is: still being restored from the device, signed out,
/// signed in, or waiting on a sign-in / sign-out call.
enum SessionStatus { restoring, signedOut, signedIn, busy }

/// What the account menu renders.
class SessionState {
  const SessionState({
    this.status = SessionStatus.restoring,
    this.account,
    this.error,
  });

  final SessionStatus status;

  /// The signed-in account. `null` while restoring or signed out.
  final Account? account;

  /// Last failure, so the UI can explain why a sign-in did not go through.
  final String? error;

  bool get isSignedIn => status == SessionStatus.signedIn;
  bool get isBusy => status == SessionStatus.busy;
  bool get isRestoring => status == SessionStatus.restoring;

  SessionState copyWith({
    SessionStatus? status,
    Account? account,
    String? error,
    bool clearAccount = false,
    bool clearError = false,
  }) =>
      SessionState(
        status: status ?? this.status,
        account: clearAccount ? null : (account ?? this.account),
        error: clearError ? null : (error ?? this.error),
      );
}

/// Owns the session: restores it on start-up, signs in as a guest, and logs
/// out (revoking the tokens server-side, then wiping them from the device).
///
/// The tokens themselves stay private to the controller — widgets get the
/// account, never the credentials.
class SessionController extends StateNotifier<SessionState> {
  SessionController({
    required SessionService service,
    required AuthRepository auth,
    required Ref ref,
  })  : _service = service,
        _auth = auth,
        _ref = ref,
        super(const SessionState()) {
    restore();
  }

  final SessionService _service;
  final AuthRepository _auth;
  final Ref _ref;

  AuthTokens? _tokens;

  /// Load a session saved by a previous run, refreshing the account from
  /// `GET /api/v1/users/me` when the backend is reachable.
  Future<void> restore() async {
    final stored = await _service.read();
    if (!mounted) return;
    if (stored == null) {
      state = const SessionState(status: SessionStatus.signedOut);
      return;
    }
    _tokens = stored.tokens;
    state = SessionState(
      status: SessionStatus.signedIn,
      account: stored.account,
    );
    await _refreshAccount();
  }

  /// Sign in without an email (`POST /api/v1/auth/guest`).
  Future<bool> signInAsGuest({String? displayName}) async {
    state = state.copyWith(status: SessionStatus.busy, clearError: true);
    try {
      final tokens = await _auth.loginAsGuest(displayName: displayName);
      await _service.saveTokens(tokens);
      _tokens = tokens;
      final account = await _auth.me(tokens.accessToken);
      await _service.saveAccount(account);
      if (!mounted) return true;
      state = SessionState(status: SessionStatus.signedIn, account: account);
      return true;
    } catch (error) {
      if (mounted) {
        state = SessionState(
          status: SessionStatus.signedOut,
          error: _message(error),
        );
      }
      return false;
    }
  }

  /// Log out: revoke the refresh tokens server-side, then drop everything held
  /// on this device.
  ///
  /// The local session is cleared even when the backend cannot be reached —
  /// the returned [LogoutOutcome] says whether the revocation went through, so
  /// the UI can tell the user the tokens are still live server-side.
  Future<LogoutOutcome> logout() async {
    final token = _tokens?.accessToken;
    state = state.copyWith(status: SessionStatus.busy, clearError: true);

    String? failure;
    if (token != null && token.isNotEmpty) {
      try {
        await _auth.logout(token);
      } catch (error) {
        failure = _message(error);
      }
    }

    await _service.clear();
    _tokens = null;
    // Client-side progress belongs to the account that just left.
    _ref.invalidate(landedTricksProvider);

    if (mounted) {
      state = SessionState(status: SessionStatus.signedOut, error: failure);
    }
    return LogoutOutcome(revokedOnServer: failure == null, error: failure);
  }

  /// Send a spot report: uploads its photos, then posts the spot itself.
  ///
  /// It lives on the session because the access token never leaves this
  /// controller. The map is refreshed afterwards, though the new spot only
  /// shows up once a moderator verifies it.
  Future<Spot> submitSpot({
    required String name,
    required String description,
    required LatLng position,
    required List<SpotPhotoUpload> photos,
  }) async {
    final token = _tokens?.accessToken;
    if (token == null || token.isEmpty) {
      throw StateError('Sign in before reporting a spot.');
    }

    final repository = _ref.read(spotRepositoryProvider);
    final photoUrls = await repository.uploadPhotos(photos, accessToken: token);
    final spot = await repository.submitSpot(
      name: name,
      description: description,
      lat: position.latitude,
      lng: position.longitude,
      photoUrls: photoUrls,
      accessToken: token,
    );
    _ref.invalidate(spotsProvider);
    return spot;
  }

  /// Re-read the account behind the current tokens. A failure here is not
  /// fatal: the cached account stays on screen.
  Future<void> _refreshAccount() async {
    final token = _tokens?.accessToken;
    if (token == null || token.isEmpty) return;
    try {
      final account = await _auth.me(token);
      await _service.saveAccount(account);
      if (!mounted) return;
      state = state.copyWith(
        status: SessionStatus.signedIn,
        account: account,
      );
    } on ApiException catch (error) {
      // The stored token is no longer accepted: start over signed out.
      if (error.statusCode == 401 || error.statusCode == 403) {
        await _service.clear();
        _tokens = null;
        if (mounted) {
          state = const SessionState(status: SessionStatus.signedOut);
        }
      }
    } catch (_) {
      // Offline: keep the cached account.
    }
  }

  String _message(Object error) =>
      error is ApiException ? 'Server error ${error.statusCode}' : '$error';
}

/// Result of [SessionController.logout].
class LogoutOutcome {
  const LogoutOutcome({required this.revokedOnServer, this.error});

  /// `true` when `POST /api/v1/auth/logout` acknowledged the revocation.
  final bool revokedOnServer;
  final String? error;
}

final sessionProvider =
    StateNotifierProvider<SessionController, SessionState>(
  (ref) => SessionController(
    service: ref.watch(sessionServiceProvider),
    auth: ref.watch(authRepositoryProvider),
    ref: ref,
  ),
);
