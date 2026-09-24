/* PkFAMILY — la modalità sviluppatore.
 *
 * Serve a cambiare le cose senza aprire un editor: correggere uno spot o un
 * tutorial, spostarne il punto, provare un altro filtro sulle tessere, puntare
 * l'app a un altro server dei percorsi. È pensata per chi fa il prodotto, non
 * per chi lo usa, e si accende a mano dalla schermata «Tu».
 *
 * Tre regole che non si negoziano, e che sono scritte anche nel pannello:
 *
 * 1. **Tutto resta su questo dispositivo.** Nessuna modifica parte verso
 *    Supabase o verso chiunque altro: si esportano dei file, e a portarli nel
 *    repository è una persona (masterplan, principio 5).
 * 2. **Niente si finge verificato.** Ogni voce toccata o creata qui porta il
 *    segno `locale`, e l'app lo mostra: uno spot diventa `verified` quando una
 *    persona lo verifica davvero, non perché qualcuno ha cambiato una casella
 *    su un telefono.
 * 3. **Nessuna chiave segreta.** Si può indicare l'indirizzo di Supabase e la
 *    chiave pubblicabile, che è fatta per stare nei client. La chiave segreta
 *    non entra qui — da nessuna porta: il controllo sta su ogni scrittura, non
 *    sulla singola casella dove qualcuno si era ricordato di metterlo.
 *
 * Il modello delle sovrascritture è per **collezione**: gli spot non sono più
 * un caso speciale, e i tutorial si correggono come loro. Le fontanelle no, e
 * non è una dimenticanza: sono 3.687 voci senza una chiave propria, la stessa
 * fontanella sta accanto a più spot, e una chiave inventata si romperebbe alla
 * prima rigenerazione dei dati. Si guardano e si esportano; si correggono su
 * OpenStreetMap, che è da dove vengono.
 */

import { CONFIG } from './config.js';
import {
  CAMPI_DERIVATI,
  VINCOLI,
  VINCOLI_CONFIG,
  campi as campiDedotti,
  foglie,
  oscura,
  pulisci as pulisciValore,
  sembraSegreta,
} from './ispettore.js';
import { leggi, scrivi } from './store.js';

const CHIAVE_STATO = 'admin.attiva';
const CHIAVE_DATI = 'admin.sovrascritture';

/** Le chiavi del magazzino che il pannello usa per sé: non si toccano da lì. */
const CHIAVI_BLOCCATE = new Set([CHIAVE_STATO, CHIAVE_DATI]);

/** La forma delle sovrascritture, versione 2: per collezione, non solo spot. */
const VUOTE = {
  versione: 2,
  collezioni: {
    spot: { modificati: {}, nuovi: [], cancellati: [] },
    tutorial: { modificati: {}, nuovi: [], cancellati: [] },
  },
  /** "spot:<id>" → {motivo, quando}: il segno «da rivedere», fuori dai record. */
  revisioni: {},
  config: {},
  /** Sale e basta: serve a non riusare mai l'identificativo di una voce
   *  cancellata. Due esportazioni fatte a distanza descriverebbero due spot
   *  diversi con lo stesso nome, e chi le unisce non avrebbe modo di saperlo. */
  contatore: 0,
};

let accesa = false;
let dati = structuredClone(VUOTE);

/**
 * Le collezioni che il pannello sa mostrare. Le registra `data.js`, che è
 * l'unico a sapere dove stanno i dati: così `admin.js` resta un modulo foglia
 * e non importa `data.js` — un ciclo fermerebbe la costruzione della demo in
 * un file solo (`build_demo.py` esce con un errore al primo ciclo trovato).
 */
const REGISTRO = new Map();

/** Lo schema dedotto, calcolato una volta sola per collezione. */
const SCHEMI = new Map();

/**
 * I valori che CONFIG aveva prima che il pannello li sovrascrivesse.
 *
 * Non si salvano sul dispositivo: si catturano a ogni avvio. Servono perché
 * togliere una sovrascrittura significhi **tornare al valore del file**, e non
 * lasciare in giro quello vecchio fino al riavvio successivo — che è come si
 * comportava prima, e faceva sembrare che «torna com'era» non funzionasse.
 */
const fabbrica = new Map();

