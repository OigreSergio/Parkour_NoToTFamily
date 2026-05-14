# Mobile (Flutter)

## Run

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://localhost:8000   # iOS sim
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000    # Android emulator
```

## Layout

```
lib/
├── main.dart
├── core/             API client, router, theme, env
├── features/
│   ├── auth/         login + register + auth controller
│   ├── map/          flutter_map view of verified spots
│   ├── chat/         conversation list + room
│   ├── videos/       category tabs of recovery/practice/conditioning
│   └── profile/      account info + logout
└── shared/           reusable widgets (bottom nav shell, etc.)
```

State: **Riverpod**. Routing: **go_router**. HTTP: **dio** with a refresh-token interceptor (`core/api_client.dart`).

## Test

```bash
flutter analyze
flutter test
```

## Permissions (later)

When wiring up location, add to `ios/Runner/Info.plist`:

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Show parkour spots near you.</string>
```

And to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
```
