import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';
import 'login_screen.dart';
import 'my_spots_screen.dart';

/// Account tab: sign-in prompt when anonymous, account details + own
/// submissions when logged in.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authAsync = ref.watch(authControllerProvider);
    final user = authAsync.valueOrNull;

    if (authAsync.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (user == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.person_outline, size: 64),
              const SizedBox(height: 12),
              const Text(
                'Sign in to suggest new spots and track your submissions.\n'
                'Browsing the map is free for everyone.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(builder: (_) => const LoginScreen()),
                ),
                child: const Text('Sign in / register'),
              ),
            ],
          ),
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        ListTile(
          leading: const CircleAvatar(child: Icon(Icons.person)),
          title: Text(user.displayName),
          subtitle: Text(user.email),
          trailing: user.isAdmin ? const Chip(label: Text('admin')) : null,
        ),
        if (user.isAdmin)
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Text(
              'Spot moderation (verify / reject / add) happens in the web '
              'admin dashboard.',
              style: TextStyle(fontStyle: FontStyle.italic),
            ),
          ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.pending_actions),
          title: const Text('My submissions'),
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute<void>(builder: (_) => const MySpotsScreen()),
          ),
        ),
        ListTile(
          leading: const Icon(Icons.logout),
          title: const Text('Log out'),
          onTap: () => ref.read(authControllerProvider.notifier).logout(),
        ),
      ],
    );
  }
}
