import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'models/onboarding.dart';
import 'providers.dart';
import 'screens/onboarding_screen.dart';
import 'screens/spots_list_screen.dart';
import 'screens/spots_map_screen.dart';
import 'screens/tutorials_screen.dart';
import 'screens/welcome_screen.dart';
import 'widgets/error_view.dart';

void main() {
  runApp(const ProviderScope(child: ParkourApp()));
}

class ParkourApp extends StatelessWidget {
  const ParkourApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Parkour NoToT Family',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.teal,
        useMaterial3: true,
      ),
      home: const _AuthGate(),
    );
  }
}

/// Decides what the app opens on.
///
/// On a cold start the answer is in the keychain, not in memory: an anonymous
/// account is resumed with its stored key before anything is drawn, so a guest
/// is not asked to sign in again every time. Only once that has failed does the
/// welcome screen appear.
class _AuthGate extends ConsumerWidget {
  const _AuthGate();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ref.watch(authControllerProvider).when(
          loading: () => const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          ),
          error: (error, _) => Scaffold(
            body: SafeArea(
              child: ErrorView(
                message: '\$error',
                onRetry: () => ref.read(authControllerProvider.notifier).restore(),
              ),
            ),
          ),
          data: (session) {
            if (session == null) return const WelcomeScreen();
            // The questions are not a wizard the app can skip: until the
            // server says `done`, they are the app.
            if (session.nextStep != OnboardingStep.done) {
              return const OnboardingScreen();
            }
            return const HomeScreen();
          },
        );
  }
}

/// Root shell with three tabs: Map, List and Tutorials.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;

  static const _titles = ['Map', 'List', 'Tutorials'];
  static const _screens = [
    SpotsMapScreen(),
    SpotsListScreen(),
    TutorialsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Parkour NoToT · ${_titles[_index]}')),
      body: IndexedStack(index: _index, children: _screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.map_outlined),
            selectedIcon: Icon(Icons.map),
            label: 'Map',
          ),
          NavigationDestination(
            icon: Icon(Icons.list_outlined),
            selectedIcon: Icon(Icons.list),
            label: 'List',
          ),
          NavigationDestination(
            icon: Icon(Icons.menu_book_outlined),
            selectedIcon: Icon(Icons.menu_book),
            label: 'Tutorials',
          ),
        ],
      ),
    );
  }
}
