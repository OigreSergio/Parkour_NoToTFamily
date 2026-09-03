import 'package:flutter/material.dart';

import '../models/spot.dart';
import '../services/spot_imagery.dart';

/// Read-only detail view for a single [Spot].
class SpotDetailScreen extends StatelessWidget {
  const SpotDetailScreen({super.key, required this.spot});

  final Spot spot;

  /// Photos of the spot, or — when it has none — a single aerial view of its
  /// coordinates, so every spot opens with a picture of the place.
  static List<String> _gallery(Spot spot) => spot.photoUrls.isNotEmpty
      ? spot.photoUrls
      : [SpotImagery.aerialUrl(spot.location, width: 800, height: 600)];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(spot.name)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (_gallery(spot).isNotEmpty) ...[
            SizedBox(
              height: 200,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _gallery(spot).length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, i) => ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.network(
                    _gallery(spot)[i],
                    width: 280,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => Container(
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
          _DifficultyStars(difficulty: spot.difficulty),
          const SizedBox(height: 16),
          Text(
            spot.description.isEmpty ? 'No description yet.' : spot.description,
            style: theme.textTheme.bodyLarge,
          ),
          const SizedBox(height: 24),
          _InfoRow(
            icon: Icons.place_outlined,
            label: 'Location',
            value: '${spot.location.lat.toStringAsFixed(5)}, '
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

class _DifficultyStars extends StatelessWidget {
  const _DifficultyStars({required this.difficulty});

  final int difficulty;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (var i = 1; i <= 5; i++)
          Icon(
            i <= difficulty ? Icons.star : Icons.star_border,
            size: 20,
            color: Colors.amber,
          ),
        const SizedBox(width: 8),
        Text('Difficulty $difficulty/5',
            style: Theme.of(context).textTheme.bodySmall),
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
