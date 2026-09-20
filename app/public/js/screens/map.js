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
import * as offline from '../offline.js';
import * as posizione from '../position.js';
import { leggi, scrivi } from '../store.js';
import { aggiungi, annuncia, avviso, distintivo, el, svuota } from '../ui.js';

/** Da qui in su si disegnano anche le fontanelle intorno. */
const ZOOM_FONTANELLE = 14;

/** Quante tessere devono mancare perché valga la pena dirlo. */
const TESSERE_PER_AVVISARE = 4;

/** Oltre questi pixel la maniglia è stata trascinata, non toccata. */
const SOGLIA_TRASCINAMENTO = 18;

/** Quanto spazio lasciare fra lo spillo scelto e il bordo del foglio. */
const RESPIRO_SOPRA_IL_FOGLIO = 48;

let mappa = null;
let foglio = null;
let corpo = null;
/** Le fontanelle dello spot scelto: si mostrano quando la scheda è alzata. */
let fontanelleDelloSpot = [];
let striscia = null;
let contesto = null;
let scelto = null;
let fontanelleCaricate = null;
let salvataggioVista = null;
/** Mostrare solo i 26 verificati dalla famiglia, invece di tutti e 1.706. */
let soloVerificati = false;

/** Gli spot del riquadro, le fontanelle intorno, e il conto nel sottotitolo. */
let richiestaQuadro = 0;

async function aggiornaQuadro() {
  const riquadro = mappa.riquadro();
  const mia = ++richiestaQuadro;
  const dentro = await dati.nelRiquadro(riquadro, { soloVerificati });
  // Trascinando si parte più volte: vince l'ultima, non la più lenta.
  if (mia !== richiestaQuadro) return;
  mappa.mostraSpot(dentro);

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
  if (!totale) return soloVerificati ? t('map.noneVerifiedHere') : t('map.noneHere');
  if (soloVerificati) return t('map.hereVerified', { n: totale });
  if (quadro.gomitoli) return t('map.hereGrouped', { n: totale, g: quadro.raccolti });
  return t('map.here', { n: totale });
}

/**
 * La striscia che dice che di questa zona mancano le tessere, e da cui si può
 * scaricarla. Prima l'unico posto per farlo era la schermata «Tu», cioè non
 * dove uno se ne accorge.
 */
function aggiornaStriscia() {
  if (!striscia) return;
  const quadro = mappa.quadro;
  const mancano = quadro.tessereMancanti >= TESSERE_PER_AVVISARE;

  if (offline.scaricamento.inCorso) {
    striscia.dataset.aperta = '1';
    svuota(striscia).append(
      el('span', { class: 'pk-small', testo: offline.scaricamento.messaggio })
    );
    return;
  }
  if (!mancano) {
    striscia.dataset.aperta = '0';
    return;
  }

  striscia.dataset.aperta = '1';
  svuota(striscia).append(
    el('span', { class: 'pk-small', style: 'flex:1', testo: t('map.missingHere') }),
    el(
      'button',
      {
        class: 'pk-btn pk-btn--fantasma',
        style: 'min-height:34px;padding:0 12px',
        onclick: async () => {
          await offline.preparaArea(mappa, {
            progresso: () => aggiornaStriscia(),
            finito: () => {
              mappa.riprova();
              setTimeout(aggiornaStriscia, 1200);
            },
          });
          aggiornaStriscia();
        },
      },
      [t('map.prepareHere')]
    )
  );
}

/** Le fontanelle arrivano da un file grande: si carica alla prima occasione. */
async function caricaFontanelle() {
  if (fontanelleCaricate) return;
  fontanelleCaricate = await dati.tutteLeFontanelle();
  aggiornaQuadro();
}

function chiudiFoglio() {
  if (scelto) annuncia(t('map.announceClosed'));
  scelto = null;
  fontanelleDelloSpot = [];
  foglio.dataset.aperto = '0';
  foglio.setAttribute('aria-hidden', 'true');
  for (const nodo of foglio.querySelectorAll('button, a')) nodo.tabIndex = -1;
  mappa.seleziona(null);
  mappa.mostraPercorso(null);
  aggiornaQuadro();
}

/**
 * Se lo spillo scelto finisce sotto il foglio, la mappa si sposta di poco.
 * La misura è quella vera del foglio, non una frazione scritta a mano: il
 * foglio ha due altezze, e con quella alta una frazione fissa lo lascerebbe
 * coperto.
 */
