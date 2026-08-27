import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/spot.dart';
import '../providers.dart';
import '../services/location_service.dart';
import '../services/spot_clustering.dart';
import '../widgets/error_view.dart';
import '../widgets/map_tiles.dart';
import '../widgets/spot_completeness.dart';
import 'auth/sign_in_screen.dart';
import 'propose_spot_screen.dart';
import 'spot_detail_screen.dart';

/// La mappa degli spot.
///
/// Tre cose la governano, e nessuna è cosmetica:
///
/// * **i tile arrivano da OpenFreeMap**, non da `tile.openstreetmap.org`: la
///   usage policy di OSM vieta esplicitamente i tile pubblici a un'app come
///   questa, e prima li stavamo usando;
/// * **i marker si costruiscono solo per il viewport**, raggruppati su griglia
///   ai livelli di zoom bassi. Con ~1.700 spot, disegnarli tutti blocca il
///   rendering;
/// * **la posizione non si chiede all'avvio.** La mappa parte da Roma, e il
///   GPS entra in gioco solo se lo tocchi.
class SpotsMapScreen extends ConsumerStatefulWidget {
  const SpotsMapScreen({super.key});

  @override
  ConsumerState<SpotsMapScreen> createState() => _SpotsMapScreenState();
}

class _SpotsMapScreenState extends ConsumerState<SpotsMapScreen> {
  final _map = MapController();

  LatLngBounds? _bounds;
  double _zoom = 12;

  @override
  void dispose() {
    _map.dispose();
    super.dispose();
  }

  void _onMapEvent(MapEvent event) {
    final camera = event.camera;
    // setState a ogni frame di pan sarebbe uno spreco: si aggiorna solo quando
    // il viewport è cambiato abbastanza da modificare i cluster.
    final moved =
        _bounds == null ||
        (camera.zoom - _zoom).abs() >= 0.5 ||
        !_bounds!.contains(camera.center);

    if (moved) {
      setState(() {
        _bounds = camera.visibleBounds;
        _zoom = camera.zoom;
      });
    }
  }

