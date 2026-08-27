import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/chat.dart';
import '../../providers.dart';
import '../auth/sign_in_screen.dart';
import 'chat_room_screen.dart';

/// L'elenco delle conversazioni.
class ChatListScreen extends ConsumerWidget {
  const ChatListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(currentProfileProvider).valueOrNull;
    final signedIn = ref.watch(isSignedInProvider);

    if (!signedIn) return const _NeedsAccount();
    if (profile != null && !profile.canUseChat) {
      return _ChatDisabled(supervised: profile.supervised);
    }

    final chats = ref.watch(myChatsProvider);

    return Scaffold(
      body: chats.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => _ChatError(error: err),
        data:
            (chats) =>
                chats.isEmpty
                    ? const _NoChats()
                    : RefreshIndicator(
                      onRefresh: () async => ref.invalidate(myChatsProvider),
                      child: ListView.separated(
                        itemCount: chats.length + 1,
                        separatorBuilder: (_, _) => const Divider(height: 1),
                        itemBuilder: (context, i) {
                          if (i == 0) return const _NoEncryptionNotice();
                          return _ChatTile(chat: chats[i - 1], me: profile?.id);
                        },
                      ),
                    ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed:
            () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => const NewChatScreen()),
            ),
        tooltip: 'Nuova conversazione',
        child: const Icon(Icons.add_comment_outlined),
      ),
    );
  }
}

/// Detto una volta, in cima all'elenco.
///
/// Non è una formalità legale spostata nell'interfaccia: chi scrive in una chat
/// dà per scontato che sia privata, e qui «privata» significa «gli altri utenti
/// non la leggono», non «nessuno la legge». La differenza va detta prima, non
/// nell'informativa che nessuno apre.
class _NoEncryptionNotice extends StatelessWidget {
  const _NoEncryptionNotice();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      color: theme.colorScheme.surfaceContainerHighest,
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.lock_open_outlined,
            size: 18,
            color: theme.colorScheme.outline,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'I messaggi non sono cifrati end-to-end: gli altri utenti non li '
              'leggono, ma chi amministra il servizio tecnicamente può. '
              'Non scriverci cose che non diresti a voce.',
              style: theme.textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}

class _ChatTile extends StatelessWidget {
  const _ChatTile({required this.chat, required this.me});

  final Chat chat;
  final String? me;

