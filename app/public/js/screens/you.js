/* PkFAMILY — "Tu": installazione, offline, aspetto, i tuoi dati.
 *
 * È la schermata che rende l'app un'applicazione e non una pagina: da qui si
 * installa sulla schermata Home, si scarica in anticipo la mappa della zona,
 * si vede quanto spazio occupa e si cancella tutto in un tocco.
 */

import * as admin from '../admin.js';
import { CONFIG } from '../config.js';
import * as dati from '../data.js';
import { t, LINGUE } from '../i18n.js';
import { dimentica } from '../legal.js';
import * as offline from '../offline.js';
import { accoda, coda, dimenticaTutto, preferiti, scrivi, svuotaCoda } from '../store.js';
import { avviso, conferma, el, modale, svuota } from '../ui.js';

let contesto = null;
let contenitore = null;

function formattaByte(byte) {
  if (!byte) return '0 MB';
  const mega = byte / 1024 / 1024;
  if (mega < 1024) return `${mega.toFixed(mega < 10 ? 1 : 0)} MB`;
  return `${(mega / 1024).toFixed(1)} GB`;
}

function sezioneInstalla() {
  const scatola = el('div', { class: 'pk-card' }, [el('h3', { testo: t('you.install') })]);
  const installata =
    window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;

  if (installata) {
    scatola.append(el('p', { class: 'pk-small pk-muted', testo: t('you.installDone') }));
    return scatola;
  }

  if (contesto.invitoInstallazione) {
    scatola.append(
      el('p', { class: 'pk-small pk-muted', testo: t('you.installWhy') }),
      el(
        'button',
        {
          class: 'pk-btn pk-btn--largo',
          onclick: async () => {
            const invito = contesto.invitoInstallazione;
            contesto.invitoInstallazione = null;
            invito.prompt();
            await invito.userChoice;
            disegna();
          },
        },
        [t('you.installNow')]
      )
    );
    return scatola;
  }

  const iOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  scatola.append(
    el('p', { class: 'pk-small pk-muted', testo: t('you.installWhy') }),
    el('p', { class: 'pk-small', testo: iOS ? t('you.installIos') : t('you.installOther') })
  );
  return scatola;
}

async function sezioneOffline() {
  const scatola = el('div', { class: 'pk-card' }, [el('h3', { testo: t('you.offline') })]);
  const dato = await offline.stato();

  if (!dato) {
    scatola.append(el('p', { class: 'pk-small pk-muted', testo: t('you.offlineNoSw') }));
    return scatola;
  }

  scatola.append(
    el('p', { class: 'pk-small' }, [
      t('you.offlineFiles', { n: dato.app }),
      el('br'),
      t('you.offlineTiles', { n: dato.tiles }),
      el('br'),
      t('you.offlineSpace', { usato: formattaByte(dato.usage), totale: formattaByte(dato.quota) }),
    ]),
    el('p', { class: 'pk-mono pk-muted', testo: `v ${dato.version || '—'}` })
  );

  const avanzamento = el('p', { class: 'pk-small pk-muted' });
  const scarica = el(
    'button',
    {
      class: 'pk-btn pk-btn--largo',
      onclick: async () => {
        const mappa = contesto.mappa;
        if (!mappa) return;
        const indirizzi = offline.tessereDelRiquadro(
          mappa.riquadro(),
          mappa.sorgente,
          Math.round(mappa.zoom),
          Math.round(mappa.zoom) + 2
        );
        const peso = offline.stimaPeso(indirizzi.length);
        const procedi = await conferma(
          t('you.prepareTitle'),
          t('you.prepareAsk', { n: peso.tessere, peso: formattaByte(peso.byte) }),
          t('you.prepareGo'),
          t('common.cancel')
        );
        if (!procedi) return;

        scarica.disabled = true;
        await offline.rendiPersistente();
        const esito = await offline.scarica(indirizzi, (fatte, totale) => {
          avanzamento.textContent = t('you.prepareProgress', { fatte, totale });
        });
        scarica.disabled = false;
        avanzamento.textContent = t('you.prepareDone', {
          scaricate: esito.scaricate,
          saltate: esito.saltate,
          fallite: esito.fallite,
        });
      },
    },
    [t('you.prepare')]
  );

  scatola.append(
    el('p', { class: 'pk-small pk-muted', testo: t('you.prepareWhy') }),
    scarica,
    avanzamento,
    el(
      'button',
      {
        class: 'pk-btn pk-btn--fantasma pk-btn--largo',
        style: 'margin-top:8px',
        onclick: async () => {
          const procedi = await conferma(
            t('you.clearTiles'),
            t('you.clearTilesAsk'),
            t('you.clearTilesGo'),
            t('common.cancel')
          );
          if (!procedi) return;
          await offline.svuotaTessere();
          await disegna();
        },
      },
      [t('you.clearTiles')]
    )
  );

  if (contesto.aggiornamentoPronto) {
    scatola.append(
      el(
        'button',
        {
          class: 'pk-btn pk-btn--largo',
          style: 'margin-top:8px',
          onclick: () => contesto.applicaAggiornamento(),
        },
        [t('you.update')]
      )
    );
  }

  return scatola;
}