  Future<void> _locateMe() async {
    final result = await ref.read(locationRequestProvider.future);
    if (!mounted) return;

    if (result.hasPosition) {
      _map.move(result.position!, 15);
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(switch (result.status) {
          LocationStatus.serviceOff =>
            'La localizzazione del dispositivo è spenta.',
          LocationStatus.deniedForever =>
            'Permesso negato in modo permanente: si riattiva dalle '
                'impostazioni del browser o del telefono.',
          LocationStatus.denied =>
            'Nessun problema: la mappa funziona lo stesso.',
          _ => 'Non è stato possibile leggere la posizione.',
        }),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final spotsAsync = ref.watch(spotsProvider);
    final filter = ref.watch(spotFilterProvider);

    return Stack(
      children: [
        FlutterMap(
          mapController: _map,
          options: MapOptions(
            // Si parte da Roma, non dalla posizione dell'utente: chiedere il
            // GPS per centrare una mappa che nessuno ha ancora guardato è la
            // richiesta che la gente nega per riflesso.
            initialCenter: LocationService.fallbackCenter,
            initialZoom: 12,
            onMapEvent: _onMapEvent,
            interactionOptions: const InteractionOptions(
              flags: InteractiveFlag.all & ~InteractiveFlag.rotate,
            ),
          ),
          children: [
            const OpenFreeMapLayer(),
            if (_bounds != null)
              _ClusterLayer(
                clusters: SpotClustering.clusterize(
                  spots: filter.apply(spotsAsync.valueOrNull ?? const []),
                  bounds: _bounds!,
                  zoom: _zoom,
                ),
                zoom: _zoom,
                onTapCluster: _openCluster,
              ),
            const MapAttribution(),
          ],
        ),

        if (spotsAsync.isLoading)
          const Positioned(
            top: 12,
            left: 0,
            right: 0,
            child: Center(child: _Pill(child: Text('Carico gli spot…'))),
          ),

        if (spotsAsync.hasError)
          Positioned(
            top: 12,
            left: 12,
            right: 12,
            child: ErrorView(
              message: 'Non riesco a caricare gli spot.\n${spotsAsync.error}',
              onRetry: () => ref.invalidate(spotsProvider),
            ),
          ),

        Positioned(
          right: 12,
          bottom: 96,
          child: Column(
            children: [
              FloatingActionButton.small(
                heroTag: 'filtri',
                onPressed: _openFilters,
                tooltip: 'Filtri',
                child: Badge(
                  isLabelVisible: filter.isActive,
                  child: const Icon(Icons.tune),
                ),
              ),
              const SizedBox(height: 8),
              FloatingActionButton.small(
                heroTag: 'posizione',
                onPressed: () => _confirmThenLocate(),
                tooltip: 'Dove sono',
                child: const Icon(Icons.my_location),
              ),
              const SizedBox(height: 8),
              FloatingActionButton.small(
                heroTag: 'proponi',
                onPressed: _proposeSpot,
                tooltip: 'Proponi uno spot',
                child: const Icon(Icons.add_location_alt_outlined),
              ),
            ],
          ),
        ),
      ],
    );
  }

  /// Spiega **prima** a cosa serve la posizione, poi la chiede.
  ///
  /// La richiesta di sistema è secca e non dice niente sull'uso che ne verrà
  /// fatto. Questa schermata precede quella e dice le due cose che contano: a
  /// cosa serve, e che non viene conservata.
  Future<void> _confirmThenLocate() async {
    final already = await ref.read(locationServiceProvider).hasPermission();
    if (already) {
      await _locateMe();
      return;
    }
    if (!mounted) return;

    final ok = await showDialog<bool>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Usare la tua posizione?'),
            content: const Text(
              'Serve a centrare la mappa dove sei e a dirti quanto dista uno spot.\n\n'
              'Resta sul tuo dispositivo: non viene salvata, non viene inviata a '
              'nessun server, non finisce nei log. Puoi dire di no e continuare a '
              'usare la mappa.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('No, grazie'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Usa la posizione'),
              ),
            ],
          ),
    );

    if (ok == true) await _locateMe();
  }

  void _openCluster(SpotCluster cluster) {
    if (cluster.isSingle) {
      _showSpot(cluster.single);
      return;
    }
    // Un gruppo non apre una lista: zooma dentro. È la cosa che chi tocca un
    // pallino con un numero sopra si aspetta.
    _map.move(cluster.center, math.min(_zoom + 2.5, 18));
  }

  void _showSpot(Spot spot) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder:
          (sheet) => Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(spot.name, style: Theme.of(sheet).textTheme.titleLarge),
                if (spot.where != null)
                  Text(spot.where!, style: Theme.of(sheet).textTheme.bodySmall),
                const SizedBox(height: 8),
                SpotCompletenessBadge(completeness: spot.completeness),
                const SizedBox(height: 12),
                Text(
                  spot.description.isEmpty
                      ? 'Nessuno ha ancora raccontato questo spot.'
                      : spot.description,
                  style: Theme.of(sheet).textTheme.bodyMedium,
                ),
                const SizedBox(height: 16),
                Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton(
                    onPressed: () {
                      Navigator.of(sheet).pop();
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => SpotDetailScreen(spot: spot),
                        ),
                      );
                    },
                    child: const Text('Apri la scheda'),
                  ),
                ),
              ],
            ),
          ),
    );
  }

  /// Proporre uno spot richiede un account: la proposta ha un autore, e senza
  /// non c'è nessuno a cui comunicare l'esito della moderazione.
  void _proposeSpot() {
    final signedIn = ref.read(accountRepositoryProvider).isSignedIn;
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder:
            (_) => signedIn ? const ProposeSpotScreen() : const SignInScreen(),
      ),
    );
  }

  void _openFilters() {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (_) => const _FilterSheet(),
    );
  }
}

/// I marker: un pallino con il numero per i gruppi, uno spillo per i singoli.
class _ClusterLayer extends StatelessWidget {
  const _ClusterLayer({
    required this.clusters,
    required this.zoom,
    required this.onTapCluster,
  });

