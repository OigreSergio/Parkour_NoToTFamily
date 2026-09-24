/* PkFAMILY — il pannello della modalità sviluppatore.
 *
 * È il posto da cui si cambiano le cose senza aprire un editor: correggere
 * uno spot o un tutorial, spostarne il punto, provare un altro filtro sulle
 * tessere, puntare l'app a un altro server, guardare cosa si è tenuta sul
 * dispositivo. Le etichette sono i nomi veri delle chiavi, non parole
 * gentili: chi apre questo pannello deve poter ritrovare la stessa chiave in
 * `js/config.js` o dentro `data/spots.json`.
 *
 * Tre scelte che tengono in piedi il resto:
 *
 * 1. **Niente schema scritto a mano.** I campi di una collezione arrivano da
 *    `admin.campiDi(nome)`, che li deduce dai dati; le impostazioni da
 *    `admin.campiConfig()`, che elenca le foglie di CONFIG. Aggiungere un
 *    campo a `build_data.py` lo fa comparire qui senza toccare questo file —
 *    ed è il motivo per cui il pannello copre 24 impostazioni invece di 11.
 * 2. **Una sezione dati alla volta.** Una sola casella di ricerca, uno solo
 *    stato di selezione. Tre elenchi affiancati vorrebbero dire tre caselle,
 *    e rimettere a fuoco dopo la ricerca ne troverebbe sempre la prima.
 * 3. **Il pannello avvisa, non impedisce.** Un valore che nessuna schermata
 *    sa leggere si salva lo stesso, dopo aver detto cosa succederà. L'unica
 *    cosa che viene rifiutata davvero è una chiave che sembra segreta, e quel
 *    rifiuto sta in `admin.js`, dove vale su ogni scrittura.
 *
 * Quello che si fa qui resta qui finché non lo si esporta (vedi js/admin.js).
 */

import * as admin from '../admin.js';
import * as dati from '../data.js';
import { t } from '../i18n.js';
import * as offline from '../offline.js';
import { elimina, scrivi, supporto, tutto } from '../store.js';
import { aggiungi, avviso, conferma, el, modale, svuota } from '../ui.js';

let contesto = null;
let contenitore = null;

/** La collezione aperta, e la voce scelta dentro quella collezione. */
let collezione = 'spot';
let scelta = null;

/** Il filtro di ricerca, uno per collezione: cambiando pastiglia non si perde. */
const filtri = new Map();

/** Quante voci si vedono adesso nell'elenco. Cresce di 20 alla volta. */
const PASSO_ELENCO = 20;
let quanteMostrate = PASSO_ELENCO;

/**
 * Quali sezioni sono aperte.
 *
 * Vive qui e non nel DOM perché `disegna()` ricostruisce tutto: senza, ogni
 * salvataggio richiuderebbe le sezioni che si erano aperte per lavorare.
 * Alla prima apertura sono aperte le tre sezioni in cui si *agisce* — Dati,
 * Configurazione, File. Stato e Magazzino restano chiuse: si leggono per
 * consultazione, e sono le due che costano (`offline.stato()` può metterci
 * sei secondi, e leggere tutto il magazzino non è gratis).
 */
const aperte = new Set(['dati', 'config', 'file']);

/** Lo stato dell'app e il magazzino si leggono all'apertura, non a ogni disegno. */
let statoLetto = null;
let magazzinoLetto = null;

// --- mattoni ----------------------------------------------------------------

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

/**
 * Una sezione che si apre e si chiude, e che si ricorda com'era.
 *
 * `chiave` è il nome con cui lo stato aperto/chiuso sopravvive a `disegna()`.
 */
