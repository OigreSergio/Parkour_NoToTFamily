import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../models/spot.dart';
import '../providers.dart';
import '../services/location_service.dart';
import '../widgets/error_view.dart';
import 'login_screen.dart';
import 'spot_detail_screen.dart';
import 'submit_spot_screen.dart';

/// OpenStreetMap view (via `flutter_map`) with one marker per verified spot.
/// Tapping a marker shows its name and description; a long-press anywhere
/// proposes a new spot at that location (login required — the submission
/// stays `pending` until an admin verifies it).
class SpotsMapScreen extends ConsumerWidget {
  const SpotsMapScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final spotsAsync = ref.watch(spotsProvider);
    final center = ref.watch(currentLocationProvider).valueOrNull ??
        LocationService.fallbackCenter;

    return spotsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => ErrorView(
        message: 'Could not load spots.\n$error',
        onRetry: () => ref.invalidate(spotsProvider),
      ),
      data: (spots) => FlutterMap(
        options: MapOptions(
          initialCenter: center,
          initialZoom: 12,
          onLongPress: (_, point) => _proposeSpot(context, ref, point),
        ),
        children: [
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'family.notot.parkour_notot',
          ),
          MarkerLayer(
            markers: [
              for (final spot in spots)
                Marker(
                  point: spot.location.toLatLng(),
                  width: 44,
                  height: 44,
                  alignment: Alignment.topCenter,
                  child: GestureDetector(
                    onTap: () => _showSpot(context, spot),
                    child: const Icon(
                      Icons.location_on,
                      color: Colors.redAccent,
                      size: 44,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  void _proposeSpot(BuildContext context, WidgetRef ref, LatLng point) {
    final user = ref.read(authControllerProvider).valueOrNull;
    if (user == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Sign in to suggest a new spot.'),
          action: SnackBarAction(
            label: 'Sign in',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => const LoginScreen()),
            ),
          ),
        ),
      );
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SubmitSpotScreen(location: point),
      ),
    );
  }

  void _showSpot(BuildContext context, Spot spot) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(spot.name, style: Theme.of(sheetContext).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              spot.description.isEmpty
                  ? 'No description yet.'
                  : spot.description,
              style: Theme.of(sheetContext).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton(
                onPressed: () {
                  Navigator.of(sheetContext).pop();
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => SpotDetailScreen(spot: spot),
                    ),
                  );
                },
                child: const Text('Details'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
