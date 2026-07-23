# Mobile (Flutter)

Cross-platform client (**Android + iOS**) written in **Dart / Flutter**. It
talks to the Python (FastAPI) backend over HTTP.

Current scope is **read-only**: browse verified parkour spots on a map and in a
list. Login, photo upload and reviews are intentionally not wired up yet.

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
├── main.dart                        ProviderScope + two tabs (Map, List)
├── providers.dart                   Riverpod providers (client, repo, location, spots)
├── models/
│   └── spot.dart                    Spot model (fromJson/toJson) — matches SpotOut
├── services/
│   ├── api_client.dart              http client, configurable base URL
│   └── location_service.dart        geolocator wrapper with fallback centre
├── repositories/
│   └── spot_repository.dart         GET /api/v1/spots (verified spots only)
├── screens/
│   ├── spots_map_screen.dart        flutter_map + one marker per spot
│   ├── spots_list_screen.dart       scrollable list, tap → detail
│   └── spot_detail_screen.dart      single-spot detail view
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
