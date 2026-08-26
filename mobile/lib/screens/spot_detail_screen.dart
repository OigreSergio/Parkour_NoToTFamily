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
          if (spot.photoUrls.isNotEmpty)
            _PhotoStrip(spot: spot)
          else
            const _NoPhotoPlaceholder(),
          const SizedBox(height: 20),
          Text(spot.name, style: theme.textTheme.headlineSmall),
          const SizedBox(height: 8),
          _DifficultyStars(difficulty: spot.difficulty),
          const SizedBox(height: 16),
          Text(
            spot.description.isEmpty ? 'No description yet.' : spot.description,
            style: theme.textTheme.bodyLarge,
          ),
          if (!spot.surveyed) ...[
            const SizedBox(height: 12),
            const _SurveyNotice(),
          ],
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

/// Horizontal carousel of the spot photos, each with its caption and credit.
///
/// [Spot.photoUrls] stays the source of truth for what to show — [Spot.photos]
/// only adds captions and attribution, and is empty against an older backend.
class _PhotoStrip extends StatelessWidget {
  const _PhotoStrip({required this.spot});

  final Spot spot;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SizedBox(
      height: 246,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: spot.photoUrls.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final photo = i < spot.photos.length ? spot.photos[i] : null;
          return SizedBox(
            width: 280,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Stack(
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.network(
                        spot.photoUrls[i],
                        width: 280,
                        height: 200,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          width: 280,
                          height: 200,
                          color: theme.colorScheme.surfaceContainerHighest,
                          child: const Icon(Icons.broken_image_outlined),
                        ),
                      ),
                    ),
                    // A context shot of the surrounding place must never read
                    // as a photo of the obstacles themselves.
                    if (photo?.kind == 'area')
                      Positioned(
                        left: 8,
                        top: 8,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.62),
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: const Text(
                            'zona',
                            style: TextStyle(color: Colors.white, fontSize: 11),
                          ),
                        ),
                      ),
                  ],
                ),
                if (photo != null) ...[
                  const SizedBox(height: 6),
                  if (photo.caption.isNotEmpty)
                    Text(
                      photo.caption,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall,
                    ),
                  if (photo.credit.isNotEmpty)
                    Text(
                      photo.credit,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: theme.colorScheme.outline,
                      ),
                    ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _NoPhotoPlaceholder extends StatelessWidget {
  const _NoPhotoPlaceholder();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      height: 140,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.add_a_photo_outlined, color: theme.colorScheme.outline),
          const SizedBox(height: 8),
          Text(
            'Ancora nessuna foto di questo spot',
            style: theme.textTheme.bodyMedium,
          ),
          Text(
            'Sei stato qui? Mandaci la tua.',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.outline,
            ),
          ),
        ],
      ),
    );
  }
}

class _SurveyNotice extends StatelessWidget {
  const _SurveyNotice();

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
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline,
              size: 20, color: theme.colorScheme.onSecondaryContainer),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Gli ostacoli di questo spot non sono ancora stati censiti sul '
              'posto: quello che leggi è il contesto, non l\'inventario. '
              'Se ci vai, aiutaci a completarlo.',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSecondaryContainer,
              ),
            ),
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
