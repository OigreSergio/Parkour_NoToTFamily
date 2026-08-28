import 'package:flutter/material.dart';

/// Rende il markdown dei testi legali senza tirarsi dietro una dipendenza.
///
/// I documenti usano un sottoinsieme deliberatamente piccolo: titoli, paragrafi,
/// `**grassetto**`, elenchi puntati e righe orizzontali. Gestirlo a mano costa
/// meno di un package e tiene leggero un bundle che già pesa.
///
/// Estratto dal gate di sicurezza, dove serviva la stessa cosa: due
/// implementazioni dello stesso renderer sarebbero divergute alla prima
/// modifica.
class MarkdownText extends StatelessWidget {
  const MarkdownText({super.key, required this.source});

  final String source;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final blocks = source.split(RegExp(r'\n\s*\n'));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [for (final raw in blocks) ..._block(context, theme, raw)],
    );
  }

  List<Widget> _block(BuildContext context, ThemeData theme, String raw) {
    final text = raw.trim();
    if (text.isEmpty) return const [];

    if (text == '---') return const [Divider(height: 32)];

    if (text.startsWith('### ')) {
      return [
        const SizedBox(height: 8),
        Text(text.substring(4).trim(), style: theme.textTheme.titleSmall),
        const SizedBox(height: 6),
      ];
    }
    if (text.startsWith('## ')) {
      return [
        const SizedBox(height: 16),
        Text(text.substring(3).trim(), style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
      ];
    }
    if (text.startsWith('# ')) {
      return [
        Text(text.substring(2).trim(), style: theme.textTheme.headlineSmall),
        const SizedBox(height: 12),
      ];
    }

    // Un elenco: ogni riga che comincia con "- " è una voce, e le righe
    // successive che non cominciano così ne sono la continuazione.
    if (text.startsWith('- ')) {
      final items = <String>[];
      for (final line in text.split('\n')) {
        if (line.trimLeft().startsWith('- ')) {
          items.add(line.trimLeft().substring(2).trim());
        } else if (items.isNotEmpty) {
          items[items.length - 1] += ' ${line.trim()}';
        }
      }
      return [
        for (final item in items)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('•  ', style: theme.textTheme.bodyMedium),
                Expanded(child: _rich(item, theme.textTheme.bodyMedium)),
              ],
            ),
          ),
        const SizedBox(height: 6),
      ];
    }

    return [
      _rich(text.replaceAll('\n', ' '), theme.textTheme.bodyMedium),
      const SizedBox(height: 12),
    ];
  }

  /// Un paragrafo con `**grassetto**`.
  Widget _rich(String text, TextStyle? style) {
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
