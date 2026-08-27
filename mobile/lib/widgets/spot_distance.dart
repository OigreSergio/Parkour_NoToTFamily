import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/spot.dart';
import '../providers.dart';
import '../services/location_service.dart';

/// Quanto dista uno spot, e come arrivarci.
///
/// La distanza si calcola **sul dispositivo**, dopo che l'utente ha chiesto la
/// posizione: le coordinate non lasciano il telefono e non vengono salvate.
/// Nessuna chiamata a un servizio di routing con la posizione dell'utente
/// dentro — le indicazioni si aprono in un'app di mappe, che è una scelta
/// dell'utente, non una trasmissione fatta alle sue spalle.
class SpotDistance extends ConsumerStatefulWidget {
  const SpotDistance({super.key, required this.spot});

  final Spot spot;

  @override
  ConsumerState<SpotDistance> createState() => _SpotDistanceState();
}

class _SpotDistanceState extends ConsumerState<SpotDistance> {
  double? _meters;
  bool _busy = false;
  String? _message;

  Future<void> _measure() async {
    setState(() {
      _busy = true;
      _message = null;
    });

    final result = await ref.refresh(locationRequestProvider.future);
    if (!mounted) return;

    setState(() {
      _busy = false;
      if (result.hasPosition) {
        _meters = LocationService.distanceMeters(
          result.position!,
          widget.spot.location.toLatLng(),
        );
      } else {
        _message = switch (result.status) {
          LocationStatus.serviceOff => 'Localizzazione spenta sul dispositivo.',
          LocationStatus.deniedForever =>
            'Permesso negato: si riattiva dalle impostazioni.',
          LocationStatus.denied => 'Va bene così.',
          _ => 'Non riesco a leggere la posizione.',
        };
      }
    });
  }

  /// Apre le indicazioni in un'app di mappe esterna.
  ///
  /// Il link porta **solo le coordinate dello spot**, non la posizione
  /// dell'utente: il punto di partenza lo mette l'app di destinazione, con il
  /// permesso che l'utente ha già dato a quella.
  Future<void> _directions() async {
    final s = widget.spot.location;
    final uri = Uri.parse(
      'https://www.openstreetmap.org/directions?to=${s.lat},${s.lng}',
    );
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Row(
      children: [
        Expanded(
          child:
              _meters != null
                  ? Text(
                    'A ${_format(_meters!)} da te, in linea d\'aria.',
                    style: theme.textTheme.bodyMedium,
                  )
                  : Text(
                    _message ?? 'Quanto dista da te?',
                    style: theme.textTheme.bodyMedium,
                  ),
        ),
        if (_meters == null)
          TextButton.icon(
            onPressed: _busy ? null : _measure,
            icon: const Icon(Icons.near_me_outlined, size: 18),
            label: Text(_busy ? '…' : 'Calcola'),
          ),
        IconButton(
          onPressed: _directions,
          tooltip: 'Indicazioni',
          icon: const Icon(Icons.directions_outlined),
        ),
      ],
    );
  }

  /// Sotto il chilometro i metri servono; sopra, due cifre bastano e un
  /// «4.271 m» si legge peggio di «4,3 km».
  static String _format(double meters) =>
      meters < 1000
          ? '${meters.round()} m'
          : '${(meters / 1000).toStringAsFixed(1).replaceAll('.', ',')} km';
}
