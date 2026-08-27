import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/profile.dart';
import '../../providers.dart';
import 'parent_access_screen.dart';

/// Registrazione, con il controllo di età davanti a tutto.
///
/// Chi ha meno di 16 anni non trova un muro: trova la strada dell'accesso
/// tramite genitore ([ParentAccessScreen]).
class SignUpScreen extends ConsumerStatefulWidget {
  const SignUpScreen({super.key});

  @override
  ConsumerState<SignUpScreen> createState() => _SignUpScreenState();
}

class _SignUpScreenState extends ConsumerState<SignUpScreen> {
  final _form = GlobalKey<FormState>();
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();

  DateTime? _birthDate;
  bool _acceptedTerms = false;
  bool _readPrivacy = false;
  bool _busy = false;
  String? _error;
  bool _done = false;

  @override
  void dispose() {
    _username.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _pickBirthDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime(now.year - AgeCheck.minimumAge, now.month, now.day),
      firstDate: DateTime(now.year - 100),
      lastDate: now,
      helpText: 'Data di nascita',
    );
    if (picked != null) setState(() => _birthDate = picked);
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;

    final check = AgeCheck.of(_birthDate);
    if (check == AgeCheck.invalid) {
      setState(() => _error = 'Inserisci la tua data di nascita.');
      return;
    }
    if (check == AgeCheck.tooYoung) {
      if (!mounted) return;
      Navigator.of(context).push(
        MaterialPageRoute<void>(builder: (_) => const ParentAccessScreen()),
      );
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(accountRepositoryProvider)
          .signUp(
            email: _email.text.trim(),
            password: _password.text,
            username: _username.text.trim(),
            birthDate: _birthDate!,
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
    if (_done) return const _CheckYourInbox();

    final theme = Theme.of(context);
    final canSubmit = _acceptedTerms && _readPrivacy && !_busy;

    return Scaffold(
      appBar: AppBar(title: const Text('Crea un account')),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            TextFormField(
              controller: _username,
              decoration: const InputDecoration(labelText: 'Come ti chiamano'),
              textInputAction: TextInputAction.next,
              validator:
                  (v) =>
                      (v == null || v.trim().length < 2)
                          ? 'Almeno due caratteri.'
                          : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _email,
              decoration: const InputDecoration(labelText: 'Email'),
              keyboardType: TextInputType.emailAddress,
              autocorrect: false,
              textInputAction: TextInputAction.next,
              validator:
                  (v) =>
                      (v == null || !v.contains('@'))
                          ? 'Serve un indirizzo email valido.'
                          : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _password,
              decoration: const InputDecoration(
                labelText: 'Password',
                helperText: 'Almeno 12 caratteri.',
              ),
              obscureText: true,
              validator:
                  (v) =>
                      (v == null || v.length < 12)
                          ? 'Almeno 12 caratteri: è la soglia sotto cui una password '
                              'non protegge granché.'
                          : null,
            ),
            const SizedBox(height: 24),

            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.cake_outlined),
              title: const Text('Data di nascita'),
              subtitle: Text(
                _birthDate == null
                    ? 'Serve solo a verificare la soglia dei ${AgeCheck.minimumAge} anni: '
                        'non viene conservata.'
                    : '${_birthDate!.day}/${_birthDate!.month}/${_birthDate!.year}',
              ),
              trailing: const Icon(Icons.edit_calendar_outlined),
              onTap: _pickBirthDate,
            ),

            const SizedBox(height: 8),
            // Caselle separate e non pre-spuntate: un consenso raggruppato o
            // già dato non è un consenso.
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: _acceptedTerms,
              onChanged: (v) => setState(() => _acceptedTerms = v ?? false),
              title: const Text('Accetto i Termini di servizio'),
            ),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: _readPrivacy,
              onChanged: (v) => setState(() => _readPrivacy = v ?? false),
              title: const Text('Ho letto l\'informativa privacy'),
            ),

            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
            ],

            const SizedBox(height: 16),
            FilledButton(
              onPressed: canSubmit ? _submit : null,
              child: Text(_busy ? 'Un momento…' : 'Crea l\'account'),
            ),
            const SizedBox(height: 12),
            TextButton(
              onPressed:
                  () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const ParentAccessScreen(),
                    ),
                  ),
              child: Text('Ho meno di ${AgeCheck.minimumAge} anni'),
            ),
          ],
        ),
      ),
    );
  }
}

class _CheckYourInbox extends StatelessWidget {
  const _CheckYourInbox();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Quasi fatto')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.mark_email_unread_outlined, size: 48),
              const SizedBox(height: 16),
              Text(
                'Ti abbiamo mandato un\'email di conferma. Aprila e sei dentro.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 12),
              Text(
                'La conferma serve a impedire che qualcuno si iscriva con un '
                'indirizzo che non è suo.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
