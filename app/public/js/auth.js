/* PkFAMILY — entrare davvero: un account vero, non un finto accesso locale.
 *
 * Parla direttamente con Supabase Auth (GoTrue) via `fetch`, senza SDK: l'app
 * non ha una fase di costruzione, ogni kilobyte che non c'è è un kilobyte che
 * il telefono non scarica, e le tre rotte che servono sono tre chiamate HTTP.
 *
 * Cosa fa e cosa non fa, perché la differenza conta:
 *
 * 1. **Non inventa niente.** Nessun account finto, nessuna sessione di
 *    cortesia: o esiste una riga in `auth.users` del progetto configurato, o
 *    qui non si entra (regola 1 di AGENTS.md). Finché `supabase.url` è vuoto
 *    questo modulo dice «non configurato» e l'app resta quella di sempre,
 *    locale e senza rete.
 * 2. **Una sola chiave, quella pubblicabile.** È fatta per stare in un client
 *    e le RLS restano in piedi lo stesso. Una chiave che sembra segreta viene
 *    rifiutata prima di partire (`chiave_segreta`): serve la
 *    `sb_publishable_...`, non la vecchia chiave anon in forma di JWT — da
 *    fuori le due non si distinguono, e sbagliare vorrebbe dire pubblicare
 *    una chiave che scavalca ogni regola.
 * 3. **I gettoni non escono di qui.** Restano nel magazzino del dispositivo
 *    (`store.js`), non finiscono in un log, in un avviso o in un'esportazione,
 *    e vanno solo verso il progetto Supabase che li ha emessi.
 * 4. **Senza rete non si viene buttati fuori.** Il rinnovo che fallisce per
 *    mancanza di rete lascia la sessione dov'è: è la promessa dell'app.
 *    Solo un rifiuto esplicito del server (gettone revocato) cancella.
 * 5. **Ogni dispositivo ha la sua sessione.** Il gettone di rinnovo ruota a
 *    ogni uso: due telefoni sullo stesso account se lo strappano di mano a
 *    vicenda. Traffico simultaneo vuol dire tante sessioni, non una condivisa
 *    — per questo c'è anche l'ingresso come ospite, che ne crea una per chi
 *    arriva senza voler lasciare un'email.
 */

import { CONFIG } from './config.js';
import { sembraSegreta } from './ispettore.js';
import { leggi, scrivi } from './store.js';

/** Dove la sessione vive sul dispositivo. */
const CHIAVE_SESSIONE = 'sessione';

/** Quanto prima della scadenza si rinnova il gettone. */
const ANTICIPO_MS = 60_000;

/** Un errore con un codice stabile: l'interfaccia traduce quello, non il testo. */
export class ErroreAccesso extends Error {
  constructor(codice, causa) {
    super(codice);
    this.name = 'ErroreAccesso';
    this.codice = codice;
    /** Il codice che ha dato il server, mai il suo testo libero. */
    this.causa = causa || '';
  }
}

let sessione = null;
let timerRinnovo = null;
/** Un rinnovo alla volta: due schermate che chiedono insieme non ne fanno due. */
let rinnovoInCorso = null;
const ascoltatori = new Set();

function base() {
  return String(CONFIG.supabase.url || '').replace(/\/+$/, '');
}

/** C'è un progetto a cui parlare? Senza, l'app resta locale e lo dice. */
export function configurato() {
  return Boolean(base() && CONFIG.supabase.publishableKey);
}

function chiave() {
  const valore = String(CONFIG.supabase.publishableKey || '');
  if (sembraSegreta(valore)) throw new ErroreAccesso('chiave_segreta');
  return valore;
}

function avvisa() {
  for (const fn of ascoltatori) {
    try {
      fn(utente());
    } catch {
      // Un ascoltatore rotto non deve impedire agli altri di sapere.
    }
  }
}

/** Si fa avvisare quando si entra o si esce. Restituisce come smettere. */
export function ascolta(fn) {
  ascoltatori.add(fn);
  return () => ascoltatori.delete(fn);
}

/** Chi sta usando l'app, senza un solo gettone dentro. */
export function utente() {
  return sessione ? { ...sessione.utente } : null;
}

/** Si è dentro? (Anche offline: la sessione resta.) */
export function dentro() {
  return Boolean(sessione);
}

/**
 * Traduce la risposta del server in un codice nostro.
 *
 * Si guarda `error_code` prima dello stato HTTP perché è l'unico campo che
 * Supabase promette stabile; il testo che lo accompagna è pensato per chi
 * sviluppa, cambia, ed è in inglese: non arriva mai a schermo.
 */
