import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';
import '../services/safety_notice.dart';

/// L'avviso di sicurezza, prima che la mappa mostri un solo spot.
///
/// Non è un banner cookie e non va costruito come tale: non è consenso al
/// trattamento di dati, è una presa d'atto contrattuale. Il flag in
/// `localStorage` che ne deriva è quindi storage tecnico.
///
/// Rifiutare non butta fuori nessuno: si resta nell'app senza spot (§ "modalità
/// informativa"), e si può cambiare idea in entrambe le direzioni.
class SafetyGateScreen extends ConsumerStatefulWidget {
  const SafetyGateScreen({super.key});

  @override
  ConsumerState<SafetyGateScreen> createState() => _SafetyGateScreenState();
}

class _SafetyGateScreenState extends ConsumerState<SafetyGateScreen> {
  bool _busy = false;
  String? _error;

  Future<void> _accept(SafetyNotice notice) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(safetyRepositoryProvider).accept(notice);
      ref.invalidate(safetyAcceptedProvider);
    } catch (err) {
      setState(
        () => _error = 'Non è stato possibile registrare la scelta: $err',
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _decline() {
    // Nessuna scrittura: chi non accetta non lascia una traccia in più.
    ref.read(safetyDeclinedProvider.notifier).state = true;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final notice = ref.watch(safetyNoticeProvider);

    return Scaffold(
      body: SafeArea(
        child: notice.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, _) => _LoadError(error: err),
          data:
              (notice) => Column(
                children: [
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(24, 32, 24, 16),
                      child: _NoticeBody(markdown: notice.text),
                    ),
                  ),
                  if (_error != null)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      child: Text(
                        _error!,
                        style: TextStyle(color: theme.colorScheme.error),
                      ),
                    ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
                    child: Column(
                      children: [
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: _busy ? null : () => _accept(notice),
                            child: Text(
                              _busy ? 'Un momento…' : 'Ho capito, continuo',
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        SizedBox(
                          width: double.infinity,
                          // Stesso peso visivo dell'altro: il rifiuto è una scelta
                          // vera, non un ripiego nascosto in fondo.
                          child: OutlinedButton(
                            onPressed: _busy ? null : _decline,
                            child: const Text('Continua senza spot'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
        ),
      ),
    );
  }
}

/// Rende il markdown dell'avviso senza tirarsi dietro una dipendenza.
///
/// Il testo usa solo titoli, paragrafi, `**grassetto**` e una riga
/// orizzontale: gestirli a mano costa meno di un package, e tiene il bundle
/// leggero.
class _NoticeBody extends StatelessWidget {
  const _NoticeBody({required this.markdown});

  final String markdown;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final blocks = markdown.split(RegExp(r'\n\s*\n'));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final raw in blocks) ...[
          if (raw.trim() == '---')
            const Divider(height: 32)
          else if (raw.startsWith('# '))
            Text(raw.substring(2).trim(), style: theme.textTheme.headlineSmall)
          else
            _RichParagraph(
              text: raw.replaceAll('\n', ' ').trim(),
              style: theme.textTheme.bodyMedium,
            ),
          const SizedBox(height: 12),
        ],
      ],
    );
  }
}

/// Un paragrafo con `**grassetto**`.
class _RichParagraph extends StatelessWidget {
  const _RichParagraph({required this.text, this.style});

  final String text;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    final bold = style?.copyWith(fontWeight: FontWeight.w700);
    final spans = <TextSpan>[];

    // Split su `**`: gli indici dispari sono le porzioni in grassetto.
    final parts = text.split('**');
    for (var i = 0; i < parts.length; i++) {
      if (parts[i].isEmpty) continue;
      spans.add(TextSpan(text: parts[i], style: i.isOdd ? bold : style));
    }

    return Text.rich(TextSpan(children: spans), style: style);
  }
}

class _LoadError extends StatelessWidget {
  const _LoadError({required this.error});

  final Object error;

  @override
  Widget build(BuildContext context) {
    // Se l'avviso non si carica non si tira dritto: senza il testo non c'è
    // niente da accettare, e mostrare la mappa sarebbe la scelta sbagliata.
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48),
            const SizedBox(height: 16),
            Text(
              'Non è stato possibile caricare le informazioni di sicurezza.\n'
              'Riprova più tardi: senza, la mappa resta senza spot.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text('$error', style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

/// La versione breve, da mostrare nella scheda di ogni spot.
///
/// È lì che si decide davvero se andarci: un avviso visto una volta all'avvio
/// non accompagna quella decisione.
class SpotSafetyReminder extends StatelessWidget {
  const SpotSafetyReminder({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, size: 18, color: theme.colorScheme.outline),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Spot non ispezionato né certificato: le condizioni cambiano nel '
              'tempo, e alcuni spot sono su proprietà privata. Vai per gradi e '
              'valuta tu il posto, sul posto.',
              style: theme.textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}