function sezione(chiave, titolo, contenuto, extra = null) {
  const dettagli = el('details', { class: 'pk-card', 'data-sezione': chiave });
  dettagli.open = aperte.has(chiave);
  dettagli.addEventListener('toggle', () => {
    if (dettagli.open) aperte.add(chiave);
    else aperte.delete(chiave);
    // Stato e magazzino costano: si leggono quando qualcuno li guarda.
    if (dettagli.open && (chiave === 'stato' || chiave === 'magazzino')) disegna();
  });
  const sommario = el('summary', { style: 'cursor:pointer;font-weight:600' }, [titolo]);
  return aggiungi(dettagli, sommario, extra, contenuto);
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

/** Un valore qualunque, scritto in una riga sola e senza sorprese. */
function inBreve(valore, massimo = 120) {
  const testo =
    valore === null || valore === undefined
      ? '—'
      : typeof valore === 'object'
        ? JSON.stringify(valore)
        : String(valore);
  return testo.length > massimo ? `${testo.slice(0, massimo)}…` : testo;
}

function aggiornaMappa() {
  if (contesto.mappa) contesto.mappa.ridisegna();
  if (contesto.aggiornaMappa) contesto.aggiornaMappa();
}

// --- controlli --------------------------------------------------------------

/**
 * Il controllo giusto per un campo, dedotto dal suo tipo.
 *
 * Il caso `scelta` porta sempre in fondo una voce «altro…»: lo schema è
 * dedotto dai dati che ci sono, non è una regola di prodotto, e chi sta
 * correggendo deve poter scrivere un valore che nel file non compare ancora.
 * Un menù senza valore parte vuoto e mai dal primo della lista: partire dal
 * primo voleva dire proporre `verified` a ogni spot nuovo, e farlo salvare a
 * chi quel campo non lo aveva nemmeno guardato.
 */
function controllo(definizione, valore) {
  if (definizione.tipo === 'booleano') {
    const casella = el('input', {
      type: 'checkbox',
      class: 'pk-input',
      style: 'width:auto;min-height:auto',
    });
    casella.checked = Boolean(valore);
    return casella;
  }

  if (definizione.tipo === 'json') {
    const area = el('textarea', {
      class: 'pk-input pk-mono',
      rows: '3',
      style: 'min-height:76px;padding:8px 12px',
    });
    area.value = valore === undefined || valore === null ? '' : JSON.stringify(valore);
    return area;
  }

  if (definizione.tipo === 'scelta') {
    const dentro = definizione.valori.includes(valore);
    const voci = definizione.valori.map((v) => el('option', { value: v, testo: v }));
    if (!valore) voci.unshift(el('option', { value: '', testo: '—' }));
    voci.push(el('option', { value: '\u0000altro', testo: t('admin.other') }));
    const menu = el('select', { class: 'pk-input' }, voci);
    const libero = el('input', { class: 'pk-input', type: 'text', style: 'margin-top:6px' });

    // Un valore che nei dati non c'è (arriva da un file importato, o da un
    // «altro…» di prima) non deve sparire dal menù: si mostra il campo libero
    // già pieno, altrimenti il primo salvataggio lo cancellerebbe.
    libero.hidden = dentro || !valore;
    libero.value = dentro ? '' : valore || '';
    menu.value = dentro ? valore : valore ? '\u0000altro' : '';

    menu.addEventListener('change', () => {
      libero.hidden = menu.value !== '\u0000altro';
      if (!libero.hidden) libero.focus();
    });

    const scatola = el('div', {}, [menu, libero]);
    scatola.pkLeggi = () => (menu.value === '\u0000altro' ? libero.value : menu.value);
    return scatola;
  }

  if (definizione.tipo === 'lungo') {
    const area = el('textarea', {
      class: 'pk-input',
      rows: '3',
      style: 'min-height:76px;padding:8px 12px',
    });
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

/** Quello che un controllo ha dentro adesso, nella forma grezza. */
function leggiControllo(nodo, definizione) {
  if (nodo.pkLeggi) return nodo.pkLeggi();
  if (definizione.tipo === 'booleano') return nodo.checked;
  return nodo.value;
}

// --- conseguenze -------------------------------------------------------------

/**
 * Cosa farà l'app di questi valori, detto prima di salvare.
 *
 * Non è una convalida: è la lettura dei punti di chiamata veri. `ui.distintivo`
 * guarda solo `verified`; `tinta()` in map.js lascia blu tutto ciò che non è
 * verified o pending; spots.js stampa la chiave grezza `spot.level.<valore>`
 * perché `i18n.t` restituisce la chiave quando non la trova; `nelRiquadro`
 * scarta le coordinate fuori intervallo. Ognuna di queste righe corrisponde a
 * una di quelle.
 *
 * **Si guarda solo quello che è cambiato.** Uno dei 26 spot verificati dalla
 * famiglia è già `verified` nel file: avvisare che «verified messo a mano vale
 * solo su questo telefono» a chi ha corretto una virgola nella descrizione non
 * è un aiuto, è un riquadro da chiudere ogni volta. Un avviso che compare
 * sempre è un avviso che non si legge più.
 */
function conseguenze(nome, campi, schema, nelFile) {
  if (nome !== 'spot') return [];
  const fuori = [];
  const stati = new Set(['verified', 'community', 'pending']);
  const livelli = new Set(['principiante', 'intermedio', 'avanzato']);

  const cambiato = (chiave) => {
    if (!nelFile) return chiave in campi;
    const prima = nelFile[chiave];
    const dopo = campi[chiave];
    return typeof prima === 'object' || typeof dopo === 'object'
      ? JSON.stringify(prima) !== JSON.stringify(dopo)
      : String(prima ?? '') !== String(dopo ?? '');
  };

  if (cambiato('status') && campi.status && !stati.has(campi.status)) {
    fuori.push(t('admin.consequence.status', { valore: campi.status }));
  }
  if (cambiato('status') && campi.status === 'verified') {
    fuori.push(t('admin.consequence.verified'));
  }
  if (cambiato('level') && campi.level && !livelli.has(campi.level)) {
    fuori.push(t('admin.consequence.level', { valore: campi.level }));
  }
  if (cambiato('lat') || cambiato('lng')) {
    const lat = Number(campi.lat);
    const lng = Number(campi.lng);
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) {
      fuori.push(t('admin.consequence.coord'));
    }
  }
  if ('name' in campi && !String(campi.name || '').trim()) {
    fuori.push(t('admin.consequence.name'));
  }
  for (const [chiave, valore] of Object.entries(campi)) {
    if (cambiato(chiave) && typeof valore === 'string' && valore.startsWith('http://')) {
      fuori.push(t('admin.consequence.http'));
      break;
    }
  }
  const conosciuti = new Set(schema.map((d) => d.nome));
  const sconosciuti = Object.keys(campi).filter(
    (k) => !conosciuti.has(k) && !(nelFile && k in nelFile)
  );
  if (sconosciuti.length) fuori.push(t('admin.consequence.unknown'));

  return fuori;
}

// --- la scheda di una voce ---------------------------------------------------

/**
 * La scheda di un record: i campi dedotti, l'ispettore, il confronto con il
 * file, «da rivedere», i pulsanti.
 *
 * L'ordine non è estetico. I campi dello schema stanno **prima** di tutto il
 * resto perché `#pk-admin-spot input` preso per primo deve restare `name`:
 * `id` è reso come testo e non come casella, e le prove esistenti contano su
 * questo. Spostare qualcosa sopra i campi rompe quelle prove, ed è il segnale
 * che qualcuno ha cambiato il contratto della scheda senza accorgersene.
 */
function scheda(nome, voce) {
  const descr = admin.descrittore(nome);
  const soloLettura = Boolean(descr && descr.soloLettura);
  const schema = admin.campiDi(nome);
  const chiave = descr && descr.chiave ? descr.chiave : 'id';
  const id = voce[chiave];
  const nelFile = id ? trovaNelFile(nome, id) : null;

  const controlli = new Map();
  const corpo = el('div', {});

  for (const definizione of schema) {
    const valore = voce[definizione.nome];
    if (soloLettura || definizione.soloLettura) {
      corpo.append(
        campo(
          definizione.nome,
          el('p', { class: 'pk-mono pk-small', style: 'margin:2px 0', testo: inBreve(valore) })
        )
      );
      continue;
    }
    const nodo = controllo(definizione, valore);
    controlli.set(definizione.nome, { nodo, definizione });
    corpo.append(campo(definizione.nome, nodo, aiutoDalFile(nelFile, definizione.nome, valore)));
  }

  // L'ispettore: le chiavi del record che lo schema non conosce. Succede con
  // un file importato, o dopo che qualcuno ha aggiunto una chiave da qui.
  const conosciuti = new Set(schema.map((d) => d.nome));
  const extra = Object.keys(voce).filter(
    (k) => !conosciuti.has(k) && !['cerca', 'locale', 'metri'].includes(k)
  );
  for (const nomeCampo of extra) {
    if (soloLettura) break;
    const definizione = { nome: nomeCampo, tipo: tipoGrezzo(voce[nomeCampo]) };
    const nodo = controllo(definizione, voce[nomeCampo]);
    controlli.set(nomeCampo, { nodo, definizione });
    corpo.append(campo(`${nomeCampo} · ${t('admin.unknownField')}`, nodo));
  }

  const leggi = () => {
    const campi = {};
    for (const [nomeCampo, { nodo, definizione }] of controlli) {
      campi[nomeCampo] = leggiControllo(nodo, definizione);
    }
    return campi;
  };

  const rev = id ? admin.revisione(nome, id) : null;
  const motivo = el('input', {
    class: 'pk-input',
    type: 'text',
    placeholder: t('admin.reviewWhy'),
    'aria-label': t('admin.reviewWhy'),
  });
  motivo.value = rev ? rev.motivo : '';

  return el('div', { class: 'pk-card', id: 'pk-admin-spot' }, [
    el('div', { class: 'pk-row' }, [
      el('h3', { testo: voce.name || t('admin.newSpot'), style: 'flex:1;min-width:0' }),
      voce.locale ? el('span', { class: 'pk-badge pk-badge--attesa', testo: t('admin.local') }) : null,
      soloLettura ? el('span', { class: 'pk-badge', testo: t('admin.readOnly') }) : null,
    ]),
    el('p', { class: 'pk-mono pk-small pk-muted', testo: String(id || '—') }),
    soloLettura ? el('p', { class: 'pk-small pk-muted', testo: t('admin.readOnlyWhy') }) : null,
    corpo,
    soloLettura ? null : bottoneChiaveNuova(nome, voce),
    soloLettura ? null : campo(t('admin.review'), motivo),
    soloLettura
      ? null
      : el('div', { class: 'pk-row pk-row--wrap' }, [
          el(
            'button',
            {
              class: 'pk-btn',
              onclick: () => salvaVoce(nome, voce, leggi(), schema, motivo.value, nelFile),
            },
            [t('admin.save')]
          ),
          nome === 'spot' && contesto.mappa
            ? el(
                'button',
                {
                  class: 'pk-btn pk-btn--fantasma',
                  onclick: () => {
                    const centro = contesto.mappa.centro;
                    const lat = controlli.get('lat');
                    const lng = controlli.get('lng');
                    if (lat) lat.nodo.value = centro.lat.toFixed(5);
                    if (lng) lng.nodo.value = centro.lng.toFixed(5);
                    avviso(t('admin.tookCentre'));
                  },
                },
                [t('admin.takeCentre')]
              )
            : null,
          id
            ? el(
                'button',
                {
                  class: 'pk-btn pk-btn--fantasma',
                  onclick: async () => {
                    await admin.ripristina(nome, id);
                    dati.riapplica();
                    scelta = trovaVoce(nome, id);
                    aggiornaMappa();
                    disegna();
                  },
                },
                [t('admin.restore')]
              )
            : null,
          id
            ? el(
                'button',
                {
                  class: 'pk-btn pk-btn--fantasma',
                  style: 'border-color:var(--rosso);color:var(--rosso)',
                  onclick: async () => {
                    const procedi = await conferma(
                      t('admin.deleteSpot'),
                      t('admin.deleteAsk', { nome: voce.name || id }),
                      t('admin.deleteGo'),
                      t('common.cancel')
                    );
                    if (!procedi) return;
                    await admin.cancella(nome, id);
                    dati.riapplica();
                    scelta = null;
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

function tipoGrezzo(valore) {
  if (typeof valore === 'boolean') return 'booleano';
  if (typeof valore === 'number') return 'numero';
  if (valore !== null && typeof valore === 'object') return 'json';
  return 'testo';
}

/** La voce come sta nel file, senza le modifiche locali. */
function trovaNelFile(nome, id) {
  const descr = admin.descrittore(nome);
  if (!descr || !descr.chiave) return null;
  const base = descr.base() || [];
  return base.find((voce) => voce[descr.chiave] === id) || null;
}

function trovaVoce(nome, id) {
  const descr = admin.descrittore(nome);
  if (!descr) return null;
  const chiave = descr.chiave || 'id';
  return admin.applica(nome, descr.base() || []).find((voce) => voce[chiave] === id) || null;
}

/** «nel file: …» sotto un campo che è stato cambiato. */
function aiutoDalFile(nelFile, nomeCampo, valoreOra) {
  if (!nelFile) return null;
  const originale = nelFile[nomeCampo];
  const uguale =
    typeof originale === 'object' || typeof valoreOra === 'object'
      ? JSON.stringify(originale) === JSON.stringify(valoreOra)
      : String(originale ?? '') === String(valoreOra ?? '');
  if (uguale) return null;
  if (originale === undefined) return t('admin.absent');
  return t('admin.fromFile', { valore: inBreve(originale, 60) });
}

/** «Aggiungi una chiave»: l'ispettore al contrario. */
function bottoneChiaveNuova(nome, voce) {
  return el(
    'button',
    {
      class: 'pk-btn pk-btn--fantasma pk-btn--largo',
      style: 'margin-bottom:12px',
      onclick: async () => {
        const casella = el('input', {
          class: 'pk-input',
          type: 'text',
          placeholder: 'difficolta_mia',
          'aria-label': t('admin.newField'),
        });
        const vai = await modale({
          titolo: t('admin.newField'),
          corpo: casella,
          azioni: [
            { testo: t('admin.newField'), valore: true, primaria: true },
            { testo: t('common.cancel'), valore: false },
          ],
        });
        const chiave = casella.value.trim();
        if (!vai || !chiave) return;
        scelta = { ...voce, [chiave]: '' };
        disegna();
      },
    },
    [t('admin.newField')]
  );
}

/**
 * Salva una voce: pulisce i valori, avvisa se c'è da avvisare, poi scrive.
 *
 * Il riquadro delle conseguenze compare solo quando c'è qualcosa da dire, e
 * offre «Salva lo stesso»: chi corregge dati sa cosa sta facendo più spesso di
 * quanto il pannello sappia indovinarlo.
 */
async function salvaVoce(nome, voce, grezzi, schema, motivo, nelFile) {
  // I valori si puliscono **due volte**, e non è uno sbaglio: qui per sapere
  // cosa si sta per salvare (le conseguenze si leggono sui valori veri, non
  // sulle stringhe delle caselle) e un JSON storto per dirlo con parole; in
  // `admin.js` per scriverli davvero. A `salva` arriva il grezzo, perché la
  // pulizia che conta deve restare in un posto solo — quello che vale anche
  // per un file importato e per una chiamata fatta a mano dalla console.
  const perTipo = new Map(schema.map((d) => [d.nome, d.tipo]));
  const campi = {};
  for (const [nomeCampo, grezzo] of Object.entries(grezzi)) {
    const definizione = perTipo.get(nomeCampo);
    const tipo = definizione === 'scelta' ? 'testo' : definizione || tipoGrezzo(voce[nomeCampo]);
    const pulito = pulisciValore(grezzo, tipo);
    if (!pulito.ok) {
      avviso(t('admin.jsonBroken'));
      return;
    }
    campi[nomeCampo] = pulito.valore;
  }

  const avvertimenti = conseguenze(nome, campi, schema, nelFile);
  if (avvertimenti.length) {
    const procedi = await modale({
      titolo: t('admin.consequences'),
      punti: avvertimenti,
      azioni: [
        { testo: t('admin.saveAnyway'), valore: true, primaria: true },
        { testo: t('common.cancel'), valore: false },
      ],
    });
    if (!procedi) return;
  }

  const descr = admin.descrittore(nome);
  const chiave = (descr && descr.chiave) || 'id';
  const id = voce[chiave];

  /**
   * Si manda **solo quello che è cambiato davvero**, e si tolgono i campi
   * tornati uguali al file.
   *
   * Mandare tutto il modulo sembrava innocuo e non lo era: `salva` registra
   * come «toccato» ogni campo che riceve, e l'esportazione per il repository
   * scrive `status_cambiato_in_locale` su ogni spot che ha `status` fra i
   * campi toccati. Correggere una virgola nella descrizione di uno dei 26
   * verificati bastava a farlo arrivare nella fonte con quel segno addosso —
   * cioè a far dubitare di una verifica che nessuno aveva toccato.
   */
  const uguale = (a, b) =>
    typeof a === 'object' || typeof b === 'object'
      ? JSON.stringify(a) === JSON.stringify(b)
      : String(a ?? '') === String(b ?? '');

  const daMandare = {};
  const daRiportare = [];
  for (const [nomeCampo, valore] of Object.entries(campi)) {
    if (id && uguale(valore, voce[nomeCampo])) continue;
    if (id && nelFile && uguale(valore, nelFile[nomeCampo])) {
      daRiportare.push(nomeCampo);
      continue;
    }
    daMandare[nomeCampo] = grezzi[nomeCampo];
  }

  try {
    if (!id) scelta = await admin.crea(nome, grezzi);
    else if (Object.keys(daMandare).length) await admin.salva(nome, id, daMandare);
    for (const nomeCampo of daRiportare) await admin.ripristinaCampo(nome, id, nomeCampo);
  } catch (errore) {
    // Il rifiuto delle chiavi segrete vale su ogni campo, non solo sulla
    // casella della chiave pubblicabile: bastava incollare un token nella
    // descrizione di uno spot per aggirarlo.
    avviso(errore.code === 'secret_refused' ? t('admin.secretRefused') : errore.message);
    return;
  }

  const idFinale = id || (scelta && scelta[chiave]);
  if (idFinale) await admin.segnaRevisione(nome, idFinale, motivo);
  dati.riapplica();
  if (id) scelta = trovaVoce(nome, id) || scelta;
  avviso(t('admin.saved'));
  aggiornaMappa();
  disegna();
}

/** Come `ispettore.pulisci`, ma senza importare il modulo in una schermata. */
function pulisciValore(valore, tipo) {
  if (tipo === 'booleano') return { ok: true, valore: Boolean(valore) };
  if (tipo === 'numero') {
    const numero = Number(valore);
    return Number.isFinite(numero) ? { ok: true, valore: numero } : { ok: false, valore: null };
  }
  if (tipo === 'json') {
    const testo = String(valore ?? '').trim();
    if (!testo) return { ok: true, valore: null };
    try {
      return { ok: true, valore: JSON.parse(testo) };
    } catch {
      return { ok: false, valore: null };
    }
  }
  return { ok: true, valore: String(valore ?? '').trim() };
}

// --- sezione: stato dell'app -------------------------------------------------

function sezioneStato() {
  const corpo = el('div', {});
  const chi = dati.chiRisponde();
  corpo.append(
    riga(
      t('admin.who'),
      chi.chi === 'motore'
        ? t('admin.who.engine')
        : `${t('admin.who.local')} — ${t(`admin.who.${chi.perche}`, { n: chi.quante || 0 })}`
    )
  );

  for (const nome of admin.collezioni()) {
    const descr = admin.descrittore(nome);
    const quante = (descr.base() || []).length;
    const conti = admin.conteggi(nome);
    corpo.append(
      riga(
        t(`admin.collection.${nome}`),
        `${quante} · ${conti.modificati}/${conti.nuovi}/${conti.cancellati}`
      )
    );
  }

  if (!statoLetto) {
    corpo.append(el('p', { class: 'pk-small pk-muted', testo: t('admin.stateReading') }));
  } else if (!statoLetto.cache) {
    // Aperta da `file:` (la demo in un file solo) non c'è nessun service
    // worker e nessuna cache: la riga dice perché è vuota, non dà un errore.
    corpo.append(el('p', { class: 'pk-small pk-muted', testo: t('admin.stateNoCache') }));
  } else {
    const c = statoLetto.cache;
    corpo.append(
      riga(t('admin.stateVersion'), c.version || '—'),
      riga(t('admin.stateFiles'), c.app),
      riga(t('admin.stateTiles'), c.tiles),
      riga(t('admin.stateArea'), c.area),
      riga(t('admin.stateMedia'), c.media),
      riga(
        t('admin.stateSpace'),
        `${Math.round((c.usage || 0) / 1024 / 1024)} MB / ${Math.round((c.quota || 0) / 1024 / 1024)} MB`
      )
    );
  }

  if (statoLetto) {
    corpo.append(
      riga(
        t('admin.statePersisted'),
        statoLetto.persistente === null
          ? '—'
          : statoLetto.persistente
            ? t('common.yes')
            : t('common.no')
      )
    );
  }

  corpo.append(
    el(
      'button',
      {
        class: 'pk-btn pk-btn--fantasma pk-btn--largo',
        onclick: async () => {
          const esito = await offline.rendiPersistente();
          avviso(esito ? t('admin.persistOk') : t('admin.persistNo'));
          statoLetto = null;
          disegna();
        },
      },
      [t('admin.persist')]
    )
  );

  return sezione('stato', t('admin.sections.state'), corpo);
}

// --- sezione: dati -----------------------------------------------------------

async function elencoDi(nome, filtro) {
  const descr = admin.descrittore(nome);
  const voci = admin.applica(nome, descr.base() || []);
  if (!filtro) return voci.slice(0, quanteMostrate);
  const cerca = filtro.toLowerCase();
  const trovate = [];
  for (const voce of voci) {
    const testo = JSON.stringify(voce).toLowerCase();
    if (testo.includes(cerca)) trovate.push(voce);
    if (trovate.length >= quanteMostrate + 1) break;
  }
  return trovate.slice(0, quanteMostrate);
}

async function sezioneDati() {
  const filtro = filtri.get(collezione) || '';

  const pastiglie = el(
    'div',
    { class: 'pk-chiprow' },
    admin.collezioni().map((nome) =>
      el(
        'button',
        {
          class: 'pk-chip',
          'aria-pressed': nome === collezione ? 'true' : 'false',
          onclick: () => {
            collezione = nome;
            scelta = null;
            quanteMostrate = PASSO_ELENCO;
            disegna();
          },
        },
        [t(`admin.collection.${nome}`)]
      )
    )
  );

  const ricerca = el('input', {
    class: 'pk-input',
    id: 'pk-admin-cerca',
    type: 'search',
    placeholder: t('admin.search', { cosa: t(`admin.collection.${collezione}`) }),
    'aria-label': t('admin.search', { cosa: t(`admin.collection.${collezione}`) }),
  });
  ricerca.value = filtro;
  let attesa = null;
  ricerca.addEventListener('input', () => {
    clearTimeout(attesa);
    attesa = setTimeout(async () => {
      filtri.set(collezione, ricerca.value);
      scelta = null;
      quanteMostrate = PASSO_ELENCO;
      await disegna();
      // Per `id`, non «il primo input di tipo search»: se un giorno ne
      // comparisse un altro, il fuoco finirebbe nel posto sbagliato.
      const rifatto = document.getElementById('pk-admin-cerca');
      if (rifatto) {
        rifatto.focus();
        rifatto.setSelectionRange(rifatto.value.length, rifatto.value.length);
      }
    }, 250);
  });

  const trovati = await elencoDi(collezione, filtro);
  const descr = admin.descrittore(collezione);
  const chiave = descr.chiave || 'id';
  const totale = (admin.applica(collezione, descr.base() || []) || []).length;

  const elenco = el(
    'div',
    { style: 'margin-top:8px' },
    trovati.map((voce) =>
      el(
        'button',
        {
          class: 'pk-item',
          onclick: () => {
            scelta = voce;
            disegna();
          },
        },
        [
          el('span', { class: 'pk-item__body' }, [
            el('span', { class: 'pk-item__name', testo: voce.name || voce.title || inBreve(voce[chiave], 40) }),
            el('span', {
              class: 'pk-item__meta',
              testo: [
                voce.status || voce.category || voce.kind || '',
                voce.locale ? t('admin.local') : '',
                admin.revisione(collezione, voce[chiave]) ? t('admin.review') : '',
              ]
                .filter(Boolean)
                .join(' · '),
            }),
          ]),
        ]
      )
    )
  );

  const corpo = el('div', {}, [pastiglie, ricerca, elenco]);

  if (totale > quanteMostrate) {
    corpo.append(
      el(
        'button',
        {
          class: 'pk-btn pk-btn--fantasma pk-btn--largo',
          style: 'margin-top:8px',
          onclick: () => {
            quanteMostrate += PASSO_ELENCO;
            disegna();
          },
        },
        [t('admin.more', { n: PASSO_ELENCO })]
      )
    );
  }

  if (!descr.soloLettura) {
    corpo.append(
      el(
        'button',
        {
          class: 'pk-btn pk-btn--fantasma pk-btn--largo',
          style: 'margin-top:8px',
          onclick: () => {
            if (collezione === 'spot') {
              const centro = contesto.mappa ? contesto.mappa.centro : { lat: 41.9, lng: 12.48 };
              scelta = {
                name: '',
                description: '',
                lat: +centro.lat.toFixed(5),
                lng: +centro.lng.toFixed(5),
              };
            } else {
              scelta = {};
            }
            disegna();
          },
        },
        [t('admin.newSpot')]
      )
    );
  }

  return sezione('dati', t('admin.sections.data'), corpo);
}

// --- sezione: configurazione -------------------------------------------------

/**
 * Tutte le foglie di CONFIG, raggruppate dal primo pezzo del percorso.
 *
 * I gruppi non si dichiarano: sono `tiles`, `routing`, `supabase`,
 * `filtroTessere`, `partenza`, `andature` più `altre` per gli scalari di primo
 * livello. Dichiararli voleva dire che una foglia nuova in `config.js` non
 * compariva qui finché qualcuno non se ne ricordava.
 */
function sezioneConfig() {
  const campi = admin.campiConfig();
  const gruppi = new Map();
  for (const definizione of campi) {
    const gruppo = definizione.gruppo || 'altre';
    if (!gruppi.has(gruppo)) gruppi.set(gruppo, []);
    gruppi.get(gruppo).push(definizione);
  }

  const corpo = el('div', {});
  for (const [gruppo, elenco] of gruppi) {
    corpo.append(
      el('h4', {
        class: 'pk-mono pk-small pk-muted',
        style: 'margin:16px 0 8px',
        testo: gruppo === 'altre' ? t('admin.groupOther') : gruppo,
      })
    );
    for (const definizione of elenco) {
      const valore = admin.valoreConfig(definizione.via);
      const nodo = controllo(definizione, valore);
      nodo.addEventListener('change', async () => {
        const grezzo = leggiControllo(nodo, definizione);
        const pulito = pulisciValore(grezzo, definizione.tipo);
        if (!pulito.ok) {
          avviso(t('admin.jsonBroken'));
          return;
        }
        try {
          await admin.impostaConfig(definizione.via, grezzo === '' ? undefined : pulito.valore);
        } catch (errore) {
          if (errore.code === 'secret_refused') {
            nodo.value = '';
            avviso(t('admin.secretRefused'));
            return;
          }
          throw errore;
        }
        if (contesto.mappa) contesto.mappa.ridisegna();
        aggiornaConteggi();
        avviso(t('admin.applied'));
      });
      const aiuto = t(`admin.aiuto.${definizione.via}`);
      corpo.append(
        campo(
          definizione.via,
          nodo,
          definizione.esce
            ? t('admin.leaves')
            : aiuto.startsWith('admin.aiuto.')
              ? null
              : aiuto
        )
      );
    }
  }

  return sezione('config', t('admin.sections.config'), corpo);
}

// --- sezione: magazzino ------------------------------------------------------

function sezioneMagazzino() {
  const corpo = el('div', {});
  corpo.append(el('p', { class: 'pk-small pk-muted', testo: t('admin.storeNote') }));

  if (!magazzinoLetto) {
    corpo.append(el('p', { class: 'pk-small pk-muted', testo: t('admin.stateReading') }));
    return sezione('magazzino', t('admin.sections.store'), corpo);
  }

  corpo.append(riga(t('admin.storeSupport'), magazzinoLetto.supporto));

  for (const [deposito, voci] of Object.entries(magazzinoLetto.depositi)) {
    corpo.append(
      el('h4', {
        class: 'pk-mono pk-small pk-muted',
        style: 'margin:16px 0 8px',
        testo: `${deposito} · ${voci.length}`,
      })
    );
    for (const voce of voci) {
      const bloccata = deposito === 'kv' && admin.chiaveMagazzinoBloccata(voce.chiave);
      const modificabile = deposito === 'kv' && !bloccata;
      const casella = el('input', { class: 'pk-input', type: 'text' });
      casella.value = inBreve(voce.valore, 400);

      const azioni = el('div', { class: 'pk-row pk-row--wrap' }, [
        modificabile
          ? el(
              'button',
              {
                class: 'pk-btn pk-btn--fantasma',
                onclick: async () => {
                  let nuovo = casella.value;
                  try {
                    nuovo = JSON.parse(casella.value);
                  } catch {
                    // Non era JSON: si salva come testo, che è quello che di
                    // solito si intende scrivendo a mano in una casella.
                  }
                  await scrivi(voce.chiave, nuovo);
                  magazzinoLetto = null;
                  avviso(t('admin.saved'));
                  disegna();
                },
              },
              [t('admin.save')]
            )
          : null,
        // In `note`, `preferiti` e `coda` si cancella e basta: crearci dentro
        // vorrebbe dire fabbricare il contributo di una persona, ed è quello
        // che vieta la prima regola non negoziabile del repository.
        bloccata
          ? null
          : el(
              'button',
              {
                class: 'pk-btn pk-btn--fantasma',
                style: 'border-color:var(--rosso);color:var(--rosso)',
                onclick: async () => {
                  await elimina(deposito, voce.chiave);
                  magazzinoLetto = null;
                  disegna();
                },
              },
              [t('admin.deleteGo')]
            ),
      ]);

      corpo.append(
        el('div', { style: 'margin-bottom:12px' }, [
          el('span', { class: 'pk-mono pk-small pk-muted', testo: voce.chiave }),
          modificabile
            ? casella
            : el('p', {
                class: 'pk-mono pk-small',
                style: 'margin:2px 0;word-break:break-all',
                testo: inBreve(voce.valore, 200),
              }),
          bloccata ? el('p', { class: 'pk-small pk-muted', testo: t('admin.storeLocked') }) : null,
          azioni,
        ])
      );
    }
  }

  return sezione('magazzino', t('admin.sections.store'), corpo);
}

// --- sezione: file -----------------------------------------------------------

function conteggi() {
  const conti = admin.conteggi('spot');
  const totali = admin.conteggiTotali();
  const scatola = el('div', { id: 'pk-admin-conti' }, [
    riga(t('admin.changed'), conti.modificati),
    riga(t('admin.added'), conti.nuovi),
    riga(t('admin.removed'), conti.cancellati),
    riga(t('admin.settings'), conti.config),
    riga(t('admin.review'), totali.revisioni),
  ]);
  for (const [nome, conto] of Object.entries(totali.per)) {
    if (nome === 'spot') continue;
    const quante = conto.modificati + conto.nuovi + conto.cancellati;
    if (quante) scatola.append(riga(t(`admin.collection.${nome}`), quante));
  }
  return scatola;
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
      const conti = await admin.importa(JSON.parse(await file.text()));
      dati.riapplica();
      aggiornaMappa();
      avviso(t('admin.imported', { n: conti.modificati + conti.nuovi }));
      if (conti.migrato) avviso(t('admin.migrated'));
      if (conti.scartate) avviso(t('admin.importDropped', { n: conti.scartate }));
      disegna();
    } catch (errore) {
      avviso(`${t('admin.importFailed')} ${errore.message}`);
    }
  });

  const corpo = el('div', {}, [
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
          scelta = null;
          aggiornaMappa();
          disegna();
        },
      },
      [t('admin.reset')]
    ),
  ]);

  return sezione('file', t('admin.files'), corpo);
}

// --- schermata --------------------------------------------------------------

/**
 * Legge quello che costa, ma solo se la sezione che lo mostra è aperta.
 *
 * `offline.stato()` può metterci fino a sei secondi quando la cache dell'app
 * non c'è ancora: farlo a ogni `disegna()` vorrebbe dire un pannello che si
 * inchioda a ogni salvataggio.
 */
async function leggiQuelCheCosta() {
  if (aperte.has('stato') && !statoLetto) {
    const [cache, persistente] = await Promise.all([offline.stato(), offline.persistente()]);
    statoLetto = { cache, persistente };
  }
  if (aperte.has('magazzino') && !magazzinoLetto) {
    magazzinoLetto = { supporto: await supporto(), depositi: await tutto() };
  }
}

async function disegna() {
  await leggiQuelCheCosta();
  // Lo scorrimento si salva e si rimette: prima, ogni salvataggio riportava in
  // cima e si perdeva di vista il campo che si stava compilando.
  const scorrimento = contenitore.scrollTop;

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
    sezioneStato(),
    await sezioneDati(),
    scelta ? scheda(collezione, scelta) : null,
    sezioneConfig(),
    sezioneMagazzino(),
    sezioneFile()
  );

  contenitore.scrollTop = scorrimento;
}

export function inizializza(ctx) {
  contesto = ctx;
  contenitore = document.getElementById('pk-admin');
}

export async function entra(parametri) {
  if (parametri && parametri.id) {
    const voce = dati.spotPerId(parametri.id);
    if (voce) {
      collezione = 'spot';
      scelta = voce;
      filtri.set('spot', voce.name);
    }
  }
  await disegna();
  contenitore.scrollTop = 0;
}

export function titolo() {
  return { titolo: t('admin.title'), sotto: t('admin.subtitle'), indietro: true };
}
