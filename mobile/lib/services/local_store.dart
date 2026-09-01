import 'package:flutter/services.dart'
    show MissingPluginException, PlatformException;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Minimal string key/value store used for the session tokens and the user
/// preferences.
///
/// It exists so both can be swapped for an in-memory implementation in tests,
/// where the platform channel behind `flutter_secure_storage` is not available.
abstract class LocalStore {
  Future<String?> read(String key);
  Future<void> write(String key, String value);
  Future<void> delete(String key);
}

/// [LocalStore] backed by `flutter_secure_storage` (Keychain on iOS, encrypted
/// shared preferences on Android).
///
/// Every call degrades to a no-op (reads return `null`) when the platform
/// channel is missing or the keystore rejects the operation: preferences and a
/// cached session are conveniences, never a reason to fail a screen.
class SecureLocalStore implements LocalStore {
  SecureLocalStore([FlutterSecureStorage? storage])
      : _storage = storage ?? FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  @override
  Future<String?> read(String key) async {
    try {
      return await _storage.read(key: key);
    } on MissingPluginException {
      return null;
    } on PlatformException {
      return null;
    }
  }

  @override
  Future<void> write(String key, String value) async {
    try {
      await _storage.write(key: key, value: value);
    } on MissingPluginException {
      // Nothing to persist to — keep the in-memory state authoritative.
    } on PlatformException {
      // Same: a keystore failure must not break the UI.
    }
  }

  @override
  Future<void> delete(String key) async {
    try {
      await _storage.delete(key: key);
    } on MissingPluginException {
      // See [write].
    } on PlatformException {
      // See [write].
    }
  }
}

/// In-memory [LocalStore]. Used by tests, and as a fallback on platforms
/// without secure storage.
class InMemoryLocalStore implements LocalStore {
  InMemoryLocalStore([Map<String, String>? seed])
      : _values = {...?seed};

  final Map<String, String> _values;

  @override
  Future<String?> read(String key) async => _values[key];

  @override
  Future<void> write(String key, String value) async => _values[key] = value;

  @override
  Future<void> delete(String key) async => _values.remove(key);
}
