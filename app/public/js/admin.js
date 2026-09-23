/* PkFAMILY — la modalità sviluppatore.
 *
 * Serve a cambiare le cose senza aprire un editor: correggere uno spot,
 * spostarne il punto, provare un altro filtro sulle tessere, puntare l'app a
 * un altro server dei percorsi. È pensata per chi fa il prodotto, non per chi
 * lo usa, e si accende a mano dalla schermata «Tu».
 *
 * Tre regole che non si negoziano, e che sono scritte anche nel pannello:
 *
 * 1. **Tutto resta su questo dispositivo.** Nessuna modifica parte verso
 *    Supabase o verso chiunque altro: si esportano dei file, e a portarli nel
 *    repository è una persona (masterplan, principio 5).
 * 2. **Niente si finge verificato.** Ogni spot toccato o creato qui porta il
 *    segno `locale`, e l'app lo mostra: uno spot diventa `verified` quando una
 *    persona lo verifica davvero, non perché qualcuno ha cambiato una casella
 *    su un telefono.
 * 3. **Nessuna chiave segreta.** Si può indicare l'indirizzo di Supabase e la
 *    chiave pubblicabile, che è fatta per stare nei client. La chiave segreta
 *    non entra qui, e il pannello lo dice a chi prova a incollarla.
 */

import { CONFIG } from './config.js';
import { leggi, scrivi } from './store.js';

const CHIAVE_STATO = 'admin.attiva';
const CHIAVE_DATI = 'admin.sovrascritture';

/** I campi di CONFIG che il pannello può cambiare, con che cosa sono. */
export const CAMPI_CONFIG = [
  { via: 'filtroTessere.chiaro', tipo: 'testo', gruppo: 'mappa' },
  { via: 'filtroTessere.scuro', tipo: 'testo', gruppo: 'mappa' },
  { via: 'tiles.mappa.url', tipo: 'testo', gruppo: 'mappa' },
  { via: 'tiles.satellite.url', tipo: 'testo', gruppo: 'mappa' },
  { via: 'cellaGomitolo', tipo: 'numero', gruppo: 'mappa' },
  { via: 'zoomFontanelle', tipo: 'numero', gruppo: 'mappa' },
  { via: 'routing.servizio', tipo: 'testo', gruppo: 'collegamenti' },
  { via: 'routing.decimali', tipo: 'numero', gruppo: 'collegamenti' },
  { via: 'supabase.url', tipo: 'testo', gruppo: 'collegamenti' },
  { via: 'supabase.publishableKey', tipo: 'testo', gruppo: 'collegamenti' },
  { via: 'tettoPrefetch', tipo: 'numero', gruppo: 'offline' },
];

/** I campi di uno spot che si possono correggere. */
export const CAMPI_SPOT = [
  { nome: 'name', tipo: 'testo' },
  { nome: 'description', tipo: 'lungo' },
  { nome: 'status', tipo: 'scelta', valori: ['verified', 'community', 'pending'] },
  { nome: 'level', tipo: 'scelta', valori: ['principiante', 'intermedio', 'avanzato'] },
  { nome: 'crowd', tipo: 'scelta', valori: ['tranquillo', 'medio', 'affollato'] },
  { nome: 'fountain', tipo: 'booleano' },
  { nome: 'lat', tipo: 'numero' },
  { nome: 'lng', tipo: 'numero' },
];

const VUOTE = { modificati: {}, nuovi: [], cancellati: [], config: {} };

let accesa = false;
let dati = structuredClone(VUOTE);

export function attiva() {
  return accesa;
}

export function sovrascritture() {
  return dati;
}

/** Legge un valore dentro un oggetto seguendo "a.b.c". */
function dentro(oggetto, via) {
  return via.split('.').reduce((nodo, pezzo) => (nodo ? nodo[pezzo] : undefined), oggetto);
}

/** Scrive un valore dentro un oggetto seguendo "a.b.c". */
function poni(oggetto, via, valore) {
  const pezzi = via.split('.');
  const ultimo = pezzi.pop();
  const nodo = pezzi.reduce((corrente, pezzo) => {
    if (!corrente[pezzo] || typeof corrente[pezzo] !== 'object') corrente[pezzo] = {};
    return corrente[pezzo];
  }, oggetto);
  nodo[ultimo] = valore;
}

/** Il valore di configurazione in vigore adesso. */
export function valoreConfig(via) {
  return dentro(CONFIG, via);
}

/** Applica a CONFIG quello che è stato cambiato dal pannello. */
function applicaConfig() {
  for (const [via, valore] of Object.entries(dati.config)) poni(CONFIG, via, valore);
}

/**
 * Prepara la modalità: va chiamata all'avvio, prima che i dati vengano letti
 * e prima che la mappa venga costruita.
 */
export async function inizializza() {
  accesa = Boolean(await leggi(CHIAVE_STATO, false));
  dati = { ...structuredClone(VUOTE), ...(await leggi(CHIAVE_DATI, null)) };
  if (accesa) applicaConfig();
  return accesa;
}

export async function accendi(valore) {
  accesa = Boolean(valore);
  await scrivi(CHIAVE_STATO, accesa);
  return accesa;
}

async function salva() {
  await scrivi(CHIAVE_DATI, dati);
}

/**
 * Gli spot come li vede l'app: cancellati tolti, modificati uniti, nuovi in
 * fondo. Quello che è passato di qui porta `locale: true`.
 */
