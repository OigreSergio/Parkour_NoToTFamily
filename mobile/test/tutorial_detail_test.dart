import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/models/video.dart';
import 'package:parkour_notot/screens/tutorial_detail_screen.dart';

TutorialVideo _video({
  String? url,
  bool locked = false,
  String? thumbnailUrl,
}) =>
    TutorialVideo(
      id: 'v1',
      title: 'Kong vault',
      description: 'Spinta delle braccia, passaggio delle gambe.',
      url: url,
      thumbnailUrl: thumbnailUrl,
      category: 'practice',
      level: 'beginner',
      trickCategory: 'vaults',
      difficulty: 4,
      durationSeconds: 485,
      locked: locked,
      createdAt: DateTime(2026, 1, 1),
    );

Future<void> _pump(WidgetTester tester, TutorialVideo video) async {
  await tester.pumpWidget(
    ProviderScope(
      child: MaterialApp(home: TutorialDetailScreen(video: video)),
    ),
  );
  await tester.pump();
}

void main() {
  group('TutorialVideo link handling', () {
    test('a video file is streamed in the app', () {
      final video = _video(url: 'https://videos.example/kong.mp4');
      expect(video.isStreamable, isTrue);
      expect(video.opensExternally, isFalse);
      expect(video.externalHost, isNull);
    });

    test('a YouTube link opens outside the app', () {
      final video = _video(url: 'https://www.youtube.com/watch?v=SYGU697kF0Q');
      expect(video.isStreamable, isFalse);
      expect(video.opensExternally, isTrue);
      expect(video.externalHost, 'youtube.com');
    });

    test('a query string does not hide the file extension', () {
      final video = _video(url: 'https://cdn.example/kong.mp4?token=abc');
      expect(video.isStreamable, isTrue);
    });

    test('a missing url is neither streamable nor external', () {
      final video = _video();
      expect(video.isStreamable, isFalse);
      expect(video.opensExternally, isFalse);
    });
  });

  group('TutorialDetailScreen', () {
    testWidgets('a YouTube tutorial offers to open it on YouTube',
        (tester) async {
      await _pump(
        tester,
        _video(url: 'https://www.youtube.com/watch?v=SYGU697kF0Q'),
      );

      expect(find.text('Watch on youtube.com'), findsOneWidget);
      expect(find.byIcon(Icons.play_circle_fill), findsOneWidget);
      // The in-app player is not even built for a link it cannot stream.
      expect(find.byType(CircularProgressIndicator), findsNothing);
    });

    testWidgets('a locked tutorial still shows the paywall', (tester) async {
      await _pump(tester, _video(url: null, locked: true));

      expect(find.text('Premium tutorial'), findsOneWidget);
      expect(find.textContaining('Watch on'), findsNothing);
    });
  });
}
