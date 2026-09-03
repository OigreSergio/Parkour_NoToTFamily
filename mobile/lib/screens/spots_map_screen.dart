import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_vector_tiles/flutter_map_vector_tiles.dart' as vt;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/spot.dart';
import '../providers.dart';
import '../services/location_service.dart';
import '../widgets/error_view.dart';
import '../widgets/sewing_pin.dart';
import 'spot_detail_screen.dart';

/// The "ricamo" map: the world stitched on linen (see `services/map_style.dart`)
/// with a sewing pin on every spot. Tapping a pin shows its name and
/// description.
///
/// While the style loads — and if it cannot be loaded at all — the map falls
/// back to plain OpenStreetMap raster tiles, so the pins are never stranded on
/// an empty background.
class SpotsMapScreen extends ConsumerWidget {
  const SpotsMapScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final spotsAsync = ref.watch(spotsProvider);
    final styleAsync = ref.watch(mapStyleProvider);
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
          maxZoom: 18,
        ),
        children: [
          styleAsync.maybeWhen(
            data: (style) => vt.VectorTileLayer(
              theme: style.theme,
              tileProviders: style.providers,
              rasterSources: style.rasterSources,
              sprites: style.sprites,
            ),
            orElse: () => TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'family.notot.parkour_notot',
            ),
          ),
          MarkerLayer(
            markers: [
              for (final spot in spots)
                Marker(
                  point: spot.location.toLatLng(),
                  width: 34,
                  height: 52,
                  alignment: Alignment.topCenter,
                  child: GestureDetector(
                    onTap: () => _showSpot(context, spot),
                    child: SewingPin(
                      color: spot.isCommunity
                          ? SewingPin.pinBlue
                          : SewingPin.pinRed,
                    ),
                  ),
                ),
            ],
          ),
          RichAttributionWidget(
            attributions: [
              TextSourceAttribution(styleAsync.maybeWhen(
                data: (style) => style.attributions
                    .map((a) => a.text)
                    .join(' · '),
                orElse: () => 'OpenStreetMap contributors',
              )),
            ],
          ),
        ],
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
            Row(
              children: [
                SewingPin(
                  color: spot.isCommunity
                      ? SewingPin.pinBlue
                      : SewingPin.pinRed,
                  size: const Size(17, 26),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    spot.name,
                    style: Theme.of(sheetContext).textTheme.titleLarge,
                  ),
                ),
              ],
            ),
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
