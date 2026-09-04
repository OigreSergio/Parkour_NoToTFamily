import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';

import 'package:parkour_notot/models/app_settings.dart';
import 'package:parkour_notot/providers.dart';
import 'package:parkour_notot/services/local_store.dart';
import 'package:parkour_notot/services/location_service.dart';

/// Location service that walks a fixed path, one step per event.
class _WalkingLocation extends LocationService {
  const _WalkingLocation(this.steps);

  final List<LatLng> steps;

  @override
  Future<LatLng> currentLatLng() async => steps.first;

  @override
  Stream<LatLng> watchLatLng() => Stream.fromIterable(steps);
}

void main() {
  ProviderContainer containerWith(LocationService service, {bool useGps = true}) {
    final container = ProviderContainer(
      overrides: [
        localStoreProvider.overrideWithValue(
          InMemoryLocalStore({
            if (!useGps)
              'app.settings': '{"use_device_location":false}',
          }),
        ),
        locationServiceProvider.overrideWithValue(service),
      ],
    );
    addTearDown(container.dispose);
    return container;
  }

  test('the position follows the user as they walk', () async {
    final container = containerWith(
      const _WalkingLocation([
        LatLng(41.9028, 12.4964),
        LatLng(41.9035, 12.4964),
        LatLng(41.9042, 12.4964),
      ]),
    );

    final seen = <LatLng>[];
    final sub = container.listen(
      livePositionProvider,
      (_, next) {
        final value = next.valueOrNull;
        if (value != null) seen.add(value);
      },
      fireImmediately: true,
    );
    addTearDown(sub.close);

    await Future<void>.delayed(const Duration(milliseconds: 50));

    expect(seen.length, greaterThanOrEqualTo(2), reason: 'more than one fix');
    expect(seen.last.latitude, closeTo(41.9042, 0.0001));
  });

  test('with location turned off the app measures from nothing', () async {
    final container = containerWith(
      const _WalkingLocation([LatLng(41.9028, 12.4964)]),
      useGps: false,
    );

    // Let the stored settings load.
    await container.read(settingsProvider.notifier).stream.firstWhere(
          (s) => !s.useDeviceLocation,
        );
    await Future<void>.delayed(const Duration(milliseconds: 20));

    expect(container.read(settingsProvider).useDeviceLocation, isFalse);
    expect(container.read(userPositionProvider), isNull);
  });

  test('the default settings do use the device position', () {
    expect(const AppSettings().useDeviceLocation, isTrue);
  });
}
