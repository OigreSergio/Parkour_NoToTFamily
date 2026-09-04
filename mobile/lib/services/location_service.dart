import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

/// Resolves the device's current position, with a graceful fallback so the map
/// and spot search always have a centre to work from.
class LocationService {
  const LocationService();

  /// Map centre used when location services are disabled or permission is
  /// denied (central Rome).
  static const LatLng fallbackCenter = LatLng(41.9028, 12.4964);

  /// Metres the user has to move before a new position is reported. Small
  /// enough that the distance to a spot ticks down as you walk towards it,
  /// large enough not to wake the GPS at every step.
  static const int liveDistanceFilterMeters = 10;

  /// The device position as it changes, for the live distance to a spot.
  ///
  /// Starts with the current fix so the UI has something immediately, then
  /// follows the user. Silent (no events) when permission is denied — the
  /// caller keeps whatever it had.
  Stream<LatLng> watchLatLng() async* {
    yield await currentLatLng();
    try {
      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return;
      }
      final stream = Geolocator.getPositionStream(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          distanceFilter: liveDistanceFilterMeters,
        ),
      );
      await for (final position in stream) {
        yield LatLng(position.latitude, position.longitude);
      }
    } catch (_) {
      // Missing plugin (tests), permission revoked mid-session, hardware
      // trouble: the last known position stays on screen.
    }
  }

  /// Returns the user's current [LatLng], or [fallbackCenter] when location
  /// services are off, permission is denied, or a fix cannot be obtained.
  Future<LatLng> currentLatLng() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        return fallbackCenter;
      }

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return fallbackCenter;
      }

      final pos = await Geolocator.getCurrentPosition();
      return LatLng(pos.latitude, pos.longitude);
    } catch (_) {
      // Missing plugin (e.g. in tests), timeouts, or hardware errors.
      return fallbackCenter;
    }
  }
}
