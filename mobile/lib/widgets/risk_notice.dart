import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/risk_notice.dart';
import '../providers.dart';

/// Blocking risk notice, shown before a spot page or a tutorial.
///
/// There is no way out other than one of the two buttons: no tap-outside, no
/// back gesture, no X in the corner. It is a warning to read, not a cookie
/// banner. `showRiskNotice` returns true only if the user accepted.
class RiskNoticeDialog extends StatelessWidget {
  const RiskNoticeDialog({super.key, required this.notice});

  final RiskNotice notice;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return PopScope(
      canPop: false,
      child: AlertDialog(
        title: Text(notice.title),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (notice.summary.isNotEmpty) ...[
                Text(notice.summary, style: theme.textTheme.bodyMedium),
                const SizedBox(height: 14),
              ],
              for (final bullet in notice.bullets)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('•  '),
                      Expanded(
                        child: Text(bullet, style: theme.textTheme.bodyMedium),
                      ),
                    ],
                  ),
                ),
              if (notice.body.isNotEmpty)
                ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  title: Text(
                    'Leggi il testo completo',
                    style: theme.textTheme.labelLarge,
                  ),
                  children: [
                    Text(notice.body, style: theme.textTheme.bodySmall),
                  ],
                ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(notice.declineLabel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(notice.acceptLabel),
          ),
        ],
      ),
    );
  }
}

/// Show the notice with [noticeId] unless it has already been accepted in this
/// session, and report whether the flow may continue.
Future<bool> showRiskNotice(
  BuildContext context,
  WidgetRef ref,
  String noticeId,
) async {
  final accepted = ref.read(acceptedNoticesProvider);
  if (accepted.contains(noticeId)) return true;

  final notice = await ref.read(legalRepositoryProvider).notice(noticeId);
  if (!context.mounted) return false;

  final ok = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (_) => RiskNoticeDialog(notice: notice),
  );
  if (ok ?? false) {
    ref.read(acceptedNoticesProvider.notifier).accept(noticeId);
    return true;
  }
  return false;
}

/// Notice ids, as served by the backend.
const String spotRiskNoticeId = 'spot_risk';
const String tutorialRiskNoticeId = 'tutorial_risk';

/// Push the screen built by [builder], but only once the notice for
/// [noticeId] has been accepted. Declining leaves the user where they are.
Future<void> pushBehindRiskNotice(
  BuildContext context,
  WidgetRef ref,
  String noticeId,
  WidgetBuilder builder,
) async {
  if (!await showRiskNotice(context, ref, noticeId)) return;
  if (!context.mounted) return;
  await Navigator.of(context).push(MaterialPageRoute<void>(builder: builder));
}
