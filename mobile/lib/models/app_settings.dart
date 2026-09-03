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

  /// Radius that reaches every spot on the planet — the map's default, so the
  /// community list shows up wherever you open the app.
  static const int allSpotsRadiusMeters = 20000000;

  /// Radius the app starts with.
  static const int defaultSearchRadiusMeters = allSpotsRadiusMeters;

  /// Radii offered in the settings screen, in metres.
  static const List<int> searchRadiusChoices = [
    5000,
    10000,
    50000,
    allSpotsRadiusMeters,
  ];

  /// Most spots the API returns in one call.
  static const int spotsLimit = 2000;

  /// Light / dark / follow the system.
  final ThemeMode themeMode;

  /// Radius passed to `GET /api/v1/spots` when looking for nearby spots.
  final int searchRadiusMeters;

  /// When `false` the map and spot search stay on the fallback centre instead
  /// of asking the device for a GPS fix.
  final bool useDeviceLocation;

  /// Search radius rendered for the UI, e.g. `50 km` or `everywhere`.
  String get searchRadiusLabel => searchRadiusMeters == allSpotsRadiusMeters
      ? 'everywhere'
      : '${(searchRadiusMeters / 1000).round()} km';

  /// Short label for the radius picker.
  static String radiusChoiceLabel(int radiusMeters) =>
      radiusMeters == allSpotsRadiusMeters
          ? 'All'
          : '${(radiusMeters / 1000).round()} km';

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
