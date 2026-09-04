import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'providers.dart';
import 'theme/pk_theme.dart';
import 'screens/spots_list_screen.dart';
import 'screens/spots_map_screen.dart';
import 'screens/submit_spot_screen.dart';
import 'screens/tutorials_screen.dart';
import 'widgets/account_menu.dart';

void main() {
  runApp(const ProviderScope(child: ParkourApp()));
}

class ParkourApp extends ConsumerWidget {
  const ParkourApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Light / dark / system comes from the settings screen.
    final themeMode = ref.watch(settingsProvider.select((s) => s.themeMode));

    return MaterialApp(
      title: 'Parkour NoToT Family',
      debugShowCheckedModeBanner: false,
      theme: PkTheme.light(),
      darkTheme: PkTheme.dark(),
      themeMode: themeMode,
      home: const HomeScreen(),
    );
  }
}

/// Root shell with three tabs: Map, List and Tutorials.
///
/// The app bar carries the account menu, from which the member reaches the
/// settings or logs out.
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
      appBar: AppBar(
        title: Text('Parkour NoToT · ${_titles[_index]}'),
        actions: const [AccountMenuButton()],
      ),
      body: IndexedStack(index: _index, children: _screens),
      // Reporting a spot belongs to the map and the list, not to the tutorials.
      floatingActionButton: _index == 2
          ? null
          : FloatingActionButton.extended(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const SubmitSpotScreen(),
                ),
              ),
              icon: const Icon(Icons.add_location_alt_outlined),
              label: const Text('Add spot'),
            ),
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