  final List<SpotCluster> clusters;
  final double zoom;
  final void Function(SpotCluster) onTapCluster;

  @override
  Widget build(BuildContext context) {
    return MarkerLayer(
      markers: [
        for (final cluster in clusters)
          Marker(
            point: cluster.center,
            width: cluster.isSingle ? 40 : 46,
            height: cluster.isSingle ? 40 : 46,
            alignment:
                cluster.isSingle ? Alignment.topCenter : Alignment.center,
            child: GestureDetector(
              onTap: () => onTapCluster(cluster),
              child:
                  cluster.isSingle
                      ? _SpotPin(spot: cluster.single)
                      : _ClusterBubble(cluster: cluster),
            ),
          ),
      ],
    );
  }
}

/// Lo spillo di un singolo spot.
///
/// Il colore dice quanto se ne sa: pieno per gli spot raccontati, scarico per i
/// segnaposto importati. Prima erano tutti rossi uguali, ed era il motivo per
/// cui fuori da Roma la mappa sembrava piena e non serviva a niente.
class _SpotPin extends StatelessWidget {
  const _SpotPin({required this.spot});

  final Spot spot;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final (icon, color) = switch (spot.completeness) {
      SpotCompleteness.verificato => (Icons.location_on, scheme.primary),
      SpotCompleteness.arricchito => (Icons.location_on, scheme.secondary),
      SpotCompleteness.daCompletare => (
        Icons.location_on_outlined,
        scheme.outline,
      ),
    };

    return Tooltip(
      message: '${spot.name} · ${spot.completeness.label}',
      child: Icon(
        icon,
        color: color,
        size: 36,
        shadows: const [Shadow(blurRadius: 3, color: Colors.black54)],
      ),
    );
  }
}

class _ClusterBubble extends StatelessWidget {
  const _ClusterBubble({required this.cluster});

  final SpotCluster cluster;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    // Un gruppo che contiene almeno uno spot raccontato si distingue: aiuta a
    // capire dove vale la pena zoomare.
    final color =
        cluster.hasContent
            ? scheme.primaryContainer
            : scheme.surfaceContainerHighest;

    return Container(
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(color: scheme.outlineVariant),
        boxShadow: const [BoxShadow(blurRadius: 4, color: Colors.black38)],
      ),
      alignment: Alignment.center,
      child: Text(
        cluster.count > 99 ? '99+' : '${cluster.count}',
        style: Theme.of(context).textTheme.labelMedium,
      ),
    );
  }
}

class _FilterSheet extends ConsumerWidget {
  const _FilterSheet();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(spotFilterProvider);
    final notifier = ref.read(spotFilterProvider.notifier);

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Filtri', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),

          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: filter.onlyWithContent,
            onChanged: notifier.setOnlyWithContent,
            title: const Text('Solo spot raccontati'),
            subtitle: const Text(
              'Nasconde i segnaposto di cui si conoscono solo le coordinate.',
            ),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: filter.onlyWithWater,
            onChanged: notifier.setOnlyWithWater,
            title: const Text('Con acqua nei pressi'),
            subtitle: const Text(
              'Solo dove risulta una fontanella. Dove non lo sappiamo, lo spot '
              'non compare.',
            ),
          ),

          const SizedBox(height: 8),
          Text('Livello', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              for (final level in const [
                'principiante',
                'intermedio',
                'avanzato',
              ])
                FilterChip(
                  label: Text(level[0].toUpperCase() + level.substring(1)),
                  selected: filter.levels.contains(level),
                  onSelected: (_) => notifier.toggleLevel(level),
                ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Filtrando per livello spariscono anche gli spot non ancora '
            'valutati, che sono la maggior parte.',
            style: Theme.of(context).textTheme.bodySmall,
          ),

          const SizedBox(height: 16),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: filter.isActive ? notifier.clear : null,
              child: const Text('Azzera i filtri'),
            ),
          ),
        ],
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Theme.of(context).colorScheme.surface,
      borderRadius: BorderRadius.circular(20),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: child,
      ),
    );
  }
}
