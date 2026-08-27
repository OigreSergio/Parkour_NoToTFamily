import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/video.dart';
import '../providers.dart';
import '../widgets/difficulty_gauge.dart';
import 'tutorial_detail_screen.dart';

/// Trick-category filter chips: `null` means "any category".
const _categoryLabels = <String?, String>{
  null: 'Any',
  'flips': 'Flips',
  'basics': 'Basics',
  'vaults': 'Vaults',
  'wall_tricks': 'Wall',
  'bar_tricks': 'Bar',
  'ground_tricks': 'Ground',
  'other': 'Other',
};

/// Suggestion generator: "New Trick" draws a fully random trick you have not
/// landed yet. From there you steer the next pick — easier, harder, or a
/// different trick category — or pin a category with the filter chips.
class SuggestionScreen extends ConsumerStatefulWidget {
  const SuggestionScreen({super.key});

  @override
  ConsumerState<SuggestionScreen> createState() => _SuggestionScreenState();
}

class _SuggestionScreenState extends ConsumerState<SuggestionScreen> {
  TutorialVideo? _suggestion;
  String? _category;
  final _random = Random();

  List<TutorialVideo> _notLanded(List<TutorialVideo> all, Set<String> landed) =>
      all.where((v) => !landed.contains(v.id)).toList();

  /// Not-landed tricks matching the pinned category (if any).
  List<TutorialVideo> _pool(List<TutorialVideo> all, Set<String> landed) =>
      _notLanded(all, landed)
          .where((v) => _category == null || v.trickCategory == _category)
          .toList();

  void _pickFrom(List<TutorialVideo> candidates, String emptyMessage) {
    if (candidates.isEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(emptyMessage)));
      return;
    }
    setState(
      () => _suggestion = candidates[_random.nextInt(candidates.length)],
    );
  }

  @override
  Widget build(BuildContext context) {
    final tutorialsAsync = ref.watch(tutorialsProvider);
    final landed = ref.watch(landedTricksProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Suggestion Generator')),
      body: tutorialsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error:
            (error, _) => Center(child: Text('Could not load tricks.\n$error')),
        data: (all) {
          final pool = _pool(all, landed);
          final current = _suggestion;
          return Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                const Text(
                  'Press "New Trick" for a random trick to try. '
                  'Then steer it: easier, harder, or another category.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      for (final entry in _categoryLabels.entries)
                        Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: ChoiceChip(
                            label: Text(entry.value),
                            selected: _category == entry.key,
                            onSelected:
                                (_) => setState(() => _category = entry.key),
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                if (current != null) ...[
                  _SuggestionCard(video: current),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          icon: const Icon(Icons.remove),
                          label: const Text('Easier'),
                          onPressed:
                              () => _pickFrom(
                                pool
                                    .where(
                                      (v) => v.difficulty < current.difficulty,
                                    )
                                    .toList(),
                                'No easier trick to suggest here.',
                              ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          icon: const Icon(Icons.add),
                          label: const Text('Harder'),
                          onPressed:
                              () => _pickFrom(
                                pool
                                    .where(
                                      (v) => v.difficulty > current.difficulty,
                                    )
                                    .toList(),
                                'No harder trick to suggest here.',
                              ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          icon: const Icon(Icons.shuffle),
                          label: const Text('Switch type'),
                          onPressed: () {
                            setState(() => _category = null);
                            _pickFrom(
                              _notLanded(all, landed)
                                  .where(
                                    (v) =>
                                        v.trickCategory !=
                                        current.trickCategory,
                                  )
                                  .toList(),
                              'No tricks left in other categories.',
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ] else
                  const Expanded(
                    child: Center(
                      child: Icon(
                        Icons.lightbulb_outline,
                        size: 64,
                        color: Colors.grey,
                      ),
                    ),
                  ),
                if (current != null) const Spacer(),
                _BigButton(
                  label: 'New Trick',
                  onPressed:
                      pool.isEmpty
                          ? null
                          : () => _pickFrom(pool, 'Nothing left to suggest!'),
                ),
                const SizedBox(height: 16),
                _BigButton(
                  label: 'All Suggestions',
                  onPressed:
                      pool.isEmpty
                          ? null
                          : () {
                            final sorted = [...pool]..sort(
                              (a, b) => a.difficulty.compareTo(b.difficulty),
                            );
                            showModalBottomSheet<void>(
                              context: context,
                              showDragHandle: true,
                              builder:
                                  (_) =>
                                      _AllSuggestionsSheet(suggestions: sorted),
                            );
                          },
                ),
                if (pool.isEmpty) ...[
                  const SizedBox(height: 12),
                  const Text('You landed everything here — nice!'),
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
        subtitle: Text(
          video.locked ? 'Premium — subscribe to watch' : video.level,
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap:
            () => Navigator.of(context).push(
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
