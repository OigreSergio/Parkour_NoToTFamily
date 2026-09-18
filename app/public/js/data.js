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
 */

import * as admin from './admin.js';

const DATI = {
  /** Gli spot come stanno nel file: non si toccano mai. */
  base: [],
  /** Gli spot come li vede l'app: base più le modifiche locali, se ce ne sono. */
  spot: [],
  perId: new Map(),
  tutorial: [],
  fontanelle: null,
  fontanelleUniche: null,
  verificati: 0,
};

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
  DATI.tutorial = tutorial.tutorials;
  riapplica();
  return DATI;
}

/**
 * Ricostruisce l'elenco degli spot partendo dal file e aggiungendoci le
 * modifiche locali della modalità sviluppatore. Si richiama ogni volta che
 * quelle cambiano, così non serve riavviare l'app per vederle.
 */
export function riapplica() {
  DATI.spot = admin.applicaAgliSpot(DATI.base).map((voce) => ({
    ...voce,
    cerca: normalizza(`${voce.name} ${voce.description || ''}`),
  }));
  DATI.verificati = DATI.spot.filter((voce) => voce.status === 'verified').length;
  DATI.perId = new Map(DATI.spot.map((voce) => [voce.id, voce]));
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

/**
 * Cerca fra gli spot.
 * `filtri`: {testo, soloVerificati, conFontanella, livello, preferiti:Set, da:{lat,lng}}
 * Restituisce un elenco ordinato: prima i più vicini, se sappiamo dove siamo.
 */
export function cerca(filtri = {}, distanzaM) {
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
export function nelRiquadro(riquadro) {
  const dentro = [];
  for (const voce of DATI.spot) {
    if (
      voce.lat >= riquadro.sud &&
      voce.lat <= riquadro.nord &&
      voce.lng >= riquadro.ovest &&
      voce.lng <= riquadro.est
    ) {
      dentro.push(voce);
    }
  }
  return dentro;
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
