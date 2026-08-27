import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart' as crypto;
import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/services/safety_notice.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(SafetyNotice.resetCacheForTest);

  test('l\'hash registrato è quello del testo davvero mostrato', () async {
    final notice = await SafetyNotice.load();

    final bytes = File(SafetyNotice.assetPath).readAsBytesSync();
    final atteso = crypto.sha256.convert(bytes).toString();

    // È il punto di tutto il meccanismo: se questi due divergono, la
    // registrazione della presa d'atto proverebbe un testo diverso da quello
    // che l'utente ha letto.
    expect(notice.sha256, atteso);
    expect(notice.version, SafetyNotice.currentVersion);
  });

  test('la versione del client combacia con quella della migration', () {
    // `current_safety_notice_version()` in 0005_account_safety_gate.sql.
    // Se cambiano di versione separatamente, il gate non ricompare mai oppure
    // ricompare sempre.
    final sql =
        File(
          '../supabase/migrations/0005_account_safety_gate.sql',
        ).readAsStringSync();

    expect(
      sql,
      contains("select '${SafetyNotice.currentVersion}'::text"),
      reason:
          'La versione dichiarata dal client (${SafetyNotice.currentVersion}) '
          'non è quella che il database considera corrente.',
    );
  });

  test('il testo dice le cose che deve dire', () async {
    final notice = await SafetyNotice.load();
    final testo = notice.text.toLowerCase();

    // Qualificazione del servizio come informativo e non organizzativo: è la
    // distinzione che pesa di più, molto più del disclaimer in sé.
    expect(testo, contains('non organizziamo'));
    expect(testo, contains('non sono ispezionati'));
    expect(testo, contains('proprietà privata'));
    expect(testo, contains('assumerti'));

    // E soprattutto ciò che NON deve dire: verso un consumatore una clausola
    // che esclude la responsabilità per danni alla persona è nulla, e una
    // clausola nulla non protegge — segnala solo che chi l'ha scritta si
    // credeva coperto.
    expect(testo, isNot(contains('esonera')));
    expect(testo, isNot(contains('manleva')));
    expect(testo, isNot(contains('rinuncia a ogni')));
    expect(testo, isNot(contains('declina ogni responsabilità')));
  });

  test('l\'hash cambia se cambia una virgola', () {
    final a = crypto.sha256.convert(utf8.encode('Testo A')).toString();
    final b = crypto.sha256.convert(utf8.encode('Testo A.')).toString();
    expect(a, isNot(b));
  });
}