function sezioneAspetto() {
  const temi = [
    ['sistema', t('you.themeSystem')],
    ['chiaro', t('you.themeLight')],
    ['scuro', t('you.themeDark')],
  ];
  const attuale = document.documentElement.dataset.tema || 'sistema';

  return el('div', { class: 'pk-card' }, [
    el('h3', { testo: t('you.look') }),
    el(
      'div',
      { class: 'pk-row pk-row--wrap' },
      temi.map(([valore, etichetta]) =>
        el(
          'button',
          {
            class: 'pk-chip',
            'aria-pressed': attuale === valore ? 'true' : 'false',
            onclick: async () => {
              // Prima si scrive, poi si cambia l'aspetto. Cambiare l'aspetto
              // fa ridisegnare la mappa nello stesso istante, e una tela
              // intera davanti a una scrittura su IndexedDB la fa aspettare:
              // chi chiudesse l'app in quel momento la ritroverebbe com'era.
              await scrivi('tema', valore);
              document.documentElement.dataset.tema = valore;
              await disegna();
            },
          },
          [etichetta]
        )
      )
    ),
    el('h3', { style: 'margin-top:16px', testo: t('you.language') }),
    el(
      'div',
      { class: 'pk-row pk-row--wrap' },
      Object.entries(LINGUE).map(([codice, nome]) =>
        el(
          'button',
          {
            class: 'pk-chip',
            'aria-pressed': document.documentElement.lang === codice ? 'true' : 'false',
            onclick: async () => {
              await scrivi('lingua', codice);
              location.reload();
            },
          },
          [nome]
        )
      )
    ),
  ]);
}

async function sezioneDati() {
  const salvati = await preferiti();
  const inCoda = await coda();

  const scatola = el('div', { class: 'pk-card' }, [
    el('h3', { testo: t('you.yourData') }),
    el('p', { class: 'pk-small', testo: t('you.savedCount', { n: salvati.length }) }),
    el('p', { class: 'pk-small pk-muted', testo: t('you.dataStaysHere') }),
  ]);

  if (inCoda.length) {
    scatola.append(
      el('p', { class: 'pk-small', testo: t('you.queueCount', { n: inCoda.length }) }),
      el('p', { class: 'pk-small pk-muted', testo: t('you.queueNote') }),
      el(
        'button',
        {
          class: 'pk-btn pk-btn--fantasma pk-btn--largo',
          onclick: async () => {
            const testo = JSON.stringify(inCoda, null, 2);
            try {
              await navigator.clipboard.writeText(testo);
              avviso(t('you.queueCopied'));
            } catch {
              avviso(t('spot.copyFailed'));
            }
          },
        },
        [t('you.queueCopy')]
      ),
      el(
        'button',
        {
          class: 'pk-btn pk-btn--fantasma pk-btn--largo',
          style: 'margin-top:8px',
          onclick: async () => {
            const procedi = await conferma(
              t('you.queueClear'),
              t('you.queueClearAsk'),
              t('you.queueClear'),
              t('common.cancel')
            );
            if (procedi) {
              await svuotaCoda();
              disegna();
            }
          },
        },
        [t('you.queueClear')]
      )
    );
  }

  scatola.append(
    el(
      'button',
      {
        class: 'pk-btn pk-btn--fantasma pk-btn--largo',
        style: 'margin-top:16px;border-color:var(--rosso);color:var(--rosso)',
        onclick: async () => {
          const procedi = await conferma(
            t('you.reset'),
            t('you.resetAsk'),
            t('you.resetGo'),
            t('common.cancel')
          );
          if (!procedi) return;
          await dimenticaTutto();
          await dimentica();
          location.reload();
        },
      },
      [t('you.reset')]
    )
  );

  return scatola;
}

