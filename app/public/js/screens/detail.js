/* PkFAMILY — la scheda di uno spot.
 *
 * È la schermata che si apre davanti a un muretto, spesso con una tacca di
 * rete: tutto quello che serve per decidere e per arrivarci sta qui e non
 * dipende dalla rete — nome, stato, descrizione, distanza, fontanelle,
 * coordinate. Il tragitto a piedi e le foto, che la rete la vogliono, si
 * aggiungono quando c'è.
 */

import * as admin from '../admin.js';
import * as dati from '../data.js';
import { distanzaM, formattaDistanza, formattaDurata } from '../geo.js';
import { t } from '../i18n.js';
import { avvisa } from '../legal.js';
import * as posizione from '../position.js';
import { percorso, stima } from '../route.js';
import { accoda, nota, preferiti, salvaNota, segnaPreferito } from '../store.js';
import { aggiungi, avviso, distintivo, el, modale, svuota } from '../ui.js';

let contesto = null;
let contenitore = null;
let corrente = null;

function foto(voce) {
  if (!voce.photos || !voce.photos.length) return null;
  const striscia = el('div', {
    style: 'display:flex;gap:8px;overflow-x:auto;margin-bottom:16px;scrollbar-width:none',
  });
  for (const indirizzo of voce.photos.slice(0, 6)) {
    const immagine = el('img', {
      src: indirizzo,
      alt: t('spot.photoAlt', { nome: voce.name }),
      loading: 'lazy',
      style:
        'height:150px;border-radius:14px;border:1px solid var(--cucitura);object-fit:cover;flex:none',
    });
    // Senza rete e senza cache la foto non c'è: si toglie invece di lasciare
    // l'icona rotta del browser.
    immagine.addEventListener('error', () => immagine.remove());
    striscia.append(immagine);
  }
  return striscia;
}

async function sezioneFontanelle(voce) {
  const elenco = await dati.fontanelleDi(voce.id);
  if (!elenco.length) return null;
  return el('div', { class: 'pk-card' }, [
    el('h3', { testo: t('spot.fountains') }),
    el('p', { class: 'pk-small pk-muted', testo: t('spot.fountainsSource') }),
    el(
      'ul',
      { style: 'margin:0;padding-left:18px' },
      elenco.slice(0, 5).map((fontanella) =>
        el('li', { class: 'pk-small' }, [
          `${t(`spot.water.${fontanella.kind}`)} — ${formattaDistanza(fontanella.distance_m)}`,
        ])
      )
    ),
  ]);
}

function sezioneDistanza(voce) {
  const mia = posizione.ultimaNota();
  const scatola = el('div', { class: 'pk-card' });

  const disegnaSenza = () => {
    svuota(scatola).append(
      el('h3', { testo: t('spot.howFar') }),
      el('p', { class: 'pk-small pk-muted', testo: t('spot.noPositionYet') }),
      el(
        'button',
        {
          class: 'pk-btn pk-btn--fantasma pk-btn--largo',
          onclick: async () => {
            try {
              await posizione.chiedi();
              disegnaCon();
            } catch {
              avviso(t('map.noPosition'));
            }
          },
        },
        [t('spot.usePosition')]
      )
    );
  };

  const disegnaCon = () => {
    const mio = posizione.ultimaNota();
    if (!mio) return disegnaSenza();
    const s = stima(mio, voce);
    svuota(scatola).append(
      el('h3', { testo: t('spot.howFar') }),
      el('p', {
        testo: t('spot.straight', {
          distanza: formattaDistanza(s.metri),
          cammino: formattaDurata(s.cammino),
          corsa: formattaDurata(s.corsa),
        }),
      }),
      el('p', { class: 'pk-small pk-muted', testo: t('spot.straightNote') }),
      el(
        'button',
        {
          class: 'pk-btn pk-btn--largo',
          disabled: !navigator.onLine,
          onclick: async (evento) => {
            const bottone = evento.currentTarget;
            bottone.disabled = true;
            bottone.textContent = t('spot.routeLoading');
            try {
              const esito = await percorso(mio, voce);
              if (contesto.mappa) contesto.mappa.mostraPercorso(esito.punti);
              svuota(scatola).append(
                el('h3', { testo: t('spot.route') }),
                el('p', {
                  testo: t('spot.routeResult', {
                    distanza: formattaDistanza(esito.metri),
                    tempo: formattaDurata(esito.secondi),
                  }),
                }),
                el('p', {
                  class: 'pk-small pk-muted',
                  testo: t('spot.routePrivacy', { metri: esito.precisione }),
                }),
                el(
                  'button',
                  {
                    class: 'pk-btn pk-btn--fantasma pk-btn--largo',
                    onclick: () => contesto.vaiA(`#/mappa/${voce.id}`),
                  },
                  [t('spot.seeOnMap')]
                )
              );
            } catch {
              bottone.disabled = false;
              bottone.textContent = t('spot.routeAsk');
              avviso(t('spot.routeFailed'));
            }
          },
        },
        [t('spot.routeAsk')]
      )
    );
  };

  if (mia) disegnaCon();
  else disegnaSenza();
  return scatola;
}