/** Chi prova a scrivere un segreto se lo sente dire. */
export class ErroreSegreto extends Error {
  constructor() {
    super('chiave segreta rifiutata');
    this.name = 'ErroreSegreto';
    this.code = 'secret_refused';
  }
}

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

// --- collezioni --------------------------------------------------------------

/**
 * Registra una collezione. `base` è una **funzione**: alla registrazione i
 * dati non sono ancora stati letti (`admin.inizializza()` viene prima di
 * `dati.carica()`), e una lista catturata adesso sarebbe vuota per sempre.
 */
export function registra({ nome, base, chiave = 'id', soloLettura = false }) {
  REGISTRO.set(nome, { nome, base, chiave, soloLettura });
  SCHEMI.delete(nome);
}

export function collezioni() {
  return [...REGISTRO.keys()];
}

export function descrittore(nome) {
  return REGISTRO.get(nome) || null;
}

/** Il ramo delle sovrascritture di una collezione, creato se non c'è. */
function ramo(nome) {
  if (!dati.collezioni[nome]) dati.collezioni[nome] = { modificati: {}, nuovi: [], cancellati: [] };
  return dati.collezioni[nome];
}

/** Lo schema di una collezione: i campi che ci sono davvero, più i vincoli. */
export function campiDi(nome) {
  if (SCHEMI.has(nome)) return SCHEMI.get(nome);
  const descr = REGISTRO.get(nome);
  if (!descr) return [];
  const schema = campiDedotti(applica(nome, descr.base() || []), VINCOLI[nome] || {});
  SCHEMI.set(nome, schema);
  return schema;
}

/** Le foglie di CONFIG, con il gruppo e il segno di quelle che escono. */
export function campiConfig() {
  return foglie(CONFIG).map((foglia) => ({
    ...foglia,
    ...(VINCOLI_CONFIG[foglia.via] || {}),
    gruppo: foglia.gruppo || 'altre',
  }));
}

// --- sovrapposizione ---------------------------------------------------------

/**
 * Le voci di una collezione come le vede l'app: cancellate tolte, modificate
 * unite, nuove in fondo. Quello che è passato di qui porta `locale: true`.
 */
export function applica(nome, base) {
  if (!accesa) return base;
  const mio = dati.collezioni[nome];
  if (!mio) return base;
  const cancellati = new Set(mio.cancellati);
  const chiave = (REGISTRO.get(nome) || {}).chiave || 'id';
  const uniti = base
    .filter((voce) => !cancellati.has(voce[chiave]))
    .map((voce) => {
      const modifica = mio.modificati[voce[chiave]];
      return modifica ? { ...voce, ...modifica, locale: true } : voce;
    });
  return uniti.concat(mio.nuovi.map((voce) => ({ ...voce, locale: true })));
}

/** Storico: vale ancora, ed è una riga. */
export function applicaAgliSpot(base) {
  return applica('spot', base);
}

/**
 * Riporta i campi scritti a mano al tipo che vogliono, e **conserva quelli
 * che lo schema non conosce**.
 *
 * Prima si scartavano in silenzio tutti i campi fuori dalla tabella: l'app
 * diceva «salvato» e li perdeva. I campi che l'app si attacca da sé mentre
 * lavora (`cerca`, `locale`, `metri`) restano fuori: non sono dati, e finirebbero
 * dritti nell'esportazione.
 */
function pulisci(campi, nome) {
  const schema = new Map(campiDi(nome).map((c) => [c.nome, c]));
  const puliti = {};
  const scartati = [];
  for (const [chiave, grezzo] of Object.entries(campi || {})) {
    if (CAMPI_DERIVATI.has(chiave)) continue;
    if (typeof grezzo === 'string' && sembraSegreta(grezzo)) throw new ErroreSegreto();
    const definizione = schema.get(chiave);
    if (!definizione) {
      puliti[chiave] = grezzo; // l'app non lo conosce, ma è un dato: si tiene
      continue;
    }
    if (definizione.soloLettura) continue;
    const tipo = definizione.tipo === 'scelta' ? 'testo' : definizione.tipo;
    const esito = pulisciValore(grezzo, tipo);
    if (esito.ok) puliti[chiave] = esito.valore;
    else scartati.push(chiave);
  }
  if (scartati.length) {
    const errore = new Error(`valori non validi: ${scartati.join(', ')}`);
    errore.code = 'invalid_values';
    errore.campi = scartati;
    throw errore;
  }
  return puliti;
}

