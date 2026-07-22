# Mobile (Flutter)

Cross-platform client (**Android + iOS + Web/PWA**) written in **Dart /
Flutter**. It talks to the Python (FastAPI) backend over HTTP.

Current scope: browse verified parkour spots on a map and in a list, submit a
new spot for review (email/password sign-in), and a Support tab with the
project's bank-transfer details. Photo upload and reviews are intentionally
not wired up yet.

## Run

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://localhost:8000   # iOS simulator
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000    # Android emulator
flutter run -d chrome                                          # Web
```

`API_BASE_URL` is optional — it defaults to `http://10.0.2.2:8000` (the Android
emulator alias for the host's `localhost`), or `http://localhost:8000` on the
web. See `lib/services/api_client.dart`.

## Web / PWA

The app also builds as an installable Progressive Web App (see
[`../docs/WEB_APP.md`](../docs/WEB_APP.md) for the full strategy and deploy
steps):

```bash
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com
# output in build/web/ — deploy to any static host
```

## Layout

```
lib/
├── main.dart                        ProviderScope + three tabs (Map, List, Support)
├── providers.dart                   Riverpod providers (client, repos, location, spots, bank details)
├── models/
│   ├── spot.dart                    Spot model (fromJson/toJson) — matches SpotOut
│   ├── auth_tokens.dart             JWT pair — matches TokenPair
│   └── bank_details.dart            Bank-transfer details — matches BankDetailsOut
├── services/
│   ├── api_client.dart              http client (GET/POST + bearer), configurable base URL
│   └── location_service.dart        geolocator wrapper with fallback centre
├── repositories/
│   ├── spot_repository.dart         GET/POST /api/v1/spots
│   ├── auth_repository.dart         POST /api/v1/auth/{register,login}
│   └── payment_repository.dart      GET /api/v1/payments/bank-details
├── screens/
│   ├── spots_map_screen.dart        flutter_map + one marker per spot
│   ├── spots_list_screen.dart       scrollable list, tap → detail
│   ├── spot_detail_screen.dart      single-spot detail view
│   ├── submit_spot_screen.dart      sign-in/sign-up + new-spot form (FAB)
│   └── support_screen.dart          bank-transfer details with tap-to-copy
└── widgets/
    └── error_view.dart              shared error/retry state
```

State: **Riverpod**. HTTP: **http**. Map: **flutter_map** (OpenStreetMap tiles,
no API key) with **latlong2**. Location: **geolocator**.

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
