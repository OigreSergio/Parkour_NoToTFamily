import '../models/spot.dart';

/// Pictures for a spot that has no photo of its own.
///
/// Every spot has coordinates, so an aerial view can always be drawn for it:
/// the web app does the same ("vista aerea" in `docs/demo/pk-scheda.js`) with
/// Esri's World Imagery export endpoint — no API key, no image stored in the
/// repo.
class SpotImagery {
  const SpotImagery._();

  static const String _export =
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery'
      '/MapServer/export';

  /// Half-size of the framed box around the spot, in degrees. Same framing as
  /// the web app: a block or two around the point.
  static const double _halfLng = 0.0015;
  static const double _halfLat = 0.0006;

  /// Aerial view centred on [location], [width] x [height] pixels.
  static String aerialUrl(
    GeoPoint location, {
    int width = 640,
    int height = 360,
  }) {
    final west = location.lng - _halfLng;
    final south = location.lat - _halfLat;
    final east = location.lng + _halfLng;
    final north = location.lat + _halfLat;
    return '$_export?bbox=$west,$south,$east,$north'
        '&bboxSR=4326&size=$width,$height&imageSR=3857&format=jpg&f=image';
  }

  /// The image to show for [spot], best first:
  ///
  /// 1. a real photo of the spot,
  /// 2. the Street View shot aimed at it — trees and roofs hide from above
  ///    what is obvious from the pavement,
  /// 3. the aerial view, which every spot can always fall back to.
  static String coverUrl(Spot spot, {int width = 640, int height = 360}) {
    final preview = spot.previewUrl;
    if (preview != null && preview.isNotEmpty) return preview;
    final streetView = spot.streetViewUrl;
    if (streetView != null && streetView.isNotEmpty) return streetView;
    return aerialUrl(spot.location, width: width, height: height);
  }

  /// True when [coverUrl] is going to be the aerial view — nothing closer to
  /// the ground was found for this spot.
  static bool onlyAerial(Spot spot) =>
      (spot.previewUrl?.isEmpty ?? true) && (spot.streetViewUrl?.isEmpty ?? true);
}