export async function salva(nome, id, campi) {
  const mio = ramo(nome);
  mio.modificati[id] = { ...(mio.modificati[id] || {}), ...pulisci(campi, nome) };
  await persisti();
  return mio.modificati[id];
}

export async function salvaSpot(id, campi) {
  return salva('spot', id, campi);
}

/**
 * Un identificativo che non si ripete.
 *
 * Prima si contavano le voci nuove: cancellata una e creata un'altra con lo
 * stesso nome, due voci finivano con lo stesso identificativo. Qui il contatore
 * sale e basta, e l'unicità si controlla comunque contro il file e contro le
 * nuove — un contatore che riparte da zero (importazione, azzeramento) non
 * deve poter creare un doppione.
 */
function identificativo(nome, campi) {
  const descr = REGISTRO.get(nome);
  const chiave = (descr || {}).chiave || 'id';
  const presi = new Set([
    ...(descr && descr.base ? (descr.base() || []).map((v) => v[chiave]) : []),
    ...ramo(nome).nuovi.map((v) => v[chiave]),
  ]);
  const radice = String(campi.name || campi.title || nome)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .slice(0, 24);
  // Il contatore non riparte mai: contare le voci nuove voleva dire che,
  // cancellata una e creata un'altra con lo stesso nome, tornava fuori lo
  // stesso identificativo.
  dati.contatore = (dati.contatore || 0) + 1;
  let candidato = `locale-${dati.contatore}-${radice}`;
  while (presi.has(candidato)) {
    dati.contatore += 1;
    candidato = `locale-${dati.contatore}-${radice}`;
  }
  return candidato;
}

export async function crea(nome, campi) {
  const descr = REGISTRO.get(nome);
  if (descr && descr.soloLettura) throw new Error(`${nome} è in sola lettura`);
  const chiave = (descr || {}).chiave || 'id';
  const voce = {
    [chiave]: identificativo(nome, campi),
    ...pulisci(campi, nome),
  };
  // Quello che nasce qui non è verificato da nessuno, e lo `status` scelto nel
  // pannello non può dire il contrario: si scrive **dopo** i campi.
  if (nome === 'spot') voce.status = 'pending';
  ramo(nome).nuovi.push(voce);
  await persisti();
  return voce;
}

export async function creaSpot(campi) {
  return crea('spot', campi);
}

export async function cancella(nome, id) {
  const mio = ramo(nome);
  const eraNuovo = mio.nuovi.findIndex((voce) => voce.id === id);
  if (eraNuovo >= 0) mio.nuovi.splice(eraNuovo, 1);
  else if (!mio.cancellati.includes(id)) mio.cancellati.push(id);
  delete mio.modificati[id];
  delete dati.revisioni[`${nome}:${id}`];
  await persisti();
}

export async function cancellaSpot(id) {
  return cancella('spot', id);
}

export async function ripristina(nome, id) {
  const mio = ramo(nome);
  delete mio.modificati[id];
  mio.cancellati = mio.cancellati.filter((altro) => altro !== id);
  await persisti();
}

export async function ripristinaSpot(id) {
  return ripristina('spot', id);
}

/** Riporta al file **un campo solo**, lasciando corretti gli altri. */
export async function ripristinaCampo(nome, id, campo) {
  const mio = ramo(nome);
  if (!mio.modificati[id]) return;
  delete mio.modificati[id][campo];
  if (!Object.keys(mio.modificati[id]).length) delete mio.modificati[id];
  await persisti();
}

// --- da rivedere -------------------------------------------------------------

/** Segna una voce come «da rivedere», con il motivo. Motivo vuoto lo toglie. */
export async function segnaRevisione(nome, id, motivo) {
  const via = `${nome}:${id}`;
  const testo = String(motivo || '').trim();
  if (!testo) delete dati.revisioni[via];
  else dati.revisioni[via] = { motivo: testo, quando: new Date().toISOString() };
  await persisti();
}

export function revisione(nome, id) {
  return dati.revisioni[`${nome}:${id}`] || null;
}

