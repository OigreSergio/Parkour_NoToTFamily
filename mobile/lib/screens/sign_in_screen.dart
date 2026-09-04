import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';
import '../widgets/stitch_divider.dart';

/// Sign in — with an email, or without one.
///
/// The guest account exists for whoever does not want to hand over an email:
/// it is a choice, not the only door. Anyone registering with an email picks
/// the name they will be known by; the server has the final word on that name
/// (no slurs, no calls to hatred, no pretending to be the staff) and whatever
/// it answers is shown here as it is.
class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key});

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _displayName = TextEditingController();

  bool _registering = true;
  bool _showPassword = false;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _displayName.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    final navigator = Navigator.of(context);
    final controller = ref.read(sessionProvider.notifier);
    final ok = _registering
        ? await controller.registerWithEmail(
            email: _email.text.trim(),
            password: _password.text,
            displayName: _displayName.text.trim(),
          )
        : await controller.signInWithEmail(
            email: _email.text.trim(),
            password: _password.text,
          );

    if (ok && navigator.canPop()) navigator.pop();
  }

  Future<void> _continueAsGuest() async {
    final navigator = Navigator.of(context);
    final ok = await ref.read(sessionProvider.notifier).signInAsGuest();
    if (ok && navigator.canPop()) navigator.pop();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final session = ref.watch(sessionProvider);
    final busy = session.isBusy;

    return Scaffold(
      appBar: AppBar(title: Text(_registering ? 'Join the family' : 'Welcome back')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              _registering
                  ? 'Pick the name the family will see, and an email to get '
                      'back in with.'
                  : 'Sign in with the email you registered.',
              style: theme.textTheme.bodyLarge,
            ),
            const SizedBox(height: 20),

            if (_registering) ...[
              TextFormField(
                controller: _displayName,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(
                  labelText: 'Your name here',
                  hintText: 'How the family will see you',
                  prefixIcon: Icon(Icons.badge_outlined),
                ),
                validator: (value) {
                  final name = (value ?? '').trim();
                  if (name.length < 2) return 'Pick a name of at least 2 letters';
                  if (name.length > 80) return 'That name is a bit long';
                  return null;
                },
              ),
              const SizedBox(height: 6),
              Text(
                'Anything goes, except insults, calls to hatred and passing '
                'yourself off as the staff.',
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.outline),
              ),
              const SizedBox(height: 16),
            ],

            TextFormField(
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              autocorrect: false,
              decoration: const InputDecoration(
                labelText: 'Email',
                prefixIcon: Icon(Icons.alternate_email),
              ),
              validator: (value) {
                final email = (value ?? '').trim();
                final looksLikeEmail =
                    RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email);
                return looksLikeEmail ? null : 'Write a valid email address';
              },
            ),
            const SizedBox(height: 16),

            TextFormField(
              controller: _password,
              obscureText: !_showPassword,
              decoration: InputDecoration(
                labelText: 'Password',
                prefixIcon: const Icon(Icons.lock_outline),
                suffixIcon: IconButton(
                  onPressed: () => setState(() => _showPassword = !_showPassword),
                  icon: Icon(
                    _showPassword ? Icons.visibility_off : Icons.visibility,
                  ),
                  tooltip: _showPassword ? 'Hide password' : 'Show password',
                ),
              ),
              validator: (value) => (value ?? '').length < 8
                  ? 'At least 8 characters'
                  : null,
            ),

            if (session.error != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: theme.colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline,
                        color: theme.colorScheme.onErrorContainer),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        session.error!,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onErrorContainer,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: busy ? null : _submit,
              icon: busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Icon(_registering ? Icons.person_add_alt : Icons.login),
              label: Text(_registering ? 'Create my account' : 'Sign in'),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: busy
                  ? null
                  : () => setState(() => _registering = !_registering),
              child: Text(
                _registering
                    ? 'I already have an account'
                    : 'I am new here, sign me up',
              ),
            ),

            const SizedBox(height: 12),
            const StitchDivider(),
            const SizedBox(height: 12),

            Text(
              'Rather not give an email?',
              textAlign: TextAlign.center,
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(
              'A guest account lets you browse the map and the beginner '
              'tutorials right away. You can register later.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodySmall
                  ?.copyWith(color: theme.colorScheme.outline),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: busy ? null : _continueAsGuest,
              icon: const Icon(Icons.person_outline),
              label: const Text('Continue as a guest'),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
