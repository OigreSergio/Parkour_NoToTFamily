import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/account.dart';
import '../providers.dart';
import '../screens/settings_screen.dart';
import '../screens/sign_in_screen.dart';
import 'logout_confirmation.dart';

/// App bar entry point to the account menu: the avatar of the signed-in
/// member, or a generic person icon when nobody is signed in.
class AccountMenuButton extends ConsumerWidget {
  const AccountMenuButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionProvider);
    final account = session.account;

    return IconButton(
      tooltip: 'Account menu',
      onPressed: () => showAccountMenu(context),
      icon: account == null
          ? const Icon(Icons.account_circle_outlined)
          : CircleAvatar(
              radius: 14,
              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
              child: Text(
                account.initial,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Theme.of(context).colorScheme.onPrimaryContainer,
                ),
              ),
            ),
    );
  }
}

/// Open the account menu as a bottom sheet.
///
/// It is the single place from which a member reaches the settings or logs
/// out.
Future<void> showAccountMenu(BuildContext context) => showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      useSafeArea: true,
      builder: (_) => const AccountMenu(),
    );

/// Contents of the account menu: who is signed in, then the actions —
/// **Settings** and **Log out** (or **Sign in as a guest** when signed out).
class AccountMenu extends ConsumerWidget {
  const AccountMenu({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionProvider);

    return SafeArea(
      top: false,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AccountHeader(account: session.account, busy: session.isBusy),
          const Divider(height: 1),
          ListTile(
            leading: const Icon(Icons.settings_outlined),
            title: const Text('Settings'),
            subtitle: const Text('Appearance, spot search, location'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // Close the sheet first, then open settings on the navigator
              // that hosted it — `context` is gone once the sheet is popped.
              final navigator = Navigator.of(context);
              navigator.pop();
              navigator.push(
                MaterialPageRoute<void>(
                  builder: (_) => const SettingsScreen(),
                ),
              );
            },
          ),
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
              subtitle: const Text('Sign out on this device'),
              onTap: session.isBusy
                  ? null
                  : () async {
                      final navigator = Navigator.of(context);
                      final loggedOut = await confirmAndLogout(context, ref);
                      if (loggedOut && navigator.canPop()) navigator.pop();
                    },
            )
          else
            ListTile(
              leading: const Icon(Icons.login),
              title: const Text('Sign in'),
              subtitle: const Text('With your email, or as a guest'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                final navigator = Navigator.of(context);
                navigator.pop();
                navigator.push(
                  MaterialPageRoute<void>(
                    builder: (_) => const SignInScreen(),
                  ),
                );
              },
            ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

/// Avatar + display name + account status at the top of the menu.
class AccountHeader extends StatelessWidget {
  const AccountHeader({super.key, required this.account, this.busy = false});

  final Account? account;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final account = this.account;

    return ListTile(
      contentPadding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      leading: CircleAvatar(
        radius: 22,
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
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: scheme.onPrimaryContainer,
                    ),
                  ),
      ),
      title: Text(
        account?.displayName ?? 'Not signed in',
        style: Theme.of(context).textTheme.titleMedium,
      ),
      subtitle: Text(_subtitle(account)),
      trailing: account == null ? null : _AccountBadges(account: account),
    );
  }

  static String _subtitle(Account? account) {
    if (account == null) return 'Browsing as a visitor';
    if (account.email != null) return account.email!;
    return account.isGuest ? 'Guest account — no email' : 'Signed in';
  }
}

/// Small chips for the qualification and the subscription.
class _AccountBadges extends StatelessWidget {
  const _AccountBadges({required this.account});

  final Account account;

  @override
  Widget build(BuildContext context) {
    final labels = <String>[
      if (account.isInstructor) 'Instructor',
      if (account.isAdmin) 'Admin',
      if (account.isSubscribed) 'Premium',
    ];
    if (labels.isEmpty) return const SizedBox.shrink();

    return Wrap(
      spacing: 4,
      children: [
        for (final label in labels)
          Chip(
            label: Text(label),
            visualDensity: VisualDensity.compact,
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
      ],
    );
  }
}
