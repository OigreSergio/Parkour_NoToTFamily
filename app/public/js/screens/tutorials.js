/* PkFAMILY — il catalogo dei tutorial.
 *
 * Le schede (titolo, canale, livello, durata) stanno nell'app e si leggono
 * senza rete: si può decidere cosa allenare anche in mezzo al nulla. Il video
 * no — quello sta su YouTube e la rete la vuole. L'app lo dice invece di far
 * finta di niente.
 *
 * Prima di un tutorial compare l'avviso sui rischi, come per gli spot.
 */

import * as dati from '../data.js';
import { formattaDurata } from '../geo.js';
import { t } from '../i18n.js';
import { avvisa } from '../legal.js';
import { avviso, el, svuota, vuoto } from '../ui.js';

const FILTRI = { livello: '', categoria: '' };
let contenitore = null;

const LIVELLI = ['beginner', 'intermediate', 'advanced'];
const CATEGORIE = ['practice', 'conditioning', 'recovery'];

async function apri(voce) {
  const procedi = await avvisa('tutorial');
  if (!procedi) return;
  if (!navigator.onLine) {
    avviso(t('tutorials.needNet'));
    return;
  }
  window.open(voce.url, '_blank', 'noopener');
}

function scheda(voce) {
  return el('button', { class: 'pk-item', onclick: () => apri(voce) }, [
    el('span', { class: 'pk-item__pin', 'aria-hidden': 'true', testo: '▷' }),
    el('span', { class: 'pk-item__body' }, [
      el('span', { class: 'pk-item__name', testo: voce.title }),
      el('span', {
        class: 'pk-item__meta',
        testo: [
          t(`tutorials.level.${voce.level}`),
          voce.channel,
          voce.seconds ? formattaDurata(voce.seconds) : null,
          '★'.repeat(Math.max(1, Math.min(5, voce.difficulty))),
        ]
          .filter(Boolean)
          .join(' · '),
      }),
    ]),
  ]);
}

function disegna() {
  const elenco = dati
    .tutorial()
    .filter((voce) => !FILTRI.livello || voce.level === FILTRI.livello)
    .filter((voce) => !FILTRI.categoria || voce.category === FILTRI.categoria);

  svuota(contenitore);
  if (!elenco.length) {
    contenitore.append(vuoto(t('tutorials.empty')));
    return;
  }
  contenitore.append(
    el('p', { class: 'pk-small pk-muted', testo: t('tutorials.count', { n: elenco.length }) }),
    el('div', {}, elenco.map(scheda))
  );
}

function chip(etichetta, attivo, quandoTocca) {
  return el(
    'button',
    { class: 'pk-chip', 'aria-pressed': attivo ? 'true' : 'false', onclick: quandoTocca },
    [etichetta]
  );
}

function disegnaFiltri() {
  const barra = document.getElementById('pk-filtri-tutorial');
  svuota(barra).append(
    ...LIVELLI.map((livello) =>
      chip(t(`tutorials.level.${livello}`), FILTRI.livello === livello, () => {
        FILTRI.livello = FILTRI.livello === livello ? '' : livello;
        disegnaFiltri();
        disegna();
      })
    ),
    ...CATEGORIE.map((categoria) =>
      chip(t(`tutorials.category.${categoria}`), FILTRI.categoria === categoria, () => {
        FILTRI.categoria = FILTRI.categoria === categoria ? '' : categoria;
        disegnaFiltri();
        disegna();
      })
    )
  );
}

export function inizializza() {
  contenitore = document.getElementById('pk-tutorial');
  disegnaFiltri();
  disegna();
}

export function entra() {
  disegna();
}

export function titolo() {
  return { titolo: t('nav.tutorials'), sotto: t('tutorials.subtitle', { n: dati.tutorial().length }) };
}
