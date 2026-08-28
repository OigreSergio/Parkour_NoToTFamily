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
        'created_at': '2026-07-01T10:00:00Z',
      });

      expect(video.id, 'abc');
      expect(video.title, 'Kong');
      expect(video.trickCategory, 'vaults');
      expect(video.difficulty, 4);
      expect(video.url, isNotNull);
    });

    test('tolerates missing optional fields', () {
      final video = TutorialVideo.fromJson({'id': 'x'});

      expect(video.title, '');
      expect(video.url, isNull);
      expect(video.trickCategory, isNull);
      expect(video.difficulty, 1);
      expect(video.landed, isFalse);
    });

    test('una tappa del percorso porta ordine, nota e autore', () {
      final video = TutorialVideo.fromJson({
        'id': 'y',
        'title': 'Atterrare e rullare',
        'description': 'Prima di imparare a salire, si impara a scendere.',
        'level': 'beginner',
        'category': 'practice',
        'is_starter': true,
        'order_index': 2,
        'stage': 'atterraggio',
        'safety_note': 'Sull\'erba finché la rullata non è pulita.',
        'author': 'Qualcuno',
        'url': 'https://www.youtube-nocookie.com/watch?v=abc',
      });

      expect(video.isStarter, isTrue);
      expect(video.orderIndex, 2);
      expect(video.stage, 'atterraggio');
      expect(video.safetyNote, contains('erba'));
      expect(video.author, 'Qualcuno');
      expect(video.hasVideo, isTrue);
    });

    test('una tappa senza video non è una tappa vuota', () {
      // Titolo, descrizione e nota di sicurezza valgono già da soli: la tappa
      // resta visibile e l'app mostra «video in arrivo». Un percorso
      // dichiaratamente incompleto è più utile di uno che finge di esserlo.
      final video = TutorialVideo.fromJson({
        'id': 'z',
        'title': 'Quadrupedia',
        'description': 'Muoversi a quattro appoggi.',
        'is_starter': true,
        'order_index': 3,
        'url': null,
      });

      expect(video.hasVideo, isFalse);
      expect(video.description, isNotEmpty);
      expect(video.isStarter, isTrue);
    });

    test('una stringa vuota non è un video', () {
      // Il seed scrive null, ma una riga inserita a mano può portare ''.
      final video = TutorialVideo.fromJson({'id': 'w', 'url': ''});
      expect(video.hasVideo, isFalse);
    });

    test('un video normale non fa parte del percorso', () {
      final video = TutorialVideo.fromJson({'id': 'v', 'title': 'Kong'});
      expect(video.isStarter, isFalse);
      expect(video.orderIndex, isNull);
      expect(video.stage, isNull);
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
