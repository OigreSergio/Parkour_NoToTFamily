import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;

import '../widgets/markdown_text.dart';

/// I documenti legali, versionati nel repo.
///
/// Vivono in `assets/legal/` come markdown, non incollati nel codice: così si
/// possono leggere, correggere e far revisionare da qualcuno che non apre un
/// editor Dart. Ogni file porta in testa la data e il numero di versione.
enum LegalDocument {
  privacy('privacy', 'Informativa privacy'),
  termini('termini', 'Termini di servizio'),
  cookie('cookie', 'Cookie e archiviazione locale'),
  noteLegali('note-legali', 'Note legali'),
  subResponsabili('sub-responsabili', 'Chi tratta i dati per noi');

  const LegalDocument(this.file, this.title);

  final String file;
  final String title;

  String get assetPath => 'assets/legal/$file.md';
}

class LegalScreen extends StatelessWidget {
  const LegalScreen({super.key, required this.document});

  final LegalDocument document;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(document.title)),
      body: FutureBuilder<String>(
        future: rootBundle.loadString(document.assetPath),
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return _LoadError(document: document, error: snapshot.error!);
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 48),
            child: MarkdownText(source: snapshot.data!),
          );
        },
      ),
    );
  }
}

class _LoadError extends StatelessWidget {
  const _LoadError({required this.document, required this.error});

  final LegalDocument document;
  final Object error;

  @override
  Widget build(BuildContext context) {
    // Un documento legale che non si carica non è un inconveniente estetico:
    // è un'informazione dovuta che non arriva. Meglio dire dove trovarlo.
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.description_outlined, size: 48),
            const SizedBox(height: 16),
            Text(
              'Non riesco a caricare «${document.title}».\n'
              'Scrivi a privacy@pkfamily.app e te lo mandiamo.',
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

/// I link ai documenti legali.
///
/// Deve essere raggiungibile da chiunque, anche senza account: un'informativa
/// che si vede solo dopo la registrazione arriva dopo che i dati sono già stati
/// raccolti, cioè troppo tardi.
class LegalLinks extends StatelessWidget {
  const LegalLinks({super.key, this.dense = false});

  final bool dense;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (!dense) ...[
          Text('Trasparenza', style: theme.textTheme.titleSmall),
          const SizedBox(height: 4),
        ],
        Wrap(
          spacing: 4,
          runSpacing: -8,
          children: [
            for (final doc in LegalDocument.values)
              TextButton(
                style: TextButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                ),
                onPressed:
                    () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => LegalScreen(document: doc),
                      ),
                    ),
                child: Text(_short(doc), style: theme.textTheme.labelMedium),
              ),
          ],
        ),
      ],
    );
  }

  /// Etichette corte: in un footer «Chi tratta i dati per noi» va a capo tre
  /// volte e non lo legge nessuno.
  static String _short(LegalDocument doc) => switch (doc) {
    LegalDocument.privacy => 'Privacy',
    LegalDocument.termini => 'Termini',
    LegalDocument.cookie => 'Cookie',
    LegalDocument.noteLegali => 'Note legali',
    LegalDocument.subResponsabili => 'Sub-responsabili',
  };
}
