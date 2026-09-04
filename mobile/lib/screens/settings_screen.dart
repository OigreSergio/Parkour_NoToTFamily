import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/account.dart';
import '../models/app_settings.dart';
import '../providers.dart';
import 'sign_in_screen.dart';
import '../services/api_client.dart';
import '../widgets/logout_confirmation.dart';

/// Everything a member can manage about the app: the account behind the
/// session, how the app looks, and how spots are searched for.
///
/// Preferences are stored on the device — the backend has no per-user settings
/// endpoint yet — and take effect immediately: the theme switches as it is
/// picked, and the spot search re-runs with the new radius.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider);
    final controller = ref.read(settingsProvider.notifier);
    final session = ref.watch(sessionProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        children: [
          const _SectionHeader('Account'),
          _AccountTile(account: session.account, busy: session.isBusy),
          if (session.isSignedIn)
            ListTile(
              leading: Icon(
                Icons.logout,
                color: Theme.of(context).colorScheme.error,
              ),
              title: Text(
                'Log out',
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
              subtitle: const Text("Revokes this device's session"),
              onTap: session.isBusy
                  ? null
                  : () => confirmAndLogout(context, ref),
            )
          else
            ListTile(
              leading: const Icon(Icons.login),
              title: const Text('Sign in'),
              subtitle: const Text('With your email, or as a guest'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(builder: (_) => const SignInScreen()),
              ),
            ),

          const Divider(),
          const _SectionHeader('Appearance'),
          ListTile(
            leading: Icon(_themeModeIcon(settings.themeMode)),
            title: const Text('Theme'),
            subtitle: Text(_themeModeLabel(settings.themeMode)),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: SegmentedButton<ThemeMode>(
              segments: [
                for (final mode in ThemeMode.values)
                  ButtonSegment<ThemeMode>(
                    value: mode,
                    icon: Icon(_themeModeIcon(mode)),
                    label: Text(_themeModeShortLabel(mode)),
                  ),
              ],
              selected: {settings.themeMode},
              showSelectedIcon: false,
              onSelectionChanged: (selection) =>
                  controller.setThemeMode(selection.first),
            ),
          ),

          const Divider(),
          const _SectionHeader('Spot search'),
          SwitchListTile(
            value: settings.useDeviceLocation,
            onChanged: controller.setUseDeviceLocation,
            secondary: const Icon(Icons.my_location),
            title: const Text('Use my location'),
            subtitle: Text(
              settings.useDeviceLocation
                  ? 'Spots are searched around your GPS position'
                  : 'Spots are searched around the default centre (Rome)',
            ),
          ),
          ListTile(
            leading: const Icon(Icons.radar),
            title: const Text('Search radius'),
            subtitle: Text(
              settings.searchRadiusMeters == AppSettings.allSpotsRadiusMeters
                  ? 'Every spot, wherever it is'
                  : 'Spots within ${settings.searchRadiusLabel}',
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: SegmentedButton<int>(
              segments: [
                for (final radius in AppSettings.searchRadiusChoices)
                  ButtonSegment<int>(
                    value: radius,
                    label: Text(AppSettings.radiusChoiceLabel(radius)),
                  ),
              ],
              selected: {settings.searchRadiusMeters},
              showSelectedIcon: false,
              onSelectionChanged: (selection) =>
                  controller.setSearchRadiusMeters(selection.first),
            ),
          ),

          const Divider(),
          const _SectionHeader('About'),
          const ListTile(
            leading: Icon(Icons.dns_outlined),
            title: Text('Backend'),
            subtitle: Text(ApiClient.defaultBaseUrl),
          ),
          ListTile(
            leading: const Icon(Icons.restore),
            title: const Text('Reset preferences'),
            subtitle: const Text('Back to the default settings'),
            onTap: () async {
              final messenger = ScaffoldMessenger.of(context);
              await controller.reset();
              messenger.showSnackBar(
                const SnackBar(content: Text('Preferences reset.')),
              );
            },
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  static String _themeModeLabel(ThemeMode mode) => switch (mode) {
        ThemeMode.system => 'Follows the system setting',
        ThemeMode.light => 'Always light',
        ThemeMode.dark => 'Always dark',
      };

  static String _themeModeShortLabel(ThemeMode mode) => switch (mode) {
        ThemeMode.system => 'System',
        ThemeMode.light => 'Light',
        ThemeMode.dark => 'Dark',
      };

  static IconData _themeModeIcon(ThemeMode mode) => switch (mode) {
        ThemeMode.system => Icons.brightness_auto_outlined,
        ThemeMode.light => Icons.light_mode_outlined,
        ThemeMode.dark => Icons.dark_mode_outlined,
      };
}

/// Small caps-ish section title between two groups of settings.
class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Theme.of(context).colorScheme.primary,
            ),
      ),
    );
  }
}

/// Who the session belongs to, mirroring the header of the account menu.
class _AccountTile extends StatelessWidget {
  const _AccountTile({required this.account, required this.busy});

  final Account? account;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final account = this.account;

    return ListTile(
      leading: CircleAvatar(
        backgroundColor: scheme.primaryContainer,
        child: busy
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : account == null
                ? Icon(Icons.person_outline, color: scheme.onPrimaryContainer)
                : Text(
                    account.initial,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: scheme.onPrimaryContainer,
                    ),
                  ),
      ),
      title: Text(account?.displayName ?? 'Not signed in'),
      subtitle: Text(
        account == null
            ? 'Browsing as a visitor'
            : account.email ??
                (account.isGuest ? 'Guest account — no email' : 'Signed in'),
      ),
    );
  }
}
