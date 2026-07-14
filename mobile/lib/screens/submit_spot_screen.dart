import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../providers.dart';
import '../services/api_client.dart';

/// Form to propose a new spot at [location] (usually a long-press on the map).
///
/// Submissions always start as `pending`: an admin has to confirm the photos
/// show a real, suitable location before the spot appears on the public map.
class SubmitSpotScreen extends ConsumerStatefulWidget {
  const SubmitSpotScreen({super.key, required this.location});

  final LatLng location;

  @override
  ConsumerState<SubmitSpotScreen> createState() => _SubmitSpotScreenState();
}

class _SubmitSpotScreenState extends ConsumerState<SubmitSpotScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _description = TextEditingController();
  final _photoUrls = TextEditingController();

  int _difficulty = 1;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _description.dispose();
    _photoUrls.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(spotRepositoryProvider).submitSpot(
            name: _name.text.trim(),
            description: _description.text.trim(),
            lat: widget.location.latitude,
            lng: widget.location.longitude,
            difficulty: _difficulty,
            photoUrls: _photoUrls.text
                .split('\n')
                .map((u) => u.trim())
                .where((u) => u.isNotEmpty)
                .toList(growable: false),
          );
      ref.invalidate(mySpotsProvider);
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Spot submitted! It will appear on the map once an admin '
              'verifies it.',
            ),
          ),
        );
      }
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = widget.location;
    return Scaffold(
      appBar: AppBar(title: const Text('Suggest a spot')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Location: ${loc.latitude.toStringAsFixed(5)}, '
                '${loc.longitude.toStringAsFixed(5)}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _name,
                decoration: const InputDecoration(labelText: 'Name'),
                maxLength: 120,
                validator: (v) => (v == null || v.trim().length < 2)
                    ? 'At least 2 characters'
                    : null,
              ),
              TextFormField(
                controller: _description,
                decoration: const InputDecoration(
                  labelText: 'Description',
                  helperText: 'What can you train here?',
                ),
                maxLength: 2000,
                maxLines: 3,
              ),
              const SizedBox(height: 12),
              Text('Difficulty: $_difficulty',
                  style: Theme.of(context).textTheme.bodyMedium),
              Slider(
                value: _difficulty.toDouble(),
                min: 1,
                max: 5,
                divisions: 4,
                label: '$_difficulty',
                onChanged: (v) => setState(() => _difficulty = v.round()),
              ),
              TextFormField(
                controller: _photoUrls,
                decoration: const InputDecoration(
                  labelText: 'Photo URLs (one per line)',
                  helperText:
                      'Real photos are required before an admin can verify '
                      'the spot.',
                ),
                maxLines: 3,
              ),
              const SizedBox(height: 20),
              if (_error != null) ...[
                Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
                const SizedBox(height: 12),
              ],
              FilledButton(
                onPressed: _busy ? null : _submit,
                child: Text(_busy ? 'Submitting…' : 'Submit for review'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