// --- configurazione ----------------------------------------------------------

export function valoreConfig(via) {
  return dentro(CONFIG, via);
}

/** Applica a CONFIG quello che è stato cambiato, ricordando com'era prima. */
function applicaConfig() {
  for (const [via, valore] of Object.entries(dati.config)) {
    if (!fabbrica.has(via)) fabbrica.set(via, dentro(CONFIG, via));
    poni(CONFIG, via, valore);
  }
}

/**
 * Dice qual è il valore «di fabbrica» di una foglia.
 *
 * Serve a `app.js`: `CONFIG.motore` viene impostato da `build.json` **dopo**
 * `admin.inizializza()`. Senza questa, la fabbrica catturata all'avvio direbbe
 * stringa vuota, e un azzeramento spegnerebbe il motore della demo.
 */
export function aggiornaFabbrica(via, valore) {
  fabbrica.set(via, valore);
}

export async function impostaConfig(via, valore) {
  if (typeof valore === 'string' && sembraSegreta(valore)) throw new ErroreSegreto();
  if (valore === '' || valore === null || valore === undefined) {
    delete dati.config[via];
    // Torna subito il valore del file, senza aspettare un riavvio.
    if (fabbrica.has(via)) poni(CONFIG, via, fabbrica.get(via));
  } else {
    if (!fabbrica.has(via)) fabbrica.set(via, dentro(CONFIG, via));
    dati.config[via] = valore;
  }
  await persisti();
  applicaConfig();
}

// --- magazzino ---------------------------------------------------------------

/** Le chiavi che il pannello usa per sé e non lascia cambiare da fuori. */
export function chiaveMagazzinoBloccata(chiave) {
  return CHIAVI_BLOCCATE.has(chiave);
}

// --- stato -------------------------------------------------------------------

export async function inizializza() {
  accesa = Boolean(await leggi(CHIAVE_STATO, false));
  dati = migra(await leggi(CHIAVE_DATI, null));
  if (accesa) applicaConfig();
  return accesa;
}

export async function accendi(valore) {
  accesa = Boolean(valore);
  await scrivi(CHIAVE_STATO, accesa);
  return accesa;
}

async function persisti() {
  SCHEMI.clear(); // i dati sono cambiati: lo schema si rideduce
  await scrivi(CHIAVE_DATI, dati);
}

/**
 * Porta alla forma di adesso quello che si trova salvato.
 *
 * La versione 1 teneva `modificati`/`nuovi`/`cancellati` al primo livello e
 * valeva solo per gli spot. Senza questa funzione un telefono che le aveva
 * salvate le avrebbe perse tutte al primo salvataggio, in silenzio: è il modo
 * peggiore di perdere il lavoro di qualcuno.
 */
export function migra(oggetto) {
  if (!oggetto || typeof oggetto !== 'object') return structuredClone(VUOTE);
  if (oggetto.collezioni) {
    const fuori = structuredClone(VUOTE);
    for (const [nome, ramoSalvato] of Object.entries(oggetto.collezioni)) {
      fuori.collezioni[nome] = {
        modificati: ramoSalvato.modificati || {},
        nuovi: ramoSalvato.nuovi || [],
        cancellati: ramoSalvato.cancellati || [],
      };
    }
    fuori.revisioni = oggetto.revisioni || {};
    fuori.config = oggetto.config || {};
    fuori.contatore = Number(oggetto.contatore) || 0;
    return fuori;
  }
  const fuori = structuredClone(VUOTE);
  fuori.collezioni.spot = {
    modificati: oggetto.modificati || {},
    nuovi: oggetto.nuovi || [],
    cancellati: oggetto.cancellati || [],
  };
  fuori.config = oggetto.config || {};
  return fuori;
}

/**
 * C'è qualcosa di modificato in locale? Lo chiede `data.js` per decidere se
 * può fidarsi del motore, che le modifiche locali non le conosce. Senza nome,
 * risponde per una collezione qualsiasi.
 */
export function haModifiche(nome) {
  if (!accesa) return false;
  const rami = nome ? [dati.collezioni[nome]] : Object.values(dati.collezioni);
  return rami.some(
    (mio) =>
      mio &&
      (Object.keys(mio.modificati).length > 0 || mio.nuovi.length > 0 || mio.cancellati.length > 0)
  );
}

