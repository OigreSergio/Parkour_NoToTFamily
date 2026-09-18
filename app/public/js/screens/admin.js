/* PkFAMILY — il pannello della modalità sviluppatore.
 *
 * È il posto da cui si cambiano le cose senza aprire un editor: correggere
 * uno spot, spostarne il punto, provare un altro filtro sulle tessere,
 * puntare l'app a un altro server. Le etichette sono i nomi veri delle chiavi
 * di configurazione, non parole gentili: chi apre questo pannello deve poter
 * ritrovare la stessa chiave in `js/config.js`.
 *
 * Quello che si fa qui resta qui finché non lo si esporta (vedi js/admin.js).
 */

import * as admin from '../admin.js';
import * as dati from '../data.js';
import { t } from '../i18n.js';
import { aggiungi, avviso, conferma, el, svuota } from '../ui.js';

let contesto = null;
let contenitore = null;
let spotScelto = null;
let filtroRicerca = '';

/** Un campo con l'etichetta sopra: l'etichetta è la chiave vera. */
function campo(etichetta, controllo, aiuto) {
  return el('label', { style: 'display:block;margin-bottom:12px' }, [
    el('span', { class: 'pk-mono pk-small pk-muted', testo: etichetta }),
    controllo,
    aiuto ? el('span', { class: 'pk-small pk-muted', style: 'display:block', testo: aiuto }) : null,
  ]);
}

function riga(etichetta, valore) {
  return el('p', { class: 'pk-small', style: 'margin:0 0 4px' }, [
    el('span', { class: 'pk-muted', testo: `${etichetta}: ` }),
    el('span', { testo: String(valore) }),
  ]);
}

/** Scarica un oggetto come file JSON, senza passare da nessun server. */
function scarica(nome, oggetto) {
  const testo = JSON.stringify(oggetto, null, 2);
  const indirizzo = URL.createObjectURL(new Blob([testo], { type: 'application/json' }));
  const collegamento = el('a', { href: indirizzo, download: nome });
  document.body.append(collegamento);
  collegamento.click();
  collegamento.remove();
  setTimeout(() => URL.revokeObjectURL(indirizzo), 4000);
}

// --- spot -------------------------------------------------------------------

function controlloSpot(voce, definizione) {
  const valore = voce[definizione.nome];
  if (definizione.tipo === 'booleano') {
    const casella = el('input', { type: 'checkbox', class: 'pk-input', style: 'width:auto;min-height:auto' });
    casella.checked = Boolean(valore);
    return casella;
  }
  if (definizione.tipo === 'scelta') {
    const scelta = el(
      'select',
      { class: 'pk-input' },
      definizione.valori.map((v) => el('option', { value: v, testo: v }))
    );
    scelta.value = valore || definizione.valori[0];
    return scelta;
  }
  if (definizione.tipo === 'lungo') {
    const area = el('textarea', { class: 'pk-input', rows: '3', style: 'min-height:76px;padding:8px 12px' });
    area.value = valore || '';
    return area;
  }
  const casella = el('input', {
    class: 'pk-input',
    type: definizione.tipo === 'numero' ? 'number' : 'text',
    step: definizione.tipo === 'numero' ? 'any' : null,
  });
  casella.value = valore === undefined || valore === null ? '' : String(valore);
  return casella;
}

function schedaSpot(voce) {
  const controlli = new Map();
  const corpo = el('div', {});

  for (const definizione of admin.CAMPI_SPOT) {
    const controllo = controlloSpot(voce, definizione);
    controlli.set(definizione.nome, { controllo, definizione });
    corpo.append(campo(definizione.nome, controllo));
  }

  const leggi = () => {
    const campi = {};
    for (const [nome, { controllo, definizione }] of controlli) {
      campi[nome] = definizione.tipo === 'booleano' ? controllo.checked : controllo.value;
    }
    return campi;
  };

  return el('div', { class: 'pk-card', id: 'pk-admin-spot' }, [
    el('div', { class: 'pk-row' }, [
      el('h3', { testo: voce.name || t('admin.newSpot'), style: 'flex:1;min-width:0' }),
      voce.locale ? el('span', { class: 'pk-badge pk-badge--attesa', testo: t('admin.local') }) : null,
    ]),
    el('p', { class: 'pk-mono pk-small pk-muted', testo: voce.id || '—' }),
    corpo,
    el('div', { class: 'pk-row pk-row--wrap' }, [
      el(
        'button',
        {
          class: 'pk-btn',
          onclick: async () => {
            const campi = leggi();
            if (voce.id) await admin.salvaSpot(voce.id, campi);
            else spotScelto = await admin.creaSpot(campi);
            dati.riapplica();
            if (voce.id) spotScelto = dati.spotPerId(voce.id) || spotScelto;
            avviso(t('admin.saved'));
            aggiornaMappa();
            disegna();
          },
        },
        [t('admin.save')]
      ),
      contesto.mappa
        ? el(
            'button',
            {
              class: 'pk-btn pk-btn--fantasma',
              onclick: () => {
                const centro = contesto.mappa.centro;
                controlli.get('lat').controllo.value = centro.lat.toFixed(5);
                controlli.get('lng').controllo.value = centro.lng.toFixed(5);
                avviso(t('admin.tookCentre'));
              },
            },
            [t('admin.takeCentre')]
          )
        : null,
      voce.id
        ? el(
            'button',
            {
              class: 'pk-btn pk-btn--fantasma',
              onclick: async () => {
                await admin.ripristinaSpot(voce.id);
                dati.riapplica();
                spotScelto = dati.spotPerId(voce.id);
                aggiornaMappa();
                disegna();
              },
            },
            [t('admin.restore')]
          )
        : null,
      voce.id
        ? el(
            'button',
            {
              class: 'pk-btn pk-btn--fantasma',
              style: 'border-color:var(--rosso);color:var(--rosso)',
              onclick: async () => {
                const procedi = await conferma(
                  t('admin.deleteSpot'),
                  t('admin.deleteAsk', { nome: voce.name }),
                  t('admin.deleteGo'),
                  t('common.cancel')
                );
                if (!procedi) return;
                await admin.cancellaSpot(voce.id);
                dati.riapplica();
                spotScelto = null;
                aggiornaMappa();
                disegna();
              },
            },
            [t('admin.deleteSpot')]
          )
        : null,
    ]),
  ]);
}

