import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/onboarding.dart';
import '../providers.dart';
import '../services/api_client.dart';
import '../widgets/error_view.dart';
import '../widgets/risk_notice.dart';

/// The questions asked after signing in, in the order the server decides.
///
/// The screen never works out what comes next: it draws `state.nextStep`, posts
/// the answer, and draws whatever comes back. An anonymous account walks the
/// same path as a registered one, minus the athlete/instructor question — the
/// server simply never sends that step to a guest.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  OnboardingState? _state;
  Object? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _error = null;
      _busy = true;
    });
    try {
      _apply(await ref.read(onboardingRepositoryProvider).state());
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _apply(OnboardingState next) {
    if (!mounted) return;
    setState(() => _state = next);
    ref.read(authControllerProvider.notifier).updateStep(next.nextStep);
  }

  /// Run [action], showing the reason on screen if the backend refuses.
  Future<void> _submit(Future<OnboardingState> Function() action) async {
    setState(() => _busy = true);
    try {
      _apply(await action());
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.detail ?? 'Non è andata. Riprova.')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _askBirthDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime(now.year - 20, now.month, now.day),
      firstDate: DateTime(now.year - 100),
      lastDate: now,
      helpText: 'Quando sei nato?',
    );
    if (picked == null || !mounted) return;

    // Under 18 the backend refuses the call without the guardian consent, so
    // it is asked here — the app already knows the date it just collected.
    final notices = <dynamic>[];
    if (_ageOn(picked, now) < 18) {
      final consent = await requestRiskNotice(
        context,
        ref,
        minorGuardianNoticeId,
        remember: false,
      );
      if (consent == null) return;
      notices.add(consent);
    }
    await _submit(
      () => ref.read(onboardingRepositoryProvider).setBirthDate(
            picked,
            accepted: notices.cast(),
          ),
    );
  }

  static int _ageOn(DateTime birthDate, DateTime today) {
    var years = today.year - birthDate.year;
    if (today.month < birthDate.month ||
        (today.month == birthDate.month && today.day < birthDate.day)) {
      years -= 1;
    }
    return years;
  }

  @override
  Widget build(BuildContext context) {
    final error = _error;
    if (error != null) {
      return Scaffold(
        body: SafeArea(child: ErrorView(message: '$error', onRetry: _load)),
      );
    }

    final state = _state;
    if (state == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Due domande')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: _body(state),
        ),
      ),
    );
  }

  Widget _body(OnboardingState state) {
    switch (state.nextStep) {
      case OnboardingStep.birthDate:
        return _Step(
          title: 'Quando sei nato?',
          summary: 'Serve a proporti esercizi adatti. Resta sul server: non '
              'viene mostrato a nessuno, nemmeno a te.',
          child: FilledButton(
            onPressed: _busy ? null : _askBirthDate,
            child: const Text('Scegli la data'),
          ),
        );

      case OnboardingStep.practitionerType:
        return _Step(
          title: 'Come ti muovi qui dentro?',
          summary: '',
          child: _Choices(
            options: state.practitionerOptions,
            busy: _busy,
            onPick: (value) => _submit(
              () => ref
                  .read(onboardingRepositoryProvider)
                  .setPractitionerType(value),
            ),
          ),
        );

      case OnboardingStep.experience:
        return _Step(
          title: 'Da quanto pratichi parkour?',
          summary: 'Da qui dipendono i livelli che ti proponiamo. Il gioco '
              'dopo serve a tararli.',
          child: _Choices(
            options: state.experienceOptions,
            busy: _busy,
            onPick: (value) => _submit(
              () => ref.read(onboardingRepositoryProvider).setExperience(value),
            ),
          ),
        );

      case OnboardingStep.experienceQuiz:
        return _QuizStep(onDone: _load);

      case OnboardingStep.instructorCertificate:
        // Two file uploads and an identity document: it belongs on a screen
        // with a real file picker, not on a stub that looks like it works.
        return const _Step(
          title: 'Il tuo certificato',
          summary: 'La verifica come istruttore si completa dal sito: servono '
              'il certificato dell’ente e un documento d’identità.',
          child: SizedBox.shrink(),
        );

      default:
        return const _Step(
          title: 'Fatto.',
          summary: 'Da qui in poi la mappa e i tutorial sono tarati su di te.',
          child: SizedBox.shrink(),
        );
    }
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.title, required this.summary, required this.child});

  final String title;
  final String summary;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListView(
      children: [
        Text(title, style: theme.textTheme.headlineSmall),
        if (summary.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(summary, style: theme.textTheme.bodyMedium),
        ],
        const SizedBox(height: 24),
        child,
      ],
    );
  }
}

