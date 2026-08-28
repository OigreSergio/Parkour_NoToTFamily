import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';

/// Le decisioni di moderazione che ti riguardano.
///
/// L'art. 17 DSA non chiede solo di motivare una rimozione: chiede che la
/// motivazione **arrivi** a chi la subisce. Un `rejection_reason` scritto in una
/// colonna che nessuno legge non è una comunicazione.
///
/// Sta in cima al profilo perché è lì che uno guarda quando si chiede perché la
/// sua proposta è sparita.
class ModerationNotices extends ConsumerWidget {
  const ModerationNotices({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notices = ref.watch(myModerationNoticesProvider).valueOrNull;
    if (notices == null || notices.isEmpty) return const SizedBox.shrink();

    final theme = Theme.of(context);
    final unread = notices.where((n) => n.isUnread).length;

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: ExpansionTile(
        initiallyExpanded: unread > 0,
        leading: Badge(
          isLabelVisible: unread > 0,
          label: Text('$unread'),
          child: const Icon(Icons.gavel_outlined),
        ),
        title: const Text('Decisioni di moderazione'),
        subtitle: Text(
          unread > 0
              ? '$unread da leggere'
              : '${notices.length} nell\'archivio',
          style: theme.textTheme.bodySmall,
        ),
        children: [
          for (final notice in notices)
            ListTile(
              dense: true,
              title: Text(notice.label),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(notice.reason),
                  if (notice.createdAt != null)
                    Text(
                      _when(notice.createdAt!),
                      style: theme.textTheme.labelSmall,
                    ),
                ],
              ),
              trailing:
                  notice.isUnread
                      ? IconButton(
                        tooltip: 'Segna come letta',
                        icon: const Icon(Icons.done),
                        onPressed: () async {
                          await ref
                              .read(moderationRepositoryProvider)
                              .markRead(notice.id);
                          ref.invalidate(myModerationNoticesProvider);
                        },
                      )
                      : null,
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Text(
              'Se pensi che una decisione sia sbagliata, scrivi a '
              'abuse@pkfamily.app: la rivediamo.',
              style: theme.textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }

  static String _when(DateTime t) => '${t.day}/${t.month}/${t.year}';
}
