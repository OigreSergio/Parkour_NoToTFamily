import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:video_player/video_player.dart';

import '../models/video.dart';
import '../providers.dart';
import '../widgets/difficulty_gauge.dart';

/// Tutorial detail: video player (or premium paywall), difficulty, level and
/// description.
///
/// Beginner tutorials play for everyone — anonymous visitors and guests who
/// signed in without an email included. When the backend marks the video as
/// `locked`, the player is replaced with a subscription prompt.
///
/// The catalog is curated from public channels, so most tutorials are YouTube
/// links rather than video files: those cannot be streamed by `video_player`
/// and open in the YouTube app (or the browser) from the thumbnail.
class TutorialDetailScreen extends ConsumerWidget {
  const TutorialDetailScreen({super.key, required this.video});

  final TutorialVideo video;

  /// Paywall, external-link banner or in-app player, in that order.
  Widget _media() {
    if (video.locked || video.url == null) {
      return _LockedBanner(thumbnailUrl: video.thumbnailUrl);
    }
    if (video.opensExternally) return _ExternalVideoBanner(video: video);
    return _TutorialPlayer(url: video.url!);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final landed = ref.watch(landedTricksProvider).contains(video.id);

    return Scaffold(
      appBar: AppBar(title: Text(video.title)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          AspectRatio(aspectRatio: 16 / 9, child: _media()),
          const SizedBox(height: 16),
          Row(
            children: [
              DifficultyGauge(difficulty: video.difficulty, size: 40),
              const SizedBox(width: 12),
              Chip(
                visualDensity: VisualDensity.compact,
                label: Text(video.level),
                avatar: video.isPremium
                    ? const Icon(Icons.workspace_premium, size: 16)
                    : const Icon(Icons.lock_open, size: 16),
              ),
              const Spacer(),
              IconButton(
                tooltip: landed ? 'Landed! Tap to unset' : 'Mark as landed',
                icon: Icon(
                  Icons.directions_run,
                  size: 28,
                  color: landed ? Colors.red : Colors.grey.shade400,
                ),
                onPressed: () =>
                    ref.read(landedTricksProvider.notifier).toggle(video.id),
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

/// Shown for a tutorial hosted on a video platform: the thumbnail with a play
/// button that hands the video over to YouTube (or the browser).
class _ExternalVideoBanner extends StatelessWidget {
  const _ExternalVideoBanner({required this.video});

  final TutorialVideo video;

  Future<void> _open(BuildContext context) async {
    final messenger = ScaffoldMessenger.of(context);
    final uri = Uri.parse(video.url!);
    final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!opened) {
      messenger.showSnackBar(
        SnackBar(content: Text('Could not open $uri')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final thumbnailUrl = video.thumbnailUrl;
    final host = video.externalHost ?? 'the web';

    return GestureDetector(
      onTap: () => _open(context),
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (thumbnailUrl != null && thumbnailUrl.isNotEmpty)
            CachedNetworkImage(imageUrl: thumbnailUrl, fit: BoxFit.cover)
          else
            const ColoredBox(color: Colors.black12),
          ColoredBox(color: Colors.black.withValues(alpha: 0.35)),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.play_circle_fill, size: 64, color: Colors.white),
              const SizedBox(height: 8),
              FilledButton.icon(
                onPressed: () => _open(context),
                icon: const Icon(Icons.open_in_new, size: 18),
                label: Text('Watch on $host'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Shown instead of the player when the tutorial requires a subscription.
class _LockedBanner extends StatelessWidget {
  const _LockedBanner({required this.thumbnailUrl});

  final String? thumbnailUrl;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        if (thumbnailUrl != null && thumbnailUrl!.isNotEmpty)
          CachedNetworkImage(imageUrl: thumbnailUrl!, fit: BoxFit.cover),
        ColoredBox(color: Colors.black.withValues(alpha: 0.6)),
        Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.lock, color: Colors.white, size: 42),
            const SizedBox(height: 8),
            const Text(
              'Premium tutorial',
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Subscribe to unlock intermediate and\nadvanced technique videos.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Subscriptions are coming soon!'),
                ),
              ),
              child: const Text('Subscribe'),
            ),
          ],
        ),
      ],
    );
  }
}

/// Minimal network video player with tap-to-toggle play/pause.
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
    _controller.initialize().then((_) {
      if (mounted) setState(() => _ready = true);
    }).catchError((Object _) {
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
        child: Center(child: Text('Could not load this video.')),
      );
    }
    if (!_ready) {
      return const ColoredBox(
        color: Colors.black12,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    return GestureDetector(
      onTap: () => setState(() {
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