  @override
  Widget build(BuildContext context) {
    final last = chat.lastMessage;

    return ListTile(
      leading: CircleAvatar(
        child: Icon(
          chat.isGroup ? Icons.groups_outlined : Icons.person_outline,
        ),
      ),
      title: Text(chat.titleFor(me)),
      subtitle:
          last == null
              ? const Text('Nessun messaggio')
              : Text(
                '${last.isMine(me) ? 'Tu' : last.displayName}: ${last.body}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
      trailing:
          last?.createdAt == null
              ? null
              : Text(
                _when(last!.createdAt!),
                style: Theme.of(context).textTheme.labelSmall,
              ),
      onTap:
          () => Navigator.of(context).push(
            MaterialPageRoute<void>(builder: (_) => ChatRoomScreen(chat: chat)),
          ),
    );
  }

  /// Orario per oggi, giorno e mese altrimenti. L'anno serve solo se è passato.
  static String _when(DateTime t) {
    final now = DateTime.now();
    final sameDay =
        t.year == now.year && t.month == now.month && t.day == now.day;
    if (sameDay) {
      return '${t.hour.toString().padLeft(2, '0')}:'
          '${t.minute.toString().padLeft(2, '0')}';
    }
    if (t.year == now.year) return '${t.day}/${t.month}';
    return '${t.day}/${t.month}/${t.year}';
  }
}

class _NeedsAccount extends StatelessWidget {
  const _NeedsAccount();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.forum_outlined, size: 48),
            const SizedBox(height: 16),
            Text(
              'Per scrivere serve un account con email confermata.\n'
              'Mappa e video funzionano anche senza.',
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

class _ChatDisabled extends StatelessWidget {
  const _ChatDisabled({required this.supervised});

  final bool supervised;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.chat_bubble_outline, size: 48),
            const SizedBox(height: 16),
            Text(
              supervised
                  ? 'Su questo account la chat è spenta.\n\n'
                      'È un account supervisionato: la chat metterebbe in '
                      'contatto con adulti sconosciuti, e la decisione di '
                      'accenderla spetta a chi lo ha aperto — dalle '
                      'impostazioni del profilo.'
                  : 'Hai disattivato la chat. Puoi riaccenderla dal profilo.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}

class _NoChats extends StatelessWidget {
  const _NoChats();

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: const [
        _NoEncryptionNotice(),
        SizedBox(height: 60),
        Center(
          child: Padding(
            padding: EdgeInsets.symmetric(horizontal: 32),
            child: Text(
              'Nessuna conversazione.\nComincia tu.',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      ],
    );
  }
}

class _ChatError extends StatelessWidget {
  const _ChatError({required this.error});

  final Object error;

  @override
  Widget build(BuildContext context) {
    // Finché la migration 0004 non è applicata, il database risponde 500 con
    // 42P17: la ricorsione nelle policy. Dirlo aiuta chi installa, invece di
    // far sembrare rotta l'app.
    final recursion = '$error'.contains('42P17');

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48),
            const SizedBox(height: 16),
            Text(
              recursion
                  ? 'La chat non è ancora attiva su questo progetto: manca la '
                      'migration 0004, che corregge la ricorsione nelle '
                      'policy di sicurezza.'
                  : 'Non riesco a caricare le conversazioni.',
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

/// Avvia una conversazione cercando una persona per nome.
class NewChatScreen extends ConsumerStatefulWidget {
  const NewChatScreen({super.key});

  @override
  ConsumerState<NewChatScreen> createState() => _NewChatScreenState();
}

class _NewChatScreenState extends ConsumerState<NewChatScreen> {
  final _query = TextEditingController();
  final _groupName = TextEditingController();
  final _selected = <String, String>{};

  bool _group = false;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _query.dispose();
    _groupName.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final repo = ref.read(chatRepositoryProvider);
      final chatId =
          _group
              ? await repo.createGroup(
                name: _groupName.text,
                memberIds: _selected.keys.toList(),
              )
              : await repo.openDirect(_selected.keys.first);

      ref.invalidate(myChatsProvider);
      if (!mounted) return;

      final chats = await ref.read(myChatsProvider.future);
      if (!mounted) return;
      final chat = chats.firstWhere(
        (c) => c.id == chatId,
        orElse: () => Chat(id: chatId, isGroup: _group),
      );
      Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(builder: (_) => ChatRoomScreen(chat: chat)),
      );
    } catch (err) {
      setState(() => _error = '$err');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(userSearchProvider(_query.text));
    final canStart =
        _selected.isNotEmpty && (!_group || _groupName.text.trim().isNotEmpty);

    return Scaffold(
      appBar: AppBar(title: const Text('Nuova conversazione')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: false, label: Text('A due')),
                ButtonSegment(value: true, label: Text('Gruppo')),
              ],
              selected: {_group},
              onSelectionChanged:
                  (s) => setState(() {
                    _group = s.first;
                    if (!_group && _selected.length > 1) {
                      final first = _selected.entries.first;
                      _selected
                        ..clear()
                        ..[first.key] = first.value;
                    }
                  }),
            ),
          ),

          if (_group)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
              child: TextField(
                controller: _groupName,
                decoration: const InputDecoration(labelText: 'Nome del gruppo'),
                onChanged: (_) => setState(() {}),
              ),
            ),

          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _query,
              decoration: const InputDecoration(
                labelText: 'Cerca per nome',
                prefixIcon: Icon(Icons.search),
              ),
              onChanged: (_) => setState(() {}),
            ),
          ),

          if (_selected.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Wrap(
                spacing: 8,
                children: [
                  for (final entry in _selected.entries)
                    Chip(
                      label: Text(entry.value),
                      onDeleted:
                          () => setState(() => _selected.remove(entry.key)),
                    ),
                ],
              ),
            ),

          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),

          Expanded(
            child: results.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('$e')),
              data:
                  (people) =>
                      people.isEmpty
                          ? const Center(
                            child: Text('Nessuno con questo nome.'),
                          )
                          : ListView(
                            children: [
                              for (final p in people)
                                CheckboxListTile(
                                  value: _selected.containsKey(p.id),
                                  title: Text(p.username),
                                  secondary: const Icon(Icons.person_outline),
                                  onChanged:
                                      (on) => setState(() {
                                        if (on == true) {
                                          if (!_group) _selected.clear();
                                          _selected[p.id] = p.username;
                                        } else {
                                          _selected.remove(p.id);
                                        }
                                      }),
                                ),
                            ],
                          ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: Padding(
        padding: const EdgeInsets.all(16),
        child: FilledButton(
          onPressed: canStart && !_busy ? _start : null,
          child: Text(_busy ? 'Un momento…' : 'Comincia'),
        ),
      ),
    );
  }
}
