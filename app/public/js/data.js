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
 */

const DATI = {
  spot: [],
  perId: new Map(),
  tutorial: [],
  fontanelle: null,
  verificati: 0,
};

/** Toglie accenti e maiuscole: "Città" e "citta" devono trovarsi. */
function normalizza(testo) {
  return (testo || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
}

async function leggiJson(percorso) {
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

  DATI.spot = spot.spots.map((voce) => ({
    ...voce,
    cerca: normalizza(`${voce.name} ${voce.description || ''}`),
  }));
  DATI.verificati = spot.verified;
  DATI.perId = new Map(DATI.spot.map((voce) => [voce.id, voce]));
  DATI.tutorial = tutorial.tutorials;
  return DATI;
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

/** Gli spot dentro il riquadro visibile, al massimo `tetto`. */
export function nelRiquadro(riquadro, tetto = 400) {
  const dentro = [];
  for (const voce of DATI.spot) {
    if (
      voce.lat >= riquadro.sud &&
      voce.lat <= riquadro.nord &&
      voce.lng >= riquadro.ovest &&
      voce.lng <= riquadro.est
    ) {
      dentro.push(voce);
      // Oltre il tetto si continua a contare ma non si accumula: a zoom basso
      // servirebbero migliaia di spilli per mostrare la stessa cosa.
      if (dentro.length > tetto * 4) break;
    }
  }
  if (dentro.length <= tetto) return dentro;

  // Sfoltimento a griglia: un solo spillo per cella, i verificati vincono.
  const passo = (riquadro.nord - riquadro.sud) / 18 || 0.01;
  const celle = new Map();
  for (const voce of dentro) {
    const chiave = `${Math.round(voce.lat / passo)},${Math.round(voce.lng / passo)}`;
    const attuale = celle.get(chiave);
    if (!attuale || (attuale.status !== 'verified' && voce.status === 'verified')) {
      celle.set(chiave, voce);
    }
  }
  return [...celle.values()].slice(0, tetto);
}
