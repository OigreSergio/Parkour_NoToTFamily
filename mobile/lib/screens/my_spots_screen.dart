import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/spot.dart';
import '../providers.dart';
import '../widgets/error_view.dart';

/// The caller's own submissions with their moderation status.
class MySpotsScreen extends ConsumerWidget {
  const MySpotsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final spotsAsync = ref.watch(mySpotsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('My submissions')),
      body: spotsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorView(
          message: 'Could not load your submissions.\n$error',
          onRetry: () => ref.invalidate(mySpotsProvider),
        ),
        data: (spots) => spots.isEmpty
            ? const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'No submissions yet. Long-press anywhere on the map to '
                    'suggest a spot!',
                    textAlign: TextAlign.center,
                  ),
                ),
              )
            : RefreshIndicator(
                onRefresh: () async => ref.invalidate(mySpotsProvider),
                child: ListView.builder(
                  physics: const AlwaysScrollableScrollPhysics(),
                  itemCount: spots.length,
                  itemBuilder: (context, i) => _SpotTile(spot: spots[i]),
                ),
              ),
      ),
    );
  }
}

class _SpotTile extends StatelessWidget {
  const _SpotTile({required this.spot});

  final Spot spot;

  @override
  Widget build(BuildContext context) {
    final (color, icon, label) = switch (spot.status) {
      'verified' => (Colors.green, Icons.verified, 'Verified — on the map'),
      'rejected' => (Colors.red, Icons.cancel_outlined, 'Rejected'),
      _ => (Colors.orange, Icons.hourglass_top, 'Pending review'),
    };
    return ListTile(
      leading: Icon(icon, color: color),
      title: Text(spot.name),
      subtitle: Text(label),
      trailing: Text(
        '${spot.createdAt.day}/${spot.createdAt.month}/${spot.createdAt.year}',
        style: Theme.of(context).textTheme.bodySmall,
      ),
    );
  }
}
