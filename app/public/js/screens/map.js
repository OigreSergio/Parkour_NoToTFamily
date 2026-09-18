/* PkFAMILY — la schermata mappa: spilli sul lino e un foglio che sale.
 *
 * Quello che si vede sulla mappa è tutto quello che c'è nel riquadro: dove
 * gli spilli si accavallerebbero il motore li raccoglie in un gomitolo con il
 * numero, e toccandolo ci si avvicina finché non si sfila. Niente sparisce in
 * silenzio, e il sottotitolo dice sempre quanti spot ci sono sotto gli occhi.
 */

import * as dati from '../data.js';
import { distanzaM, formattaDistanza } from '../geo.js';
import { t } from '../i18n.js';
import { creaMappa } from '../map.js';
import * as posizione from '../position.js';
import { leggi, scrivi } from '../store.js';
import { aggiungi, avviso, distintivo, el, svuota } from '../ui.js';

/** Da qui in su si disegnano anche le fontanelle intorno. */
const ZOOM_FONTANELLE = 14;

let mappa = null;
let foglio = null;
let contesto = null;
let scelto = null;
let fontanelleCaricate = null;
let salvataggioVista = null;

/** Gli spot del riquadro, le fontanelle intorno, e il conto nel sottotitolo. */
function aggiornaQuadro() {
  const riquadro = mappa.riquadro();
  mappa.mostraSpot(dati.nelRiquadro(riquadro));

  if (mappa.zoom >= ZOOM_FONTANELLE && fontanelleCaricate) {
    const vicine = fontanelleCaricate.filter(
      (f) =>
        f.lat >= riquadro.sud &&
        f.lat <= riquadro.nord &&
        f.lng >= riquadro.ovest &&
        f.lng <= riquadro.est
    );
    mappa.mostraFontanelle(vicine.slice(0, 160));
  } else if (!scelto) {
    mappa.mostraFontanelle([]);
  }

  aggiornaSottotitolo();
}

function aggiornaSottotitolo() {
  const sezione = document.querySelector('.pk-screen[data-schermata="mappa"]');
  if (!sezione || sezione.dataset.attiva !== '1') return;
  const nodo = document.getElementById('pk-sottotitolo');
  if (nodo) nodo.textContent = testoSottotitolo();
}

function testoSottotitolo() {
  const quadro = mappa.quadro;
  const totale = quadro.spilli + quadro.raccolti;
  if (!totale) return t('map.noneHere');
  if (quadro.gomitoli) return t('map.hereGrouped', { n: totale, g: quadro.raccolti });
  return t('map.here', { n: totale });
}

/** Le fontanelle arrivano da un file grande: si carica alla prima occasione. */
async function caricaFontanelle() {
  if (fontanelleCaricate) return;
  fontanelleCaricate = await dati.tutteLeFontanelle();
  aggiornaQuadro();
}

function chiudiFoglio() {
  scelto = null;
  foglio.dataset.aperto = '0';
  foglio.setAttribute('aria-hidden', 'true');
  for (const nodo of foglio.querySelectorAll('button, a')) nodo.tabIndex = -1;
  mappa.seleziona(null);
  mappa.mostraPercorso(null);
  aggiornaQuadro();
}

/** Se lo spillo scelto finisce sotto il foglio, la mappa si sposta di poco. */
function scostaDalFoglio(voce) {
  const contenitore = document.getElementById('pk-map');
  const altezza = contenitore.clientHeight;
  if (!altezza) return;
  const p = mappa.aSchermo(voce);
  const desiderata = altezza * 0.34;
  if (p.y > desiderata) mappa.spostaDi(0, desiderata - p.y);
}

