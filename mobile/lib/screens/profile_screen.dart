import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/profile.dart';
import '../providers.dart';
import '../widgets/moderation_notices.dart';
import 'legal_screen.dart';
import 'auth/sign_in_screen.dart';

/// Profilo, impostazioni e diritti dell'interessato.
///
/// Export e cancellazione sono **pulsanti**, non promesse in una pagina legale:
/// gli artt. 15, 17 e 20 GDPR danno diritti che devono essere esercitabili, e
/// un modulo da compilare via email è un attrito che li svuota.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(currentProfileProvider);

    return profile.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text('$err')),
      data:
          (profile) =>
              profile == null
                  ? const _SignedOut()
                  : _ProfileBody(profile: profile),
    );
  }
}

class _SignedOut extends StatelessWidget {
  const _SignedOut();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.person_outline, size: 48),
            const SizedBox(height: 16),
            Text(
              'Mappa e video funzionano anche senza account.\n'
              'Serve per proporre spot, commentare e usare la chat.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed:
                  () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const SignInScreen(),
                    ),
                  ),
              child: const Text('Entra o registrati'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileBody extends ConsumerStatefulWidget {
  const _ProfileBody({required this.profile});

  final Profile profile;

  @override
  ConsumerState<_ProfileBody> createState() => _ProfileBodyState();
}

class _ProfileBodyState extends ConsumerState<_ProfileBody> {
  bool _busy = false;

  Future<void> _guard(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
      ref.invalidate(currentProfileProvider);
    } catch (err) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$err')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _exportData() async {
    await _guard(() async {
      final data = await ref.read(accountRepositoryProvider).exportMyData();
      final json = const JsonEncoder.withIndent('  ').convert(data);
      await Clipboard.setData(ClipboardData(text: json));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('I tuoi dati sono negli appunti, in formato JSON.'),
          ),
        );
      }
    });
  }

  Future<void> _confirmDeletion() async {
    final ok = await showDialog<bool>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Eliminare l\'account?'),
            content: const Text(
              'Hai 30 giorni per cambiare idea: fino ad allora non viene cancellato '
              'niente.\n\n'
              'Alla scadenza spariscono profilo e contenuti personali. I messaggi '
              'che hai già mandato restano nelle conversazioni degli altri, ma '
              'senza il tuo nome: cancellarli del tutto toglierebbe agli altri '
              'partecipanti metà della loro conversazione.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Annulla'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Elimina'),
              ),
            ],
          ),
    );

    if (ok == true) {
      await _guard(() => ref.read(accountRepositoryProvider).requestDeletion());
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.profile;
    final theme = Theme.of(context);

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const ModerationNotices(),
        ListTile(
          leading: const CircleAvatar(child: Icon(Icons.person)),
          title: Text(p.username.isEmpty ? 'Senza nome' : p.username),
          subtitle: Text(switch (p.role) {
            'admin' => 'Amministratore',
            'instructor' => 'Istruttore riconosciuto',
            _ => 'Membro',
          }),
        ),

        if (p.isPendingDeletion) ...[
          const SizedBox(height: 8),
          Card(
            color: theme.colorScheme.errorContainer,
            child: ListTile(
              title: const Text('Eliminazione in corso'),
              subtitle: const Text(
                'Hai 30 giorni dalla richiesta per annullarla.',
              ),
              trailing: TextButton(
                onPressed:
                    _busy
                        ? null
                        : () => _guard(
                          () =>
                              ref
                                  .read(accountRepositoryProvider)
                                  .cancelDeletion(),
                        ),
                child: const Text('Annulla'),
              ),
            ),
          ),
        ],

        const Divider(height: 32),

        if (p.supervised)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Account supervisionato',
                    style: theme.textTheme.titleSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Questo account è intestato a un adulto per un minore che '
                    'lo usa sotto la sua supervisione. La chat parte spenta.',
                    style: theme.textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ),

        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          value: p.chatEnabled,
          onChanged:
              _busy
                  ? null
                  : (v) => _guard(
                    () => ref.read(accountRepositoryProvider).setChatEnabled(v),
                  ),
          title: const Text('Chat'),
          subtitle: Text(
            p.supervised
                ? 'Attivandola, chi usa questo account potrà scrivere e ricevere '
                    'messaggi da adulti che non conosce. Valuta se è il caso.'
                : 'Messaggi privati e di gruppo.',
          ),
        ),

        Consumer(
          builder: (context, ref, _) {
            final accepted = ref.watch(safetyAcceptedProvider).value ?? false;
            return SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: accepted,
              onChanged:
                  _busy
                      ? null
                      : (v) => _guard(() async {
                        final repo = ref.read(safetyRepositoryProvider);
                        if (v) {
                          await repo.accept(
                            await ref.read(safetyNoticeProvider.future),
                          );
                        } else {
                          await repo.revoke();
                        }
                        ref.invalidate(safetyAcceptedProvider);
                      }),
              title: const Text('Mostra gli spot sulla mappa'),
              subtitle: const Text(
                'Spegnendolo la mappa resta senza spot. Video e resto '
                'dell\'app non cambiano.',
              ),
            );
          },
        ),

        const Divider(height: 32),
        Text('I tuoi dati', style: theme.textTheme.titleSmall),
        const SizedBox(height: 8),

        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.download_outlined),
          title: const Text('Scarica i miei dati'),
          subtitle: const Text('Profilo, spot, commenti, messaggi. In JSON.'),
          onTap: _busy ? null : _exportData,
        ),

        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.delete_outline, color: theme.colorScheme.error),
          title: Text(
            'Elimina l\'account',
            style: TextStyle(color: theme.colorScheme.error),
          ),
          onTap: _busy || p.isPendingDeletion ? null : _confirmDeletion,
        ),

        const Divider(height: 32),
        const Divider(height: 32),
        const LegalLinks(),

        const SizedBox(height: 16),
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.logout),
          title: const Text('Esci'),
          onTap:
              _busy
                  ? null
                  : () => _guard(
                    () => ref.read(accountRepositoryProvider).signOut(),
                  ),
        ),
      ],
    );
  }
}
