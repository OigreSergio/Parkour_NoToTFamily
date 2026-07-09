import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:parkour_notot/main.dart';

void main() {
  testWidgets('app boots into the Map/List shell', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: ParkourApp()));
    await tester.pump();

    // The bottom navigation exposes the two tabs.
    expect(find.text('Map'), findsWidgets);
    expect(find.text('List'), findsWidgets);
  });
}