async function apriFoglio(voce) {
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
    el('button', { class: 'pk-btn pk-btn--largo', onclick: () => contesto.vaiA(`#/spot/${voce.id}`) }, [
      t('map.open'),
    ])
  );
  foglio.dataset.aperto = '1';
  foglio.removeAttribute('aria-hidden');
  for (const nodo of foglio.querySelectorAll('button, a')) nodo.tabIndex = 0;

  mappa.seleziona(voce.id);
  scostaDalFoglio(voce);

  // Le fontanelle di questo spot, con i metri: è il dato che il masterplan
  // vuole sulla mappa, e l'unico posto dove la distanza è già calcolata.
  const sue = await dati.fontanelleDi(voce.id);
  if (scelto && scelto.id === voce.id) {
    mappa.mostraFontanelle(sue.map((f) => ({ lat: f.lat, lng: f.lng, metri: f.distance_m })));
  }
}

async function centraSuDiMe(bottone) {
  const etichetta = bottone ? bottone.textContent : null;
  if (bottone) {
    bottone.disabled = true;
    bottone.textContent = '…';
  }
  try {
    const mia = await posizione.chiedi();
    mappa.segnaPosizione(mia);
    mappa.vai({ lat: mia.lat, lng: mia.lng, zoom: Math.max(mappa.zoom, 15) });
    posizione.segui((aggiornata) => mappa.segnaPosizione(aggiornata));
  } catch {
    avviso(t('map.noPosition'));
  } finally {
    if (bottone) {
      bottone.disabled = false;
      bottone.textContent = etichetta;
    }
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

  const interruttoreSfondo = el('button', {
    class: 'pk-map__tool',
    testo: '▤',
    'aria-label': t('map.layer'),
    'aria-pressed': sorgente === 'satellite' ? 'true' : 'false',
    title: sorgente === 'satellite' ? t('map.satellite') : t('map.plain'),
    onclick: async (evento) => {
      const nuova = mappa.sorgente === 'mappa' ? 'satellite' : 'mappa';
      mappa.cambiaSorgente(nuova);
      const bottone = evento.currentTarget;
      bottone.setAttribute('aria-pressed', nuova === 'satellite' ? 'true' : 'false');
      bottone.title = nuova === 'satellite' ? t('map.satellite') : t('map.plain');
      await scrivi('mappa.sorgente', nuova);
    },
  });

  contenitore.append(
    el('div', { class: 'pk-map__tools' }, [
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
        onclick: (evento) => centraSuDiMe(evento.currentTarget),
      }),
      interruttoreSfondo,
    ])
  );

  foglio = el('div', {
    class: 'pk-sheet',
    dati: { aperto: '0' },
    'aria-hidden': 'true',
    'aria-label': t('map.sheet'),
  });
  contenitore.append(foglio);

  mappa.su('selezione', (voce) => (voce ? apriFoglio(voce) : chiudiFoglio()));
  // Il conto nel sottotitolo si aggiorna quando la tela è stata disegnata:
  // prima di allora sarebbe il conto del fotogramma precedente.
  mappa.su('disegnato', aggiornaSottotitolo);
  mappa.su('gomitolo', () => {
    if (scelto) chiudiFoglio();
  });
  mappa.su('movimento', ({ centro, zoom }) => {
    aggiornaQuadro();
    // La vista si salva quando il dito si ferma, non sessanta volte al
    // secondo: era una transazione su IndexedDB per ogni fotogramma.
    clearTimeout(salvataggioVista);
    salvataggioVista = setTimeout(() => {
      scrivi('mappa.vista', { lat: centro.lat, lng: centro.lng, zoom });
    }, 400);
  });

  const mia = posizione.ultimaNota();
  if (mia) mappa.segnaPosizione(mia);
  aggiornaQuadro();
  caricaFontanelle();
}

/** Si entra nella mappa, eventualmente puntando a uno spot preciso. */
export function entra(parametri) {
  if (!mappa) return;
  mappa.ridisegna();
  if (parametri && parametri.id) {
    const voce = dati.spotPerId(parametri.id);
    if (voce) {
      mappa.vai({ lat: voce.lat, lng: voce.lng, zoom: Math.max(mappa.zoom, 16) });
      aggiornaQuadro();
      apriFoglio(voce);
      return;
    }
  }
  if (scelto) mappa.seleziona(scelto.id);
  aggiornaQuadro();
}

export function titolo() {
  return { titolo: t('nav.map'), sotto: mappa ? testoSottotitolo() : '' };
}
