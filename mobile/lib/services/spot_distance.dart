import 'package:latlong2/latlong.dart';

import '../models/spot.dart';

/// How far a spot is from where you are standing.
///
/// Straight-line ("as the crow flies") distance: it is what a map pin can
/// honestly tell you without routing. The value is `null` when the device
/// position is unknown, so the UI simply says nothing rather than guessing.
class SpotDistance {
  const SpotDistance._();

  static const Distance _distance = Distance();

  /// Metres between [from] and [spot], or `null` without a position.
  static double? metersTo(Spot spot, LatLng? from) {
    if (from == null) return null;
    return _distance.as(LengthUnit.Meter, from, spot.location.toLatLng());
  }

  /// `320 m` under a kilometre, `4.7 km` up to 100, `1204 km` beyond.
  static String format(double meters) {
    if (meters < 1000) return '${meters.round()} m';
    final km = meters / 1000;
    if (km < 100) return '${km.toStringAsFixed(1)} km';
    return '${km.round()} km';
  }

  /// Ready-to-show label, or `null` when there is no position to measure from.
  static String? labelFor(Spot spot, LatLng? from) {
    final meters = metersTo(spot, from);
    return meters == null ? null : format(meters);
  }
}
