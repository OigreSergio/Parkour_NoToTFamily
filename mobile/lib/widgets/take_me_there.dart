import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/spot.dart';
import '../services/spot_directions.dart';

/// "Take me there": hands the spot to the phone's own maps app.
///
/// Tries the platform's own scheme first (Android shows every map app
/// installed, iOS opens Apple Maps) and falls back to a web map, so the button
/// works wherever the app runs — including the browser.
class TakeMeThereButton extends StatelessWidget {
  const TakeMeThereButton({
    super.key,
    required this.spot,
    this.distanceLabel,
    this.compact = false,
  });

  final Spot spot;

  /// Live distance to show on the button, when the position is known.
  final String? distanceLabel;

  /// Small text version, for tight spots like a list row.
  final bool compact;

  Future<void> _open(BuildContext context) async {
    final messenger = ScaffoldMessenger.of(context);
    for (final uri in SpotDirections.candidatesFor(spot)) {
      try {
        if (await launchUrl(uri, mode: LaunchMode.externalApplication)) return;
      } catch (_) {
        // This scheme is not handled here: try the next one.
      }
    }
    messenger.showSnackBar(
      const SnackBar(content: Text('No maps app answered. Odd!')),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (compact) {
      return TextButton.icon(
        onPressed: () => _open(context),
        icon: const Icon(Icons.directions_walk, size: 16),
        // One word: the row is narrow, and the icon carries the meaning.
        label: const Text('Go'),
        style: TextButton.styleFrom(
          visualDensity: VisualDensity.compact,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          minimumSize: Size.zero,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
        ),
      );
    }

    return FilledButton.icon(
      onPressed: () => _open(context),
      icon: const Icon(Icons.directions_walk),
      label: Text(
        distanceLabel == null ? 'Take me there' : 'Take me there · $distanceLabel',
      ),
    );
  }
}
