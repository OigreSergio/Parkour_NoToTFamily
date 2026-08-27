import 'package:flutter/material.dart';

import '../models/spot.dart';

/// Etichetta dello stato di completezza di uno spot.
///
/// Serve a non far sembrare uguali due cose diverse: uno spot che qualcuno ha
/// visitato e raccontato, e un puntino importato di cui si conoscono solo le
/// coordinate. Sulla mappa erano indistinguibili, ed è il motivo per cui fuori
/// da Roma l'app non serviva a niente.
class SpotCompletenessBadge extends StatelessWidget {
  const SpotCompletenessBadge({super.key, required this.completeness});

  final SpotCompleteness completeness;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final (icon, color) = switch (completeness) {
      SpotCompleteness.verificato => (
        Icons.verified_outlined,
        theme.colorScheme.primary,
      ),
      SpotCompleteness.arricchito => (
        Icons.photo_camera_outlined,
        theme.colorScheme.secondary,
      ),
      SpotCompleteness.daCompletare => (
        Icons.help_outline,
        theme.colorScheme.outline,
      ),
    };

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 4),
        Text(
          completeness.label,
          style: theme.textTheme.labelSmall?.copyWith(color: color),
        ),
      ],
    );
  }
}

/// L'invito a completare uno spot che nessuno ha ancora raccontato.
///
/// Non è un contorno: livello, affollamento e "cosa ci si allena" **non
/// esistono in nessuna API**. L'unica fonte è chi c'è stato davvero, e questo
/// riquadro è il canale che lo raccoglie. È ciò che nel tempo porta gli spot da
/// «da completare» a «verificato».
///
/// Chiede esattamente quello che manca, non un generico "aggiungi
/// informazioni": una domanda precisa riceve molte più risposte.
class ContributeToSpot extends StatelessWidget {
  const ContributeToSpot({super.key, required this.spot, this.onContribute});

  final Spot spot;
  final VoidCallback? onContribute;

  @override
  Widget build(BuildContext context) {
    final missing = spot.missing;
    if (missing.isEmpty) return const SizedBox.shrink();

    final theme = Theme.of(context);
    final list =
        missing.length == 1
            ? missing.first
            : '${missing.take(missing.length - 1).join(', ')} e ${missing.last}';

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Ci sei stato?', style: theme.textTheme.titleSmall),
            const SizedBox(height: 6),
            Text(
              'Di questo spot manca $list. '
              'Nessun database lo sa: lo sa solo chi ci è passato.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            FilledButton.tonal(
              onPressed: onContribute,
              child: const Text('Racconta questo spot'),
            ),
          ],
        ),
      ),
    );
  }
}

/// La riga di credito sotto una foto.
///
/// Non è decorazione: Mapillary pubblica in CC-BY-SA 4.0 e Wikimedia Commons
/// richiede l'attribuzione. Senza questa riga la foto non è pubblicabile, ed è
/// il motivo per cui `spot_photos` ha un vincolo che rifiuta una foto di terzi
/// priva di autore e licenza.
class PhotoCredit extends StatelessWidget {
  const PhotoCredit({super.key, required this.photo});

  final SpotPhoto photo;

  @override
  Widget build(BuildContext context) {
    final credit = photo.credit;
    if (credit == null) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Text(
        credit,
        style: Theme.of(context).textTheme.labelSmall,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}