function sezioneAccount() {
  const configurato = Boolean(CONFIG.supabase.url);
  return el('div', { class: 'pk-card' }, [
    el('h3', { testo: t('you.account') }),
    el('p', {
      class: 'pk-small pk-muted',
      testo: configurato ? t('you.accountConfigured') : t('you.accountLocal'),
    }),
  ]);
}

/**
 * La prova e i poteri: da qui si dice all'app che chi la sta usando la sta
 * costruendo. Sta in fondo, e si accende a mano — non si eredita da un
 * indirizzo, da una rete o da un cookie.
 */
function sezioneAvanzate() {
  const costruzione = contesto.costruzione || { canale: 'sviluppo' };
  const scatola = el('div', { class: 'pk-card' }, [el('h3', { testo: t('you.advanced') })]);

  if (costruzione.canale === 'beta') {
    scatola.append(
      el('p', { class: 'pk-small', testo: t('you.betaWhat') }),
      el('p', {
        class: 'pk-mono pk-small pk-muted',
        testo: `beta ${costruzione.versione || '?'} · ${(costruzione.quando || '').slice(0, 10)}`,
      }),
      el(
        'button',
        {
          class: 'pk-btn pk-btn--largo',
          onclick: async () => {
            const area = el('textarea', {
              class: 'pk-input',
              rows: '4',
              style: 'min-height:96px;padding:8px 12px;margin-bottom:16px',
              placeholder: t('you.betaProblemPlaceholder'),
              'aria-label': t('you.betaProblem'),
            });
            const invia = await modale({
              titolo: t('you.betaProblem'),
              sommario: t('you.betaProblemNote'),
              corpo: area,
              azioni: [
                { testo: t('spot.fixQueue'), valore: true, primaria: true },
                { testo: t('common.cancel'), valore: false },
              ],
            });
            if (invia && area.value.trim()) {
              await accoda({
                tipo: 'problema_beta',
                testo: area.value.trim(),
                dove: location.hash || '#/mappa',
                versione: costruzione.versione || '',
                schermo: `${window.innerWidth}x${window.innerHeight}`,
              });
              avviso(t('spot.fixQueued'));
              disegna();
            }
          },
        },
        [t('you.betaProblem')]
      )
    );
  }

  scatola.append(
    el('p', { class: 'pk-small pk-muted', style: 'margin-top:12px', testo: t('you.devWhat') }),
    el(
      'button',
      {
        class: `pk-btn pk-btn--largo${admin.attiva() ? '' : ' pk-btn--fantasma'}`,
        onclick: async () => {
          if (admin.attiva()) {
            await admin.accendi(false);
            dati.riapplica();
            contesto.aggiornaFascia();
            if (contesto.mappa) contesto.mappa.ridisegna();
            await disegna();
            return;
          }
          const procedi = await conferma(
            t('you.devOn'),
            t('you.devAsk'),
            t('you.devGo'),
            t('common.cancel')
          );
          if (!procedi) return;
          await admin.accendi(true);
          contesto.aggiornaFascia();
          contesto.vaiA('#/admin');
        },
      },
      [admin.attiva() ? t('you.devOff') : t('you.devOn')]
    )
  );

  return scatola;
}

function sezioneInformazioni() {
  return el('div', { class: 'pk-card' }, [
    el('h3', { testo: t('you.about') }),
    el('p', { class: 'pk-small', testo: t('you.aboutSpots', { n: dati.spot().length, v: dati.contaVerificati() }) }),
    el('p', { class: 'pk-small pk-muted', testo: t('you.aboutOnlyVerified') }),
    el('p', { class: 'pk-small pk-muted', testo: t('you.credits') }),
  ]);
}

async function disegna() {
  svuota(contenitore).append(
    sezioneInstalla(),
    await sezioneOffline(),
    sezioneAspetto(),
    await sezioneDati(),
    sezioneAccount(),
    sezioneAvanzate(),
    sezioneInformazioni()
  );
}

export function inizializza(ctx) {
  contesto = ctx;
  contenitore = document.getElementById('pk-tu');
}

export function entra() {
  return disegna();
}

export function titolo() {
  return { titolo: t('nav.you'), sotto: '' };
}
