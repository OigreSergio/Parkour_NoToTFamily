import '../models/risk_notice.dart';
import '../services/api_client.dart';

/// Reads the risk notices from the backend.
///
/// The endpoint is public on purpose: you have to be able to read what you
/// would be agreeing to before you have an account.
class LegalRepository {
  LegalRepository(this._api);

  final ApiClient _api;

  List<RiskNotice>? _cache;

  Future<List<RiskNotice>> fetchNotices() async {
    final cached = _cache;
    if (cached != null) return cached;
    final data = await _api.getJson('/api/v1/legal/documents') as List<dynamic>;
    final notices = data
        .map((e) => RiskNotice.fromJson(e as Map<String, dynamic>))
        .toList(growable: false);
    _cache = notices;
    return notices;
  }

  /// The notice with [id], or [RiskNotice.offline] if it cannot be loaded.
  Future<RiskNotice> notice(String id) async {
    try {
      final notices = await fetchNotices();
      return notices.firstWhere((n) => n.id == id);
    } catch (_) {
      return RiskNotice.offline;
    }
  }
}
