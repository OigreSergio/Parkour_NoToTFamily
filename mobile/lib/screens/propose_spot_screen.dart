import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';

/// Proponi uno spot.
///
/// Va in coda di moderazione (`status = 'pending'`): finché un admin non lo
/// verifica lo vede solo chi l'ha proposto. Non è burocrazia — è la ragione per
/// cui la mappa può dirsi curata invece che aperta a chiunque.
///
/// Livello e affollamento si possono lasciare in bianco, ed è la scelta
/// giusta se non se ne è sicuri: «non valutato» vale più di una risposta a caso.
class ProposeSpotScreen extends ConsumerStatefulWidget {
  const ProposeSpotScreen({super.key});

  @override
  ConsumerState<ProposeSpotScreen> createState() => _ProposeSpotScreenState();
}

class _ProposeSpotScreenState extends ConsumerState<ProposeSpotScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _description = TextEditingController();
  final _lat = TextEditingController();
  final _lng = TextEditingController();

  String? _skill;
  String? _crowd;
  bool? _water;
  bool _busy = false;
  bool _done = false;
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _description.dispose();
    _lat.dispose();
    _lng.dispose();
    super.dispose();
  }

  Future<void> _useMyPosition() async {
    final result = await ref.refresh(locationRequestProvider.future);
    if (!mounted || !result.hasPosition) return;
    setState(() {
      _lat.text = result.position!.latitude.toStringAsFixed(6);
      _lng.text = result.position!.longitude.toStringAsFixed(6);
    });
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(spotWriteRepositoryProvider)
          .propose(
            name: _name.text,
            lat: double.parse(_lat.text.replaceAll(',', '.')),
            lng: double.parse(_lng.text.replaceAll(',', '.')),
            description: _description.text,
            skillLevel: _skill,
            crowdLevel: _crowd,
            hasFountain: _water,
          );
      if (mounted) setState(() => _done = true);
    } catch (err) {
      setState(() => _error = '$err');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_done) {
      return Scaffold(
        appBar: AppBar(title: const Text('Proposta inviata')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.check_circle_outline, size: 48),
                const SizedBox(height: 16),
                Text(
                  'Lo vedi solo tu finché non viene verificato.',
                  style: theme.textTheme.titleMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                Text(
                  'Se viene rifiutato ti diciamo perché.',
                  style: theme.textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Proponi uno spot')),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            TextFormField(
              controller: _name,
              decoration: const InputDecoration(
                labelText: 'Nome',
                helperText: 'Come lo chiamate voi.',
              ),
              validator:
                  (v) =>
                      (v == null || v.trim().length < 3)
                          ? 'Almeno tre caratteri.'
                          : null,
            ),
            const SizedBox(height: 16),

            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _lat,
                    decoration: const InputDecoration(labelText: 'Latitudine'),
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                      signed: true,
                    ),
                    validator: (v) => _coord(v, 90),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _lng,
                    decoration: const InputDecoration(labelText: 'Longitudine'),
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                      signed: true,
                    ),
                    validator: (v) => _coord(v, 180),
                  ),
                ),
              ],
            ),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: _useMyPosition,
                icon: const Icon(Icons.my_location, size: 18),
                label: const Text('Usa dove sono adesso'),
              ),
            ),

            const SizedBox(height: 8),
            TextFormField(
              controller: _description,
              decoration: const InputDecoration(
                labelText: 'Com\'è',
                helperText:
                    'Superfici, cosa ci si allena, cose da sapere. È la parte '
                    'che serve davvero a chi non c\'è mai stato.',
              ),
              maxLines: 4,
            ),

            const SizedBox(height: 24),
            Text('Facoltativi', style: theme.textTheme.labelLarge),
            Text(
              'Lasciali in bianco se non sei sicurə: «non valutato» è meglio di '
              'una risposta a caso.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 12),

            _Choice(
              label: 'Livello',
              options: const ['principiante', 'intermedio', 'avanzato'],
              value: _skill,
              onChanged: (v) => setState(() => _skill = v),
            ),
            const SizedBox(height: 12),
            _Choice(
              label: 'Affollamento',
              options: const ['tranquillo', 'medio', 'affollato'],
              value: _crowd,
              onChanged: (v) => setState(() => _crowd = v),
            ),
            const SizedBox(height: 12),
            _Choice(
              label: 'Acqua nei pressi',
              options: const ['sì', 'no'],
              value: switch (_water) {
                true => 'sì',
                false => 'no',
                null => null,
              },
              onChanged:
                  (v) => setState(
                    () =>
                        _water = switch (v) {
                          'sì' => true,
                          'no' => false,
                          _ => null,
                        },
                  ),
            ),

            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
            ],

            const SizedBox(height: 24),
            FilledButton(
              onPressed: _busy ? null : _submit,
              child: Text(_busy ? 'Invio…' : 'Proponi'),
            ),
            const SizedBox(height: 12),
            Text(
              'Non proporre spot su proprietà privata senza permesso, e non '
              'caricare foto in cui si riconoscono persone che non ti hanno '
              'dato il consenso.',
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }

  static String? _coord(String? raw, double max) {
    final v = double.tryParse((raw ?? '').replaceAll(',', '.'));
    if (v == null) return 'Numero non valido.';
    if (v.abs() > max) return 'Fuori intervallo.';
    return null;
  }
}

class _Choice extends StatelessWidget {
  const _Choice({
    required this.label,
    required this.options,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final List<String> options;
  final String? value;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.labelMedium),
        const SizedBox(height: 6),
        Wrap(
          spacing: 8,
          children: [
            for (final option in options)
              ChoiceChip(
                label: Text(option[0].toUpperCase() + option.substring(1)),
                selected: value == option,
                // Ritoccare la stessa scelta la annulla: tornare a "non lo so"
                // deve costare quanto sceglierlo.
                onSelected: (sel) => onChanged(sel ? option : null),
              ),
          ],
        ),
      ],
    );
  }
}
