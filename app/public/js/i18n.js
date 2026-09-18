/* PkFAMILY — le parole dell'interfaccia.
 *
 * Nessuna stringa scritta dentro il codice (masterplan 3.9): stanno in
 * `i18n/<lingua>.json`. L'italiano è la base e fa da rete di sicurezza per le
 * chiavi che una traduzione non ha ancora.
 */

export const LINGUE = { it: 'Italiano', en: 'English' };

let corrente = 'it';
let dizionario = {};
let base = {};

async function carica(lingua) {
  const risposta = await fetch(`i18n/${lingua}.json`);
  if (!risposta.ok) throw new Error(`lingua non trovata: ${lingua}`);
  return risposta.json();
}

/** Prepara le lingue. `preferita` vince sulla lingua del browser. */
export async function inizializza(preferita) {
  base = await carica('it');
  const scelta = preferita || (navigator.language || 'it').slice(0, 2).toLowerCase();
  corrente = LINGUE[scelta] ? scelta : 'it';
  dizionario = corrente === 'it' ? base : await carica(corrente).catch(() => base);
  document.documentElement.lang = corrente;
  return corrente;
}

export function lingua() {
  return corrente;
}

/** Il testo di una chiave, con le sostituzioni fra graffe: t('x', {n: 3}). */
export function t(chiave, sostituzioni) {
  let testo = dizionario[chiave] ?? base[chiave];
  if (testo === undefined) return chiave;
  if (sostituzioni) {
    for (const [nome, valore] of Object.entries(sostituzioni)) {
      testo = testo.replaceAll(`{${nome}}`, String(valore));
    }
  }
  return testo;
}

/** Riscrive nella lingua scelta tutti i nodi con `data-t`. */
export function applica(radice = document) {
  for (const nodo of radice.querySelectorAll('[data-t]')) {
    nodo.textContent = t(nodo.dataset.t);
  }
  for (const nodo of radice.querySelectorAll('[data-t-placeholder]')) {
    nodo.placeholder = t(nodo.dataset.tPlaceholder);
  }
  for (const nodo of radice.querySelectorAll('[data-t-aria]')) {
    nodo.setAttribute('aria-label', t(nodo.dataset.tAria));
  }
}