/// Buttons for the options the server sent, in the order it sent them.
class _Choices extends StatelessWidget {
  const _Choices({
    required this.options,
    required this.onPick,
    required this.busy,
  });

  final List<OnboardingOption> options;
  final void Function(String value) onPick;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final option in options)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: busy ? null : () => onPick(option.value),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(option.label),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

/// The vault-naming game.
class _QuizStep extends ConsumerStatefulWidget {
  const _QuizStep({required this.onDone});

  final Future<void> Function() onDone;

  @override
  ConsumerState<_QuizStep> createState() => _QuizStepState();
}

class _QuizStepState extends ConsumerState<_QuizStep> {
  Quiz? _quiz;
  QuizResult? _result;
  List<int?> _answers = const [];
  int _index = 0;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _deal();
  }

  Future<void> _deal() async {
    setState(() {
      _error = null;
      _result = null;
    });
    try {
      final quiz = await ref.read(onboardingRepositoryProvider).startQuiz();
      if (!mounted) return;
      setState(() {
        _quiz = quiz;
        _answers = List<int?>.filled(quiz.questions.length, null);
        _index = 0;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error);
    }
  }

  Future<void> _answer(int option) async {
    final quiz = _quiz;
    if (quiz == null) return;
    setState(() => _answers[_index] = option);
    if (_index < quiz.questions.length - 1) {
      setState(() => _index += 1);
      return;
    }
    try {
      final result = await ref
          .read(onboardingRepositoryProvider)
          .submitQuiz(quiz.attemptId, _answers);
      if (mounted) setState(() => _result = result);
    } catch (error) {
      if (mounted) setState(() => _error = error);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final error = _error;
    if (error != null) return ErrorView(message: '$error', onRetry: _deal);

    final result = _result;
    if (result != null) {
      return ListView(
        children: [
          Text('${result.score} su ${result.total}',
              style: theme.textTheme.labelLarge),
          const SizedBox(height: 4),
          Text(result.passed ? 'Ci siamo.' : 'Ci sta.',
              style: theme.textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(result.message, style: theme.textTheme.bodyMedium),
          const SizedBox(height: 20),
          // Le correzioni si vedono sempre: chi sbaglia esce sapendo i nomi,
          // che è metà del motivo per cui il gioco esiste.
          for (final c in result.corrections)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: Icon(
                c.isCorrect ? Icons.check : Icons.close,
                color: c.isCorrect ? Colors.green : Colors.redAccent,
              ),
              title: Text(c.correctAnswer),
              subtitle: c.isCorrect
                  ? null
                  : Text(c.givenAnswer == null
                      ? 'saltata'
                      : 'avevi detto ${c.givenAnswer}'),
            ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: () => widget.onDone(),
            child: const Text('Continua'),
          ),
          TextButton(onPressed: _deal, child: const Text('Rigioca')),
        ],
      );
    }

    final quiz = _quiz;
    if (quiz == null) {
      return const Center(child: CircularProgressIndicator());
    }

    final question = quiz.questions[_index];
    return ListView(
      children: [
        Text('Movimento ${_index + 1} di ${quiz.questions.length}',
            style: theme.textTheme.labelLarge),
        const SizedBox(height: 4),
        Text(quiz.title, style: theme.textTheme.headlineSmall),
        if (_index == 0) ...[
          const SizedBox(height: 8),
          Text(quiz.intro, style: theme.textTheme.bodyMedium),
        ],
        const SizedBox(height: 20),
        Text(question.clue, style: theme.textTheme.bodyLarge),
        const SizedBox(height: 20),
        for (var i = 0; i < question.options.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: () => _answer(i),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(question.options[i]),
                  ),
                ),
              ),
            ),
          ),
        if (_index > 0)
          TextButton(
            onPressed: () => setState(() => _index -= 1),
            child: const Text('Indietro'),
          ),
      ],
    );
  }
}