function scostaDalFoglio(voce) {
  const contenitore = document.getElementById('pk-map');
  const altezza = contenitore.clientHeight;
  if (!altezza) return;
  const p = mappa.aSchermo(voce);
  const coperto = foglio.getBoundingClientRect().height || altezza * 0.46;
  const desiderata = Math.max(altezza - coperto - RESPIRO_SOPRA_IL_FOGLIO, altezza * 0.18);
  if (p.y > desiderata) mappa.spostaDi(0, desiderata - p.y);
}

/**
 * Alza o abbassa la scheda. Alzata non è la stessa scheda più grande: mostra
 * la descrizione per intero e l'acqua vicina, che raccolta non ci starebbero.
 * Un'altezza diversa con dentro le stesse righe sarebbe solo spazio vuoto.
 */
function alzaFoglio(alto) {
  foglio.dataset.altezza = alto ? 'alto' : 'basso';
  const maniglia = foglio.querySelector('.pk-sheet__grip');
  if (maniglia) maniglia.setAttribute('aria-expanded', alto ? 'true' : 'false');
  if (!scelto) return;
  riempiFoglio(scelto);
  scostaDalFoglio(scelto);
}

/**
 * La maniglia del foglio: si trascina su e giù come su qualunque telefono, e
 * si tocca per alternare le due altezze. È un bottone, non un segno grafico,
 * perché il gesto deve esistere anche per chi arriva con il tasto Tab: lì
 * Invio fa la stessa cosa del trascinamento, e `aria-expanded` dice com'è
 * messo il foglio adesso.
 */
function creaManiglia() {
  let partenza = null;
  let trascinata = false;

  const maniglia = el('button', {
    type: 'button',
    class: 'pk-sheet__grip',
    'aria-label': t('map.sheetToggle'),
    'aria-expanded': foglio.dataset.altezza === 'alto' ? 'true' : 'false',
    onclick: () => {
      // Un trascinamento ha già deciso: il click che lo segue non deve
      // rifare il contrario.
      if (trascinata) {
        trascinata = false;
        return;
      }
      alzaFoglio(foglio.dataset.altezza !== 'alto');
    },
  });

  maniglia.addEventListener('pointerdown', (evento) => {
    partenza = evento.clientY;
    trascinata = false;
    maniglia.setPointerCapture(evento.pointerId);
  });

  const finisci = (evento) => {
    if (partenza === null) return;
    const dy = evento.clientY - partenza;
    partenza = null;
    if (Math.abs(dy) < SOGLIA_TRASCINAMENTO) return; // era un tocco
    trascinata = true;
    if (dy < 0) {
      alzaFoglio(true);
    } else if (foglio.dataset.altezza === 'alto') {
      alzaFoglio(false);
    } else {
      // Già in basso e si tira ancora giù: il foglio se ne va.
      chiudiFoglio();
    }
  };

  maniglia.addEventListener('pointerup', finisci);
  maniglia.addEventListener('pointercancel', () => {
    partenza = null;
  });

  return maniglia;
}

/** La riga della distanza nel foglio: il numero, o il modo per averlo. */
function rigaDistanza(voce) {
  const mia = posizione.ultimaNota();
  if (mia) {
    return el('span', {
      class: 'pk-small pk-muted',
      id: 'pk-foglio-distanza',
      testo: formattaDistanza(distanzaM(mia, voce)),
    });
  }
  return el(
    'button',
    {
      class: 'pk-chip',
      id: 'pk-foglio-distanza',
      onclick: async (evento) => {
        const bottone = evento.currentTarget;
        bottone.disabled = true;
        try {
          const trovata = await posizione.chiedi();
          mappa.segnaPosizione(trovata);
          posizione.segui(seguiPosizione);
          if (scelto) apriFoglio(scelto);
        } catch {
          bottone.disabled = false;
          avviso(t('map.noPosition'));
        }
      },
    },
    [t('spot.usePosition')]
  );
}

/** La posizione si muove: la distanza nel foglio si muove con lei. */
function seguiPosizione(aggiornata) {
  mappa.segnaPosizione(aggiornata);
  if (!scelto) return;
  const nodo = document.getElementById('pk-foglio-distanza');
  if (nodo && nodo.tagName === 'SPAN') {
    nodo.textContent = formattaDistanza(distanzaM(aggiornata, scelto));
  }
}

