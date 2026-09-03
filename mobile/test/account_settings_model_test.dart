import 'package:flutter/material.dart' show ThemeMode;
import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/models/account.dart';
import 'package:parkour_notot/models/app_settings.dart';

void main() {
  group('Account.fromJson', () {
    test('parses a full payload', () {
      final account = Account.fromJson({
        'id': 'a1b2c3',
        'email': 'traceur@example.com',
        'display_name': 'Sergio',
        'role': 'instructor',
        'is_email_verified': true,
        'is_guest': false,
        'is_subscribed': true,
        'created_at': '2026-01-01T00:00:00Z',
      });

      expect(account.id, 'a1b2c3');
      expect(account.displayName, 'Sergio');
      expect(account.email, 'traceur@example.com');
      expect(account.isInstructor, isTrue);
      expect(account.isAdmin, isFalse);
      expect(account.isSubscribed, isTrue);
      expect(account.initial, 'S');
    });

    test('defaults the fields a guest payload leaves out', () {
      final account = Account.fromJson({
        'id': 'a1b2c3',
        'email': null,
        'display_name': 'Guest-9f2c',
        'is_guest': true,
      });

      expect(account.email, isNull);
      expect(account.role, 'user');
      expect(account.isGuest, isTrue);
      expect(account.isSubscribed, isFalse);
    });

    test('falls back to a readable name when the payload has none', () {
      final account = Account.fromJson({'id': 'x', 'display_name': '  '});

      expect(account.displayName, 'Traceur');
      expect(account.initial, 'T');
    });
  });

  group('AppSettings', () {
    test('round-trips through JSON', () {
      const settings = AppSettings(
        themeMode: ThemeMode.dark,
        searchRadiusMeters: 10000,
        useDeviceLocation: false,
      );

      expect(AppSettings.fromJson(settings.toJson()), settings);
    });

    test('defaults everything a stored blob is missing', () {
      final settings = AppSettings.fromJson(const {});

      expect(settings.themeMode, ThemeMode.system);
      expect(
        settings.searchRadiusMeters,
        AppSettings.defaultSearchRadiusMeters,
      );
      expect(settings.useDeviceLocation, isTrue);
    });

    test('rejects a radius the API would refuse', () {
      final settings = AppSettings.fromJson(const {'search_radius_m': 999999});

      expect(
        settings.searchRadiusMeters,
        AppSettings.defaultSearchRadiusMeters,
      );
    });

    test('searchRadiusLabel reads in kilometres', () {
      expect(
        const AppSettings(searchRadiusMeters: 10000).searchRadiusLabel,
        '10 km',
      );
    });

    test('the whole-planet radius reads as "everywhere"', () {
      const settings = AppSettings(
        searchRadiusMeters: AppSettings.allSpotsRadiusMeters,
      );
      expect(settings.searchRadiusLabel, 'everywhere');
      expect(AppSettings.radiusChoiceLabel(settings.searchRadiusMeters), 'All');
      expect(AppSettings.radiusChoiceLabel(50000), '50 km');
    });

    test('defaults to reaching every spot', () {
      expect(
        const AppSettings().searchRadiusMeters,
        AppSettings.allSpotsRadiusMeters,
      );
    });
  });
}