export function applicaAgliSpot(base) {
  if (!accesa) return base;
  const cancellati = new Set(dati.cancellati);
  const uniti = base
    .filter((voce) => !cancellati.has(voce.id))
    .map((voce) => {
      const modifica = dati.modificati[voce.id];
      return modifica ? { ...voce, ...modifica, locale: true } : voce;
    });
  return uniti.concat(dati.nuovi.map((voce) => ({ ...voce, locale: true })));
}

function ripulisci(campi) {
  const puliti = {};
  for (const { nome, tipo } of CAMPI_SPOT) {
    if (!(nome in campi)) continue;
    const grezzo = campi[nome];
    if (tipo === 'numero') {
      const numero = Number(grezzo);
      if (Number.isFinite(numero)) puliti[nome] = numero;
    } else if (tipo === 'booleano') {
      puliti[nome] = Boolean(grezzo);
    } else {
      const testo = String(grezzo || '').trim();
      if (testo) puliti[nome] = testo;
      else if (nome === 'description') puliti[nome] = '';
    }
  }
  return puliti;
}

export async function salvaSpot(id, campi) {
  dati.modificati[id] = { ...(dati.modificati[id] || {}), ...ripulisci(campi) };
  await salva();
  return dati.modificati[id];
}

export async function creaSpot(campi) {
  const numero = dati.nuovi.length + 1;
  const voce = {
    id: `locale-${numero}-${String(campi.name || 'spot').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 24)}`,
    ...ripulisci(campi),
    // Uno spot nuovo nasce `pending`: nessuno lo ha ancora verificato, e
    // l'app non deve mai far credere il contrario. Va scritto **dopo** i campi
    // arrivati dal modulo, non prima: al contrario, uno `status` scelto nel
    // pannello lo scavalcava, e il pulsante «Nuovo spot qui» creava uno spot
    // già verificato — che poi finiva così anche nell'esportazione.
    status: 'pending',
  };
  dati.nuovi.push(voce);
  await salva();
  return voce;
}

export async function cancellaSpot(id) {
  const eraNuovo = dati.nuovi.findIndex((voce) => voce.id === id);
  if (eraNuovo >= 0) dati.nuovi.splice(eraNuovo, 1);
  else if (!dati.cancellati.includes(id)) dati.cancellati.push(id);
  delete dati.modificati[id];
  await salva();
}

export async function ripristinaSpot(id) {
  delete dati.modificati[id];
  dati.cancellati = dati.cancellati.filter((altro) => altro !== id);
  await salva();
}

export async function impostaConfig(via, valore) {
  if (valore === '' || valore === null || valore === undefined) delete dati.config[via];
  else dati.config[via] = valore;
  await salva();
  applicaConfig();
}

/** C'è qualcosa di modificato in locale? Lo chiede `data.js` per decidere se
 *  può fidarsi del motore, che le modifiche locali non le conosce. */
export function haModifiche() {
  return (
    accesa &&
    (Object.keys(dati.modificati).length > 0 ||
      dati.nuovi.length > 0 ||
      dati.cancellati.length > 0)
  );
}

export function conteggi() {
  return {
    modificati: Object.keys(dati.modificati).length,
    nuovi: dati.nuovi.length,
    cancellati: dati.cancellati.length,
    config: Object.keys(dati.config).length,
  };
}

/** Tutto quello che è stato cambiato, pronto da salvare in un file. */
export function esporta() {
  return {
    formato: 'pkfamily/sovrascritture',
    versione: 1,
    quando: new Date().toISOString(),
    nota: "Modifiche locali fatte dalla modalità sviluppatore. Non sono pubblicate da nessuna parte: per portarle nel prodotto servono una persona e una revisione.",
    ...structuredClone(dati),
  };
}

/**
 * Gli spot toccati, riscritti con i nomi di campo della fonte del repository
 * (`scripts/data/webapp_fixed_spots.json`): è il file da rivedere e unire a
 * mano, non una scorciatoia per pubblicare.
 */
export function esportaPerIlRepository(base) {
  const perId = new Map(base.map((voce) => [voce.id, voce]));
  const verso = (voce) => ({
    id: voce.id,
    name: voce.name,
    lat: voce.lat,
    lng: voce.lng,
    description: voce.description || '',
    skillLevel: voce.level || 'intermedio',
    crowdLevel: voce.crowd || 'medio',
    hasFountain: Boolean(voce.fountain),
    photosCount: (voce.photos || []).length,
    photos: voce.photos || [],
    rating: voce.rating || 0,
    ratingCount: voce.ratingCount || 0,
    status: voce.status || 'pending',
  });

  const modificati = Object.entries(dati.modificati)
    .map(([id, campi]) => {
      const originale = perId.get(id);
      return originale ? verso({ ...originale, ...campi }) : null;
    })
    .filter(Boolean);

  return {
    formato: 'pkfamily/spot-da-rivedere',
    versione: 1,
    quando: new Date().toISOString(),
    da_rivedere: modificati.concat(dati.nuovi.map(verso)),
    da_togliere: [...dati.cancellati],
  };
}

export async function importa(oggetto) {
  if (!oggetto || oggetto.formato !== 'pkfamily/sovrascritture') {
    throw new Error('non è un file di sovrascritture di PkFAMILY');
  }
  dati = {
    modificati: oggetto.modificati || {},
    nuovi: oggetto.nuovi || [],
    cancellati: oggetto.cancellati || [],
    config: oggetto.config || {},
  };
  await salva();
  applicaConfig();
  return conteggi();
}

export async function azzera() {
  dati = structuredClone(VUOTE);
  await salva();
}
