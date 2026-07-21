import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/bank_details.dart';
import '../providers.dart';
import '../widgets/error_view.dart';

/// Shows how to support the project with a bank transfer.
///
/// The coordinates come from the backend (`GET /api/v1/payments/bank-details`)
/// so the IBAN is never hardcoded in the client or the repository.
class SupportScreen extends ConsumerWidget {
  const SupportScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailsAsync = ref.watch(bankDetailsProvider);

    return detailsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => ErrorView(
        message: 'Could not load payment details.\n$error',
        onRetry: () => ref.invalidate(bankDetailsProvider),
      ),
      data: (details) {
        if (details == null) {
          return const Center(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Text(
                'Donations are not set up yet.\nCheck back soon!',
                textAlign: TextAlign.center,
              ),
            ),
          );
        }
        return _BankDetailsView(details: details);
      },
    );
  }
}

class _BankDetailsView extends StatelessWidget {
  const _BankDetailsView({required this.details});

  final BankDetails details;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Icon(Icons.volunteer_activism,
            size: 56, color: theme.colorScheme.primary),
        const SizedBox(height: 12),
        Text(
          'Support the project',
          style: theme.textTheme.titleLarge,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        Text(
          'Parkour NoToT Family is free and community-driven. '
          'If you want to help keep it running, you can chip in '
          'with a bank transfer (SEPA).',
          style: theme.textTheme.bodyMedium,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),
        Card(
          child: Column(
            children: [
              _CopyableRow(label: 'Beneficiary', value: details.beneficiary),
              const Divider(height: 1),
              _CopyableRow(
                label: 'IBAN',
                value: details.iban,
                displayValue: details.ibanFormatted,
                monospace: true,
              ),
              if (details.bic != null) ...[
                const Divider(height: 1),
                _CopyableRow(
                    label: 'BIC/SWIFT', value: details.bic!, monospace: true),
              ],
              if (details.transferNote != null) ...[
                const Divider(height: 1),
                _CopyableRow(
                    label: 'Transfer note', value: details.transferNote!),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),
        Text(
          'Tap a row to copy it. Transfers within SEPA (EU) are free '
          'with most banks.',
          style: theme.textTheme.bodySmall,
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

/// A labelled value that copies itself to the clipboard when tapped.
class _CopyableRow extends StatelessWidget {
  const _CopyableRow({
    required this.label,
    required this.value,
    this.displayValue,
    this.monospace = false,
  });

  final String label;
  final String value;

  /// Optional prettified rendering (e.g. IBAN in blocks of four); the raw
  /// [value] is what gets copied.
  final String? displayValue;
  final bool monospace;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      title: Text(label, style: Theme.of(context).textTheme.labelSmall),
      subtitle: Text(
        displayValue ?? value,
        style: monospace
            ? const TextStyle(fontFamily: 'monospace', fontSize: 15)
            : null,
      ),
      trailing: const Icon(Icons.copy, size: 18),
      onTap: () async {
        await Clipboard.setData(ClipboardData(text: value));
        if (context.mounted) {
          ScaffoldMessenger.of(context)
            ..hideCurrentSnackBar()
            ..showSnackBar(SnackBar(content: Text('$label copied')));
        }
      },
    );
  }
}
