import 'package:flutter/material.dart';

import '../models/spot.dart';

/// What a spot is rated — or, for now, that nobody has rated it.
///
/// The app never invents a score: stars appear only once real people have left
/// a rating ([Spot.isRated]). Until then the spot reads *Not rated yet*, which
/// is the honest thing to show to someone who has never been there.
class SpotRating extends StatelessWidget {
  const SpotRating({super.key, required this.spot, this.compact = false});

  final Spot spot;

  /// Compact form for a list row: just the label or `4.2 ★ (7)`.
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (!spot.isRated) {
      final label = Text(
        compact ? 'Not rated' : 'Not rated yet',
        style: (compact ? theme.textTheme.labelSmall : theme.textTheme.bodyMedium)
            ?.copyWith(color: theme.colorScheme.outline),
      );
      return compact
          ? Chip(
              label: label,
              visualDensity: VisualDensity.compact,
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            )
          : Row(
              children: [
                Icon(Icons.star_border,
                    size: 18, color: theme.colorScheme.outline),
                const SizedBox(width: 6),
                label,
              ],
            );
    }

    final rating = spot.rating!;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var i = 1; i <= 5; i++)
          Icon(
            i <= rating.round() ? Icons.star : Icons.star_border,
            size: compact ? 14 : 20,
            color: Colors.amber,
          ),
        const SizedBox(width: 6),
        Text(
          '${rating.toStringAsFixed(1)} (${spot.ratingCount})',
          style: compact ? theme.textTheme.labelSmall : theme.textTheme.bodyMedium,
        ),
      ],
    );
  }
}
