import 'package:flutter/material.dart';

import '../models/spot.dart';

/// Read-only detail view for a single [Spot].
class SpotDetailScreen extends StatelessWidget {
  const SpotDetailScreen({super.key, required this.spot});

  final Spot spot;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(spot.name)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (spot.photoUrls.isNotEmpty) ...[
            SizedBox(
              height: 200,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: spot.photoUrls.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder:
                    (context, i) => ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.network(
                        spot.photoUrls[i],
                        width: 280,
                        fit: BoxFit.cover,
                        errorBuilder:
                            (_, __, ___) => Container(
                              width: 280,
                              color: theme.colorScheme.surfaceContainerHighest,
                              child: const Icon(Icons.broken_image_outlined),
                            ),
                      ),
                    ),
              ),
            ),
            const SizedBox(height: 20),
          ],
          Text(spot.name, style: theme.textTheme.headlineSmall),
          const SizedBox(height: 8),
          _SkillLevel(spot: spot),
          const SizedBox(height: 16),
          Text(
            spot.description.isEmpty ? 'No description yet.' : spot.description,
            style: theme.textTheme.bodyLarge,
          ),
          const SizedBox(height: 24),
          _InfoRow(
            icon: Icons.place_outlined,
            label: 'Location',
            value:
                '${spot.location.lat.toStringAsFixed(5)}, '
                '${spot.location.lng.toStringAsFixed(5)}',
          ),
          _InfoRow(
            icon: Icons.verified_outlined,
            label: 'Status',
            value: spot.status,
          ),
        ],
      ),
    );
  }
}

/// Livello dello spot, oppure la dichiarazione che nessuno l'ha valutato.
///
/// La maggior parte degli spot importati non ha una valutazione: dirlo è
/// l'unica risposta onesta, e apre la porta al contributo della community.
class _SkillLevel extends StatelessWidget {
  const _SkillLevel({required this.spot});

  final Spot spot;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final label = spot.skillLabel;

    if (label == null) {
      return Row(
        children: [
          Icon(Icons.help_outline, size: 18, color: theme.colorScheme.outline),
          const SizedBox(width: 6),
          Text(
            'Livello non ancora valutato',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.outline,
            ),
          ),
        ],
      );
    }

    return Wrap(
      spacing: 8,
      children: [
        Chip(
          visualDensity: VisualDensity.compact,
          avatar: const Icon(Icons.trending_up, size: 16),
          label: Text(label),
        ),
        if (spot.crowdLabel != null)
          Chip(
            visualDensity: VisualDensity.compact,
            avatar: const Icon(Icons.groups_outlined, size: 16),
            label: Text(spot.crowdLabel!),
          ),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: theme.colorScheme.primary),
          const SizedBox(width: 12),
          Text('$label: ', style: theme.textTheme.labelLarge),
          Expanded(child: Text(value, style: theme.textTheme.bodyMedium)),
        ],
      ),
    );
  }
}
