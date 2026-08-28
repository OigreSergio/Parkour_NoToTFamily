import 'package:flutter/material.dart';

import 'starter_path_screen.dart';
import 'suggestion_screen.dart';
import 'tutorial_list_screen.dart';

/// A tile of the Tutorials grid.
class _Category {
  const _Category(this.label, this.trickCategory, this.color, this.icon);

  final String label;

  /// Backend `trick_category` value; `null` means "All Tricks" (no filter).
  final String? trickCategory;

  final Color color;
  final IconData icon;
}

const _categories = <_Category>[
  _Category('Flips', 'flips', Color(0xFF34A853), Icons.flip_camera_android),
  _Category('Basics', 'basics', Color(0xFFA6408F), Icons.directions_walk),
  _Category('Vaults', 'vaults', Color(0xFF2A6AA8), Icons.call_made),
  _Category('Wall Tricks', 'wall_tricks', Color(0xFFF5C231), Icons.stairs),
  _Category(
    'Bar Tricks',
    'bar_tricks',
    Color(0xFFF0913A),
    Icons.fitness_center,
  ),
  _Category('Other Tricks', 'other', Color(0xFF7B2FBE), Icons.auto_awesome),
  _Category(
    'Ground Tricks',
    'ground_tricks',
    Color(0xFFE23B3B),
    Icons.sports_gymnastics,
  ),
  _Category('All Tricks', null, Color(0xFF1FA88C), Icons.grid_view),
];

/// La sezione video.
///
/// In cima il percorso «Inizia da qui»: chi apre questa schermata senza aver
/// mai fatto parkour non sa da quale categoria cominciare, e una griglia di
/// otto riquadri non glielo dice. Sotto, le categorie per chi sa già cosa
/// cerca.
///
/// Tutto è aperto: nessun account, nessuna email, nessun video bloccato.
class TutorialsScreen extends StatelessWidget {
  const TutorialsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
          child: SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              icon: const Icon(Icons.school_outlined),
              label: const Text('Inizia da qui — non hai mai fatto parkour?'),
              onPressed:
                  () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const StarterPathScreen(),
                    ),
                  ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.lightbulb_outline),
                  label: const Text('Suggestions'),
                  onPressed:
                      () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => const SuggestionScreen(),
                        ),
                      ),
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: GridView.count(
            padding: const EdgeInsets.all(12),
            crossAxisCount: 2,
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.6,
            children: [for (final c in _categories) _CategoryTile(category: c)],
          ),
        ),
      ],
    );
  }
}

class _CategoryTile extends StatelessWidget {
  const _CategoryTile({required this.category});

  final _Category category;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: category.color,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap:
            () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder:
                    (_) => TutorialListScreen(
                      title: category.label,
                      trickCategory: category.trickCategory,
                    ),
              ),
            ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(category.icon, size: 40, color: Colors.white),
            const SizedBox(height: 8),
            Text(
              category.label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