function sezioneSpot() {
  const ricerca = el('input', {
    class: 'pk-input',
    type: 'search',
    placeholder: t('admin.searchSpot'),
    'aria-label': t('admin.searchSpot'),
  });
  ricerca.value = filtroRicerca;
  let attesa = null;
  ricerca.addEventListener('input', () => {
    clearTimeout(attesa);
    attesa = setTimeout(() => {
      filtroRicerca = ricerca.value;
      spotScelto = null;
      disegna();
      const rifatto = contenitore.querySelector('input[type="search"]');
      if (rifatto) {
        rifatto.focus();
        rifatto.setSelectionRange(rifatto.value.length, rifatto.value.length);
      }
    }, 250);
  });

  const trovati = filtroRicerca ? dati.cerca({ testo: filtroRicerca }).slice(0, 8) : [];

  return el('div', { class: 'pk-card' }, [
    el('h3', { testo: t('admin.spots') }),
    ricerca,
    el(
      'div',
      { style: 'margin-top:8px' },
      trovati.map((voce) =>
        el(
          'button',
          {
            class: 'pk-item',
            onclick: () => {
              spotScelto = voce;
              disegna();
            },
          },
          [
            el('span', { class: 'pk-item__body' }, [
              el('span', { class: 'pk-item__name', testo: voce.name }),
              el('span', {
                class: 'pk-item__meta',
                testo: `${voce.status}${voce.locale ? ' · ' + t('admin.local') : ''} · ${voce.lat}, ${voce.lng}`,
              }),
            ]),
          ]
        )
      )
    ),
    el(
      'button',
      {
        class: 'pk-btn pk-btn--fantasma pk-btn--largo',
        style: 'margin-top:8px',
        onclick: () => {
          const centro = contesto.mappa ? contesto.mappa.centro : { lat: 41.9, lng: 12.48 };
          spotScelto = { name: '', description: '', lat: +centro.lat.toFixed(5), lng: +centro.lng.toFixed(5) };
          disegna();
        },
      },
      [t('admin.newSpot')]
    ),
  ]);
}

// --- configurazione ---------------------------------------------------------

/** Una chiave segreta non deve poter entrare in un client, nemmeno per prova. */
function sembraSegreta(valore) {
  const testo = String(valore || '');
  return /service_role|sb_secret|^eyJ[\w-]+\.[\w-]+\.[\w-]+$/.test(testo) && !testo.startsWith('sb_publishable');
}

function sezioneConfig(gruppo, titolo) {
  const campi = admin.CAMPI_CONFIG.filter((c) => c.gruppo === gruppo);
  const scatola = el('div', { class: 'pk-card' }, [el('h3', { testo: titolo })]);

  for (const definizione of campi) {
    const valore = admin.valoreConfig(definizione.via);
    const controllo = el('input', {
      class: 'pk-input',
      type: definizione.tipo === 'numero' ? 'number' : 'text',
      step: definizione.tipo === 'numero' ? 'any' : null,
    });
    controllo.value = valore === undefined || valore === null ? '' : String(valore);
    controllo.addEventListener('change', async () => {
      if (definizione.via === 'supabase.publishableKey' && sembraSegreta(controllo.value)) {
        controllo.value = '';
        avviso(t('admin.secretRefused'));
        return;
      }
      const nuovo =
        definizione.tipo === 'numero' ? Number(controllo.value) : controllo.value.trim();
      await admin.impostaConfig(
        definizione.via,
        controllo.value === '' ? undefined : nuovo
      );
      if (contesto.mappa) contesto.mappa.ridisegna();
      aggiornaConteggi();
      avviso(t('admin.applied'));
    });
    const aiuto = t(`admin.aiuto.${definizione.via}`);
    scatola.append(campo(definizione.via, controllo, aiuto.startsWith('admin.aiuto.') ? null : aiuto));
  }

  return scatola;
}

