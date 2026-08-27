import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/profile.dart';
import '../../providers.dart';

/// Chi ha meno di 16 anni chiede a un genitore di aprire l'accesso.
///
/// Come funziona, e perché così:
///
/// * l'account lo apre **l'adulto**, a suo nome. Non esiste un account del
///   minore, quindi non si tratta nessuna email di minore e l'art. 8 GDPR non
///   entra in gioco;
/// * del minore qui non si raccoglie niente: solo l'email dell'adulto, per
///   mandargli **una** richiesta;
/// * se entro 7 giorni la richiesta non viene completata, si cancella. Non si
///   tiene a bagno un archivio di contatti di terzi raccolti da minorenni;
/// * l'invio passa da una Edge Function server-side, che applica il rate limit.
///   È un canale di invio email pilotato da un input utente: senza limiti
///   diventerebbe uno strumento di molestia.
///
/// Va detto onestamente: nulla impedisce a un quindicenne di dichiarare 16
/// anni, e nessun servizio gratuito può verificarlo davvero. Questo flusso dà
/// una strada corretta a chi la vuole percorrere, non costruisce una barriera
/// che non esiste.
class ParentAccessScreen extends ConsumerStatefulWidget {
  const ParentAccessScreen({super.key});

  @override
  ConsumerState<ParentAccessScreen> createState() => _ParentAccessScreenState();
}

class _ParentAccessScreenState extends ConsumerState<ParentAccessScreen> {
  final _form = GlobalKey<FormState>();
  final _parentEmail = TextEditingController();
  bool _busy = false;
  bool _sent = false;
  String? _error;

  @override
  void dispose() {
    _parentEmail.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    if (!_form.currentState!.validate()) return;

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(parentAccessRepositoryProvider)
          .requestAccess(parentEmail: _parentEmail.text.trim());
      if (mounted) setState(() => _sent = true);
    } catch (err) {
      setState(() => _error = '$err');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_sent) {
      return Scaffold(
        appBar: AppBar(title: const Text('Richiesta inviata')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.outgoing_mail, size: 48),
                const SizedBox(height: 16),
                Text(
                  'Abbiamo scritto a chi hai indicato.',
                  style: theme.textTheme.titleMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                Text(
                  'Se non completa la registrazione entro 7 giorni, la '
                  'richiesta e l\'indirizzo vengono cancellati.',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Chiedi a un genitore')),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(
              'Per aprire un account da solə servono ${AgeCheck.minimumAge} anni.',
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Text(
              'Non è una regola nostra: sotto quella soglia la legge europea '
              'chiede il consenso di un genitore, e per verificarlo davvero '
              'serve che sia lui ad aprire l\'accesso.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 20),
            const _Steps(),
            const SizedBox(height: 24),
            TextFormField(
              controller: _parentEmail,
              decoration: const InputDecoration(
                labelText: 'Email di un genitore o tutore',
                helperText:
                    'Riceverà una sola email. Nessun altro dato viene raccolto.',
              ),
              keyboardType: TextInputType.emailAddress,
              autocorrect: false,
              validator:
                  (v) =>
                      (v == null || !v.contains('@'))
                          ? 'Serve un indirizzo email valido.'
                          : null,
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
            ],
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _busy ? null : _send,
              child: Text(_busy ? 'Invio…' : 'Invia la richiesta'),
            ),
            const SizedBox(height: 24),
            Text(
              'Nel frattempo la sezione video resta aperta: è il posto giusto '
              'da cui cominciare comunque.',
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _Steps extends StatelessWidget {
  const _Steps();

  @override
  Widget build(BuildContext context) {
    const steps = [
      'Tu indichi l\'email di un genitore o tutore.',
      'Lui riceve un link e apre l\'account a suo nome.',
      'Tu lo usi sotto la sua supervisione: mappa e video completi.',
      'La chat parte spenta. Può accenderla lui dalle impostazioni.',
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < steps.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(radius: 12, child: Text('${i + 1}')),
                const SizedBox(width: 12),
                Expanded(child: Text(steps[i])),
              ],
            ),
          ),
      ],
    );
  }
}
