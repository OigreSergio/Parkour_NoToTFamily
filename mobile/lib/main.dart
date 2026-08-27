import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
              ? const HomeScreen()
              : const _MissingConfigScreen(),
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

  static const _titles = ['Mappa', 'Lista', 'Video'];
  static const _screens = [
    SpotsMapScreen(),
    SpotsListScreen(),
    TutorialsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('PkFAMILY · ${_titles[_index]}')),
      body: IndexedStack(index: _index, children: _screens),
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
        ],
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
