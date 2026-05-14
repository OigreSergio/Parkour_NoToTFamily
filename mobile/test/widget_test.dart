import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:parkour_notot/main.dart';

void main() {
  testWidgets('app boots to login when unauthenticated', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: ParkourApp()));
    await tester.pump();
    expect(find.text('Log in'), findsWidgets);
  });
}
