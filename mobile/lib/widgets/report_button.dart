import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';
import '../repositories/moderation_repository.dart';

/// Le categorie di segnalazione.
///
/// Poche e distinte. Un elenco lungo fa scegliere «altro» a tutti, e una
/// segnalazione senza categoria costringe chi modera a ricostruire il contesto
/// da zero.
const _reasons = <String>[
  'Contenuto illecito',
  'Molestie o minacce',
  'Contenuto inadatto a minori',
  'Spot pericoloso',
  'Spot su proprietà privata',
  'Spam',
  'Altro',
];

/// Il pulsante «segnala», da mettere ovunque ci sia contenuto altrui.
///
/// Che ci sia un modo per segnalare, raggiungibile dove il contenuto sta, non è
/// una cortesia: l'art. 16 DSA chiede un meccanismo di notice-and-action, e un
/// indirizzo email in fondo alle condizioni d'uso non lo è.
class ReportButton extends ConsumerWidget {
  const ReportButton({
    super.key,
    required this.kind,
    required this.targetId,
    this.label,
  });

  final ReportKind kind;
  final String targetId;
  final String? label;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    Future<void> submit() async {
      if (!ref.read(isSignedInProvider)) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Serve un account per segnalare.')),
        );
        return;
      }

      final reason = await showModalBottomSheet<String>(
        context: context,
        showDragHandle: true,
        isScrollControlled: true,
        builder: (_) => const _ReportSheet(),
      );
      if (reason == null || !context.mounted) return;

      try {
        await ref
            .read(moderationRepositoryProvider)
            .report(kind: kind, targetId: targetId, reason: reason);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'Segnalato. Chi hai segnalato non saprà che sei statə tu.',
              ),
            ),
          );
        }
      } catch (err) {
        if (context.mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text('$err')));
        }
      }
    }

    if (label != null) {
      return TextButton.icon(
        onPressed: submit,
        icon: const Icon(Icons.flag_outlined, size: 18),
        label: Text(label!),
      );
    }
    return IconButton(
      tooltip: 'Segnala',
      onPressed: submit,
      icon: const Icon(Icons.flag_outlined),
    );
  }
}

class _ReportSheet extends StatefulWidget {
  const _ReportSheet();

  @override
  State<_ReportSheet> createState() => _ReportSheetState();
}

class _ReportSheetState extends State<_ReportSheet> {
  String _reason = _reasons.first;
  final _detail = TextEditingController();

  @override
  void dispose() {
    _detail.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;

    return Padding(
      padding: EdgeInsets.fromLTRB(20, 0, 20, bottom + 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Segnala', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 4),
          Text(
            'La legge un moderatore. Chi hai segnalato non sa che sei statə tu.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 12),

          RadioGroup<String>(
            groupValue: _reason,
            onChanged: (v) => setState(() => _reason = v!),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final reason in _reasons)
                  RadioListTile<String>(
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                    value: reason,
                    title: Text(reason),
                  ),
              ],
            ),
          ),

          const SizedBox(height: 8),
          TextField(
            controller: _detail,
            decoration: const InputDecoration(
              labelText: 'Dettagli (facoltativi)',
              isDense: true,
              border: OutlineInputBorder(),
            ),
            maxLines: 3,
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed:
                  () => Navigator.pop(
                    context,
                    _detail.text.trim().isEmpty
                        ? _reason
                        : '$_reason — ${_detail.text.trim()}',
                  ),
              child: const Text('Invia la segnalazione'),
            ),
          ),
        ],
      ),
    );
  }
}
