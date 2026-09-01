import 'package:flutter/material.dart' show ThemeMode;

/// User preferences edited from the settings screen.
///
/// These are client-only: the backend does not store per-user preferences yet,
/// so they live on the device (see `services/settings_store.dart`). Every field
/// is optional on parse and falls back to its default, so a settings blob
/// written by an older build still loads.
class AppSettings {
  const AppSettings({
    this.themeMode = ThemeMode.system,
    this.searchRadiusMeters = defaultSearchRadiusMeters,
    this.useDeviceLocation = true,
  });

  /// Widest radius the API allows (`radius_m` is capped at 50 km server-side).
  static const int defaultSearchRadiusMeters = 50000;

  /// Radii offered in the settings screen, in metres.
  static const List<int> searchRadiusChoices = [5000, 10000, 25000, 50000];

  /// Light / dark / follow the system.
  final ThemeMode themeMode;

  /// Radius passed to `GET /api/v1/spots` when looking for nearby spots.
  final int searchRadiusMeters;

  /// When `false` the map and spot search stay on the fallback centre instead
  /// of asking the device for a GPS fix.
  final bool useDeviceLocation;

  /// Search radius rendered for the UI, e.g. `50 km`.
  String get searchRadiusLabel => '${(searchRadiusMeters / 1000).round()} km';

  AppSettings copyWith({
    ThemeMode? themeMode,
    int? searchRadiusMeters,
    bool? useDeviceLocation,
  }) =>
      AppSettings(
        themeMode: themeMode ?? this.themeMode,
        searchRadiusMeters: searchRadiusMeters ?? this.searchRadiusMeters,
        useDeviceLocation: useDeviceLocation ?? this.useDeviceLocation,
      );

  factory AppSettings.fromJson(Map<String, dynamic> json) {
    final radius = (json['search_radius_m'] as num?)?.toInt();
    return AppSettings(
      themeMode: _themeModeFromName(json['theme_mode'] as String?),
      searchRadiusMeters: radius == null || !searchRadiusChoices.contains(radius)
          ? defaultSearchRadiusMeters
          : radius,
      useDeviceLocation: json['use_device_location'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() => {
        'theme_mode': themeMode.name,
        'search_radius_m': searchRadiusMeters,
        'use_device_location': useDeviceLocation,
      };

  static ThemeMode _themeModeFromName(String? name) {
    for (final mode in ThemeMode.values) {
      if (mode.name == name) return mode;
    }
    return ThemeMode.system;
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AppSettings &&
          other.themeMode == themeMode &&
          other.searchRadiusMeters == searchRadiusMeters &&
          other.useDeviceLocation == useDeviceLocation;

  @override
  int get hashCode =>
      Object.hash(themeMode, searchRadiusMeters, useDeviceLocation);
}
