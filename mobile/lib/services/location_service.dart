import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

/// Resolves the device's current position, with a graceful fallback so the map
/// and spot search always have a centre to work from.
class LocationService {
  const LocationService();

  /// Map centre used when location services are disabled or permission is
  /// denied (central Rome).
  static const LatLng fallbackCenter = LatLng(41.9028, 12.4964);

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
