import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/main.dart';
import 'package:parkour_notot/services/supabase_client.dart';

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

  testWidgets('la shell espone le tre sezioni', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: MaterialApp(home: HomeScreen())),
    );
    await tester.pump();

    expect(find.text('Mappa'), findsWidgets);
    expect(find.text('Lista'), findsWidgets);
    expect(find.text('Video'), findsWidgets);
  });
}
