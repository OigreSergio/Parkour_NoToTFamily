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

export function cerca(filtri) {
  return chiedi('/cerca', {
    q: filtri.testo,
    verificati: filtri.soloVerificati,
    fontanella: filtri.conFontanella,
    livello: filtri.livello,
    lat: filtri.da ? filtri.da.lat : undefined,
    lng: filtri.da ? filtri.da.lng : undefined,
    tetto: filtri.tetto,
  });
}

export function vicini(punto, quanti) {
  return chiedi('/vicini', { lat: punto.lat, lng: punto.lng, quanti });
}

export function spot(identificativo) {
  return chiedi(`/spot/${encodeURIComponent(identificativo)}`);
}

export function tutorial(filtri) {
  return chiedi('/tutorial', { livello: filtri.livello, categoria: filtri.categoria });
}