function codiceDi(stato, dati) {
  const dallServer = String(dati.error_code || dati.code || '');
  if (dallServer === 'anonymous_provider_disabled') return 'ospiti_spenti';
  if (dallServer === 'otp_expired' || dallServer === 'otp_disabled') return 'codice_scaduto';
  if (dallServer === 'validation_failed' || dallServer === 'email_address_invalid') {
    return 'email_non_valida';
  }
  if (stato === 429) return 'troppi_tentativi';
  if (stato === 401 || stato === 403) return 'rifiutato';
  return 'rifiutato';
}

async function chiama(rotta, { metodo = 'POST', corpo, gettone } = {}) {
  if (!configurato()) throw new ErroreAccesso('non_configurato');
  const intestazioni = { apikey: chiave(), 'Content-Type': 'application/json' };
  if (gettone) intestazioni.Authorization = `Bearer ${gettone}`;

  let risposta;
  try {
    risposta = await fetch(`${base()}${rotta}`, {
      method: metodo,
      headers: intestazioni,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
  } catch (errore) {
    // Rete assente, DNS che non risolve, progetto spento: da qui non si
    // distinguono, e per chi usa l'app sono la stessa cosa.
    throw new ErroreAccesso('senza_rete', errore && errore.name);
  }

  const testo = await risposta.text();
  let dati = {};
  try {
    dati = testo ? JSON.parse(testo) : {};
  } catch {
    // Una pagina d'errore in HTML davanti al progetto: non è JSON, e il suo
    // contenuto non ci interessa.
    dati = {};
  }
  if (!risposta.ok) {
    const codice = codiceDi(risposta.status, dati);
    throw new ErroreAccesso(codice, String(dati.error_code || dati.code || risposta.status));
  }
  return dati;
}

/** Legge il nome e il ruolo dalla riga di `profiles`, se si riesce. */
async function profilo(id, gettone) {
  try {
    const risposta = await fetch(
      `${base()}/rest/v1/profiles?id=eq.${encodeURIComponent(id)}&select=display_name,role`,
      { headers: { apikey: chiave(), Authorization: `Bearer ${gettone}` } }
    );
    if (!risposta.ok) return {};
    const righe = await risposta.json();
    const riga = Array.isArray(righe) ? righe[0] : null;
    return riga ? { nome: riga.display_name || '', ruolo: riga.role || '' } : {};
  } catch {
    // Il profilo è un di più: senza, si è dentro lo stesso.
    return {};
  }
}

/** Da quello che risponde GoTrue alla sessione che teniamo noi. */
function daRisposta(dati) {
  const persona = dati.user || {};
  const durata = Number(dati.expires_in || 3600) * 1000;
  return {
    access_token: dati.access_token,
    refresh_token: dati.refresh_token,
    scadenza: Date.now() + durata,
    utente: {
      id: persona.id || '',
      email: persona.email || '',
      anonimo: Boolean(persona.is_anonymous),
      nome: '',
      ruolo: '',
    },
  };
}

async function deposita(nuova) {
  sessione = nuova;
  await scrivi(CHIAVE_SESSIONE, nuova);
  programmaRinnovo();
  avvisa();
}

async function butta() {
  sessione = null;
  clearTimeout(timerRinnovo);
  timerRinnovo = null;
  await scrivi(CHIAVE_SESSIONE, undefined);
  avvisa();
}

function programmaRinnovo() {
  clearTimeout(timerRinnovo);
  if (!sessione) return;
  const fra = Math.max(1000, sessione.scadenza - Date.now() - ANTICIPO_MS);
  // Su un telefono che dorme il timer non scatta: c'è anche il controllo al
  // ritorno in primo piano, più sotto.
  timerRinnovo = setTimeout(() => {
    rinnova().catch(() => {});
  }, fra);
}

/**
 * Rinnova il gettone. Un rifiuto del server cancella la sessione (il gettone
 * di rinnovo è stato speso o revocato); l'assenza di rete no.
 */
async function rinnova() {
  if (!sessione) return null;
  if (rinnovoInCorso) return rinnovoInCorso;
  const vecchia = sessione;
  rinnovoInCorso = (async () => {
    try {
      const dati = await chiama('/auth/v1/token?grant_type=refresh_token', {
        corpo: { refresh_token: vecchia.refresh_token },
      });
      const nuova = daRisposta(dati);
      nuova.utente = { ...nuova.utente, nome: vecchia.utente.nome, ruolo: vecchia.utente.ruolo };
      await deposita(nuova);
      return nuova;
    } catch (errore) {
      if (errore instanceof ErroreAccesso && errore.codice === 'senza_rete') {
        // Si riproverà: la sessione resta, e l'app pure.
        return vecchia;
      }
      await butta();
      throw errore;
    } finally {
      rinnovoInCorso = null;
    }
  })();
  return rinnovoInCorso;
}

/**
 * Le intestazioni per una chiamata autenticata, con il gettone già rinnovato
 * se stava per scadere. È l'unico modo con cui un gettone esce da questo
 * modulo, e va usato solo verso il progetto Supabase configurato.
 */
export async function intestazioni() {
  if (!sessione) throw new ErroreAccesso('fuori');
  if (sessione.scadenza - Date.now() < ANTICIPO_MS) await rinnova();
  if (!sessione) throw new ErroreAccesso('fuori');
  return { apikey: chiave(), Authorization: `Bearer ${sessione.access_token}` };
}

/**
 * Chiede a Supabase di mandare il codice all'indirizzo indicato.
 *
 * `create_user: true` perché per la demo iscriversi ed entrare sono lo stesso
 * gesto: chi arriva la prima volta non deve scegliere fra due pulsanti che
 * fanno la stessa cosa.
 */
export async function chiediCodice(email) {
  const indirizzo = String(email || '').trim();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(indirizzo)) throw new ErroreAccesso('email_non_valida');
  await chiama('/auth/v1/otp', { corpo: { email: indirizzo, create_user: true } });
  return true;
}

/** Verifica il codice ricevuto per email e apre la sessione. */
export async function verificaCodice(email, codice) {
  const cifre = String(codice || '').replace(/\s+/g, '');
  if (!cifre) throw new ErroreAccesso('codice_errato');
  let dati;
  try {
    dati = await chiama('/auth/v1/verify', {
      corpo: { type: 'email', email: String(email || '').trim(), token: cifre },
    });
  } catch (errore) {
    // Un codice sbagliato e uno scaduto arrivano con lo stesso stato: si
    // distinguono solo per `error_code`, che `codiceDi` ha già guardato.
    if (errore instanceof ErroreAccesso && errore.codice === 'rifiutato') {
      throw new ErroreAccesso('codice_errato', errore.causa);
    }
    throw errore;
  }
  const nuova = daRisposta(dati);
  await deposita(nuova);
  Object.assign(nuova.utente, await profilo(nuova.utente.id, nuova.access_token));
  await deposita(nuova);
  return utente();
}

/**
 * Entra come ospite: un utente anonimo vero in `auth.users`, con il suo nome
 * generato dal database (migrazione 0004). Non è un finto account — è una
 * riga come le altre, solo senza email.
 */
export async function entraComeOspite() {
  const dati = await chiama('/auth/v1/signup', { corpo: {} });
  if (!dati.access_token) throw new ErroreAccesso('ospiti_spenti');
  const nuova = daRisposta(dati);
  nuova.utente.anonimo = true;
  await deposita(nuova);
  Object.assign(nuova.utente, await profilo(nuova.utente.id, nuova.access_token));
  await deposita(nuova);
  return utente();
}

/**
 * Esce. Prova a dirlo anche al server, ma la sessione locale se ne va in ogni
 * caso: chi tocca «esci» su un telefono in metropolitana deve uscire lì.
 */
export async function esci() {
  const vecchia = sessione;
  await butta();
  if (!vecchia) return;
  try {
    await chiama('/auth/v1/logout', { corpo: {}, gettone: vecchia.access_token });
  } catch {
    // Il gettone scadrà da solo.
  }
}

/**
 * Riprende la sessione salvata all'avvio dell'app.
 *
 * Si chiama sempre, anche senza progetto configurato: se qualcuno spegne
 * `supabase.url` mentre una sessione è depositata, quella va tolta di mezzo
 * invece di restare a mostrare un nome che non risponde più a niente.
 *
 * Il rinnovo di un gettone scaduto **non** si aspetta: su una rete lenta
 * terrebbe fermo l'avvio dell'app, che è la cosa che questa applicazione
 * promette di non fare. Parte per conto suo e, quando arriva, avvisa.
 */
export async function inizializza() {
  const salvata = await leggi(CHIAVE_SESSIONE, null);
  if (!salvata || !salvata.refresh_token) {
    sessione = null;
    return null;
  }
  if (!configurato()) {
    await butta();
    return null;
  }
  sessione = salvata;
  if (salvata.scadenza - Date.now() < ANTICIPO_MS) rinnova().catch(() => {});
  else programmaRinnovo();
  avvisa();
  return utente();
}

// Un telefono che torna in primo piano dopo mezz'ora ha un gettone scaduto e
// un timer che non è mai scattato: il momento giusto per rinnovare è questo.
if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    if (sessione && sessione.scadenza - Date.now() < ANTICIPO_MS) rinnova().catch(() => {});
  });
}