/** I conteggi di una collezione, nella forma di sempre. */
export function conteggi(nome = 'spot') {
  const mio = dati.collezioni[nome] || { modificati: {}, nuovi: [], cancellati: [] };
  return {
    modificati: Object.keys(mio.modificati).length,
    nuovi: mio.nuovi.length,
    cancellati: mio.cancellati.length,
    config: Object.keys(dati.config).length,
    revisioni: Object.keys(dati.revisioni).filter((via) => via.startsWith(`${nome}:`)).length,
  };
}

export function conteggiTotali() {
  const per = {};
  for (const nome of Object.keys(dati.collezioni)) per[nome] = conteggi(nome);
  return {
    per,
    config: Object.keys(dati.config).length,
    revisioni: Object.keys(dati.revisioni).length,
  };
}

// --- file --------------------------------------------------------------------

/** Nessun valore che sembri un segreto esce in un file, nemmeno per sbaglio. */
function ripulitoDaiSegreti(valore) {
  if (typeof valore === 'string') return oscura(valore);
  if (Array.isArray(valore)) return valore.map(ripulitoDaiSegreti);
  if (valore && typeof valore === 'object') {
    return Object.fromEntries(Object.entries(valore).map(([k, v]) => [k, ripulitoDaiSegreti(v)]));
  }
  return valore;
}

/**
 * Tutto quello che è stato cambiato, pronto da salvare in un file.
 *
 * Porta la versione 2 **e** rispecchia gli spot al primo livello: in giro ci
 * sono copie già consegnate (APK, beta, bundle del Mac) che leggono solo
 * quelle. Un formato consegnato è un contratto.
 *
 * Il magazzino del dispositivo non entra qui: dentro ci sono l'ultima vista
 * della mappa — che è dove è stata una persona — le note e la coda delle
 * segnalazioni. Escluderlo per regola chiude la questione una volta sola.
 */
export function esporta() {
  const spot = dati.collezioni.spot || { modificati: {}, nuovi: [], cancellati: [] };
  return ripulitoDaiSegreti({
    formato: 'pkfamily/sovrascritture',
    versione: 2,
    quando: new Date().toISOString(),
    nota: "Modifiche locali fatte dalla modalità sviluppatore. Non sono pubblicate da nessuna parte: per portarle nel prodotto servono una persona e una revisione.",
    collezioni: structuredClone(dati.collezioni),
    revisioni: structuredClone(dati.revisioni),
    config: structuredClone(dati.config),
    contatore: dati.contatore || 0,
    // Rispecchiati per le copie che leggono ancora la versione 1.
    modificati: structuredClone(spot.modificati),
    nuovi: structuredClone(spot.nuovi),
    cancellati: [...spot.cancellati],
  });
}

/**
 * Gli spot toccati, riscritti con i nomi di campo della fonte del repository
 * (`scripts/data/webapp_fixed_spots.json`): è il file da rivedere e unire a
 * mano, non una scorciatoia per pubblicare.
 */
