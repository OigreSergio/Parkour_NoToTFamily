/* PkFAMILY — i dati che l'app porta con sé.
 *
 * Tre file generati da `app/tools/build_data.py` dalle fonti del repository:
 * gli spot (26 verificati dalla famiglia, il resto importato e marcato
 * `community`), le fontanelle vicine a ciascuno e il catalogo dei tutorial.
 * Vengono letti una volta all'avvio e restano in memoria: 1.706 spot sono
 * pochi da scorrere e permettono di cercare senza rete e senza attese.
 *
 * Gli spot `community` non sono verificati da nessuno: la mappa e la lista lo
 * dicono sempre, e non diventano verificati da soli (principio 2).
 *
 * Quando la modalità sviluppatore è accesa, quello che l'app mostra è il file
 * più le modifiche locali di chi sta lavorando: vedi `riapplica()`.
 *
 * Nella demo da computer c'è anche un motore in Python (`CONFIG.motore`): le
 * domande pesanti — chi è nel riquadro, chi corrisponde a una ricerca — vanno
 * a lui. Se non risponde, o se ci sono modifiche locali che lui non conosce,
 * si torna a rispondere qui: l'app deve funzionare comunque.
 */

import * as admin from './admin.js';
import * as motore from './motore.js';

const DATI = {
  /** Gli spot come stanno nel file: non si toccano mai. */
  base: [],
  /** Gli spot come li vede l'app: base più le modifiche locali, se ce ne sono. */
  spot: [],
  perId: new Map(),
  /** I tutorial come stanno nel file, e come li vede l'app. Due liste, non una:
   *  sovrapporre le modifiche su quella già sovrapposta vorrebbe dire non poter
   *  più far tornare indietro un tutorial cancellato. */
  baseTutorial: [],
  tutorial: [],
  fontanelle: null,
  fontanelleUniche: null,
  verificati: 0,
};

/**
 * Le collezioni che il pannello sviluppatore sa mostrare e correggere.
 *
 * Le registra questo modulo perché è l'unico che sa dove stanno i dati: così
 * `admin.js` non importa `data.js`, e il verso delle dipendenze resta uno solo
 * — un ciclo fermerebbe la costruzione della demo in un file solo.
 *
 * `base` è una funzione e non una lista: alla registrazione i dati non sono
 * ancora stati letti (`admin.inizializza()` viene prima di `carica()`), e una
 * lista catturata adesso resterebbe vuota per sempre.
 *
 * Le fontanelle sono in sola lettura: 3.687 voci senza chiave propria, la
 * stessa fontanella accanto a più spot. Una chiave inventata si romperebbe
 * alla prima rigenerazione dei dati.
 */
admin.registra({ nome: 'spot', base: () => DATI.base });
admin.registra({ nome: 'tutorial', base: () => DATI.baseTutorial });
admin.registra({
  nome: 'fontanelle',
  base: () => DATI.fontanelleUniche || [],
  chiave: null,
  soloLettura: true,
});

