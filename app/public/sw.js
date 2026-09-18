/* PkFAMILY — il service worker: è la parte che fa funzionare l'app senza rete.
 *
 * Tre cache, con tre vite diverse:
 *
 *   pkfamily-app-<versione>  il guscio dell'app e i dati che porta con sé
 *                            (elenco in precache.json, generato da
 *                            app/tools/build_precache.py). Cambia versione,
 *                            si riscarica tutto e la vecchia sparisce.
 *   pkfamily-tiles           le tessere di mappa viste passando. Sono tante e
 *                            pesano: c'è un tetto, e le più vecchie escono
 *                            per prime.
 *   pkfamily-area            le tessere scaricate apposta con "prepara
 *                            quest'area": nessun tetto, nessuno sfratto.
 *   pkfamily-media           le foto degli spot già aperti.
 *
 * Quello che riguarda le persone — Supabase, il proxy dei percorsi — non
 * viene mai messo in cache: passa dalla rete o non passa affatto.
 */

const PREFISSO_APP = 'pkfamily-app-';
const CACHE_META = 'pkfamily-meta';
const CACHE_TILE = 'pkfamily-tiles';
/** Le tessere scaricate apposta dalla schermata «Tu»: stanno a parte e non
 *  vengono mai sfrattate. Chi prepara un'area prima di partire deve
 *  ritrovarla, non scoprire che è uscita per far posto a un giro in centro. */
const CACHE_AREA = 'pkfamily-area';
const CACHE_MEDIA = 'pkfamily-media';

// Tetti pensati per un telefono: ~4000 tessere sono già una città intera.
const MAX_TILE = 4000;
const MAX_MEDIA = 300;

const CHIAVE_VERSIONE = new URL('__pk_version', self.registration.scope).toString();

/** Indirizzo assoluto di un file dell'app, a partire dal percorso relativo. */
function indirizzo(relativo) {
  return new URL(relativo, self.registration.scope).toString();
}

/** Sembra una tessera di mappa? `.../{z}/{x}/{y}.png` o `.../tile/{z}/{y}/{x}`. */
function eTessera(url) {
  return /\/\d{1,2}\/\d{1,6}\/\d{1,6}(\.\w{2,4})?(\?|$)/.test(url.pathname + url.search);
}

// Contare le chiavi di una cache costa quanto leggerle tutte: farlo a ogni
// tessera salvata voleva dire quattromila letture per una scrittura. Si conta
// ogni tanto, e si aspetta l'esito invece di lasciarlo correre per conto suo.
const PASSO_POTATURA = 50;
const daUltimaPotatura = new Map();

/** Tiene la cache sotto il tetto, buttando le voci più vecchie. */
async function limita(nome, massimo) {
  const cache = await caches.open(nome);
  const chiavi = await cache.keys();
  if (chiavi.length <= massimo) return;
  for (const chiave of chiavi.slice(0, chiavi.length - massimo)) {
    await cache.delete(chiave);
  }
}

/** Pota, ma solo una volta ogni `PASSO_POTATURA` scritture. */
async function forsePota(nome, massimo) {
  const contate = (daUltimaPotatura.get(nome) || 0) + 1;
  if (contate < PASSO_POTATURA) {
    daUltimaPotatura.set(nome, contate);
    return;
  }
  daUltimaPotatura.set(nome, 0);
  await limita(nome, massimo);
}

async function versioneInstallata() {
  const meta = await caches.open(CACHE_META);
  const risposta = await meta.match(CHIAVE_VERSIONE);
  return risposta ? risposta.text() : null;
}

async function installa() {
  // precache.json va letto dalla rete, altrimenti non ci si accorge mai di un
  // aggiornamento; se la rete non c'è, l'installazione fallisce e resta buona
  // quella di prima.
  const risposta = await fetch(indirizzo('precache.json'), { cache: 'no-store' });
  if (!risposta.ok) throw new Error('precache.json non raggiungibile');
  const elenco = await risposta.json();

  const cache = await caches.open(PREFISSO_APP + elenco.version);
  await cache.addAll(elenco.files.map(indirizzo));

  const meta = await caches.open(CACHE_META);
  await meta.put(CHIAVE_VERSIONE, new Response(elenco.version));
}