export function esportaPerIlRepository(base, impronta = null) {
  const perId = new Map(base.map((voce) => [voce.id, voce]));
  const presenti = new Map(campiDi('spot').map((c) => [c.nome, c.presenti]));

  const verso = (voce, toccati = []) => {
    const fuori = {
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
      status: voce.status || 'pending',
    };
    // `rating` e `ratingCount` non si inventano: nei 1.706 spot non li ha
    // nessuno, e riemetterli a zero significherebbe scrivere nella fonte un
    // dato che non è mai esistito.
    if (voce.rating !== undefined || presenti.get('rating')) fuori.rating = voce.rating || 0;
    if (voce.ratingCount !== undefined || presenti.get('ratingCount')) {
      fuori.ratingCount = voce.ratingCount || 0;
    }
    if (toccati.length) {
      fuori.campi_toccati = [...toccati];
      // Senza questo, una casella toccata su un telefono arriva nella fonte
      // come uno spot verificato, e il generatore lo conta fra i verificati.
      if (toccati.includes('status')) fuori.status_cambiato_in_locale = true;
    }
    const segno = dati.revisioni[`spot:${voce.id}`];
    if (segno) fuori.da_rivedere_perche = segno.motivo;
    return fuori;
  };

  const spot = dati.collezioni.spot || { modificati: {}, nuovi: [], cancellati: [] };

  /**
   * Gli spot che devono comparire nel file: quelli corretti, **più** quelli
   * segnati «da rivedere» senza aver cambiato niente.
   *
   * I secondi sono il caso più frequente del segno, non un caso limite: «la
   * foto non è di questo posto, non so quale sia quella giusta» è una
   * segnalazione che non tocca nessun campo. Senza questa riga quel segno si
   * contava nel pannello e poi non arrivava nel file, cioè non arrivava a
   * nessuno.
   */
  const daEmettere = new Set(Object.keys(spot.modificati));
  for (const via of Object.keys(dati.revisioni)) {
    if (!via.startsWith('spot:')) continue;
    const id = via.slice('spot:'.length);
    if (perId.has(id)) daEmettere.add(id);
  }

  const modificati = [...daEmettere]
    .map((id) => {
      const originale = perId.get(id);
      const campi = spot.modificati[id] || {};
      return originale ? verso({ ...originale, ...campi }, Object.keys(campi)) : null;
    })
    .filter(Boolean);

  return ripulitoDaiSegreti({
    formato: 'pkfamily/spot-da-rivedere',
    versione: 2,
    quando: new Date().toISOString(),
    nota: "Da rivedere a mano. Niente qui è verificato: `status_cambiato_in_locale` segna gli spot in cui lo stato è stato toccato su un dispositivo.",
    // L'impronta della base serve ad accorgersi che questo file è vecchio.
    base: impronta,
    da_rivedere: modificati.concat(spot.nuovi.map((voce) => verso(voce))),
    da_togliere: [...spot.cancellati],
  });
}

/** Un valore qualsiasi, in profondità, sembra un segreto? */
function contieneSegreti(valore) {
  if (typeof valore === 'string') return sembraSegreta(valore);
  if (Array.isArray(valore)) return valore.some(contieneSegreti);
  if (valore && typeof valore === 'object') return Object.values(valore).some(contieneSegreti);
  return false;
}

/**
 * Legge un file di sovrascritture.
 *
 * Due controlli che prima non c'erano, e che sono la parte importante:
 *
 * - un file che contiene una chiave segreta in un punto qualsiasi viene
 *   rifiutato **per intero**: non si applica metà di un file sospetto;
 * - le impostazioni che il pannello non espone vengono scartate, e si dice
 *   quante. Prima passava qualunque percorso: bastava un `motore` in un file
 *   perché l'app iniziasse a mandare le ricerche — e con loro la posizione di
 *   chi la usa — a un indirizzo scelto da chi aveva scritto il file.
 */
export async function importa(oggetto) {
  if (!oggetto || oggetto.formato !== 'pkfamily/sovrascritture') {
    throw new Error('non è un file di sovrascritture di PkFAMILY');
  }
  if (contieneSegreti(oggetto)) throw new ErroreSegreto();

  const nuovi = migra(oggetto);
  // Un file può cambiare le impostazioni che il pannello espone, ma **non**
  // quelle che mandano dati fuori dal dispositivo: `motore` e il servizio dei
  // percorsi. Scriverle a mano nel pannello è un gesto di chi sta lì; farlo
  // fare a un file è un indirizzo scelto da qualcun altro, verso cui l'app
  // manderebbe le ricerche e con loro la posizione di chi le fa.
  const permesse = new Set(campiConfig().filter((f) => !f.esce).map((f) => f.via));
  const config = {};
  let scartate = 0;
  for (const [via, valore] of Object.entries(nuovi.config)) {
    if (permesse.has(via)) config[via] = valore;
    else scartate += 1;
  }
  nuovi.config = config;

  dati = nuovi;
  await persisti();
  applicaConfig();
  return { ...conteggi('spot'), scartate, migrato: !oggetto.collezioni };
}

export async function azzera() {
  // Prima di buttare via le sovrascritture, CONFIG torna com'era nel file:
  // altrimenti i valori provati resterebbero in vigore fino al riavvio.
  for (const [via, valore] of fabbrica.entries()) poni(CONFIG, via, valore);
  dati = structuredClone(VUOTE);
  await persisti();
}

export { sembraSegreta };
