import 'dart:convert';

import '../models/app_settings.dart';
import 'local_store.dart';

/// Reads and writes [AppSettings] on the device.
///
/// The backend has no per-user preferences endpoint yet, so settings are local
/// to the install. They are stored as a single JSON blob, which keeps adding a
/// preference to a one-line change here.
class SettingsStore {
  const SettingsStore(this._store);

  final LocalStore _store;

  static const String settingsKey = 'app.settings';

  /// The stored preferences, or the defaults when nothing was saved yet (or
  /// the blob cannot be read).
  Future<AppSettings> read() async {
    final raw = await _store.read(settingsKey);
    if (raw == null || raw.isEmpty) return const AppSettings();
    try {
      return AppSettings.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return const AppSettings();
    }
  }

  Future<void> write(AppSettings settings) =>
      _store.write(settingsKey, jsonEncode(settings.toJson()));
}
