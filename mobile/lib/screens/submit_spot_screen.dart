import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';

/// Submit a new spot for review.
///
/// `POST /api/v1/spots` requires a logged-in user, so the screen shows a
/// sign-in / sign-up form first and the spot form once authenticated. The
/// created spot is `pending` until an admin verifies it — it will not show up
/// on the map right away.
class SubmitSpotScreen extends ConsumerWidget {
  const SubmitSpotScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tokens = ref.watch(authTokensProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(tokens == null ? 'Sign in to add a spot' : 'Add a spot'),
      ),
      body: tokens == null ? const _AuthForm() : const _SpotForm(),
    );
  }
}

/// Email/password sign-in, with a toggle to create a new account.
class _AuthForm extends ConsumerStatefulWidget {
  const _AuthForm();

  @override
  ConsumerState<_AuthForm> createState() => _AuthFormState();
}

class _AuthFormState extends ConsumerState<_AuthForm> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _displayName = TextEditingController();

  bool _registerMode = false;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _displayName.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    final auth = ref.read(authRepositoryProvider);
    try {
      if (_registerMode) {
        await auth.register(
          email: _email.text.trim(),
          password: _password.text,
          displayName: _displayName.text.trim(),
        );
      }
      final tokens = await auth.login(
        email: _email.text.trim(),
        password: _password.text,
      );
      ref.read(authTokensProvider.notifier).state = tokens;
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            _registerMode
                ? 'Create an account to submit spots.'
                : 'Sign in to submit spots for review.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          if (_registerMode) ...[
            TextFormField(
              controller: _displayName,
              decoration: const InputDecoration(
                labelText: 'Display name',
                border: OutlineInputBorder(),
              ),
              validator: (v) =>
                  (v == null || v.trim().length < 2) ? 'At least 2 characters' : null,
            ),
            const SizedBox(height: 12),
          ],
          TextFormField(
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(
              labelText: 'Email',
              border: OutlineInputBorder(),
            ),
            validator: (v) =>
                (v == null || !v.contains('@')) ? 'Enter a valid email' : null,
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _password,
            obscureText: true,
            decoration: const InputDecoration(
              labelText: 'Password',
              border: OutlineInputBorder(),
            ),
            validator: (v) =>
                (v == null || v.length < 8) ? 'At least 8 characters' : null,
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: _busy
                ? const SizedBox(
                    height: 18, width: 18, child: CircularProgressIndicator())
                : Text(_registerMode ? 'Create account & sign in' : 'Sign in'),
          ),
          TextButton(
            onPressed: _busy
                ? null
                : () => setState(() => _registerMode = !_registerMode),
            child: Text(_registerMode
                ? 'I already have an account'
                : 'No account yet? Create one'),
          ),
        ],
      ),
    );
  }
}

/// The actual spot form, shown once the user is authenticated.
class _SpotForm extends ConsumerStatefulWidget {
  const _SpotForm();

  @override
  ConsumerState<_SpotForm> createState() => _SpotFormState();
}

class _SpotFormState extends ConsumerState<_SpotForm> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _description = TextEditingController();
  final _lat = TextEditingController();
  final _lng = TextEditingController();

  int _difficulty = 1;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _description.dispose();
    _lat.dispose();
    _lng.dispose();
    super.dispose();
  }

  Future<void> _useCurrentLocation() async {
    final center = await ref.read(currentLocationProvider.future);
    _lat.text = center.latitude.toStringAsFixed(6);
    _lng.text = center.longitude.toStringAsFixed(6);
  }

  double? _parseCoord(String raw) => double.tryParse(raw.replaceAll(',', '.'));

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final tokens = ref.read(authTokensProvider);
    if (tokens == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final spot = await ref.read(spotRepositoryProvider).submitSpot(
            name: _name.text.trim(),
            description: _description.text.trim(),
            lat: _parseCoord(_lat.text)!,
            lng: _parseCoord(_lng.text)!,
            difficulty: _difficulty,
            accessToken: tokens.accessToken,
          );
      if (!mounted) return;
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(
          '"${spot.name}" submitted! It will appear on the map once an admin '
          'verifies it.',
        ),
        duration: const Duration(seconds: 5),
      ));
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String? _validateCoord(String? v, double bound) {
    final parsed = v == null ? null : _parseCoord(v);
    if (parsed == null) return 'Enter a number';
    if (parsed < -bound || parsed > bound) return 'Out of range (±$bound)';
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextFormField(
            controller: _name,
            decoration: const InputDecoration(
              labelText: 'Spot name',
              border: OutlineInputBorder(),
            ),
            validator: (v) =>
                (v == null || v.trim().length < 2) ? 'At least 2 characters' : null,
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _description,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Description (optional)',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _lat,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true, signed: true),
                  decoration: const InputDecoration(
                    labelText: 'Latitude',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) => _validateCoord(v, 90),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextFormField(
                  controller: _lng,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true, signed: true),
                  decoration: const InputDecoration(
                    labelText: 'Longitude',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) => _validateCoord(v, 180),
                ),
              ),
            ],
          ),
          TextButton.icon(
            onPressed: _busy ? null : _useCurrentLocation,
            icon: const Icon(Icons.my_location),
            label: const Text('Use my current location'),
          ),
          const SizedBox(height: 4),
          Text('Difficulty: $_difficulty/5',
              style: Theme.of(context).textTheme.labelLarge),
          Slider(
            value: _difficulty.toDouble(),
            min: 1,
            max: 5,
            divisions: 4,
            label: '$_difficulty',
            onChanged: _busy
                ? null
                : (v) => setState(() => _difficulty = v.round()),
          ),
          if (_error != null) ...[
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
            const SizedBox(height: 8),
          ],
          FilledButton.icon(
            onPressed: _busy ? null : _submit,
            icon: _busy
                ? const SizedBox(
                    height: 18, width: 18, child: CircularProgressIndicator())
                : const Icon(Icons.send),
            label: const Text('Submit for review'),
          ),
          const SizedBox(height: 8),
          Text(
            'New spots are reviewed by an admin before going public.',
            style: Theme.of(context).textTheme.bodySmall,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
