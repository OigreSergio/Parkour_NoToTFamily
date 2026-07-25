import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/video.dart';
import '../providers.dart';
import '../widgets/difficulty_gauge.dart';
import 'tutorial_detail_screen.dart';

/// Suggestion generator, mirroring the reference design: press "New Trick"
/// for a single suggestion based on what you have landed already, or
/// "All Suggestions" for the full list.
///
/// Suggestions are tricks you have NOT landed yet, close to your current
/// level: at most 2 difficulty points above the hardest trick you landed.
class SuggestionScreen extends ConsumerStatefulWidget {
  const SuggestionScreen({super.key});

  @override
  ConsumerState<SuggestionScreen> createState() => _SuggestionScreenState();
}

class _SuggestionScreenState extends ConsumerState<SuggestionScreen> {
  TutorialVideo? _suggestion;
  final _random = Random();

  List<TutorialVideo> _suggestions(
    List<TutorialVideo> all,
    Set<String> landed,
  ) {
    final landedMax = all
        .where((v) => landed.contains(v.id))
        .map((v) => v.difficulty)
        .fold(0, max);
    // Newcomers get the easiest tricks; others get up to +2 difficulty.
    final ceiling = landedMax == 0 ? 3 : landedMax + 2;
    final candidates = all
        .where((v) => !landed.contains(v.id) && v.difficulty <= ceiling)
        .toList();
    candidates.sort((a, b) => a.difficulty.compareTo(b.difficulty));
    return candidates;
  }

  @override
  Widget build(BuildContext context) {
    final tutorialsAsync = ref.watch(tutorialsProvider);
    final landed = ref.watch(landedTricksProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Suggestion Generator')),
      body: tutorialsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('Could not load tricks.\n$error')),
        data: (all) {
          final suggestions = _suggestions(all, landed);
          return Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                const Text(
                  'Press the button to get suggestions on tricks to try, '
                  'based off of what you have landed already! Tap a '
                  'suggestion to open its tutorial.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                if (_suggestion != null)
                  _SuggestionCard(video: _suggestion!)
                else
                  const Expanded(
                    child: Center(
                      child: Icon(Icons.lightbulb_outline,
                          size: 64, color: Colors.grey),
                    ),
                  ),
                if (_suggestion != null) const Spacer(),
                _BigButton(
                  label: 'New Trick',
                  onPressed: suggestions.isEmpty
                      ? null
                      : () => setState(() => _suggestion =
                          suggestions[_random.nextInt(suggestions.length)]),
                ),
                const SizedBox(height: 16),
                _BigButton(
                  label: 'All Suggestions',
                  onPressed: suggestions.isEmpty
                      ? null
                      : () => showModalBottomSheet<void>(
                            context: context,
                            showDragHandle: true,
                            builder: (_) =>
                                _AllSuggestionsSheet(suggestions: suggestions),
                          ),
                ),
                if (suggestions.isEmpty) ...[
                  const SizedBox(height: 12),
                  const Text('You landed everything at your level — nice!'),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SuggestionCard extends StatelessWidget {
  const _SuggestionCard({required this.video});

  final TutorialVideo video;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: DifficultyGauge(difficulty: video.difficulty),
        title: Text(video.title),
        subtitle: Text(video.locked ? 'Premium — subscribe to watch' : video.level),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => TutorialDetailScreen(video: video),
          ),
        ),
      ),
    );
  }
}

class _AllSuggestionsSheet extends StatelessWidget {
  const _AllSuggestionsSheet({required this.suggestions});

  final List<TutorialVideo> suggestions;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemCount: suggestions.length,
      itemBuilder: (_, i) => _SuggestionCard(video: suggestions[i]),
    );
  }
}

class _BigButton extends StatelessWidget {
  const _BigButton({required this.label, required this.onPressed});

  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 64,
      child: FilledButton(
        onPressed: onPressed,
        child: Text(label, style: const TextStyle(fontSize: 24)),
      ),
    );
  }
}
