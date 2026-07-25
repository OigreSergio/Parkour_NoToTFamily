import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/models/video.dart';

void main() {
  group('TutorialVideo.fromJson', () {
    test('parses a full payload', () {
      final video = TutorialVideo.fromJson({
        'id': 'abc',
        'title': 'Kong',
        'description': 'Dive over the obstacle.',
        'url': 'https://videos.example/kong.mp4',
        'thumbnail_url': 'https://videos.example/kong.jpg',
        'category': 'practice',
        'level': 'beginner',
        'trick_category': 'vaults',
        'difficulty': 4,
        'duration_seconds': 90,
        'is_premium': false,
        'locked': false,
        'created_at': '2026-07-01T10:00:00Z',
      });

      expect(video.id, 'abc');
      expect(video.title, 'Kong');
      expect(video.trickCategory, 'vaults');
      expect(video.difficulty, 4);
      expect(video.locked, isFalse);
      expect(video.url, isNotNull);
    });

    test('tolerates missing optional fields', () {
      final video = TutorialVideo.fromJson({'id': 'x'});

      expect(video.title, '');
      expect(video.url, isNull);
      expect(video.trickCategory, isNull);
      expect(video.difficulty, 1);
      expect(video.isPremium, isFalse);
      expect(video.locked, isFalse);
      expect(video.landed, isFalse);
    });

    test('locked premium video has no url and keeps metadata', () {
      final video = TutorialVideo.fromJson({
        'id': 'y',
        'title': 'Double Kong',
        'level': 'advanced',
        'is_premium': true,
        'locked': true,
        'url': null,
        'difficulty': 8,
      });

      expect(video.locked, isTrue);
      expect(video.isPremium, isTrue);
      expect(video.url, isNull);
      expect(video.title, 'Double Kong');
    });
  });

  test('toggleLanded flips the landed flag only', () {
    final video = TutorialVideo.fromJson({'id': 'z', 'difficulty': 5});
    final landed = video.toggleLanded();

    expect(landed.landed, isTrue);
    expect(landed.toggleLanded().landed, isFalse);
    expect(landed.difficulty, 5);
    expect(landed.id, 'z');
  });
}
