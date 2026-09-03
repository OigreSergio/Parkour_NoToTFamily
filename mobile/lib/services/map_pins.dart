import 'dart:math' as math;

import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../models/spot.dart';

/// Chooses which spots get a pin on the map.
///
/// With the whole community list loaded there are thousands of spots, and at
/// low zoom every one of them lands on the same few pixels: drawing them all is
/// what makes the map crawl and, on a phone, run the tab out of memory. So the
/// pins are thinned on a grid whose cell is a fixed number of *pixels* — at
/// street zoom a cell is metres wide and every spot survives, at country zoom
/// only one pin per area remains. The web app thins the same way.
class MapPins {
  const MapPins._();

  /// Minimum distance between two pins, in screen pixels.
  static const double spacingPixels = 44;

  /// Hard ceiling on the pins built for one frame, whatever the zoom.
  static const int defaultMaxPins = 400;

  /// Web Mercator tile size, the base of the zoom scale.
  static const double _tileSize = 256;

  /// Degrees of longitude covered by [spacingPixels] at [zoom].
  static double cellSizeDegrees(double zoom) =>
      spacingPixels * 360 / (_tileSize * math.pow(2, zoom));

  /// The spots to draw for a camera looking at [bounds] from [zoom].
  ///
  /// Spots verified by the family always win over community ones inside the
  /// same cell, so the family's map never disappears behind the imported list.
  static List<Spot> visible(
    List<Spot> spots, {
    required LatLngBounds bounds,
    required double zoom,
    int maxPins = defaultMaxPins,
  }) {
    final cell = cellSizeDegrees(zoom);
    final kept = <String, Spot>{};

    for (final spot in spots) {
      final point = LatLng(spot.location.lat, spot.location.lng);
      if (!bounds.contains(point)) continue;

      final key = '${(point.latitude / cell).floor()}:'
          '${(point.longitude / cell).floor()}';
      final current = kept[key];
      if (current == null || (current.isCommunity && !spot.isCommunity)) {
        kept[key] = spot;
      }
    }

    final pins = kept.values.toList(growable: false);
    return pins.length <= maxPins ? pins : pins.sublist(0, maxPins);
  }
}
