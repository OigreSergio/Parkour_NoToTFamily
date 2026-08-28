import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/chat.dart';
import '../../providers.dart';
import '../../repositories/moderation_repository.dart';

/// Una conversazione aperta.
class ChatRoomScreen extends ConsumerStatefulWidget {
  const ChatRoomScreen({super.key, required this.chat});

  final Chat chat;

  @override
  ConsumerState<ChatRoomScreen> createState() => _ChatRoomScreenState();
}

class _ChatRoomScreenState extends ConsumerState<ChatRoomScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  bool _sending = false;

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  /// I nomi dei partecipanti, per dare un autore ai messaggi che arrivano da
  /// Realtime — che consegna la riga grezza, senza la join su `profiles`.
  Map<String, String> get _names => {
    for (final m in widget.chat.members) m.userId: m.displayName,
  };

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending) return;

    setState(() => _sending = true);
    // Si svuota subito: se l'invio fallisce il testo torna, ma nel caso normale
    // — che è la stragrande maggioranza — l'input non resta bloccato.
    _input.clear();

    try {
      await ref
          .read(chatRepositoryProvider)
          .send(chatId: widget.chat.id, body: text);
    } catch (err) {
      if (mounted) {
        _input.text = text;
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$err')));
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _leave() async {
    final ok = await showDialog<bool>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Uscire dalla conversazione?'),
            content: const Text(
              'I messaggi che hai già scritto restano: gli altri li hanno letti, e '
              'toglierli lascerebbe a metà la loro conversazione.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Annulla'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Esci'),
              ),
            ],
          ),
    );

    if (ok != true || !mounted) return;
    await ref.read(chatRepositoryProvider).leave(widget.chat.id);
    ref.invalidate(myChatsProvider);
    if (mounted) Navigator.of(context).pop();
  }

  Future<void> _blockOther() async {
    final me = ref.read(currentUserIdProvider);
    final other = widget.chat.members.where((m) => m.userId != me).toList();
    if (other.isEmpty) return;

    final ok = await showDialog<bool>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: Text('Bloccare ${other.first.displayName}?'),
            content: const Text(
              'Non potrà più scriverti, e tu non potrai scrivere a lui. Il blocco '
              'vale anche lato server: non è solo l\'app che smette di mostrarvi i '
              'messaggi.\n\nNon gli viene detto niente.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Annulla'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Blocca'),
              ),
            ],
          ),
    );

    if (ok != true || !mounted) return;
    await ref.read(chatRepositoryProvider).block(other.first.userId);
    ref.invalidate(blockedIdsProvider);
    if (mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Bloccato.')));
    }
  }

  /// Segnala la persona, non il singolo messaggio.
  ///
  /// Serve quando il problema è il comportamento nel suo insieme e non una
  /// frase: senza, l'unico modo di segnalare qualcuno sarebbe scegliere
  /// arbitrariamente uno dei suoi messaggi.
  Future<void> _reportPerson() async {
    final me = ref.read(currentUserIdProvider);
    final other = widget.chat.members.where((m) => m.userId != me).toList();
    if (other.isEmpty) return;

    final reason = await showDialog<String>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: Text('Segnalare ${other.first.displayName}?'),
            content: const Text(
              'Un moderatore guarderà il comportamento di questa persona. '
              'Non saprà che sei statə tu.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Annulla'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, 'Comportamento in chat'),
                child: const Text('Segnala'),
              ),
            ],
          ),
    );
    if (reason == null || !mounted) return;

    try {
      await ref
          .read(moderationRepositoryProvider)
          .report(
            kind: ReportKind.profile,
            targetId: other.first.userId,
            reason: reason,
          );
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Segnalato.')));
      }
    } catch (err) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$err')));
      }
    }
  }

  Future<void> _report(ChatMessage message) async {
    final reason = await showDialog<String>(
      context: context,
      builder: (ctx) => _ReportDialog(message: message),
    );
    if (reason == null || !mounted) return;

    try {
      await ref
          .read(chatRepositoryProvider)
          .reportMessage(messageId: message.id, reason: reason);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Segnalato. Un moderatore lo guarderà.'),
          ),
        );
      }
    } catch (err) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$err')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final me = ref.watch(currentUserIdProvider);
    final stream = ref.watch(chatMessagesProvider(widget.chat.id));

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.chat.titleFor(me)),
        actions: [
          PopupMenuButton<String>(
            onSelected:
                (value) => switch (value) {
                  'esci' => _leave(),
                  'blocca' => _blockOther(),
                  'segnala' => _reportPerson(),
                  _ => null,
                },
            itemBuilder:
                (_) => [
                  if (!widget.chat.isGroup) ...[
                    const PopupMenuItem(value: 'blocca', child: Text('Blocca')),
                    const PopupMenuItem(
                      value: 'segnala',
                      child: Text('Segnala la persona'),
                    ),
                  ],
                  const PopupMenuItem(value: 'esci', child: Text('Esci')),
                ],
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: stream.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error:
                  (err, _) => Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text('Non riesco a leggere i messaggi.\n$err'),
                    ),
                  ),
              data:
                  (messages) =>
                      messages.isEmpty
                          ? const Center(
                            child: Text('Ancora niente. Scrivi tu.'),
                          )
                          : ListView.builder(
                            controller: _scroll,
                            reverse: true,
                            padding: const EdgeInsets.all(12),
                            itemCount: messages.length,
                            itemBuilder: (context, i) {
                              // `reverse: true` mostra l'ultimo in basso senza dover
                              // scrollare a mano a ogni messaggio nuovo.
                              final message = messages[messages.length - 1 - i];
                              return _Bubble(
                                message: message,
                                isMine: message.isMine(me),
                                nameFallback: _names[message.senderId],
                                onReport:
                                    message.isMine(me)
                                        ? null
                                        : () => _report(message),
                              );
                            },
                          ),
            ),
          ),
          _Composer(controller: _input, sending: _sending, onSend: _send),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({
    required this.message,
    required this.isMine,
    this.nameFallback,
    this.onReport,
  });

  final ChatMessage message;
  final bool isMine;
  final String? nameFallback;
  final VoidCallback? onReport;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final name =
        message.isFromDeletedAccount
            ? message.displayName
            : (message.senderName ?? nameFallback ?? 'Traceur');

    return Align(
      alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
      child: GestureDetector(
        onLongPress: onReport,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 3),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          constraints: const BoxConstraints(maxWidth: 420),
          decoration: BoxDecoration(
            color:
                isMine
                    ? theme.colorScheme.primaryContainer
                    : theme.colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (!isMine)
                Text(
                  name,
                  style: theme.textTheme.labelSmall?.copyWith(
                    fontStyle:
                        message.isFromDeletedAccount ? FontStyle.italic : null,
                  ),
                ),
              Text(message.body, style: theme.textTheme.bodyMedium),
            ],
          ),
        ),
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.sending,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool sending;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 4, 8, 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                minLines: 1,
                maxLines: 5,
                maxLength: 4000,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => onSend(),
                decoration: const InputDecoration(
                  hintText: 'Scrivi…',
                  counterText: '',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
            ),
            IconButton.filled(
              onPressed: sending ? null : onSend,
              icon: const Icon(Icons.send),
            ),
          ],
        ),
      ),
    );
  }
}

/// Segnalazione di un messaggio.
///
/// Le categorie non sono decorative: l'art. 16 DSA chiede che una segnalazione
/// sia abbastanza precisa da poter essere trattata, e «contenuto illecito» e
/// «spam» richiedono a chi modera due reazioni molto diverse.
class _ReportDialog extends StatefulWidget {
  const _ReportDialog({required this.message});

  final ChatMessage message;

  @override
  State<_ReportDialog> createState() => _ReportDialogState();
}

class _ReportDialogState extends State<_ReportDialog> {
  static const _reasons = [
    'Contenuto illecito',
    'Molestie o minacce',
    'Contenuto inadatto a minori',
    'Spam',
    'Altro',
  ];

  String _reason = _reasons.first;
  final _detail = TextEditingController();

  @override
  void dispose() {
    _detail.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Segnala il messaggio'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
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
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Annulla'),
        ),
        FilledButton(
          onPressed:
              () => Navigator.pop(
                context,
                _detail.text.trim().isEmpty
                    ? _reason
                    : '$_reason — ${_detail.text.trim()}',
              ),
          child: const Text('Segnala'),
        ),
      ],
    );
  }
}
