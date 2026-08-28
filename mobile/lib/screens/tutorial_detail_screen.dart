import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';

import '../models/video.dart';
import '../widgets/video_opener.dart';
import '../providers.dart';
import '../widgets/difficulty_gauge.dart';

/// Tutorial detail: video player (or premium paywall), difficulty, level and
/// description.
///
/// Beginner tutorials play for everyone — anonymous visitors and guests who
/// signed in without an email included. When the backend marks the video as
/// `locked`, the player is replaced with a subscription prompt.
class TutorialDetailScreen extends ConsumerWidget {
  const TutorialDetailScreen({super.key, required this.video});

  final TutorialVideo video;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final landed = ref.watch(landedTricksProvider).contains(video.id);

    return Scaffold(
      appBar: AppBar(title: Text(video.title)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          AspectRatio(aspectRatio: 16 / 9, child: VideoOpener(video: video)),
          const SizedBox(height: 16),
          Row(
            children: [
              DifficultyGauge(difficulty: video.difficulty, size: 40),
              const SizedBox(width: 12),
              Chip(
                visualDensity: VisualDensity.compact,
                label: Text(video.level),
              ),
              const Spacer(),
              IconButton(
                tooltip: landed ? 'Landed! Tap to unset' : 'Mark as landed',
                icon: Icon(
                  Icons.directions_run,
                  size: 28,
                  color: landed ? Colors.red : Colors.grey.shade400,
                ),
                onPressed:
                    () => ref
                        .read(landedTricksProvider.notifier)
                        .toggle(video.id),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            video.description.isEmpty
                ? 'No description yet.'
                : video.description,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }
}

/// Shown instead of the player when the tutorial requires a subscription.
class _TutorialPlayer extends StatefulWidget {
  const _TutorialPlayer({required this.url});

  final String url;

  @override
  State<_TutorialPlayer> createState() => _TutorialPlayerState();
}

class _TutorialPlayerState extends State<_TutorialPlayer> {
  late final VideoPlayerController _controller;
  bool _ready = false;
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _controller = VideoPlayerController.networkUrl(Uri.parse(widget.url));
    _controller
        .initialize()
        .then((_) {
          if (mounted) setState(() => _ready = true);
        })
        .catchError((Object _) {
          if (mounted) setState(() => _failed = true);
        });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_failed) {
      return const ColoredBox(
        color: Colors.black12,
        child: Center(child: Text('Non riesco a caricare questo video.')),
      );
    }
    if (!_ready) {
      return const ColoredBox(
        color: Colors.black12,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    return GestureDetector(
      onTap:
          () => setState(() {
            if (_controller.value.isPlaying) {
              _controller.pause();
            } else {
              _controller.play();
            }
          }),
      child: Stack(
        alignment: Alignment.center,
        children: [
          VideoPlayer(_controller),
          if (!_controller.value.isPlaying)
            const Icon(Icons.play_circle, size: 64, color: Colors.white70),
        ],
      ),
    );
  }
}
