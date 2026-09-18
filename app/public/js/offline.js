/* PkFAMILY — l'offline come funzione, non come incidente.
 *
 * Due cose: sapere quanto dell'app è già sul dispositivo, e poter scaricare
 * in anticipo le tessere della zona dove si andrà ad allenarsi. Il secondo è
 * il motivo per cui questa app esiste: uno spot senza campo resta
 * raggiungibile se la mappa è già scesa a casa.
 */

import { CONFIG } from './config.js';
import { LATO_TESSERA } from './geo.js';
import { t } from './i18n.js';
import { avviso, conferma } from './ui.js';

const CACHE_TILE = 'pkfamily-tiles';
/** Le tessere scaricate apposta stanno in una cache loro: non vengono mai
 *  sfrattate per far posto a quelle viste passando. */
const CACHE_AREA = 'pkfamily-area';

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
    tiles: (await conta(CACHE_TILE)) + (await conta(CACHE_AREA)),
    area: await conta(CACHE_AREA),
    media: await conta(CACHE_MEDIA),
    usage: spazio.usage || 0,
    quota: spazio.quota || 0,
  };
}

/** Butta via tessere e foto: l'app resta installata e offline. */
export async function svuotaTessere() {
  await Promise.all([
    caches.delete(CACHE_TILE),
    caches.delete(CACHE_MEDIA),
    caches.delete(CACHE_AREA),
  ]);
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
 * livello `a`. Restituisce anche quante ne servirebbero in tutto: se il tetto
 * ne taglia via una parte, chi chiede deve poterlo dire invece di far credere
 * di aver scaricato tutto.
 */
export function tessereDelRiquadro(riquadro, sorgente, da, a, tetto = CONFIG.tettoPrefetch) {
  const indirizzi = [];
  const zoomMax = CONFIG.tiles[sorgente].zoomMax;
  let totale = 0;

  for (let z = Math.max(1, Math.round(da)); z <= Math.min(Math.round(a), zoomMax); z++) {
    const n = 2 ** z;
    const perX = (lng) => Math.floor(((((lng % 360) + 540) % 360) / 360) * n) % n;
    const perY = (lat) => {
      const rad = (Math.max(-85.05, Math.min(85.05, lat)) * Math.PI) / 180;
      return Math.floor(((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * n);
    };

    const y1 = perY(riquadro.nord);
    const y2 = perY(riquadro.sud);
    const primaY = Math.max(0, Math.min(y1, y2));
    const ultimaY = Math.min(n - 1, Math.max(y1, y2));

    // Le colonne si percorrono in avanti partendo da ovest, anche quando il
    // riquadro scavalca il 180° meridiano: percorrendole da min a max si
    // scaricava la fascia dall'altra parte del mondo.
    const xOvest = perX(riquadro.ovest);
    const xEst = perX(riquadro.est);
    const quante = ((xEst - xOvest + n) % n) + 1;

    for (let y = primaY; y <= ultimaY; y++) {
      for (let passo = 0; passo < quante; passo++) {
        totale += 1;
        if (indirizzi.length >= tetto) continue;
        indirizzi.push(indirizzoTessera(sorgente, z, (xOvest + passo) % n, y));
      }
    }
  }
  return { indirizzi, totale };
}

/**
 * Scarica le tessere e le mette dove il service worker le cercherà.
 * `avanzamento(fatte, totale)` viene chiamato lungo la strada.
 * Restituisce {scaricate, saltate, fallite}.
 */
export async function scarica(indirizzi, avanzamento) {
  const cache = await caches.open(CACHE_AREA);
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


/** Quanti livelli di zoom in più si scaricano oltre a quello che si vede. */
export const LIVELLI_IN_PIU = 3;

/**
 * Lo stato dello scaricamento vive qui e non nei nodi di una schermata: si
 * parte dalla mappa o da «Tu», si cambia schermata, e l'avanzamento resta.
 * È anche ciò che impedisce di farlo partire due volte.
 */
export const scaricamento = { inCorso: false, messaggio: '' };

function pesoLeggibile(byte) {
  const mega = byte / 1024 / 1024;
  return mega < 1024 ? `${mega.toFixed(mega < 10 ? 1 : 0)} MB` : `${(mega / 1024).toFixed(1)} GB`;
}

/**
 * Scarica la zona che la mappa sta mostrando. `progresso` viene chiamata a
 * ogni passo con il testo da mostrare; `finito` alla fine.
 * Restituisce true se lo scaricamento è davvero partito.
 */
export async function preparaArea(mappa, { progresso, finito } = {}) {
  if (scaricamento.inCorso || !mappa) return false;

  // Senza una misura vera il riquadro è un punto, e si scaricherebbero tre
  // tessere credendo di aver preparato una città.
  if (!mappa.misurata) {
    avviso(t('you.prepareNoMap'));
    return false;
  }

  const zoomOra = Math.round(mappa.zoom);
  const { indirizzi, totale } = tessereDelRiquadro(
    mappa.riquadro(),
    mappa.sorgente,
    zoomOra,
    zoomOra + LIVELLI_IN_PIU
  );
  if (!indirizzi.length) {
    avviso(t('you.prepareNoMap'));
    return false;
  }

  const peso = stimaPeso(indirizzi.length);
  const domanda =
    totale > indirizzi.length
      ? t('you.prepareAskCapped', {
          n: indirizzi.length,
          totale,
          peso: pesoLeggibile(peso.byte),
          z: zoomOra,
          zmax: zoomOra + LIVELLI_IN_PIU,
        })
      : t('you.prepareAsk', {
          n: indirizzi.length,
          peso: pesoLeggibile(peso.byte),
          z: zoomOra,
          zmax: zoomOra + LIVELLI_IN_PIU,
        });

  const procedi = await conferma(t('you.prepareTitle'), domanda, t('you.prepareGo'), t('common.cancel'));
  if (!procedi) return false;

  scaricamento.inCorso = true;
  scaricamento.messaggio = t('you.prepareProgress', { fatte: 0, totale: indirizzi.length });
  if (progresso) progresso(scaricamento.messaggio);

  await rendiPersistente();
  const esito = await scarica(indirizzi, (fatte, quante) => {
    scaricamento.messaggio = t('you.prepareProgress', { fatte, totale: quante });
    if (progresso) progresso(scaricamento.messaggio);
  });

  scaricamento.inCorso = false;
  scaricamento.messaggio = t('you.prepareDone', {
    scaricate: esito.scaricate,
    saltate: esito.saltate,
    fallite: esito.fallite,
  });
  if (progresso) progresso(scaricamento.messaggio);
  if (finito) finito(esito);
  return true;
}
