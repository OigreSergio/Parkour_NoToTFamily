/* PkFAMILY — l'offline come funzione, non come incidente.
 *
 * Due cose: sapere quanto dell'app è già sul dispositivo, e poter scaricare
 * in anticipo le tessere della zona dove si andrà ad allenarsi. Il secondo è
 * il motivo per cui questa app esiste: uno spot senza campo resta
 * raggiungibile se la mappa è già scesa a casa.
 */

import { CONFIG } from './config.js';
import { LATO_TESSERA } from './geo.js';

const CACHE_TILE = 'pkfamily-tiles';

const CACHE_MEDIA = 'pkfamily-media';
const PREFISSO_APP = 'pkfamily-app-';

function attesa(millisecondi) {
  return new Promise((risolvi) => setTimeout(risolvi, millisecondi));
}

async function conta(nome) {
  if (!(await caches.has(nome))) return 0;
  const cache = await caches.open(nome);
  return (await cache.keys()).length;
}

/**
 * Cosa c'è davvero sul dispositivo. Si legge dalla Cache API, non dal service
 * worker: così la risposta arriva anche mentre il worker sta ancora
 * installando, che è esattamente il momento in cui si va a curiosare.
 * Torna null se l'offline non è attivo (pagina non sicura, o prima visita
 * ancora in corso).
 */
export async function stato() {
  if (!('caches' in self)) return null;

  let nomi = await caches.keys();
  if (!nomi.some((nome) => nome.startsWith(PREFISSO_APP)) && 'serviceWorker' in navigator) {
    // Prima visita: si dà al worker il tempo di finire, ma non all'infinito.
    await Promise.race([navigator.serviceWorker.ready, attesa(6000)]);
    nomi = await caches.keys();
  }

  const nomeApp = nomi.find((nome) => nome.startsWith(PREFISSO_APP));
  if (!nomeApp) return null;

  const spazio =
    navigator.storage && navigator.storage.estimate ? await navigator.storage.estimate() : {};
  return {
    version: nomeApp.slice(PREFISSO_APP.length),
    app: await conta(nomeApp),
    tiles: await conta(CACHE_TILE),
    media: await conta(CACHE_MEDIA),
    usage: spazio.usage || 0,
    quota: spazio.quota || 0,
  };
}

/** Butta via tessere e foto: l'app resta installata e offline. */
export async function svuotaTessere() {
  await Promise.all([caches.delete(CACHE_TILE), caches.delete(CACHE_MEDIA)]);
}

/** Chiede al browser di non buttare via i dati dell'app quando ha fretta. */
export async function rendiPersistente() {
  if (!navigator.storage || !navigator.storage.persist) return false;
  if (await navigator.storage.persisted()) return true;
  return navigator.storage.persist();
}

function indirizzoTessera(sorgente, z, x, y) {
  return CONFIG.tiles[sorgente].url.replace('{z}', z).replace('{x}', x).replace('{y}', y);
}

/**
 * Gli indirizzi delle tessere che coprono un riquadro, dal livello `da` al
 * livello `a`, fermandosi al tetto per non riempire il telefono per sbaglio.
 */
export function tessereDelRiquadro(riquadro, sorgente, da, a, tetto = CONFIG.tettoPrefetch) {
  const indirizzi = [];
  const zoomMax = CONFIG.tiles[sorgente].zoomMax;

  for (let z = Math.max(1, Math.round(da)); z <= Math.min(Math.round(a), zoomMax); z++) {
    const n = 2 ** z;
    const perX = (lng) => Math.floor((((lng + 180) % 360) / 360) * n);
    const perY = (lat) => {
      const rad = (Math.max(-85.05, Math.min(85.05, lat)) * Math.PI) / 180;
      return Math.floor(((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * n);
    };
    const x1 = perX(riquadro.ovest);
    const x2 = perX(riquadro.est);
    const y1 = perY(riquadro.nord);
    const y2 = perY(riquadro.sud);
    for (let y = Math.min(y1, y2); y <= Math.max(y1, y2); y++) {
      for (let x = Math.min(x1, x2); x <= Math.max(x1, x2); x++) {
        if (indirizzi.length >= tetto) return indirizzi;
        indirizzi.push(indirizzoTessera(sorgente, z, ((x % n) + n) % n, y));
      }
    }
  }
  return indirizzi;
}

/**
 * Scarica le tessere e le mette dove il service worker le cercherà.
 * `avanzamento(fatte, totale)` viene chiamato lungo la strada.
 * Restituisce {scaricate, saltate, fallite}.
 */
export async function scarica(indirizzi, avanzamento) {
  const cache = await caches.open(CACHE_TILE);
  const esito = { scaricate: 0, saltate: 0, fallite: 0 };
  let indice = 0;

  async function operaio() {
    while (indice < indirizzi.length) {
      const mio = indirizzi[indice++];
      try {
        if (await cache.match(mio)) esito.saltate++;
        else {
          await cache.add(mio);
          esito.scaricate++;
        }
      } catch {
        esito.fallite++;
      }
      if (avanzamento) avanzamento(esito.scaricate + esito.saltate + esito.fallite, indirizzi.length);
    }
  }

  // Quattro alla volta: abbastanza da essere veloce, poco da non farsi
  // sbattere fuori dal server delle tessere.
  await Promise.all([operaio(), operaio(), operaio(), operaio()]);
  return esito;
}

/** Quante tessere servono, in numeri comprensibili prima di premere. */
export function stimaPeso(quante) {
  // Una tessera raster sta fra 10 e 40 kB: 25 kB è una media onesta.
  return { tessere: quante, byte: quante * 25 * 1024, lato: LATO_TESSERA };
}