/** Il contenuto della scheda, nella misura che l'altezza di adesso consente. */
function riempiFoglio(voce) {
  const alto = foglio.dataset.altezza === 'alto';
  const testo = voce.description || '';
  aggiungi(
    svuota(corpo),
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
      rigaDistanza(voce),
    ]),
    testo
      ? el('p', { class: 'pk-small pk-muted', testo: alto ? testo : testo.slice(0, 180) })
      : null,
    // L'acqua vicina è già calcolata per gli spilli sulla mappa: alzando la
    // scheda si legge, invece di doverla indovinare dai punti azzurri.
    alto && fontanelleDelloSpot.length
      ? el('p', { class: 'pk-small pk-muted', testo: t('spot.fountains') })
      : null,
    alto && fontanelleDelloSpot.length
      ? el(
          'ul',
          { class: 'pk-small pk-muted' },
          fontanelleDelloSpot
            .slice(0, 3)
            .map((f) =>
              el('li', {
                testo: `${t(`spot.water.${f.kind}`)} — ${formattaDistanza(f.distance_m)}`,
              })
            )
        )
      : null,
    el('button', { class: 'pk-btn pk-btn--largo', onclick: () => contesto.vaiA(`#/spot/${voce.id}`) }, [
      t('map.open'),
    ])
  );
  for (const nodo of corpo.querySelectorAll('button, a')) nodo.tabIndex = 0;
}

async function apriFoglio(voce) {
  scelto = voce;

  riempiFoglio(voce);
  foglio.dataset.aperto = '1';
  foglio.removeAttribute('aria-hidden');
  for (const nodo of foglio.querySelectorAll('button, a')) nodo.tabIndex = 0;

  mappa.seleziona(voce.id);
  scostaDalFoglio(voce);

  // Lo spillo è cambiato dentro un disegno: senza questa frase, chi non vede
  // la tela non saprebbe che è successo qualcosa.
  const stato = voce.status === 'verified' ? t('spot.verified') : t('spot.community');
  const mia = posizione.ultimaNota();
  annuncia(
    mia
      ? t('map.announceChosenFar', {
          nome: voce.name,
          stato,
          distanza: formattaDistanza(distanzaM(mia, voce)),
        })
      : t('map.announceChosen', { nome: voce.name, stato })
  );

  // Le fontanelle di questo spot, con i metri: è il dato che il masterplan
  // vuole sulla mappa, e l'unico posto dove la distanza è già calcolata.
  const sue = await dati.fontanelleDi(voce.id);
  if (scelto && scelto.id === voce.id) {
    mappa.mostraFontanelle(sue.map((f) => ({ lat: f.lat, lng: f.lng, metri: f.distance_m })));
    fontanelleDelloSpot = sue;
    if (foglio.dataset.altezza === 'alto') riempiFoglio(voce);
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
    posizione.segui(seguiPosizione);
    if (scelto) apriFoglio(scelto);
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
  soloVerificati = Boolean(await leggi('mappa.soloVerificati', false));

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
      // I 26 verificati dalla famiglia in mezzo a 1.680 segnalati: senza un
      // modo di isolarli, la mappa a zoom basso è tutta blu.
      el('button', {
        class: 'pk-map__tool',
        testo: '✓',
        'aria-label': t('map.onlyVerified'),
        'aria-pressed': soloVerificati ? 'true' : 'false',
        title: t('map.onlyVerified'),
        onclick: async (evento) => {
          soloVerificati = !soloVerificati;
          evento.currentTarget.setAttribute('aria-pressed', soloVerificati ? 'true' : 'false');
          await scrivi('mappa.soloVerificati', soloVerificati);
          aggiornaQuadro();
        },
      }),
    ])
  );

  striscia = el('div', { class: 'pk-map__strip', dati: { aperta: '0' } });
  contenitore.append(striscia);

  foglio = el('div', {
    class: 'pk-sheet',
    dati: { aperto: '0', altezza: 'basso' },
    'aria-hidden': 'true',
    'aria-label': t('map.sheet'),
  });
  corpo = el('div', { class: 'pk-sheet__corpo' });
  // La maniglia si crea una volta sola: rifarla a ogni scelta porterebbe via
  // il focus a chi sta usando la tastiera.
  foglio.append(creaManiglia(), corpo);
  contenitore.append(foglio);

  mappa.su('selezione', (voce) => (voce ? apriFoglio(voce) : chiudiFoglio()));
  // Il conto nel sottotitolo si aggiorna quando la tela è stata disegnata:
  // prima di allora sarebbe il conto del fotogramma precedente.
  mappa.su('disegnato', () => {
    aggiornaSottotitolo();
    aggiornaStriscia();
  });
  mappa.su('gomitolo', (gomitolo) => {
    if (scelto) chiudiFoglio();
    annuncia(t('map.announceCluster', { n: gomitolo.conta }));
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
