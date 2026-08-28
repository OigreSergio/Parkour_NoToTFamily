import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/video.dart';

/// Il riquadro da cui si apre un video.
///
/// **Nessuna richiesta verso Google parte da questa pagina.** Non è una
/// sfumatura: la scelta abituale — incorporare un player, o anche solo mostrare
/// la miniatura presa da `i.ytimg.com` — contatta i server di Google appena la
/// schermata compare, prima che l'utente abbia deciso alcunché. Con un servizio
/// che ha fra gli utenti anche dei minori, e che dichiara di non profilare
/// nessuno, quella richiesta è esattamente ciò che non deve esistere.
///
/// Quindi: anteprima disegnata in locale, e al tocco il video si apre **fuori**
/// dall'app, su youtube-nocookie. Il prezzo è la riproduzione in-app, che qui
/// non c'è. È un prezzo accettabile: aprire un link è una navigazione che fa
/// l'utente, non una trasmissione fatta alle sue spalle.
///
/// La prima volta lo si spiega. Poi la scelta resta ricordata — è una
/// preferenza, non un consenso al trattamento, e vive in `SharedPreferences`
/// come storage tecnico.
class VideoOpener extends ConsumerStatefulWidget {
  const VideoOpener({super.key, required this.video});

  final TutorialVideo video;

  @override
  ConsumerState<VideoOpener> createState() => _VideoOpenerState();
}

class _VideoOpenerState extends ConsumerState<VideoOpener> {
  static const String _prefKey = 'pk_video_esterni_ok';

  Future<void> _open() async {
    final url = widget.video.url;
    if (url == null) return;

    final prefs = await SharedPreferences.getInstance();
    var explained = false;
    try {
      explained = prefs.getBool(_prefKey) ?? false;
    } catch (_) {
      // Storage non disponibile (finestra anonima, permessi negati): si
      // rispiega. Meglio ripetersi che aprire senza aver detto niente.
    }

    if (!explained) {
      if (!mounted) return;
      final ok = await showDialog<bool>(
        context: context,
        builder:
            (ctx) => AlertDialog(
              title: const Text('Il video è su YouTube'),
              content: const Text(
                'Si apre fuori da PkFAMILY, sui server di Google, che a quel punto '
                'vedranno la tua visita come qualsiasi altra volta che apri '
                'YouTube.\n\n'
                'Lo teniamo fuori apposta: così finché non tocchi tu, da questa '
                'pagina non parte nessuna richiesta verso Google — nemmeno per '
                'l\'anteprima.',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx, false),
                  child: const Text('Lascia stare'),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(ctx, true),
                  child: const Text('Apri il video'),
                ),
              ],
            ),
      );
      if (ok != true) return;
      try {
        await prefs.setBool(_prefKey, true);
      } catch (_) {
        // Non poterlo ricordare non è un motivo per non aprire.
      }
    }

    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final video = widget.video;

    if (!video.hasVideo) return _ComingSoon(video: video);

    return InkWell(
      onTap: _open,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          // Un fondo disegnato qui, non una miniatura scaricata da Google.
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              theme.colorScheme.surfaceContainerHighest,
              theme.colorScheme.surfaceContainerLow,
            ],
          ),
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            Icon(
              Icons.play_circle_outline,
              size: 64,
              color: theme.colorScheme.primary,
            ),
            Positioned(
              left: 12,
              right: 12,
              bottom: 10,
              child: Text(
                video.author == null
                    ? 'Guarda su YouTube'
                    : 'Guarda su YouTube · ${video.author}',
                textAlign: TextAlign.center,
                style: theme.textTheme.labelSmall,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Una tappa del percorso che non ha ancora un video.
///
/// Non sparisce: titolo, descrizione e nota di sicurezza valgono già da soli, e
/// un percorso dichiaratamente incompleto è più utile di uno che finge di
/// esserlo.
class _ComingSoon extends StatelessWidget {
  const _ComingSoon({required this.video});

  final TutorialVideo video;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      alignment: Alignment.center,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.videocam_off_outlined,
            color: theme.colorScheme.outline,
            size: 32,
          ),
          const SizedBox(height: 8),
          Text(
            'Video in arrivo',
            style: theme.textTheme.labelMedium?.copyWith(
              color: theme.colorScheme.outline,
            ),
          ),
        ],
      ),
    );
  }
}

/// La riga di sicurezza di una tappa.
///
/// Sta sul singolo video e non in un banner generale perché non è la stessa per
/// tutti: quello che serve sapere prima di una rullata non è quello che serve
/// prima di un salto di precisione.
class VideoSafetyNote extends StatelessWidget {
  const VideoSafetyNote({super.key, required this.note});

  final String? note;

  /// L'avvertenza di fondo, per i video che non ne hanno una propria.
  static const String generic =
      'Vai per gradi, scegli una superficie adatta e non superare il tuo '
      'livello. Un video non sostituisce qualcuno che ti guarda.';

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.health_and_safety_outlined,
            size: 18,
            color: theme.colorScheme.outline,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              note?.trim().isNotEmpty == true ? note!.trim() : generic,
              style: theme.textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}
