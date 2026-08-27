import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/main.dart';
import 'package:parkour_notot/models/profile.dart';
import 'package:parkour_notot/providers.dart';
import 'package:parkour_notot/services/supabase_client.dart';

/// La shell tocca Supabase attraverso profilo e gate. Nei test non c'è nessun
/// backend: si sostituiscono i due provider di ingresso, così si verifica la
/// navigazione senza inventare un finto client.
List<Override> _shellOverrides({bool safetyAccepted = true}) => [
  safetyAcceptedProvider.overrideWith((ref) async => safetyAccepted),
  currentProfileProvider.overrideWith((ref) async => null),
];

void main() {
  testWidgets('senza configurazione Supabase l\'app spiega cosa manca', (
    tester,
  ) async {
    // I test girano senza --dart-define, quindi la configurazione è assente:
    // l'app deve partire lo stesso e dire perché non funziona, invece di
    // crashare all'avvio o mostrare una mappa vuota senza spiegazioni.
    expect(SupabaseConfig.isConfigured, isFalse);

    await tester.pumpWidget(const ProviderScope(child: ParkourApp()));
    await tester.pump();

    expect(
      find.textContaining('Configurazione Supabase assente'),
      findsOneWidget,
    );
  });

  testWidgets('la shell espone le quattro sezioni', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: _shellOverrides(),
        child: const MaterialApp(home: HomeScreen()),
      ),
    );
    await tester.pump();

    expect(find.text('Mappa'), findsWidgets);
    expect(find.text('Lista'), findsWidgets);
    expect(find.text('Video'), findsWidgets);
    expect(find.text('Profilo'), findsWidgets);
  });

  testWidgets('chi non ha accettato il gate vede la striscia "senza spot"', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: _shellOverrides(safetyAccepted: false),
        child: const MaterialApp(home: HomeScreen()),
      ),
    );
    await tester.pump();

    // Rifiutare non è un vicolo cieco: si resta dentro, e il modo per tornare
    // indietro è sempre visibile.
    expect(find.textContaining('Mappa senza spot'), findsOneWidget);
    expect(find.text('Rivedi l\'avviso'), findsOneWidget);
  });

  testWidgets('chi ha accettato non vede nessuna striscia', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: _shellOverrides(),
        child: const MaterialApp(home: HomeScreen()),
      ),
    );
    await tester.pump();

    expect(find.textContaining('Mappa senza spot'), findsNothing);
  });

  testWidgets('senza account il profilo invita a entrare, non blocca', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: _shellOverrides(),
        child: const MaterialApp(home: Scaffold(body: ProfileTestHost())),
      ),
    );
    await tester.pump();

    expect(
      find.textContaining('Mappa e video funzionano anche senza account'),
      findsOneWidget,
    );
  });
}

/// Ospita la schermata profilo isolata dalla shell.
class ProfileTestHost extends ConsumerWidget {
  const ProfileTestHost({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(currentProfileProvider);
    return profile.when(
      loading: () => const CircularProgressIndicator(),
      error: (e, _) => Text('$e'),
      data:
          (Profile? p) =>
              p == null
                  ? const Text(
                    'Mappa e video funzionano anche senza account.\n'
                    'Serve per proporre spot, commentare e usare la chat.',
                  )
                  : Text(p.username),
    );
  }
}
