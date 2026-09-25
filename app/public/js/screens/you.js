/* PkFAMILY — "Tu": installazione, offline, aspetto, i tuoi dati.
 *
 * È la schermata che rende l'app un'applicazione e non una pagina: da qui si
 * installa sulla schermata Home, si scarica in anticipo la mappa della zona,
 * si vede quanto spazio occupa e si cancella tutto in un tocco.
 */

import * as admin from '../admin.js';
import * as auth from '../auth.js';
import * as dati from '../data.js';
import { t, LINGUE } from '../i18n.js';
import { dimentica } from '../legal.js';
import * as offline from '../offline.js';
import { accoda, coda, dimenticaTutto, preferiti, scrivi, svuotaCoda } from '../store.js';
import { aggiungi, avviso, conferma, el, modale, svuota } from '../ui.js';

let contesto = null;
let contenitore = null;

/** Sta già aspettando che il service worker finisca di installarsi? */
let attesaWorker = false;

function mostraAvanzamento(testo) {
  const nodo = document.getElementById('pk-offline-avanzamento');
  if (nodo) nodo.textContent = testo;
}

/** Quanti livelli di zoom in più si scaricano oltre a quello che si vede. */
const LIVELLI_IN_PIU = 3;

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

  if (globalThis.__PK_INLINE__) {
    // Demo in un file solo: non c'è nessuna cache da riempire, l'app è già
    // tutta qui. Dirle «non posso lavorare offline» sarebbe falso.
    scatola.append(el('p', { class: 'pk-small', testo: t('you.offlineSingleFile') }));
    return scatola;
  }

  const dato = await offline.stato();

  if (!dato) {
    scatola.append(el('p', { class: 'pk-small pk-muted', testo: t('you.offlineNoSw') }));
    // Alla primissima apertura il service worker sta ancora installando:
    // «qui l'app non può lavorare offline» sarebbe una bugia lunga un secondo.
    // Si aspetta che sia pronto e si ridisegna, una volta sola.
    if ('serviceWorker' in navigator && !attesaWorker) {
      attesaWorker = true;
      navigator.serviceWorker.ready.then(() => {
        attesaWorker = false;
        if (contenitore && contenitore.isConnected) disegna();
      });
    }
    return scatola;
  }

  scatola.append(
    el('p', { class: 'pk-small' }, [
      t('you.offlineFiles', { n: dato.app }),
      el('br'),
      t('you.offlineTiles', { n: dato.tiles }),
      el('br'),
      t('you.offlineArea', { n: dato.area || 0 }),
      el('br'),
      t('you.offlineSpace', { usato: formattaByte(dato.usage), totale: formattaByte(dato.quota) }),
    ]),
    el('p', { class: 'pk-mono pk-muted', testo: `v ${dato.version || '—'}` })
  );

  const avanzamento = el('p', {
    id: 'pk-offline-avanzamento',
    class: 'pk-small pk-muted',
    testo: offline.scaricamento.messaggio,
  });

  const scarica = el(
    'button',
    {
      class: 'pk-btn pk-btn--largo',
      disabled: offline.scaricamento.inCorso,
      onclick: async () => {
        const partito = await offline.preparaArea(contesto.mappa, {
          progresso: mostraAvanzamento,
          finito: () => disegna(),
        });
        if (partito) await disegna();
      },
    },
    [offline.scaricamento.inCorso ? t('you.prepareRunning') : t('you.prepare')]
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
          offline.scaricamento.messaggio = '';
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

/** Da un codice d'errore dell'accesso alla frase da mostrare. */
function messaggioAccesso(errore) {
  const codice = errore && errore.codice ? errore.codice : 'rifiutato';
  const frase = t(`auth.err.${codice}`);
  // `t` restituisce la chiave quando non la conosce: meglio una frase generica
  // che una stringa con dei punti dentro.
  return frase.startsWith('auth.err.') ? t('auth.err.rifiutato') : frase;
}

/**
 * Entrare con l'email: si chiede il codice, poi lo si scrive.
 *
 * Due finestre di fila invece di una sola con due caselle, perché fra la prima
 * e la seconda c'è un'attesa vera — la posta — e una finestra che resta aperta
 * mentre si va a cercare il codice in un'altra applicazione è una finestra che
 * su un telefono si perde.
 */
async function entraConEmail() {
  const casella = el('input', {
    class: 'pk-input',
    type: 'email',
    inputmode: 'email',
    autocomplete: 'email',
    placeholder: 'nome@esempio.it',
    'aria-label': t('you.emailLabel'),
  });
  const manda = await modale({
    titolo: t('you.codeTitle'),
    sommario: t('you.codeAsk'),
    corpo: casella,
    azioni: [
      { testo: t('you.codeSend'), valore: true, primaria: true },
      { testo: t('common.cancel'), valore: false },
    ],
  });
  if (!manda) return;

  const indirizzo = casella.value.trim();
  try {
    await auth.chiediCodice(indirizzo);
  } catch (errore) {
    avviso(messaggioAccesso(errore));
    return;
  }

  // Si può sbagliare a copiare sei cifre: si richiede senza rifare tutto.
  for (;;) {
    const cifre = el('input', {
      class: 'pk-input',
      inputmode: 'numeric',
      autocomplete: 'one-time-code',
      maxlength: '8',
      'aria-label': t('you.codeEnter'),
    });
    const entra = await modale({
      titolo: t('you.codeTitle'),
      sommario: t('you.codeSent', { email: indirizzo }),
      corpo: cifre,
      azioni: [
        { testo: t('you.codeGo'), valore: true, primaria: true },
        { testo: t('common.cancel'), valore: false },
      ],
    });
    if (!entra) return;
    try {
      await auth.verificaCodice(indirizzo, cifre.value);
      avviso(t('you.signedIn'));
      return;
    } catch (errore) {
      avviso(messaggioAccesso(errore));
      if (!errore || errore.codice !== 'codice_errato') return;
    }
  }
}

/**
 * L'account, quello vero.
 *
 * Senza un progetto configurato la sezione resta quella di prima: l'app è
 * locale e lo dice. Con un progetto configurato si entra davvero — con
 * l'email o come ospite — e quello che si vede qui viene da `auth.users` e da
 * `profiles`, non da una finzione locale.
 */
function sezioneAccount() {
  const scatola = el('div', { class: 'pk-card' }, [el('h3', { testo: t('you.account') })]);

  if (!auth.configurato()) {
    scatola.append(el('p', { class: 'pk-small pk-muted', testo: t('you.accountLocal') }));
    return scatola;
  }

  const chi = auth.utente();
  if (!chi) {
    return aggiungi(
      scatola,
      el('p', { class: 'pk-small pk-muted', testo: t('you.accountWhy') }),
      el('button', { class: 'pk-btn pk-btn--largo', onclick: entraConEmail }, [t('you.signIn')]),
      el('p', {
        class: 'pk-small pk-muted',
        style: 'margin-top:16px',
        testo: t('you.guestWhy'),
      }),
      el(
        'button',
        {
          class: 'pk-btn pk-btn--fantasma pk-btn--largo',
          onclick: async () => {
            try {
              await auth.entraComeOspite();
              avviso(t('you.signedIn'));
            } catch (errore) {
              avviso(messaggioAccesso(errore));
            }
          },
        },
        [t('you.signInGuest')]
      )
    );
  }

  const nome = chi.nome || chi.email || t('you.guestBadge');
  return aggiungi(
    scatola,
    el('p', { testo: t('you.signedAs', { nome }) }),
    chi.anonimo ? el('p', { class: 'pk-small pk-muted', testo: t('you.guestNow') }) : null,
    chi.ruolo === 'admin' || chi.ruolo === 'instructor'
      ? el('p', { class: 'pk-small pk-muted', testo: t(`you.role.${chi.ruolo}`) })
      : null,
    el('p', { class: 'pk-small pk-muted', style: 'margin-top:12px', testo: t('you.accountOne') }),
    el(
      'button',
      {
        class: 'pk-btn pk-btn--fantasma pk-btn--largo',
        onclick: async () => {
          const procedi = await conferma(
            t('you.signOut'),
            chi.anonimo ? t('you.signOutGuestAsk') : t('you.signOutAsk'),
            t('you.signOut'),
            t('common.cancel')
          );
          if (!procedi) return;
          await auth.esci();
        },
      },
      [t('you.signOut')]
    )
  );
}

/**
 * La prova e i poteri: da qui si dice all'app che chi la sta usando la sta
 * costruendo. Sta in fondo, e **si accende con un tocco**: non si eredita da
 * una rete, da un cookie o da un indirizzo.
 *
 * C'è un secondo modo di arrivare a questo tocco, e non è un'eccezione:
 * `#/sviluppatore` (il QR di `qr.py --admin`) mette davanti la stessa
 * decisione di questo pulsante, spiegata con le parole di chi ci è arrivato
 * da un QR (`admin.qrAsk` invece di `you.devAsk`). Offre, non accende. `#/admin` invece non
 * accende niente in nessun caso — un indirizzo scritto a mano, o arrivato in
 * un messaggio, non deve dare poteri a nessuno.
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

/**
 * Quale ridisegno è l'ultimo partito.
 *
 * `disegna` aspetta due volte (lo spazio occupato, i preferiti), e in mezzo
 * un altro ridisegno può partire: basta entrare mentre la schermata sta già
 * rispondendo a qualcos'altro. Prima ognuno svuotava e poi ognuno attaccava il
 * suo, e la schermata compariva doppia — due «Sei dentro come…», due pulsanti
 * «Esci». Non è un caso di laboratorio: l'accesso avvisa due volte, una quando
 * la sessione è aperta e una quando arriva il nome dal profilo.
 */
let generazione = 0;

async function disegna() {
  const mia = ++generazione;
  const pezzi = [
    sezioneInstalla(),
    await sezioneOffline(),
    sezioneAspetto(),
    await sezioneDati(),
    sezioneAccount(),
    sezioneAvanzate(),
    sezioneInformazioni(),
  ];
  // Vince l'ultimo partito, e il contenitore si svuota solo quando i pezzi
  // nuovi ci sono già: nessuno vede la schermata vuota per un istante.
  if (mia !== generazione) return;
  svuota(contenitore).append(...pezzi);
}

export function inizializza(ctx) {
  contesto = ctx;
  contenitore = document.getElementById('pk-tu');
  // Entrare e uscire non passano sempre da qui: il rinnovo di un gettone
  // scaduto può cadere mentre la schermata è già aperta. Si ridisegna quando
  // l'accesso cambia, non quando si torna sulla schermata.
  auth.ascolta(() => {
    const sezione = contenitore && contenitore.closest('.pk-screen');
    if (sezione && sezione.dataset.attiva === '1') disegna();
  });
}

export function entra() {
  return disegna();
}

export function titolo() {
  return { titolo: t('nav.you'), sotto: '' };
}
