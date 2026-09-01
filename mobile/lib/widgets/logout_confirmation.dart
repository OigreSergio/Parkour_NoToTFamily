import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';

/// Ask before signing out, then run the log out.
///
/// Logging out revokes the refresh tokens server-side and wipes the ones held
/// on the device, so it is worth a confirmation step. Returns `true` when the
/// user went through with it.
Future<bool> confirmAndLogout(BuildContext context, WidgetRef ref) async {
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('Log out?'),
      content: const Text(
        'You will stay able to browse spots and beginner tutorials. '
        'Sign back in to pick your account up again.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(true),
          child: const Text('Log out'),
        ),
      ],
    ),
  );

  if (confirmed != true) return false;
  if (!context.mounted) return false;

  final messenger = ScaffoldMessenger.of(context);
  final outcome = await ref.read(sessionProvider.notifier).logout();
  messenger.showSnackBar(
    SnackBar(
      content: Text(
        outcome.revokedOnServer
            ? 'Logged out.'
            : 'Logged out on this device. The server could not be reached '
                '(${outcome.error}), so the session is still open there.',
      ),
    ),
  );
  return true;
}
