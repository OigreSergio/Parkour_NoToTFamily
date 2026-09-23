/* PkFAMILY — il cliente del motore in Python.
 *
 * Quando l'app gira dentro la demo da computer, a cercare fra 1.706 spot non è
 * più il browser: è `app/demo/motore.py`. Questo modulo è l'unico posto che sa
 * come chiederglielo, e `data.js` lo usa solo se `CONFIG.motore` è impostato —
 * altrimenti l'app fa tutto da sé, come sempre.
 *
 * Se il motore non risponde non si resta a mani vuote: chi chiama riceve un
 * errore e `data.js` torna a calcolare in locale. Una demo che si pianta
 * perché è caduto un processo non dimostrerebbe granché.
 */

import { CONFIG } from './config.js';
import { arrotonda } from './geo.js';

/** `CONFIG.motore` è la base (per esempio `/api`); `percorso` le si attacca
 *  dietro. Tenere il prefisso in un posto solo evita gli `/api/api/`. */
function indirizzo(percorso, parametri) {
  const base = CONFIG.motore.replace(/\/$/, '');
  const query = new URLSearchParams();
  for (const [nome, valore] of Object.entries(parametri || {})) {
    if (valore === undefined || valore === null || valore === '' || valore === false) continue;
    query.set(nome, valore === true ? '1' : String(valore));
  }
  const coda = query.toString();
  return `${base}${percorso}${coda ? `?${coda}` : ''}`;
}

async function chiedi(percorso, parametri) {
  const risposta = await fetch(indirizzo(percorso, parametri), {
    headers: { Accept: 'application/json' },
  });
  if (!risposta.ok) throw new Error(`motore: ${risposta.status}`);
  return risposta.json();
}

export function acceso() {
  return Boolean(CONFIG.motore);
}

/** Chi risponde dall'altra parte, e con quanti dati. */
export function stato() {
  return chiedi('/stato');
}

export function nelRiquadro(riquadro, { soloVerificati, conFontanelle } = {}) {
  return chiedi('/riquadro', {
    nord: riquadro.nord,
    sud: riquadro.sud,
    ovest: riquadro.ovest,
    est: riquadro.est,
    verificati: soloVerificati,
    fontanelle: conFontanelle,
  });
}

/**
 * La posizione di una persona non esce mai com'è.
 *
 * `route.js` lo fa da sempre prima di chiedere un percorso; qui mancava, e il
 * motore riceveva le coordinate a precisione piena. Di suo il motore gira
 * dentro il telefono o dentro la demo, ma `CONFIG.motore` si può cambiare dal
 * pannello sviluppatore e da un file importato: l'arrotondamento va fatto dove
 * si compone la richiesta, non dove si spera che l'indirizzo sia innocuo.
 * Tre cifre sono circa 110 metri (AGENTS.md, regola 4).
 */
function fuori(punto) {
  return punto ? arrotonda(punto, CONFIG.routing.decimali) : null;
}

export function cerca(filtri) {
  const da = fuori(filtri.da);
  return chiedi('/cerca', {
    q: filtri.testo,
    verificati: filtri.soloVerificati,
    fontanella: filtri.conFontanella,
    livello: filtri.livello,
    lat: da ? da.lat : undefined,
    lng: da ? da.lng : undefined,
    tetto: filtri.tetto,
  });
}

export function vicini(punto, quanti) {
  const p = fuori(punto);
  return chiedi('/vicini', { lat: p ? p.lat : undefined, lng: p ? p.lng : undefined, quanti });
}

export function spot(identificativo) {
  return chiedi(`/spot/${encodeURIComponent(identificativo)}`);
}

export function tutorial(filtri) {
  return chiedi('/tutorial', { livello: filtri.livello, categoria: filtri.categoria });
}
