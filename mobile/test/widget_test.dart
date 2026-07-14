import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:parkour_notot/main.dart';

void main() {
  testWidgets('app boots into the Map/List/Profile shell', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: ParkourApp()));
    await tester.pump();

    // The bottom navigation exposes the three tabs.
    expect(find.text('Map'), findsWidgets);
    expect(find.text('List'), findsWidgets);
    expect(find.text('Profile'), findsWidgets);
  });
}
