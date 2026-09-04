import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;

import '../models/spot.dart';

/// Hands a spot over to whatever maps app the phone uses for directions.
///
/// No map app is assumed: on Android the `geo:` intent lets the system offer
/// the ones installed (Google Maps, Organic Maps, Magic Earth…), on iOS the
/// spot goes to Apple Maps, and anywhere else — the web build included — a
/// plain https link opens the user's default map site. Every URI carries the
/// spot's name, so it arrives labelled and not as bare coordinates.
class SpotDirections {
  const SpotDirections._();

  /// The URIs to try, best first: the caller launches the first one the
  /// platform accepts and falls back to the next.
  static List<Uri> candidatesFor(
    Spot spot, {
    bool isWeb = kIsWeb,
    String? operatingSystem,
  }) {
    final lat = spot.location.lat;
    final lng = spot.location.lng;
    final label = Uri.encodeComponent(spot.name);
    final universal = Uri.parse(
      'https://www.google.com/maps/dir/?api=1&destination=$lat,$lng',
    );

    if (isWeb) return [universal];

    final os = operatingSystem ?? _currentOs();
    return switch (os) {
      // Lets Android show every maps app installed, the user picks.
      'android' => [
          Uri.parse('geo:$lat,$lng?q=$lat,$lng($label)'),
          universal,
        ],
      // Apple Maps by its own scheme, then the web page it shares with it.
      'ios' || 'macos' => [
          Uri.parse('maps://?daddr=$lat,$lng&q=$label'),
          Uri.parse('https://maps.apple.com/?daddr=$lat,$lng&q=$label'),
          universal,
        ],
      _ => [universal],
    };
  }

  static String _currentOs() {
    try {
      return Platform.operatingSystem;
    } catch (_) {
      return 'unknown';
    }
  }
}
