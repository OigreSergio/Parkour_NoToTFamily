import 'package:flutter/material.dart';

import '../models/spot.dart';
import '../repositories/moderation_repository.dart';
import '../widgets/report_button.dart';
import '../widgets/spot_completeness.dart';
import '../widgets/spot_distance.dart';
import 'safety_gate_screen.dart' show SpotSafetyReminder;

/// Read-only detail view for a single [Spot].
class SpotDetailScreen extends StatelessWidget {
  const SpotDetailScreen({super.key, required this.spot});

  final Spot spot;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(spot.name),
        actions: [ReportButton(kind: ReportKind.spot, targetId: spot.id)],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (spot.photos.isNotEmpty) ...[
            SizedBox(
              height: 224,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: spot.photos.length,
                separatorBuilder: (_, _) => const SizedBox(width: 8),
                itemBuilder: (context, i) {
                  final photo = spot.photos[i];
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(12),
                        child: Image.network(
                          photo.url,
                          width: 280,
                          height: 200,
                          fit: BoxFit.cover,
                          errorBuilder:
                              (_, _, _) => Container(
                                width: 280,
                                height: 200,
                                color:
                                    theme.colorScheme.surfaceContainerHighest,
                                child: const Icon(Icons.broken_image_outlined),
                              ),
                        ),
                      ),
                      SizedBox(width: 280, child: PhotoCredit(photo: photo)),
                    ],
                  );
                },
              ),
            ),
            const SizedBox(height: 20),
          ],
          Text(spot.name, style: theme.textTheme.headlineSmall),
          if (spot.where != null) ...[
            const SizedBox(height: 4),
            Text(spot.where!, style: theme.textTheme.bodySmall),
          ],
          const SizedBox(height: 6),
          SpotCompletenessBadge(completeness: spot.completeness),
          const SizedBox(height: 10),
          _SkillLevel(spot: spot),
          const SizedBox(height: 16),
          // È qui che si decide davvero se andarci: un avviso visto una volta
          // all'avvio non accompagna quella decisione.
          const SpotSafetyReminder(),
          const SizedBox(height: 16),
          if (spot.description.isNotEmpty) ...[
            Text(spot.description, style: theme.textTheme.bodyLarge),
            const SizedBox(height: 20),
          ],
          // Chiede esattamente ciò che manca. È l'unico canale da cui possono
          // arrivare livello, affollamento e "cosa ci si allena": nessuna API
          // li conosce.
          ContributeToSpot(spot: spot),
          const SizedBox(height: 12),
          SpotDistance(spot: spot),
          const SizedBox(height: 12),
          _InfoRow(
            icon: Icons.place_outlined,
            label: 'Coordinate',
            value:
                '${spot.location.lat.toStringAsFixed(5)}, '
                '${spot.location.lng.toStringAsFixed(5)}',
          ),
          _InfoRow(
            icon: Icons.water_drop_outlined,
            label: 'Acqua',
            value: switch (spot.hasFountain) {
              true => 'sì, nei pressi',
              false => 'no',
              // Null non è "no": è che nessuno ha guardato.
              null => 'non lo sappiamo',
            },
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
