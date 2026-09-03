import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';
import '../services/spot_imagery.dart';
import '../widgets/error_view.dart';
import 'spot_detail_screen.dart';

/// Scrollable list of verified spots. Tapping a row opens its detail screen.
class SpotsListScreen extends ConsumerWidget {
  const SpotsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final spotsAsync = ref.watch(spotsProvider);

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
              return ListTile(
                leading: _SpotThumbnail(url: SpotImagery.coverUrl(spot, width: 112, height: 112)),
                title: Text(spot.name),
                subtitle: Text(
                  spot.description.isEmpty
                      ? 'No description yet.'
                      : spot.description,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: _DifficultyBadge(difficulty: spot.difficulty),
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

class _DifficultyBadge extends StatelessWidget {
  const _DifficultyBadge({required this.difficulty});

  final int difficulty;

  @override
  Widget build(BuildContext context) {
    return Chip(
      visualDensity: VisualDensity.compact,
      label: Text('$difficulty/5'),
      avatar: const Icon(Icons.trending_up, size: 16),
    );
  }
}
