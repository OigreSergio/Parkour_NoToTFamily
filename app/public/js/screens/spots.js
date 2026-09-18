/* PkFAMILY — l'elenco degli spot: cercare senza rete, in ordine di vicinanza.
 *
 * È la schermata gemella della mappa e ne è anche l'alternativa accessibile:
 * tutto quello che si vede fra gli spilli si trova anche qui, con la tastiera
 * e con un lettore di schermo.
 */

import * as dati from '../data.js';
import { distanzaM, formattaDistanza } from '../geo.js';
import { t } from '../i18n.js';
import * as posizione from '../position.js';
import { preferiti } from '../store.js';
import { el, svuota, vuoto } from '../ui.js';

const FILTRI = { testo: '', soloVerificati: false, conFontanella: false, livello: '', preferiti: null };
const TETTO_VISIBILE = 120;

let contesto = null;
let campo = null;
let contenitore = null;
let idPreferiti = new Set();
let mostrati = TETTO_VISIBILE;
/** Ogni ricerca ha un numero: se ne parte un'altra, la vecchia non scrive. */
let richiesta = 0;

/**
 * Da dove si misurano le distanze. La posizione vera se c'è; altrimenti il
 * centro della mappa — che è comunque dove stai guardando, e serve a chi
 * arriva in una città nuova e non vuole dare il permesso alla posizione.
 * La lista dice sempre quale delle due sta usando.
 */
function origineDistanze() {
  const mia = posizione.ultimaNota();
  if (mia) return { punto: mia, vera: true };
  const mappa = contesto && contesto.mappa;
  if (mappa && mappa.misurata) return { punto: mappa.centro, vera: false };
  return { punto: null, vera: false };
}

function riga(voce, origine) {
  const metri = origine.punto ? distanzaM(origine.punto, voce) : null;
  const pezzi = [
    voce.status === 'verified' ? t('spot.verified') : t('spot.community'),
    voce.level ? t(`spot.level.${voce.level}`) : null,
    voce.fountain ? t('spot.fountain') : null,
    metri === null ? null : formattaDistanza(metri),
  ].filter(Boolean);

  return el(
    'button',
    {
      class: 'pk-item',
      onclick: () => contesto.vaiA(`#/spot/${voce.id}`),
    },
    [
      el('span', {
        class: `pk-item__pin${voce.status === 'verified' ? '' : ' pk-item__pin--community'}`,
        'aria-hidden': 'true',
        testo: idPreferiti.has(voce.id) ? '★' : '⌖',
      }),
      el('span', { class: 'pk-item__body' }, [
        el('span', { class: 'pk-item__name', testo: voce.name }),
        el('span', { class: 'pk-item__meta', testo: pezzi.join(' · ') }),
      ]),
    ]
  );
}

async function disegna() {
  const origine = origineDistanze();
  const mia = ++richiesta;
  const elenco = await dati.cerca(
    { ...FILTRI, da: origine.punto, preferiti: FILTRI.preferiti },
    distanzaM
  );
  if (mia !== richiesta) return;
  svuota(contenitore);

  if (!elenco.length) {
    contenitore.append(vuoto(t('spots.empty')));
    return;
  }

  contenitore.append(
    el('p', { class: 'pk-small pk-muted' }, [
      t('spots.count', { n: elenco.length }),
      origine.punto
        ? ` · ${origine.vera ? t('spots.fromYou') : t('spots.fromMap')}`
        : '',
    ])
  );
  const lista = el('div', {}, elenco.slice(0, mostrati).map((voce) => riga(voce, origine)));
  contenitore.append(lista);

  if (elenco.length > mostrati) {
    contenitore.append(
      el(
        'button',
        {
          class: 'pk-btn pk-btn--fantasma pk-btn--largo',
          onclick: () => {
            mostrati += TETTO_VISIBILE;
            disegna();
          },
        },
        [t('spots.more')]
      )
    );
  }
}

function chip(etichetta, attivo, quandoTocca) {
  return el(
    'button',
    { class: 'pk-chip', 'aria-pressed': attivo ? 'true' : 'false', onclick: quandoTocca },
    [etichetta]
  );
}

function disegnaFiltri() {
  const barra = document.getElementById('pk-filtri');
  svuota(barra).append(
    chip(t('filter.verified'), FILTRI.soloVerificati, () => {
      FILTRI.soloVerificati = !FILTRI.soloVerificati;
      mostrati = TETTO_VISIBILE;
      disegnaFiltri();
      disegna();
    }),
    chip(t('filter.fountain'), FILTRI.conFontanella, () => {
      FILTRI.conFontanella = !FILTRI.conFontanella;
      mostrati = TETTO_VISIBILE;
      disegnaFiltri();
      disegna();
    }),
    chip(t('filter.saved'), Boolean(FILTRI.preferiti), async () => {
      FILTRI.preferiti = FILTRI.preferiti ? null : idPreferiti;
      mostrati = TETTO_VISIBILE;
      disegnaFiltri();
      disegna();
    }),
    ...['principiante', 'intermedio', 'avanzato'].map((livello) =>
      chip(t(`spot.level.${livello}`), FILTRI.livello === livello, () => {
        FILTRI.livello = FILTRI.livello === livello ? '' : livello;
        mostrati = TETTO_VISIBILE;
        disegnaFiltri();
        disegna();
      })
    )
  );
}

export async function inizializza(ctx) {
  contesto = ctx;
  campo = document.getElementById('pk-cerca');
  contenitore = document.getElementById('pk-lista');
  campo.placeholder = t('spots.search');
  campo.setAttribute('aria-label', t('spots.search'));

  let attesa = null;
  campo.addEventListener('input', () => {
    clearTimeout(attesa);
    attesa = setTimeout(() => {
      FILTRI.testo = campo.value;
      mostrati = TETTO_VISIBILE;
      disegna();
    }, 120);
  });

  idPreferiti = new Set(await preferiti());
  disegnaFiltri();
  disegna();
}

export async function entra() {
  idPreferiti = new Set(await preferiti());
  if (FILTRI.preferiti) FILTRI.preferiti = idPreferiti;
  disegna();
}

export function titolo() {
  return { titolo: t('nav.spots'), sotto: t('spots.subtitle', { n: dati.contaVerificati() }) };
}