async function sezionePersonale(voce) {
  const salvati = new Set(await preferiti());
  const testoNota = await nota(voce.id);

  const bottone = el(
    'button',
    {
      class: `pk-btn pk-btn--largo${salvati.has(voce.id) ? '' : ' pk-btn--fantasma'}`,
      onclick: async () => {
        const nuovo = !salvati.has(voce.id);
        await segnaPreferito(voce.id, nuovo);
        if (nuovo) salvati.add(voce.id);
        else salvati.delete(voce.id);
        bottone.textContent = nuovo ? t('spot.saved') : t('spot.save');
        bottone.className = `pk-btn pk-btn--largo${nuovo ? '' : ' pk-btn--fantasma'}`;
      },
    },
    [salvati.has(voce.id) ? t('spot.saved') : t('spot.save')]
  );

  const area = el('textarea', {
    class: 'pk-input',
    rows: '3',
    style: 'min-height:80px;padding:8px 12px;resize:vertical',
    placeholder: t('spot.notePlaceholder'),
    'aria-label': t('spot.note'),
  });
  area.value = testoNota;
  let attesa = null;
  area.addEventListener('input', () => {
    clearTimeout(attesa);
    attesa = setTimeout(() => salvaNota(voce.id, area.value), 400);
  });

  return el('div', { class: 'pk-card' }, [
    el('h3', { testo: t('spot.yours') }),
    bottone,
    el('p', { class: 'pk-small pk-muted', style: 'margin-top:12px', testo: t('spot.noteNote') }),
    area,
  ]);
}

function sezioneCoordinate(voce) {
  const coordinate = `${voce.lat}, ${voce.lng}`;
  return el('div', { class: 'pk-card' }, [
    el('h3', { testo: t('spot.where') }),
    el('p', { class: 'pk-mono', testo: coordinate }),
    el('div', { class: 'pk-row pk-row--wrap' }, [
      el(
        'button',
        {
          class: 'pk-btn pk-btn--fantasma',
          onclick: async () => {
            try {
              await navigator.clipboard.writeText(coordinate);
              avviso(t('spot.copied'));
            } catch {
              avviso(t('spot.copyFailed'));
            }
          },
        },
        [t('spot.copy')]
      ),
      el(
        'a',
        {
          class: 'pk-btn pk-btn--fantasma',
          href: `geo:${voce.lat},${voce.lng}?q=${voce.lat},${voce.lng}(${encodeURIComponent(voce.name)})`,
          rel: 'noreferrer',
        },
        [t('spot.openInMaps')]
      ),
      el(
        'button',
        {
          class: 'pk-btn pk-btn--fantasma',
          onclick: () => contesto.vaiA(`#/mappa/${voce.id}`),
        },
        [t('spot.seeOnMap')]
      ),
    ]),
  ]);
}

function sezioneCorrezione(voce) {
  return el(
    'button',
    {
      class: 'pk-btn pk-btn--fantasma pk-btn--largo',
      onclick: async () => {
        const area = el('textarea', {
          class: 'pk-input',
          rows: '4',
          style: 'min-height:96px;padding:8px 12px;margin-bottom:16px',
          placeholder: t('spot.fixPlaceholder'),
          'aria-label': t('spot.fixTitle'),
        });
        const invia = await modale({
          titolo: t('spot.fixTitle'),
          sommario: t('spot.fixNote'),
          corpo: area,
          azioni: [
            { testo: t('spot.fixQueue'), valore: true, primaria: true },
            { testo: t('common.cancel'), valore: false },
          ],
        });
        if (invia && area.value.trim()) {
          await accoda({ tipo: 'correzione_spot', spot: voce.id, testo: area.value.trim() });
          avviso(t('spot.fixQueued'));
        }
      },
    },
    [t('spot.fix')]
  );
}

export function inizializza(ctx) {
  contesto = ctx;
  contenitore = document.getElementById('pk-dettaglio');
}

export async function entra(parametri) {
  const voce = dati.spotPerId(parametri.id);
  corrente = voce;
  svuota(contenitore);

  if (!voce) {
    contenitore.append(el('p', { testo: t('spot.missing') }));
    return;
  }

  // L'avviso sui rischi viene prima della scheda, come nell'app pubblicata.
  const procedi = await avvisa('spot');
  if (!procedi) {
    contesto.indietro();
    return;
  }

  aggiungi(
    contenitore,
    el('div', { class: 'pk-row pk-row--wrap', style: 'margin-bottom:8px' }, [
      distintivo(voce.status),
      voce.level ? el('span', { class: 'pk-badge', testo: t(`spot.level.${voce.level}`) }) : null,
      voce.crowd ? el('span', { class: 'pk-badge', testo: t(`spot.crowd.${voce.crowd}`) }) : null,
    ]),
    el('h1', { testo: voce.name }),
    voce.status !== 'verified'
      ? el('p', { class: 'pk-small pk-muted', testo: t('spot.communityNote') })
      : null,
    foto(voce),
    voce.description ? el('p', { testo: voce.description }) : null,
    sezioneDistanza(voce),
    sezioneCoordinate(voce),
    await sezionePersonale(voce),
    await sezioneFontanelle(voce),
    sezioneCorrezione(voce),
    admin.attiva()
      ? el(
          'button',
          {
            class: 'pk-btn pk-btn--fantasma pk-btn--largo',
            style: 'margin-top:8px;border-color:var(--ambra);color:var(--ambra)',
            onclick: () => contesto.vaiA(`#/admin/${voce.id}`),
          },
          [t('admin.editThis')]
        )
      : null
  );
  contenitore.scrollTop = 0;
}

export function titolo() {
  return { titolo: corrente ? corrente.name : t('nav.spots'), sotto: '', indietro: true };
}