async function attiva() {
  const versione = await versioneInstallata();
  const nomi = await caches.keys();
  await Promise.all(
    nomi
      .filter((nome) => nome.startsWith(PREFISSO_APP) && nome !== PREFISSO_APP + versione)
      .map((nome) => caches.delete(nome))
  );
  await self.clients.claim();
}

/** Prima la cache, poi la rete; quello che arriva dalla rete resta. */
async function primaLaCache(richiesta, nomeCache, massimo) {
  const cache = await caches.open(nomeCache);
  const salvata = await cache.match(richiesta);
  if (salvata) return salvata;

  const risposta = await fetch(richiesta);
  // Le risposte opache (no-cors) si salvano lo stesso: valgono per le tessere.
  if (risposta && (risposta.ok || risposta.type === 'opaque')) {
    await cache.put(richiesta, risposta.clone());
    if (massimo) await forsePota(nomeCache, massimo);
  }
  return risposta;
}

async function rispondi(evento) {
  const richiesta = evento.request;
  const url = new URL(richiesta.url);
  const versione = await versioneInstallata();
  const cacheApp = PREFISSO_APP + versione;

  // Il file che dice quale versione esiste: sempre dalla rete, se c'è.
  if (url.toString() === indirizzo('precache.json')) {
    try {
      return await fetch(richiesta, { cache: 'no-store' });
    } catch {
      const cache = await caches.open(cacheApp);
      return (await cache.match(richiesta)) || Response.error();
    }
  }

  // Una navigazione (apertura dell'app, ricarica, link aperto dall'icona):
  // si risponde sempre con il guscio già in cache. È questo che permette di
  // aprire l'app in metropolitana.
  if (richiesta.mode === 'navigate') {
    const cache = await caches.open(cacheApp);
    const guscio = await cache.match(indirizzo('index.html'));
    if (guscio) return guscio;
    try {
      return await fetch(richiesta);
    } catch {
      return new Response(
        '<!doctype html><meta charset="utf-8"><p>PkFAMILY non è ancora installata su questo dispositivo: apri l\'app una volta con la rete.</p>',
        { headers: { 'Content-Type': 'text/html; charset=utf-8' }, status: 503 }
      );
    }
  }

  const stessaOrigine = url.origin === self.location.origin;

  // Il motore della demo in Python risponde sotto /api/: sono domande su dati,
  // non file. Una risposta vecchia servita dalla cache sarebbe peggio di
  // nessuna risposta.
  if (stessaOrigine && url.pathname.includes('/api/')) {
    return fetch(richiesta);
  }

  if (stessaOrigine) {
    return primaLaCache(richiesta, cacheApp, null).catch(async () => {
      const cache = await caches.open(cacheApp);
      return (await cache.match(richiesta)) || Response.error();
    });
  }

  if (eTessera(url)) {
    // Prima si guarda fra le tessere scaricate apposta: quelle non scadono e
    // non escono mai dalla cache.
    const area = await caches.open(CACHE_AREA);
    const preparata = await area.match(richiesta);
    if (preparata) return preparata;
    return primaLaCache(richiesta, CACHE_TILE, MAX_TILE).catch(() => Response.error());
  }

  if (richiesta.destination === 'image') {
    return primaLaCache(richiesta, CACHE_MEDIA, MAX_MEDIA).catch(() => Response.error());
  }

  // Supabase, percorsi, qualunque altra chiamata: rete e basta. Nessun dato
  // che riguarda una persona finisce in una cache del browser.
  return fetch(richiesta);
}

self.addEventListener('install', (evento) => {
  evento.waitUntil(installa());
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(attiva());
});

self.addEventListener('fetch', (evento) => {
  if (evento.request.method !== 'GET') return;
  evento.respondWith(rispondi(evento));
});

self.addEventListener('message', (evento) => {
  // Un solo messaggio: "installa subito la versione nuova". Lo stato delle
  // cache la pagina se lo legge da sola (js/offline.js), che funziona anche
  // mentre questo worker sta ancora installando.
  if (evento.data && evento.data.type === 'skip-waiting') self.skipWaiting();
});
