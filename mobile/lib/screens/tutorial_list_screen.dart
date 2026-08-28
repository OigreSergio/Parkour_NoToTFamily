import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/video.dart';
import '../providers.dart';
import '../widgets/difficulty_gauge.dart';
import '../widgets/error_view.dart';
import 'tutorial_detail_screen.dart';

/// Scrollable list of trick tutorials, optionally filtered by category.
///
/// Every row shows the thumbnail, the trick name, a 1–10 difficulty gauge and
/// a "landed" toggle. Locked (premium) tutorials show a lock badge but remain
/// browsable by everyone.
class TutorialListScreen extends ConsumerStatefulWidget {
  const TutorialListScreen({
    super.key,
    required this.title,
    this.trickCategory,
  });

  final String title;

  /// Backend `trick_category` filter; `null` shows every tutorial.
  final String? trickCategory;

  @override
  ConsumerState<TutorialListScreen> createState() => _TutorialListScreenState();
}

class _TutorialListScreenState extends ConsumerState<TutorialListScreen> {
  String _search = '';
  bool _searching = false;

  List<TutorialVideo> _filter(List<TutorialVideo> all) {
    final query = _search.trim().toLowerCase();
    final items =
        all
            .where(
              (v) =>
                  widget.trickCategory == null ||
                  v.trickCategory == widget.trickCategory,
            )
            .where(
              (v) => query.isEmpty || v.title.toLowerCase().contains(query),
            )
            .toList();
    items.sort(
      (a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()),
    );
    return items;
  }

  @override
  Widget build(BuildContext context) {
    final tutorialsAsync = ref.watch(tutorialsProvider);
    final landed = ref.watch(landedTricksProvider);

    return Scaffold(
      appBar: AppBar(
        title:
            _searching
                ? TextField(
                  autofocus: true,
                  decoration: const InputDecoration(
                    hintText: 'Cerca un movimento…',
                    border: InputBorder.none,
                  ),
                  onChanged: (value) => setState(() => _search = value),
                )
                : Text(widget.title),
        actions: [
          IconButton(
            icon: Icon(_searching ? Icons.close : Icons.search),
            onPressed:
                () => setState(() {
                  _searching = !_searching;
                  if (!_searching) _search = '';
                }),
          ),
        ],
      ),
      body: tutorialsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error:
            (error, _) => ErrorView(
              message: 'Could not load tutorials.\n$error',
              onRetry: () => ref.invalidate(tutorialsProvider),
            ),
        data: (all) {
          final tutorials = _filter(all);
          if (tutorials.isEmpty) {
            return const Center(child: Text('Qui non c\'è ancora niente.'));
          }
          return RefreshIndicator(
            onRefresh: () => ref.refresh(tutorialsProvider.future),
            child: ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              itemCount: tutorials.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, i) {
                final video = tutorials[i];
                return _TutorialRow(
                  video: video.copyWith(landed: landed.contains(video.id)),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class _TutorialRow extends ConsumerWidget {
  const _TutorialRow({required this.video});

  final TutorialVideo video;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListTile(
      leading: _Thumbnail(url: video.thumbnailUrl),
      title: Text(video.title),
      subtitle: video.author == null ? null : Text('di ${video.author}'),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          DifficultyGauge(difficulty: video.difficulty),
          IconButton(
            tooltip:
                video.landed
                    ? 'Fatto — tocca per togliere'
                    : 'Segna come fatto',
            icon: Icon(
              Icons.directions_run,
              color: video.landed ? Colors.red : Colors.grey.shade400,
            ),
            onPressed:
                () => ref.read(landedTricksProvider.notifier).toggle(video.id),
          ),
        ],
      ),
      onTap:
          () => Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => TutorialDetailScreen(video: video),
            ),
          ),
    );
  }
}

class _Thumbnail extends StatelessWidget {
  const _Thumbnail({required this.url});

  final String? url;

  @override
  Widget build(BuildContext context) {
    const placeholder = SizedBox(
      width: 56,
      height: 42,
      child: ColoredBox(
        color: Color(0xFFE0E0E0),
        child: Icon(Icons.ondemand_video, color: Colors.grey),
      ),
    );
    if (url == null || url!.isEmpty) return placeholder;
    return ClipRRect(
      borderRadius: BorderRadius.circular(4),
      child: CachedNetworkImage(
        imageUrl: url!,
        width: 56,
        height: 42,
        fit: BoxFit.cover,
        placeholder: (_, __) => placeholder,
        errorWidget: (_, __, ___) => placeholder,
      ),
    );
  }
}
