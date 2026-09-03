# Mobile (Flutter)

Cross-platform client (**Android + iOS**) written in **Dart / Flutter**. It
talks to the Python (FastAPI) backend over HTTP.

Current scope is **read-only**: browse verified parkour spots on a map and in a
list, plus an account menu (settings, guest sign-in, log out). Email login,
photo upload and reviews are intentionally not wired up yet.

## Run

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://localhost:8000   # iOS simulator
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000    # Android emulator
```

`API_BASE_URL` is optional — it defaults to `http://10.0.2.2:8000` (the Android
emulator alias for the host's `localhost`). See `lib/services/api_client.dart`.

## Layout

```
lib/
├── main.dart                        ProviderScope, theme mode, tabs + account menu
├── providers.dart                   Riverpod providers (client, repos, session, settings)
├── models/
│   ├── spot.dart                    Spot model (fromJson/toJson) — matches SpotOut
│   ├── account.dart                 Signed-in account — matches UserOut
│   └── app_settings.dart            On-device preferences (theme, radius, location)
├── services/
│   ├── api_client.dart              http client, configurable base URL
│   ├── local_store.dart             key/value store (secure storage, or in-memory)
│   ├── session_service.dart         tokens + cached account on the device
│   ├── settings_store.dart          preference persistence
│   └── location_service.dart        geolocator wrapper with fallback centre
├── repositories/
│   ├── spot_repository.dart         GET /api/v1/spots (verified spots only)
│   └── auth_repository.dart         guest sign-in, /users/me, logout
├── screens/
│   ├── spots_map_screen.dart        flutter_map + one marker per spot
│   ├── spots_list_screen.dart       scrollable list, tap → detail
│   ├── spot_detail_screen.dart      single-spot detail view
│   ├── tutorial_detail_screen.dart  player, paywall or "watch on YouTube"
│   └── settings_screen.dart         account, appearance, spot search, about
└── widgets/
    ├── error_view.dart              shared error/retry state
    ├── account_menu.dart            app bar avatar → menu (settings / log out)
    └── logout_confirmation.dart     confirm dialog + log out feedback
```

State: **Riverpod**. HTTP: **http**. Map: **flutter_map** (OpenStreetMap tiles,
no API key) with **latlong2**. Location: **geolocator**.

## Account menu & settings

The app bar carries an avatar button that opens the **account menu**: it names
the account behind the session and leads to the two actions the menu exists
for — **Settings** and **Log out** (replaced by *Sign in as a guest* when
nobody is signed in).

- **Log out** asks for confirmation, calls `POST /api/v1/auth/logout` to revoke
  the refresh tokens server-side, then wipes the tokens from the device. If the
  backend cannot be reached the local session is cleared anyway and the user is
  told the server-side session is still open.
- **Guest sign-in** (`POST /api/v1/auth/guest`) needs no email; the account is
  then read from `GET /api/v1/users/me`. Email login and registration land with
  the full auth flow (roadmap milestone 3).
- **Settings** (`screens/settings_screen.dart`) manages the account, the theme
  (system / light / dark), the spot **search radius** and whether the device
  location is used. Changes apply immediately and are stored on the device —
  the backend has no per-user preferences endpoint yet.

Tokens live in `flutter_secure_storage` (Keychain / encrypted shared
preferences) behind `services/local_store.dart`, which degrades to a no-op when
the platform channel is unavailable, so tests and unsupported platforms still
run.

## Tutorials

The catalog is curated from public channels (`backend/seeds/videos.json`), so
most tutorials are **YouTube links, not video files**: `video_player` cannot
stream those, and the detail screen shows the thumbnail with a *Watch on
youtube.com* button that hands the video to the YouTube app or the browser
(`url_launcher`). A tutorial whose `url` points straight at a media file
(`.mp4`, `.m3u8`, `.webm`, `.mov`, `.m4v`) still plays inline — see
`TutorialVideo.isStreamable`.

## Data source

`GET /api/v1/spots?lat=&lng=&radius_m=&limit=` returns only `verified` spots.
The request is centred on the user's GPS position (or a fallback when location
is unavailable). Spot shape is documented in
[`../docs/DATA_MODEL.md`](../docs/DATA_MODEL.md).

## Test

```bash
flutter analyze
flutter test
```

## Permissions

Already configured for location:

- **Android** — `INTERNET` + `ACCESS_FINE_LOCATION` in
  `android/app/src/main/AndroidManifest.xml`.
- **iOS** — `NSLocationWhenInUseUsageDescription` in `ios/Runner/Info.plist`.
