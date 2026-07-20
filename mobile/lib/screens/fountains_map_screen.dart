import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../models/fountain.dart';
import '../providers.dart';
import '../services/location_service.dart';
import '../widgets/error_view.dart';

/// Map of Rome's public drinking fountains (nasoni, taps and drinkable
/// fountains), from the bundled dataset that cross-references OpenStreetMap
/// and Wikidata. Opened from the fountain icon in the home app bar.
class FountainsMapScreen extends ConsumerWidget {
  const FountainsMapScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final fountainsAsync = ref.watch(fountainsProvider);
    final center = ref.watch(currentLocationProvider).valueOrNull ??
        LocationService.fallbackCenter;

    return Scaffold(
      appBar: AppBar(
        title: fountainsAsync.when(
          loading: () => const Text('Fontanelle · Roma'),
          error: (_, __) => const Text('Fontanelle · Roma'),
          data: (d) => Text('Fontanelle · Roma (${d.fountains.length})'),
        ),
      ),
      body: fountainsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorView(
          message: 'Could not load the fountain dataset.\n$error',
          onRetry: () => ref.invalidate(fountainsProvider),
        ),
        data: (dataset) => _FountainsMap(dataset: dataset, center: center),
      ),
    );
  }
}

class _FountainsMap extends StatefulWidget {
  const _FountainsMap({required this.dataset, required this.center});

  final FountainDataset dataset;
  final LatLng center;

  @override
  State<_FountainsMap> createState() => _FountainsMapState();
}

class _FountainsMapState extends State<_FountainsMap> {
  final MapController _controller = MapController();

  /// Cap on simultaneously rendered markers; when the viewport holds more,
  /// the list is subsampled evenly (high-confidence fountains are listed
  /// first in the dataset, so they survive subsampling).
  static const int _maxMarkers = 400;

  LatLngBounds? _bounds;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  List<Fountain> _visibleFountains() {
    final bounds = _bounds;
    final all = widget.dataset.fountains;
    final visible = bounds == null
        ? all
        : all.where((f) => bounds.contains(f.toLatLng())).toList();
    if (visible.length <= _maxMarkers) return visible;
    final step = visible.length / _maxMarkers;
    return [
      for (var i = 0; i < _maxMarkers; i++) visible[(i * step).floor()],
    ];
  }

  @override
  Widget build(BuildContext context) {
    final fountains = _visibleFountains();

    return FlutterMap(
      mapController: _controller,
      options: MapOptions(
        initialCenter: widget.center,
        initialZoom: 14,
        onMapEvent: (event) {
          // Re-filter markers whenever the viewport settles.
          if (event is MapEventMoveEnd ||
              event is MapEventFlingAnimationEnd ||
              event is MapEventDoubleTapZoomEnd ||
              event is MapEventScrollWheelZoom) {
            setState(() => _bounds = _controller.camera.visibleBounds);
          }
        },
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'family.notot.parkour_notot',
        ),
        MarkerLayer(
          markers: [
            for (final fountain in fountains)
              Marker(
                point: fountain.toLatLng(),
                width: 34,
                height: 34,
                alignment: Alignment.topCenter,
                child: GestureDetector(
                  onTap: () => _showFountain(context, fountain),
                  child: Icon(
                    fountain.kind == 'fountain'
                        ? Icons.water
                        : Icons.water_drop,
                    color: fountain.confidence > 1
                        ? Colors.indigo
                        : Colors.blueAccent,
                    size: 34,
                  ),
                ),
              ),
          ],
        ),
        SimpleAttributionWidget(
          source: Text(
            ['OpenStreetMap contributors', 'Wikidata'].join(' · '),
          ),
        ),
      ],
    );
  }

  void _showFountain(BuildContext context, Fountain fountain) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        final theme = Theme.of(sheetContext);
        return Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.water_drop, color: Colors.blueAccent),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      fountain.displayName,
                      style: theme.textTheme.titleLarge,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(fountain.kindLabel, style: theme.textTheme.bodyMedium),
              const SizedBox(height: 8),
              Text(
                fountain.confidence > 1
                    ? 'Confirmed by ${fountain.confidence} independent '
                        'sources: ${_sourceLabels(fountain.sources)}.'
                    : 'Source: ${_sourceLabels(fountain.sources)}.',
                style: theme.textTheme.bodySmall,
              ),
              if (fountain.wheelchair != null) ...[
                const SizedBox(height: 4),
                Text(
                  'Wheelchair access: ${fountain.wheelchair}',
                  style: theme.textTheme.bodySmall,
                ),
              ],
              if (fountain.bottle != null) ...[
                const SizedBox(height: 4),
                Text(
                  'Bottle refill: ${fountain.bottle}',
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  static String _sourceLabels(List<String> sources) => sources
      .map(
        (s) => switch (s) {
          'osm_drinking_water' ||
          'osm_water_tap' ||
          'osm_fountain' =>
            'OpenStreetMap',
          'wikidata' => 'Wikidata',
          _ => s,
        },
      )
      .toSet()
      .join(', ');
}
