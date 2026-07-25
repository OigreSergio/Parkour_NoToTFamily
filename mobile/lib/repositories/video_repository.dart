import '../models/video.dart';
import '../services/api_client.dart';

/// Read-side gateway for `GET /api/v1/videos`.
class VideoRepository {
  const VideoRepository(this._api);

  final ApiClient _api;

  /// Fetch tutorial videos, optionally filtered by trick category
  /// (`flips`, `basics`, `vaults`, `wall_tricks`, `bar_tricks`,
  /// `ground_tricks`, `other`).
  Future<List<TutorialVideo>> fetchTutorials({String? trickCategory}) async {
    final json = await _api.getJson('/api/v1/videos', query: {
      if (trickCategory != null) 'trick_category': trickCategory,
      'limit': 200,
    });
    return (json as List<dynamic>)
        .map((e) => TutorialVideo.fromJson(e as Map<String, dynamic>))
        .toList(growable: false);
  }
}
