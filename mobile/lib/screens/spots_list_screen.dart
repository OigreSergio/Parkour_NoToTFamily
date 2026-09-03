import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';
import '../services/spot_distance.dart';
import '../services/spot_imagery.dart';
import '../widgets/error_view.dart';
import '../widgets/spot_rating.dart';
import 'spot_detail_screen.dart';

/// Scrollable list of verified spots. Tapping a row opens its detail screen.
class SpotsListScreen extends ConsumerWidget {
  const SpotsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final spotsAsync = ref.watch(spotsProvider);
    // Null until the device gives a fix (or when the user turned location off):
    // the rows then simply omit the distance.
    final here = ref.watch(currentLocationProvider).valueOrNull;

    return spotsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => ErrorView(
        message: 'Could not load spots.\n$error',
        onRetry: () => ref.invalidate(spotsProvider),
      ),
      data: (spots) {
        if (spots.isEmpty) {
          return const Center(child: Text('No spots nearby yet.'));
        }
        return RefreshIndicator(
          onRefresh: () => ref.refresh(spotsProvider.future),
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            itemCount: spots.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, i) {
              final spot = spots[i];
              final distance = SpotDistance.labelFor(spot, here);
              return ListTile(
                leading: _SpotThumbnail(
                  url: SpotImagery.coverUrl(spot, width: 112, height: 112),
                ),
                title: Text(spot.name),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      spot.description.isEmpty
                          ? 'No description yet.'
                          : spot.description,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (distance != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Row(
                          children: [
                            const Icon(Icons.near_me_outlined, size: 14),
                            const SizedBox(width: 4),
                            Text(
                              distance,
                              style: Theme.of(context).textTheme.labelMedium,
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
                isThreeLine: distance != null,
                trailing: SpotRating(spot: spot, compact: true),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => SpotDetailScreen(spot: spot),
                  ),
                ),
              );
            },
          ),
        );
      },
    );
  }
}

/// Spot photo, or the aerial view of its coordinates when it has none — so a
/// row never falls back to a bare icon.
class _SpotThumbnail extends StatelessWidget {
  const _SpotThumbnail({required this.url});

  final String? url;

  @override
  Widget build(BuildContext context) {
    if (url == null) {
      return const SizedBox(
        width: 56,
        height: 56,
        child: Icon(Icons.place_outlined),
      );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: Image.network(
        url!,
        width: 56,
        height: 56,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => const SizedBox(
          width: 56,
          height: 56,
          child: Icon(Icons.place_outlined),
        ),
      ),
    );
  }
}