/** Toglie accenti e maiuscole: "Città" e "citta" devono trovarsi. */
function normalizza(testo) {
  return (testo || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
}

/**
 * Legge un file di dati. Nella demo in un file solo i dati sono già dentro la
 * pagina (`__PK_INLINE__`): non c'è un server a cui chiederli, e `fetch` da
 * `file://` non funzionerebbe comunque.
 */
async function leggiJson(percorso) {
  const dentro = globalThis.__PK_INLINE__ && globalThis.__PK_INLINE__[percorso];
  if (dentro) return dentro;
  const risposta = await fetch(percorso);
  if (!risposta.ok) throw new Error(`${percorso}: ${risposta.status}`);
  return risposta.json();
}

/** Carica spot e tutorial. Le fontanelle arrivano dopo, alla prima scheda. */
export async function carica() {
  const [spot, tutorial] = await Promise.all([
    leggiJson('data/spots.json'),
    leggiJson('data/tutorials.json'),
  ]);

  DATI.base = spot.spots;
  DATI.baseTutorial = tutorial.tutorials;
  riapplica();
  return DATI;
}

/**
 * Ricostruisce l'elenco degli spot partendo dal file e aggiungendoci le
 * modifiche locali della modalità sviluppatore. Si richiama ogni volta che
 * quelle cambiano, così non serve riavviare l'app per vederle.
 */
export function riapplica() {
  DATI.spot = admin.applica('spot', DATI.base).map((voce) => ({
    ...voce,
    cerca: normalizza(`${voce.name} ${voce.description || ''}`),
  }));
  DATI.verificati = DATI.spot.filter((voce) => voce.status === 'verified').length;
  DATI.perId = new Map(DATI.spot.map((voce) => [voce.id, voce]));
  // Anche i tutorial: se le modifiche locali valessero solo per gli spot, la
  // regola «niente si finge verificato» varrebbe a metà.
  DATI.tutorial = admin.applica('tutorial', DATI.baseTutorial);
  return DATI.spot.length;
}

/** Gli spot come stanno nel file, senza modifiche locali: serve all'esportazione. */
export function spotDelFile() {
  return DATI.base;
}

export function spot() {
  return DATI.spot;
}

export function spotPerId(id) {
  return DATI.perId.get(id) || null;
}

export function contaVerificati() {
  return DATI.verificati;
}

export function tutorial() {
  return DATI.tutorial;
}

export function tutorialPerId(id) {
  return DATI.tutorial.find((voce) => voce.id === id) || null;
}

/** Le fontanelle di uno spot. Il file è grande: si legge alla prima richiesta. */
export async function fontanelleDi(id) {
  if (motoreUtilizzabile()) {
    try {
      const esito = await motore.spot(id);
      return esito.fountains || [];
    } catch {
      // Si risponde qui sotto.
    }
  }
  if (!DATI.fontanelle) {
    try {
      const dati = await leggiJson('data/fountains.json');
      DATI.fontanelle = dati.bySpot || {};
    } catch {
      DATI.fontanelle = {};
    }
  }
  return DATI.fontanelle[id] || [];
}

/** Il motore può rispondere? Non se ha in mano dati diversi dai nostri. */
function motoreUtilizzabile() {
  return motore.acceso() && !admin.haModifiche();
}

/** L'ultima domanda al motore è rimasta senza risposta? */
let motoreMuto = false;

/**
 * Chi sta rispondendo alle domande dell'app, e perché.
 *
 * Restituisce `{chi: 'locale'|'motore', perche: string}`. Serve al pannello:
 * «il motore è configurato» e «il motore sta rispondendo» sono due cose
 * diverse, e finché non si vede la seconda non si capisce perché una ricerca
 * dia risultati che non tornano con quello che si è appena corretto.
 */
export function chiRisponde() {
  if (!motore.acceso()) return { chi: 'locale', perche: 'whyNotConfigured' };
  if (admin.haModifiche()) {
    const conti = admin.conteggiTotali();
    const quante = Object.values(conti.per).reduce(
      (somma, c) => somma + c.modificati + c.nuovi + c.cancellati,
      0
    );
    return { chi: 'locale', perche: 'whyChanges', quante };
  }
  if (motoreMuto) return { chi: 'locale', perche: 'whySilent' };
  return { chi: 'motore', perche: '' };
}

function dentroIlRiquadro(voce, riquadro) {
  return (
    voce.lat >= riquadro.sud &&
    voce.lat <= riquadro.nord &&
    voce.lng >= riquadro.ovest &&
    voce.lng <= riquadro.est
  );
}

/**
 * Cerca fra gli spot.
 * `filtri`: {testo, soloVerificati, conFontanella, livello, preferiti:Set, da:{lat,lng}}
 * Restituisce un elenco ordinato: prima i più vicini, se sappiamo dove siamo.
 */
export async function cerca(filtri = {}, distanzaM) {
  if (motoreUtilizzabile() && !filtri.preferiti) {
    try {
      const esito = await motore.cerca(filtri);
      motoreMuto = false;
      return esito.spots;
    } catch {
      // Il motore non c'è o non risponde: si continua qui sotto. Lo si segna,
      // perché «configurato» e «sta rispondendo» sono due cose diverse e il
      // pannello deve poter dire quale delle due.
      motoreMuto = true;
    }
  }
  return cercaInLocale(filtri, distanzaM);
}

function cercaInLocale(filtri, distanzaM) {
  const testo = normalizza(filtri.testo);
  const parole = testo ? testo.split(/\s+/).filter(Boolean) : [];

  let risultati = DATI.spot.filter((voce) => {
    if (filtri.soloVerificati && voce.status !== 'verified') return false;
    if (filtri.conFontanella && !voce.fountain) return false;
    if (filtri.livello && voce.level !== filtri.livello) return false;
    if (filtri.preferiti && !filtri.preferiti.has(voce.id)) return false;
    return parole.every((parola) => voce.cerca.includes(parola));
  });

  if (filtri.da && distanzaM) {
    risultati = risultati
      .map((voce) => ({ voce, metri: distanzaM(filtri.da, voce) }))
      .sort((a, b) => a.metri - b.metri)
      .map((coppia) => Object.assign(coppia.voce, { metri: coppia.metri }));
  } else if (parole.length) {
    // Senza posizione: chi ha la parola nel nome viene prima di chi ce l'ha
    // solo nella descrizione.
    const peso = (voce) => (normalizza(voce.name).includes(testo) ? 0 : 1);
    risultati = [...risultati].sort((a, b) => peso(a) - peso(b) || a.name.localeCompare(b.name));
  }

  return risultati;
}

/**
 * Gli spot dentro il riquadro visibile. Li restituisce tutti: chi disegna la
 * mappa li raccoglie in gomitoli quando sono troppi vicini, e il numero sul
 * gomitolo dice quanti sono. Qui non si butta via niente — la versione
 * precedente sfoltiva a griglia e gli spot in eccesso sparivano in silenzio,
 * che su una mappa di spot è il difetto peggiore possibile.
 */
export async function nelRiquadro(riquadro, opzioni = {}) {
  if (motoreUtilizzabile()) {
    try {
      const esito = await motore.nelRiquadro(riquadro, opzioni);
      motoreMuto = false;
      return esito.spots;
    } catch {
      // Si risponde qui sotto.
      motoreMuto = true;
    }
  }
  const dentro = [];
  for (const voce of DATI.spot) {
    if (!dentroIlRiquadro(voce, riquadro)) continue;
    if (opzioni.soloVerificati && voce.status !== 'verified') continue;
    dentro.push(voce);
  }
  return dentro;
}

/** Il catalogo dei tutorial, filtrato per livello e categoria. */
export async function tutorialFiltrati(filtri = {}) {
  // `motoreUtilizzabile()` e non `motore.acceso()`: con una modifica locale in
  // corso il motore ha in mano dati diversi dai nostri, e un tutorial corretto
  // qui tornerebbe dal motore com'era nel file. Gli spot lo facevano già; i
  // tutorial no, da quando il pannello sa correggerli anche loro.
  if (motoreUtilizzabile()) {
    try {
      const esito = await motore.tutorial(filtri);
      motoreMuto = false;
      return esito.tutorials;
    } catch {
      // Si risponde qui sotto.
      motoreMuto = true;
    }
  }
  return DATI.tutorial
    .filter((voce) => !filtri.livello || voce.level === filtri.livello)
    .filter((voce) => !filtri.categoria || voce.category === filtri.categoria);
}

/**
 * Tutte le fontanelle, una volta sola e senza doppioni.
 *
 * Il file le elenca per spot, e la stessa fontanella compare accanto a più
 * spot vicini: sulla mappa sarebbe una goccia disegnata sopra l'altra. La
 * chiave è la coordinata arrotondata, che nei dati è già a cinque decimali.
 */
export async function tutteLeFontanelle() {
  if (DATI.fontanelleUniche) return DATI.fontanelleUniche;
  if (!DATI.fontanelle) await fontanelleDi('');

  const viste = new Map();
  for (const elenco of Object.values(DATI.fontanelle || {})) {
    for (const fontanella of elenco) {
      const chiave = `${fontanella.lat},${fontanella.lng}`;
      if (!viste.has(chiave)) {
        viste.set(chiave, { lat: fontanella.lat, lng: fontanella.lng, kind: fontanella.kind });
      }
    }
  }
  DATI.fontanelleUniche = [...viste.values()];
  return DATI.fontanelleUniche;
}
