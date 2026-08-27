import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers.dart';
import 'sign_up_screen.dart';

class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key});

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  String? _error;
  String? _notice;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action, {String? onDone}) async {
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      await action();
      if (mounted && onDone != null) setState(() => _notice = onDone);
    } catch (err) {
      setState(() => _error = '$err');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final account = ref.read(accountRepositoryProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Entra')),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            TextFormField(
              controller: _email,
              decoration: const InputDecoration(labelText: 'Email'),
              keyboardType: TextInputType.emailAddress,
              autocorrect: false,
              validator:
                  (v) =>
                      (v == null || !v.contains('@'))
                          ? 'Email non valida.'
                          : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _password,
              decoration: const InputDecoration(labelText: 'Password'),
              obscureText: true,
              validator:
                  (v) =>
                      (v == null || v.isEmpty)
                          ? 'Inserisci la password.'
                          : null,
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
            ],
            if (_notice != null) ...[
              const SizedBox(height: 12),
              Text(_notice!, style: theme.textTheme.bodySmall),
            ],
            const SizedBox(height: 20),
            FilledButton(
              onPressed:
                  _busy
                      ? null
                      : () {
                        if (!_form.currentState!.validate()) return;
                        _run(
                          () => account.signIn(
                            email: _email.text.trim(),
                            password: _password.text,
                          ),
                        );
                      },
              child: Text(_busy ? 'Un momento…' : 'Entra'),
            ),
            TextButton(
              onPressed:
                  _busy
                      ? null
                      : () {
                        final email = _email.text.trim();
                        if (!email.contains('@')) {
                          setState(
                            () =>
                                _error =
                                    'Scrivi la tua email qui sopra, poi riprova.',
                          );
                          return;
                        }
                        _run(
                          () => account.sendPasswordReset(email),
                          // Nessuna conferma che l'indirizzo esista: rivelarlo
                          // permetterebbe di sapere chi è iscritto.
                          onDone:
                              'Se quell\'indirizzo è registrato, riceverà le '
                              'istruzioni per reimpostare la password.',
                        );
                      },
              child: const Text('Password dimenticata'),
            ),
            const Divider(height: 40),
            OutlinedButton(
              onPressed:
                  () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const SignUpScreen(),
                    ),
                  ),
              child: const Text('Non ho un account'),
            ),
          ],
        ),
      ),
    );
  }
}