// --- esportazione -----------------------------------------------------------

function conteggi() {
  const conti = admin.conteggi();
  return el('div', { id: 'pk-admin-conti' }, [
    riga(t('admin.changed'), conti.modificati),
    riga(t('admin.added'), conti.nuovi),
    riga(t('admin.removed'), conti.cancellati),
    riga(t('admin.settings'), conti.config),
  ]);
}

function aggiornaConteggi() {
  const vecchi = document.getElementById('pk-admin-conti');
  if (vecchi) vecchi.replaceWith(conteggi());
}

function sezioneFile() {
  const ingresso = el('input', { type: 'file', accept: 'application/json', style: 'display:none' });
  ingresso.addEventListener('change', async () => {
    const file = ingresso.files && ingresso.files[0];
    if (!file) return;
    try {
      const conteggi = await admin.importa(JSON.parse(await file.text()));
      dati.riapplica();
      aggiornaMappa();
      avviso(t('admin.imported', { n: conteggi.modificati + conteggi.nuovi }));
      disegna();
    } catch (errore) {
      avviso(`${t('admin.importFailed')} ${errore.message}`);
    }
  });

  return el('div', { class: 'pk-card' }, [
    el('h3', { testo: t('admin.files') }),
    conteggi(),
    el('p', { class: 'pk-small pk-muted', testo: t('admin.filesNote') }),
    el(
      'button',
      {
        class: 'pk-btn pk-btn--largo',
        onclick: () => scarica('pkfamily-sovrascritture.json', admin.esporta()),
      },
      [t('admin.exportAll')]
    ),
    el(
      'button',
      {
        class: 'pk-btn pk-btn--fantasma pk-btn--largo',
        style: 'margin-top:8px',
        onclick: () =>
          scarica('pkfamily-spot-da-rivedere.json', admin.esportaPerIlRepository(dati.spotDelFile())),
      },
      [t('admin.exportSpots')]
    ),
    el(
      'button',
      {
        class: 'pk-btn pk-btn--fantasma pk-btn--largo',
        style: 'margin-top:8px',
        onclick: () => ingresso.click(),
      },
      [t('admin.import')]
    ),
    ingresso,
    el(
      'button',
      {
        class: 'pk-btn pk-btn--fantasma pk-btn--largo',
        style: 'margin-top:16px;border-color:var(--rosso);color:var(--rosso)',
        onclick: async () => {
          const procedi = await conferma(
            t('admin.reset'),
            t('admin.resetAsk'),
            t('admin.resetGo'),
            t('common.cancel')
          );
          if (!procedi) return;
          await admin.azzera();
          dati.riapplica();
          spotScelto = null;
          aggiornaMappa();
          disegna();
        },
      },
      [t('admin.reset')]
    ),
  ]);
}

function aggiornaMappa() {
  if (contesto.mappa) contesto.mappa.ridisegna();
  if (contesto.aggiornaMappa) contesto.aggiornaMappa();
}

// --- schermata --------------------------------------------------------------

function disegna() {
  aggiungi(
    svuota(contenitore),
    el('div', { class: 'pk-card', style: 'border-color:var(--ambra)' }, [
      el('h3', { testo: t('admin.title') }),
      el('p', { class: 'pk-small', testo: t('admin.rule1') }),
      el('p', { class: 'pk-small', testo: t('admin.rule2') }),
      el('p', { class: 'pk-small', testo: t('admin.rule3') }),
      el(
        'button',
        {
          class: 'pk-btn pk-btn--fantasma pk-btn--largo',
          onclick: async () => {
            await admin.accendi(false);
            dati.riapplica();
            aggiornaMappa();
            contesto.aggiornaFascia();
            contesto.vaiA('#/tu');
          },
        },
        [t('admin.turnOff')]
      ),
    ]),
    sezioneSpot(),
    spotScelto ? schedaSpot(spotScelto) : null,
    sezioneConfig('mappa', t('admin.groupMap')),
    sezioneConfig('collegamenti', t('admin.groupLinks')),
    sezioneConfig('offline', t('admin.groupOffline')),
    sezioneFile()
  );
}

export function inizializza(ctx) {
  contesto = ctx;
  contenitore = document.getElementById('pk-admin');
}

export function entra(parametri) {
  if (parametri && parametri.id) {
    const voce = dati.spotPerId(parametri.id);
    if (voce) {
      spotScelto = voce;
      filtroRicerca = voce.name;
    }
  }
  disegna();
  contenitore.scrollTop = 0;
}

export function titolo() {
  return { titolo: t('admin.title'), sotto: t('admin.subtitle'), indietro: true };
}
