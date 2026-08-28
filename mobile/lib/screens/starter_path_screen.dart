import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/video.dart';
import '../providers.dart';
import '../widgets/video_opener.dart';

/// «Inizia da qui»: sette tappe, nell'ordine in cui ha senso affrontarle.
///
/// L'ordine è la sostanza, non la presentazione. Chi arriva al parkour da
/// internet vede prima i salti e poi, forse, gli atterraggi — ed è il motivo
/// per cui si fa male. Qui si atterra prima di saltare, e si scalda prima di
/// atterrare.
class StarterPathScreen extends ConsumerWidget {
  const StarterPathScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final path = ref.watch(starterPathProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Inizia da qui')),
      body: path.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error:
            (err, _) => Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text('Non riesco a caricare il percorso.\n$err'),
              ),
            ),
        data:
            (stages) =>
                stages.isEmpty
                    ? const _NotSeededYet()
                    : ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: stages.length + 1,
                      itemBuilder:
                          (context, i) =>
                              i == 0
                                  ? const _Intro()
                                  : _Stage(step: i, video: stages[i - 1]),
                    ),
      ),
    );
  }
}

class _Intro extends StatelessWidget {
  const _Intro();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Non serve saper saltare per cominciare.',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Sette tappe, in quest\'ordine. Le prime tre non sembrano parkour '
            'e sono quelle che ti tengono intero: si impara a scendere prima '
            'che a salire.',
            style: theme.textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}

class _Stage extends StatelessWidget {
  const _Stage({required this.step, required this.video});

  final int step;
  final TutorialVideo video;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(radius: 14, child: Text('$step')),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(video.title, style: theme.textTheme.titleMedium),
                ),
              ],
            ),
            const SizedBox(height: 12),

            AspectRatio(aspectRatio: 16 / 9, child: VideoOpener(video: video)),
            const SizedBox(height: 12),

            if (video.description.isNotEmpty) ...[
              Text(video.description, style: theme.textTheme.bodyMedium),
              const SizedBox(height: 12),
            ],

            VideoSafetyNote(note: video.safetyNote),
          ],
        ),
      ),
    );
  }
}

/// Il percorso non è ancora stato caricato sul database.
///
/// Dirlo è meglio di una schermata vuota: chi installa capisce che manca un
/// passo, invece di pensare che la sezione sia rotta.
class _NotSeededYet extends StatelessWidget {
  const _NotSeededYet();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.playlist_add, size: 48),
            const SizedBox(height: 16),
            Text(
              'Il percorso non è ancora stato caricato.',
              style: Theme.of(context).textTheme.titleSmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Si carica con scripts/seed_starter_path.mjs.',
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
