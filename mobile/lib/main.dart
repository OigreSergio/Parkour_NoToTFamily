import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'providers.dart';
import 'screens/profile_screen.dart';
import 'screens/safety_gate_screen.dart';
import 'screens/spots_list_screen.dart';
import 'screens/spots_map_screen.dart';
import 'screens/tutorials_screen.dart';
import 'services/supabase_client.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initSupabase();
  runApp(const ProviderScope(child: ParkourApp()));
}

class ParkourApp extends StatelessWidget {
  const ParkourApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PkFAMILY',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.teal,
        brightness: Brightness.dark,
        useMaterial3: true,
      ),
      home:
          SupabaseConfig.isConfigured
              ? const _Root()
              : const _MissingConfigScreen(),
    );
  }
}

/// Decide cosa mostrare all'avvio: il gate di sicurezza, o l'app.
///
/// Apre anche una **sessione anonima** se non ce n'è una. Serve a dare
/// un'identità anche a chi non si registra, perché la presa d'atto del gate
/// possa essere registrata lato server e la policy RESTRICTIVE su `spots`
/// possa applicarla davvero. Senza, per un visitatore anonimo il gate sarebbe
/// un suggerimento aggirabile.
class _Root extends ConsumerStatefulWidget {
  const _Root();

  @override
  ConsumerState<_Root> createState() => _RootState();
}

class _RootState extends ConsumerState<_Root> {
  late final Future<void> _session;

  @override
  void initState() {
    super.initState();
    // Se le sessioni anonime sono disattivate nella dashboard questa fallisce:
    // l'app resta usabile, semplicemente senza spot finché non si fa il login.
    _session = ref
        .read(accountRepositoryProvider)
        .ensureSession()
        .catchError((_) {});
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<void>(
      future: _session,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        final accepted = ref.watch(safetyAcceptedProvider);
        final declined = ref.watch(safetyDeclinedProvider);

        return accepted.when(
          loading:
              () => const Scaffold(
                body: Center(child: CircularProgressIndicator()),
              ),
          // Se non si riesce a sapere se ha accettato, si mostra il gate: nel
          // dubbio non si aprono gli spot.
          error: (_, _) => const SafetyGateScreen(),
          data:
              (accepted) =>
                  (accepted || declined)
                      ? const HomeScreen()
                      : const SafetyGateScreen(),
        );
      },
    );
  }
}

/// La shell: mappa, lista, video, profilo.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;

  static const _titles = ['Mappa', 'Lista', 'Video', 'Profilo'];
  static const _screens = [
    SpotsMapScreen(),
    SpotsListScreen(),
    TutorialsScreen(),
    ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('PkFAMILY · ${_titles[_index]}')),
      body: Column(
        children: [
          const _NoSpotsBanner(),
          Expanded(child: IndexedStack(index: _index, children: _screens)),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.map_outlined),
            selectedIcon: Icon(Icons.map),
            label: 'Mappa',
          ),
          NavigationDestination(
            icon: Icon(Icons.list_outlined),
            selectedIcon: Icon(Icons.list),
            label: 'Lista',
          ),
          NavigationDestination(
            icon: Icon(Icons.menu_book_outlined),
            selectedIcon: Icon(Icons.menu_book),
            label: 'Video',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profilo',
          ),
        ],
      ),
    );
  }
}

/// La striscia per chi sta usando l'app in modalità informativa senza spot.
///
/// Rifiutare il gate non è un vicolo cieco: si resta dentro, con la mappa vuota
/// e un modo sempre visibile per cambiare idea.
class _NoSpotsBanner extends ConsumerWidget {
  const _NoSpotsBanner();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final accepted = ref.watch(safetyAcceptedProvider).value ?? false;
    if (accepted) return const SizedBox.shrink();

    final theme = Theme.of(context);
    return Material(
      color: theme.colorScheme.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 8, 10),
        child: Row(
          children: [
            Expanded(
              child: Text(
                'Mappa senza spot. I video restano completi.',
                style: theme.textTheme.bodySmall,
              ),
            ),
            TextButton(
              onPressed:
                  () => ref.read(safetyDeclinedProvider.notifier).state = false,
              child: const Text('Rivedi l\'avviso'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Mostrata quando il build è partito senza le variabili Supabase.
///
/// Meglio dire cosa manca che lasciare l'utente davanti a una mappa vuota e
/// una pila di errori di rete in console.
class _MissingConfigScreen extends StatelessWidget {
  const _MissingConfigScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.settings_ethernet, size: 48),
              const SizedBox(height: 16),
              Text(
                SupabaseConfig.missingConfigMessage,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
