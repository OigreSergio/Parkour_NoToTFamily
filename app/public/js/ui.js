/* PkFAMILY — i mattoni dell'interfaccia: nodi, fogli, finestre, avvisi.
 *
 * Niente framework: l'app deve partire dalla cache in un secondo anche su un
 * telefono lento, e ogni kilobyte che non c'è è un kilobyte che non si
 * scarica. Queste funzioni bastano per tutte le schermate.
 */

import { t } from './i18n.js';

/** Crea un nodo: el('div', {class: 'x', onclick: fn}, ['testo', altroNodo]). */
export function el(tag, attributi = {}, figli = []) {
  const nodo = document.createElement(tag);
  for (const [nome, valore] of Object.entries(attributi)) {
    if (valore === undefined || valore === null || valore === false) continue;
    if (nome === 'class') nodo.className = valore;
    else if (nome === 'testo') nodo.textContent = valore;
    else if (nome === 'html') nodo.innerHTML = valore;
    else if (nome.startsWith('on') && typeof valore === 'function') {
      nodo.addEventListener(nome.slice(2), valore);
    } else if (nome === 'dati') Object.assign(nodo.dataset, valore);
    else if (valore === true) nodo.setAttribute(nome, '');
    else nodo.setAttribute(nome, valore);
  }
  for (const figlio of [].concat(figli)) {
    if (figlio === null || figlio === undefined || figlio === false) continue;
    nodo.append(figlio instanceof Node ? figlio : document.createTextNode(String(figlio)));
  }
  return nodo;
}

export function svuota(nodo) {
  while (nodo.firstChild) nodo.firstChild.remove();
  return nodo;
}

/**
 * Aggiunge dei figli saltando quelli che non ci sono.
 * `nodo.append(null)` scriverebbe la parola «null» nella pagina: è il motivo
 * per cui questa funzione esiste e va usata al posto di `append` ogni volta
 * che un pezzo di interfaccia è condizionato.
 */
export function aggiungi(nodo, ...figli) {
  for (const figlio of figli.flat()) {
    if (figlio === null || figlio === undefined || figlio === false) continue;
    nodo.append(figlio);
  }
  return nodo;
}

/** Lo stato vuoto: un segno a punto croce, una frase, a volte un'azione. */
export function vuoto(testo, azione) {
  return el('div', { class: 'pk-empty' }, [
    el('div', { class: 'pk-empty__mark', 'aria-hidden': 'true' }, ['✕ ✕ ✕']),
    el('p', { testo }),
    azione || null,
  ]);
}

/** Etichetta di stato di uno spot: colore più parola, mai solo colore. */
export function distintivo(stato) {
  const classe = stato === 'verified' ? 'pk-badge--verificato' : 'pk-badge--community';
  const parola = stato === 'verified' ? t('spot.verified') : t('spot.community');
  return el('span', { class: `pk-badge ${classe}` }, [parola]);
}

let contenitoreModali = null;

function radiceModali() {
  if (!contenitoreModali) {
    contenitoreModali = document.getElementById('app') || document.body;
  }
  return contenitoreModali;
}

/**
 * Finestra modale. Restituisce una promessa con il valore dell'azione scelta.
 * `azioni` è un elenco di {testo, valore, primaria}.
 */
export function modale({ titolo, sommario, punti = [], corpo = null, azioni = [] }) {
  return new Promise((risolvi) => {
    const chiudi = (valore) => {
      finestra.remove();
      document.removeEventListener('keydown', suTasto);
      risolvi(valore);
    };
    const suTasto = (evento) => {
      if (evento.key === 'Escape') {
        const uscita = azioni.find((a) => !a.primaria);
        if (uscita) chiudi(uscita.valore);
      }
    };

    const scatola = el('div', { class: 'pk-modal__box', role: 'document' }, [
      el('h2', { id: 'pk-modal-titolo', testo: titolo }),
      sommario ? el('p', { class: 'pk-muted', testo: sommario }) : null,
      punti.length
        ? el(
            'ul',
            { class: 'pk-modal__list' },
            punti.map((punto) => el('li', { testo: punto }))
          )
        : null,
      corpo,
      el(
        'div',
        { class: 'pk-row pk-row--wrap', style: 'gap:8px;flex-direction:column;align-items:stretch' },
        azioni.map((azione) =>
          el(
            'button',
            {
              class: `pk-btn pk-btn--largo${azione.primaria ? '' : ' pk-btn--fantasma'}`,
              onclick: () => chiudi(azione.valore),
            },
            [azione.testo]
          )
        )
      ),
    ]);

    const finestra = el(
      'div',
      {
        class: 'pk-modal',
        role: 'dialog',
        'aria-modal': 'true',
        'aria-labelledby': 'pk-modal-titolo',
      },
      [scatola]
    );

    radiceModali().append(finestra);
    document.addEventListener('keydown', suTasto);
    const primo = scatola.querySelector('button');
    if (primo) primo.focus();
  });
}

/** Conferma breve: sì/no, con le parole che le si danno. */
export function conferma(titolo, sommario, siTesto, noTesto) {
  return modale({
    titolo,
    sommario,
    azioni: [
      { testo: siTesto, valore: true, primaria: true },
      { testo: noTesto || t('common.cancel'), valore: false },
    ],
  });
}

let avvisoAttivo = null;

/** Messaggio che compare in basso e se ne va da solo. */
export function avviso(testo) {
  if (avvisoAttivo) avvisoAttivo.remove();
  const nodo = el('div', {
    class: 'pk-card',
    role: 'status',
    style:
      'position:absolute;left:16px;right:16px;bottom:76px;z-index:50;margin:0;text-align:center',
    testo,
  });
  radiceModali().append(nodo);
  avvisoAttivo = nodo;
  setTimeout(() => {
    if (nodo.isConnected) nodo.remove();
    if (avvisoAttivo === nodo) avvisoAttivo = null;
  }, 3200);
}
