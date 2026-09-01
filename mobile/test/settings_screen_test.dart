import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/models/app_settings.dart';
import 'package:parkour_notot/providers.dart';
import 'package:parkour_notot/screens/settings_screen.dart';
import 'package:parkour_notot/services/api_client.dart';
import 'package:parkour_notot/services/local_store.dart';
import 'package:parkour_notot/services/settings_store.dart';

import 'support/fake_backend.dart';

void main() {
  late InMemoryLocalStore store;
  late ProviderContainer container;

  /// Scroll [finder] into view before tapping it. The settings list is longer
  /// than a phone screen, and a `ListView` does not build what is off-screen.
  Future<void> tapItem(WidgetTester tester, Finder finder) async {
    if (finder.evaluate().isEmpty) {
      await tester.scrollUntilVisible(
        finder,
        120,
        scrollable: find.byType(Scrollable).first,
      );
    }
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
    await tester.tap(finder);
    await tester.pumpAndSettle();
  }

  Future<void> pumpSettings(WidgetTester tester) async {
    // A tall viewport so the whole settings list is laid out at once.
    tester.view.physicalSize = const Size(1000, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: SettingsScreen()),
      ),
    );
    await tester.pumpAndSettle();
  }

  setUp(() {
    store = InMemoryLocalStore();
    container = ProviderContainer(
      overrides: [
        localStoreProvider.overrideWithValue(store),
        apiClientProvider.overrideWithValue(
          ApiClient(
            baseUrl: 'http://backend.test',
            httpClient: FakeBackend().client,
          ),
        ),
      ],
    );
    addTearDown(container.dispose);
  });

  testWidgets('picking a theme applies it and writes it to the device',
      (tester) async {
    await pumpSettings(tester);
    expect(container.read(settingsProvider).themeMode, ThemeMode.system);

    await tapItem(tester, find.text('Dark'));

    expect(container.read(settingsProvider).themeMode, ThemeMode.dark);
    expect(find.text('Always dark'), findsOneWidget);
    expect(
      await store.read(SettingsStore.settingsKey),
      contains('"theme_mode":"dark"'),
    );
  });

  testWidgets('the search radius drives the spot query', (tester) async {
    await pumpSettings(tester);
    expect(
      container.read(settingsProvider).searchRadiusMeters,
      AppSettings.defaultSearchRadiusMeters,
    );

    await tapItem(tester, find.text('10 km'));

    expect(container.read(settingsProvider).searchRadiusMeters, 10000);
    expect(find.text('Spots within 10 km'), findsOneWidget);
  });

  testWidgets('turning location off falls back to the default centre',
      (tester) async {
    await pumpSettings(tester);
    expect(container.read(settingsProvider).useDeviceLocation, isTrue);

    await tapItem(tester, find.text('Use my location'));

    expect(container.read(settingsProvider).useDeviceLocation, isFalse);
    expect(
      find.text('Spots are searched around the default centre (Rome)'),
      findsOneWidget,
    );
  });

  testWidgets('preferences saved earlier are restored', (tester) async {
    store = InMemoryLocalStore({
      SettingsStore.settingsKey:
          '{"theme_mode":"light","search_radius_m":25000,'
              '"use_device_location":false}',
    });
    container = ProviderContainer(
      overrides: [
        localStoreProvider.overrideWithValue(store),
        apiClientProvider.overrideWithValue(
          ApiClient(
            baseUrl: 'http://backend.test',
            httpClient: FakeBackend().client,
          ),
        ),
      ],
    );
    addTearDown(container.dispose);

    await pumpSettings(tester);

    final settings = container.read(settingsProvider);
    expect(settings.themeMode, ThemeMode.light);
    expect(settings.searchRadiusMeters, 25000);
    expect(settings.useDeviceLocation, isFalse);
  });

  testWidgets('resetting goes back to the defaults', (tester) async {
    await pumpSettings(tester);
    await tapItem(tester, find.text('Dark'));
    await tapItem(tester, find.text('Reset preferences'));

    expect(container.read(settingsProvider), const AppSettings());
    expect(find.text('Preferences reset.'), findsOneWidget);
  });
}
