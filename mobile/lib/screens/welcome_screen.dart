import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';
import '../services/api_client.dart';
import '../widgets/risk_notice.dart';

/// The way in.
///
/// Only one door for now: an anonymous account. Nothing is asked — no email,
/// no chosen name — but the risk notice comes first, because a guest gets the
/// same spots and the same tutorials and therefore takes the same risk.
class WelcomeScreen extends ConsumerStatefulWidget {
  const WelcomeScreen({super.key});

  @override
  ConsumerState<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends ConsumerState<WelcomeScreen> {
  bool _busy = false;

  Future<void> _continueAsGuest() async {
    setState(() => _busy = true);
    try {
      // `remember: false`: we need the document and its version to send, and
      // an acceptance already given this session would skip the dialog.
      final notice = await requestRiskNotice(
        context,
        ref,
        liabilityWaiverNoticeId,
        remember: false,
      );
      if (notice == null) return;

      final session =
          await ref.read(authControllerProvider.notifier).signInAsGuest([notice]);
      if (!mounted) return;
      final key = session.guestKey;
      if (key != null) {
        await Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => GuestKeyScreen(
              displayName: session.displayName,
              guestKey: key,
            ),
          ),
        );
      }
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.detail ?? 'Non riusciamo a entrare. Riprova.')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Spacer(),
              Text('PkFAMILY', style: theme.textTheme.displaySmall),
              const SizedBox(height: 12),
              Text(
                'Spot segnalati dalla community e tutorial, gratis.',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 28),
              Text(
                'Puoi entrare senza account: non ti chiediamo né email né nome, '
                'te ne diamo uno noi. Le domande però sono le stesse per tutti — '
                'servono a proporti esercizi adatti.',
                style: theme.textTheme.bodyMedium,
              ),
              const Spacer(),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _busy ? null : _continueAsGuest,
                  child: _busy
                      ? const SizedBox(
                          height: 18,
                          width: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Continua senza account'),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Ti daremo una chiave da conservare: è l’unico modo per '
                'ritrovare questo profilo su un altro telefono.',
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}

/// The one time the guest key is ever shown.
///
/// An anonymous account has no email to recover it with: this string is the
/// account. The screen cannot be dismissed with the back gesture, because
/// leaving it by accident means losing the profile silently.
class GuestKeyScreen extends StatelessWidget {
  const GuestKeyScreen({
    super.key,
    required this.displayName,
    required this.guestKey,
  });

  final String displayName;
  final String guestKey;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return PopScope(
      canPop: false,
      child: Scaffold(
        appBar: AppBar(title: const Text('Account anonimo')),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Text('Da qui in poi sei', style: theme.textTheme.bodyMedium),
              const SizedBox(height: 4),
              Text(displayName, style: theme.textTheme.headlineSmall),
              const SizedBox(height: 20),
              Text(
                'Nome generato: non dice niente di te. Questa è la tua chiave, '
                'e la vedi una volta sola.',
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: SelectableText(
                    guestKey,
                    style: theme.textTheme.bodyLarge?.copyWith(
                      fontFamily: 'monospace',
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: guestKey));
                  if (!context.mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Copiata. Incollala dove non la perdi.'),
                    ),
                  );
                },
                icon: const Icon(Icons.copy_all_outlined),
                label: const Text('Copia la chiave'),
              ),
              const SizedBox(height: 20),
              Text(
                'Serve a ritrovare questo profilo su un altro dispositivo, o se '
                'reinstalli l’app. Senza, l’avanzamento resta solo su questo '
                'telefono.',
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('L’ho salvata, continua'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
