import 'package:flutter/material.dart';

import '../models/spot.dart';
import '../services/spot_imagery.dart';

/// Read-only detail view for a single [Spot].
class SpotDetailScreen extends StatelessWidget {
  const SpotDetailScreen({super.key, required this.spot});

  final Spot spot;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final photos = spot.photoUrls;

    return Scaffold(
      appBar: AppBar(title: Text(spot.name)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (photos.isNotEmpty)
            SizedBox(
              height: 200,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: photos.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, i) => ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.network(
                    photos[i],
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
            )
          else
            _SatelliteView(spot: spot),
          const SizedBox(height: 20),
          if (spot.isCommunity) ...[
            const _UnverifiedBanner(),
            const SizedBox(height: 16),
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

/// Satellite view of a spot nobody has photographed yet.
///
/// The community spots come from a shared online list: no one from the family
/// has been there, so there is no photo — but there is always the sky. The
/// imagery is Esri's World Imagery, the same source the web app uses.
class _SatelliteView extends StatelessWidget {
  const _SatelliteView({required this.spot});

  final Spot spot;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: AspectRatio(
            aspectRatio: 16 / 9,
            child: Image.network(
              SpotImagery.aerialUrl(spot.location, width: 800, height: 450),
              fit: BoxFit.cover,
              loadingBuilder: (context, child, progress) => progress == null
                  ? child
                  : ColoredBox(
                      color: theme.colorScheme.surfaceContainerHighest,
                      child: const Center(
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    ),
              errorBuilder: (_, __, ___) => ColoredBox(
                color: theme.colorScheme.surfaceContainerHighest,
                child: const Center(child: Icon(Icons.satellite_alt_outlined)),
              ),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            Icon(
              Icons.satellite_alt_outlined,
              size: 14,
              color: theme.colorScheme.outline,
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                'Satellite view — no photo of this spot yet. '
                'Imagery © Esri World Imagery.',
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.outline),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Says out loud that a community spot has not been checked by anyone.
class _UnverifiedBanner extends StatelessWidget {
  const _UnverifiedBanner();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(Icons.help_outline, color: theme.colorScheme.onSecondaryContainer),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Not verified: found on the shared community list, nobody from '
              'the family has been there yet.',
              style: theme.textTheme.bodySmall
                  ?.copyWith(color: theme.colorScheme.onSecondaryContainer),
            ),
          ),
        ],
      ),
    );
  }
}
