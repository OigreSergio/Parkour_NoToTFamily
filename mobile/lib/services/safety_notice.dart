import 'dart:convert';

import 'package:crypto/crypto.dart' as crypto;
import 'package:flutter/services.dart' show rootBundle;

/// L'avviso di sicurezza mostrato prima che la mappa apra un solo spot.
///
/// Il testo vive in `assets/legal/`, versionato nel repo. L'hash **si calcola a
/// runtime dal file effettivamente caricato**, non è una costante scritta a
/// mano: così quello che finisce in `safety_acknowledgements.text_sha256` è per
/// costruzione l'impronta del testo che l'utente ha davvero visto. Una costante
/// potrebbe restare indietro rispetto al file, e a quel punto la registrazione
/// proverebbe la cosa sbagliata.
///
/// Quando il testo cambia: nuovo file `safety_notice_<versione>.md`,
/// [currentVersion] aggiornata qui, e una migration che ridefinisce
/// `current_safety_notice_version()`. Il gate ricompare a tutti.
class SafetyNotice {
  const SafetyNotice._({
    required this.version,
    required this.text,
    required this.sha256,
  });

  /// Deve combaciare con `current_safety_notice_version()` lato database.
  static const String currentVersion = 'v1';

  static const String assetPath =
      'assets/legal/safety_notice_$currentVersion.md';

  final String version;
  final String text;

  /// Impronta del testo esatto mostrato, in esadecimale minuscolo.
  final String sha256;

  static SafetyNotice? _cached;

  static Future<SafetyNotice> load() async {
    final cached = _cached;
    if (cached != null) return cached;

    final text = await rootBundle.loadString(assetPath);
    // Le stesse identiche bytes che il database registrerà: UTF-8, senza
    // normalizzazioni. Se il file cambia di un carattere, cambia l'hash.
    final digest = crypto.sha256.convert(utf8.encode(text));

    return _cached = SafetyNotice._(
      version: currentVersion,
      text: text,
      sha256: digest.toString(),
    );
  }

  /// Solo per i test: svuota la cache tra un caso e l'altro.
  static void resetCacheForTest() => _cached = null;
}
