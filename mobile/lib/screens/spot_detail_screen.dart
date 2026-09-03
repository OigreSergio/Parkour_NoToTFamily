import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/spot.dart';
import '../models/water_point.dart';
import '../providers.dart';
import '../repositories/water_repository.dart';
import '../services/spot_distance.dart';
import '../services/spot_imagery.dart';
import '../widgets/spot_rating.dart';

/// Read-only detail view for a single [Spot].
class SpotDetailScreen extends ConsumerWidget {
  const SpotDetailScreen({super.key, required this.spot});

  final Spot spot;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final photos = spot.photoUrls;
    final here = ref.watch(currentLocationProvider).valueOrNull;
    final distance = SpotDistance.labelFor(spot, here);

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
            _GroundOrSkyView(spot: spot),
          const SizedBox(height: 20),
          if (spot.isCommunity) ...[
            const _UnverifiedBanner(),
            const SizedBox(height: 16),
          ],
          Text(spot.name, style: theme.textTheme.headlineSmall),
          const SizedBox(height: 8),
          SpotRating(spot: spot),
          if (distance != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.near_me_outlined, size: 18),
                const SizedBox(width: 6),
                Text('$distance from you', style: theme.textTheme.bodyMedium),
              ],
            ),
          ],
          const SizedBox(height: 16),
          Text(
            spot.description.isEmpty ? 'No description yet.' : spot.description,
            style: theme.textTheme.bodyLarge,
          ),
          const SizedBox(height: 20),
          _WaterNearby(spot: spot),
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

/// The best picture of a spot that has no photo of its own.
///
/// Street View first: from above, trees, canopies and roofs hide exactly the
/// walls and rails a traceur is looking for, while the pavement view shows
/// them. The satellite view stays as the fallback for spots no car ever drove
/// past. Both are labelled for what they are.
class _GroundOrSkyView extends StatelessWidget {
  const _GroundOrSkyView({required this.spot});

  final Spot spot;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final streetView = spot.streetViewUrl;
    final fromTheGround = streetView != null && streetView.isNotEmpty;
    final url = fromTheGround
        ? streetView
        : SpotImagery.aerialUrl(spot.location, width: 800, height: 450);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: AspectRatio(
            aspectRatio: 16 / 9,
            child: Image.network(
              url,
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
              fromTheGround ? Icons.streetview : Icons.satellite_alt_outlined,
              size: 14,
              color: theme.colorScheme.outline,
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                fromTheGround
                    ? 'Street View pointed at the spot — no photo of it yet. '
                        'Imagery © Google.'
                    : 'Satellite view — no photo or street-level shot of this '
                        'spot yet. Imagery © Esri World Imagery.',
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

/// Where to fill a bottle near the spot, from OpenStreetMap.
///
/// Parkour is thirsty work and the family's spots are often a piazza with a
/// *nasone* around the corner. The lookup runs when the spot is opened and
/// says plainly when nothing is mapped nearby — "none found" is different from
/// "there is none".
class _WaterNearby extends ConsumerWidget {
  const _WaterNearby({required this.spot});

  final Spot spot;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final water = ref.watch(waterNearSpotProvider(spot));

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.water_drop_outlined, color: theme.colorScheme.primary),
          const SizedBox(width: 10),
          Expanded(
            child: water.when(
              loading: () => Text(
                'Looking for drinking water nearby…',
                style: theme.textTheme.bodyMedium,
              ),
              error: (_, __) => Text(
                'Could not check for drinking water right now.',
                style: theme.textTheme.bodyMedium,
              ),
              data: (points) => _summary(context, points),
            ),
          ),
        ],
      ),
    );
  }

  Widget _summary(BuildContext context, List<WaterPoint> points) {
    final theme = Theme.of(context);

    if (points.isEmpty) {
      return Text(
        'No drinking water mapped within '
        '${WaterRepositoryRadius.label}. Bring a bottle.',
        style: theme.textTheme.bodyMedium,
      );
    }

    final nearest = points.first;
    final rest = points.length - 1;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${nearest.label} ${SpotDistance.format(nearest.distanceMeters)} away'
          '${nearest.name == null ? '' : ' — ${nearest.name}'}',
          style: theme.textTheme.bodyMedium
              ?.copyWith(fontWeight: FontWeight.w600),
        ),
        if (rest > 0)
          Text(
            '$rest more within ${WaterRepositoryRadius.label}.',
            style: theme.textTheme.bodySmall,
          ),
        Text(
          'Data © OpenStreetMap contributors.',
          style: theme.textTheme.bodySmall
              ?.copyWith(color: theme.colorScheme.outline),
        ),
      ],
    );
  }
}

/// The search radius, spelled out once for the copy above.
class WaterRepositoryRadius {
  const WaterRepositoryRadius._();

  static String get label =>
      SpotDistance.format(WaterRepository.defaultRadiusMeters.toDouble());
}
