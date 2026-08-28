import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:parkour_notot/screens/legal_screen.dart';

/// I testi legali sono codice come il resto: se si rompono, si rompono in
/// silenzio e ce ne accorgiamo quando serve.
///
/// Questi controlli non dicono se i testi sono *giusti* — quello lo dirà un
/// legale (`docs/OPS_TODO.md`). Dicono che ci sono, che sono raggiungibili e
/// che nessuno ci ha rimesso dentro le formule nulle che abbiamo tolto apposta.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  String read(LegalDocument doc) => File(doc.assetPath).readAsStringSync();

  test('ogni documento dichiarato esiste davvero', () {
    for (final doc in LegalDocument.values) {
      final file = File(doc.assetPath);
      expect(
        file.existsSync(),
        isTrue,
        reason:
            '${doc.assetPath} non esiste: la voce «${doc.title}» porterebbe a '
            'una schermata di errore.',
      );
      // Un file da due righe è un file dimenticato a metà.
      expect(file.lengthSync(), greaterThan(1000), reason: doc.assetPath);
    }
  });

  test('ogni documento è datato e versionato', () {
    for (final doc in LegalDocument.values) {
      final testo = read(doc);
      expect(testo, startsWith('# '), reason: doc.assetPath);
      expect(
        testo,
        contains('versione'),
        reason:
            '${doc.assetPath} non dichiara una versione: senza, non si può '
            'dire a un utente quale testo ha accettato.',
      );
    }
  });

  test('nessun documento contiene clausole nulle', () {
    // Verso un consumatore, la clausola che limita la responsabilità per danni
    // alla persona è inefficace (artt. 33 e 36 Cod. Consumo), e per dolo o
    // colpa grave è nulla in ogni caso (art. 1229 c.c.). Scriverla non protegge
    // nessuno: segnala solo che chi l'ha scritta si credeva coperto.
    //
    // «esonera» compare deliberatamente nei Termini, ma solo per dire che NON
    // la stiamo chiedendo: il controllo è quindi sulle formule d'esonero vere e
    // proprie, non sulla parola isolata.
    const vietate = [
      'esonera pkfamily',
      'esonera il titolare',
      'declina ogni responsabilità',
      'manleva',
      'manlevare',
      'rinuncia a ogni',
      'rinuncia a qualsiasi',
      'in nessun caso saremo responsabili',
      'nessuna responsabilità potrà essere',
    ];

    for (final doc in LegalDocument.values) {
      final testo = read(doc).toLowerCase();
      for (final formula in vietate) {
        expect(
          testo,
          isNot(contains(formula)),
          reason:
              '${doc.assetPath} contiene «$formula», che è una clausola nulla.',
        );
      }
    }
  });

  test('nessun documento promette cose che non facciamo', () {
    // La chat non è cifrata end-to-end e l'informativa lo dice. Se un domani
    // qualcuno scrivesse il contrario in un altro documento, sarebbe una
    // dichiarazione falsa in un testo che l'utente ha diritto di credere.
    for (final doc in LegalDocument.values) {
      final testo = read(doc).toLowerCase();
      if (testo.contains('end-to-end')) {
        expect(
          testo,
          anyOf(contains('non è cifrata'), contains('non la facciamo')),
          reason:
              '${doc.assetPath} nomina la cifratura end-to-end senza dire che '
              'non c\'è.',
        );
      }
      // Nessuno certifica la conformità al GDPR, e non esiste un bollino da
      // esibire. «Gli spot non sono certificati» è invece vero e resta.
      expect(testo, isNot(contains('conforme al gdpr')));
      expect(testo, isNot(contains('certificazione gdpr')));
      expect(testo, isNot(contains('siamo certificat')));
    }
  });

  test('l\'informativa copre quello che l\'art. 13 richiede', () {
    final testo = read(LegalDocument.privacy).toLowerCase();

    for (final atteso in [
      'titolare', // chi tratta
      'base giuridica', // art. 13.1.c
      'art. 6.1.b',
      'art. 6.1.f',
      'quanto teniamo', // art. 13.2.a, conservazione
      'i tuoi diritti', // artt. 15-22
      'garante', // art. 13.2.d, reclamo
      'privacy@pkfamily.app', // recapito
      'supabase', // destinatari
      'clausole contrattuali standard', // trasferimenti extra-UE
    ]) {
      expect(testo, contains(atteso), reason: 'manca «$atteso»');
    }

    // Le tre cose che nessun modello scriverebbe, e che qui sono vere.
    expect(testo, contains('non la conserviamo'), reason: 'geolocalizzazione');
    expect(testo, contains('non è cifrata end-to-end'));
    expect(testo, contains('sessione anonima'));
  });

  test('i Termini dicono le cose che devono dire', () {
    final testo = read(LegalDocument.termini).toLowerCase();

    for (final atteso in [
      'gratuito',
      '16 anni', // età minima
      'genitore', // account supervisionato
      'non organizziamo', // servizio informativo, non organizzativo
      'non sono ispezionati',
      'proprietà privata',
      'art. 1229', // il limite dichiarato, non aggirato
      'legge italiana',
      'abuse@pkfamily.app', // punto di contatto DSA
    ]) {
      expect(testo, contains(atteso), reason: 'manca «$atteso»');
    }

    // Foro del consumatore: la clausola di foro esclusivo del fornitore sarebbe
    // vessatoria, e qui è scritto il contrario.
    expect(testo, contains('in cui risiedi'));
  });

  test('la cookie policy non promette un banner che non c\'è', () {
    final testo = read(LegalDocument.cookie).toLowerCase();
    expect(testo, contains('non usa cookie di profilazione'));
    expect(testo, contains('sessione'));
    // Se un domani entrasse Analytics, questo test va aggiornato prima —
    // che è esattamente il punto.
    expect(testo, isNot(contains('google analytics attivo')));
  });

  test('le note legali identificano il titolare come chiede il d.lgs. 70/2003', () {
    final testo = read(LegalDocument.noteLegali);
    expect(testo.toLowerCase(), contains('d.lgs. 70/2003'));
    expect(testo, contains('@pkfamily.app'));

    // Il nome del titolare è ancora un segnaposto. Il test non fallisce — il
    // testo è in bozza — ma lo dice forte, così non si arriva alla
    // pubblicazione con una parentesi quadra nell'imprint.
    if (testo.contains('[nome e cognome')) {
      // ignore: avoid_print
      print(
        'ATTENZIONE: note-legali.md contiene ancora il segnaposto del nome del '
        'titolare. Va completato prima della pubblicazione (docs/OPS_TODO.md).',
      );
    }
  });

  test('i sub-responsabili elencano chi tocca davvero i dati', () {
    final testo = read(LegalDocument.subResponsabili).toLowerCase();
    for (final atteso in ['supabase', 'cloudflare', 'github', 'francoforte']) {
      expect(testo, contains(atteso), reason: 'manca «$atteso»');
    }
  });

  test('i documenti sono dichiarati fra gli asset', () {
    final pubspec = File('pubspec.yaml').readAsStringSync();
    expect(
      pubspec,
      contains('assets/legal/'),
      reason:
          'senza la dichiarazione in pubspec.yaml i testi non finiscono nel '
          'bundle e le pagine legali sono vuote in produzione.',
    );
  });
}
