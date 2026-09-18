/* PkFAMILY — la schermata mappa: spilli sul lino e un foglio che sale.
 *
 * Gli spilli mostrati sono solo quelli dentro al riquadro visibile, sfoltiti
 * a griglia quando sono troppi: con 1.706 spot disegnarli tutti a zoom basso
 * costa e non dice niente in più.
 */

import * as dati from '../data.js';
import { distanzaM, formattaDistanza } from '../geo.js';
import { t } from '../i18n.js';
import { creaMappa } from '../map.js';
import * as posizione from '../position.js';
import { leggi, scrivi } from '../store.js';
import { aggiungi, avviso, distintivo, el, svuota } from '../ui.js';

let mappa = null;
let foglio = null;
let contesto = null;
let scelto = null;

function aggiornaSpilli() {
  const riquadro = mappa.riquadro();
  mappa.mostraSpot(dati.nelRiquadro(riquadro, 400));
}

function chiudiFoglio() {
  scelto = null;
  foglio.dataset.aperto = '0';
  mappa.seleziona(null);
}

function apriFoglio(voce) {
  scelto = voce;
  const mia = posizione.ultimaNota();
  const metri = mia ? formattaDistanza(distanzaM(mia, voce)) : null;

  aggiungi(
    svuota(foglio),
    el('div', { class: 'pk-sheet__grip', 'aria-hidden': 'true' }),
    el('div', { class: 'pk-row' }, [
      el('h2', { testo: voce.name, style: 'flex:1;min-width:0' }),
      el('button', {
        class: 'pk-iconbtn',
        'aria-label': t('common.close'),
        testo: '✕',
        onclick: chiudiFoglio,
      }),
    ]),
    el('p', { class: 'pk-row pk-row--wrap', style: 'margin-top:8px' }, [
      distintivo(voce.status),
      voce.fountain ? el('span', { class: 'pk-badge', testo: t('spot.fountain') }) : null,
      metri ? el('span', { class: 'pk-small pk-muted', testo: metri }) : null,
    ]),
    voce.description
      ? el('p', { class: 'pk-small pk-muted', testo: voce.description.slice(0, 180) })
      : null,
    el(
      'button',
      {
        class: 'pk-btn pk-btn--largo',
        onclick: () => contesto.vaiA(`#/spot/${voce.id}`),
      },
      [t('map.open')]
    )
  );
  foglio.dataset.aperto = '1';
  mappa.seleziona(voce.id);
}

async function centraSuDiMe() {
  try {
    const mia = await posizione.chiedi();
    mappa.segnaPosizione(mia);
    mappa.vai({ lat: mia.lat, lng: mia.lng, zoom: Math.max(mappa.zoom, 15) });
    posizione.segui((aggiornata) => mappa.segnaPosizione(aggiornata));
  } catch {
    avviso(t('map.noPosition'));
  }
}

export async function inizializza(ctx) {
  contesto = ctx;
  const contenitore = document.getElementById('pk-map');
  mappa = creaMappa(contenitore, { etichetta: t('map.label') });
  ctx.mappa = mappa;

  const vista = await leggi('mappa.vista', null);
  if (vista) mappa.vai(vista);
  const sorgente = await leggi('mappa.sorgente', 'mappa');
  mappa.cambiaSorgente(sorgente);

  const strumenti = el('div', { class: 'pk-map__tools' }, [
    el('button', {
      class: 'pk-map__tool',
      testo: '+',
      'aria-label': t('map.zoomIn'),
      onclick: () => mappa.zoomAvanti(),
    }),
    el('button', {
      class: 'pk-map__tool',
      testo: '−',
      'aria-label': t('map.zoomOut'),
      onclick: () => mappa.zoomIndietro(),
    }),
    el('button', {
      class: 'pk-map__tool',
      testo: '◎',
      'aria-label': t('map.locate'),
      onclick: centraSuDiMe,
    }),
    el('button', {
      class: 'pk-map__tool',
      testo: '▤',
      'aria-label': t('map.layer'),
      onclick: async (evento) => {
        const nuova = mappa.sorgente === 'mappa' ? 'satellite' : 'mappa';
        mappa.cambiaSorgente(nuova);
        evento.currentTarget.setAttribute('aria-pressed', nuova === 'satellite' ? 'true' : 'false');
        await scrivi('mappa.sorgente', nuova);
      },
    }),
  ]);
  contenitore.append(strumenti);

  foglio = el('div', { class: 'pk-sheet', dati: { aperto: '0' } });
  contenitore.append(foglio);

  mappa.su('selezione', (voce) => (voce ? apriFoglio(voce) : chiudiFoglio()));
  mappa.su('movimento', ({ centro, zoom }) => {
    aggiornaSpilli();
    scrivi('mappa.vista', { lat: centro.lat, lng: centro.lng, zoom });
  });

  const mia = posizione.ultimaNota();
  if (mia) mappa.segnaPosizione(mia);
  aggiornaSpilli();
}

/** Si entra nella mappa, eventualmente puntando a uno spot preciso. */
export function entra(parametri) {
  if (!mappa) return;
  mappa.ridisegna();
  if (parametri && parametri.id) {
    const voce = dati.spotPerId(parametri.id);
    if (voce) {
      mappa.vai({ lat: voce.lat, lng: voce.lng, zoom: Math.max(mappa.zoom, 16) });
      aggiornaSpilli();
      apriFoglio(voce);
    }
  } else if (scelto) {
    mappa.seleziona(scelto.id);
  }
}

export function titolo() {
  return { titolo: t('nav.map'), sotto: t('map.subtitle', { n: dati.spot().length }) };
}
