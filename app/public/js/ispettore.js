/* PkFAMILY — lo schema dedotto dai dati, invece che scritto a mano.
 *
 * Il pannello sviluppatore aveva due tabelle compilate a mano: otto campi di
 * uno spot su dodici, undici impostazioni su ventiquattro. Ogni campo nuovo
 * nei dati era un campo invisibile nel pannello, e nessuno se ne accorgeva —
 * il video di uno spot è rimasto fuori per giorni senza che niente protestasse.
 *
 * Qui lo schema si ricava guardando i dati: quali chiavi ci sono, di che tipo
 * sono i valori, e quali hanno così pochi valori distinti da meritare un menù
 * invece di un campo libero. Le regole di quel giudizio sono costanti con
 * scritto accanto il perché, perché sono scelte, non verità.
 *
 * Questo modulo è volutamente **puro**: nessun import, nessun DOM, nessuno
 * stato. Si può provare da solo, e `data.js` importa `admin.js` e mai il
 * contrario — un ciclo di dipendenze fermerebbe la costruzione della demo in
 * un file solo (`build_demo.py` esce con un errore al primo ciclo).
 */

/** Oltre questi valori distinti un campo non è più una scelta: è testo. */
export const SOGLIA_SCELTA = 12;

/** Sotto questi, un campo con un valore solo resterebbe un menù da una voce. */
export const MINIMO_SCELTA = 2;

/** Più lungo di così non è un'etichetta da menù: è una frase o un indirizzo. */
export const LUNGHEZZA_MASSIMA_SCELTA = 40;

/**
 * Quello che l'inferenza non può sapere, e che qualcuno deve dire.
 *
 * `status` è il caso che spiega la tabella: nei 1.706 spot valgono solo
 * `community` (1.680) e `verified` (26). Dedotto dai dati, il menù non
 * conterrebbe `pending` — che è proprio lo stato con cui nasce ogni spot
 * creato dal pannello. Una regola di prodotto non si indovina dai dati.
 */
export const VINCOLI = {
  spot: {
    id: { soloLettura: true },
    status: { valori: ['verified', 'community', 'pending'] },
  },
  tutorial: {
    id: { soloLettura: true },
  },
  fontanelle: {},
};

/** Le foglie di CONFIG che mandano dati fuori dal dispositivo. */
export const VINCOLI_CONFIG = {
  motore: { esce: true },
  'routing.servizio': { esce: true },
};

/** I campi che l'app attacca ai record mentre lavora: non sono dati. */
export const CAMPI_DERIVATI = new Set(['cerca', 'locale', 'metri']);

/**
 * Sembra una chiave segreta?
 *
 * La chiave pubblicabile di Supabase è fatta per stare nei client e va bene;
 * la segreta e un token JWT no. Il controllo sta qui, e non nel pannello, così
 * vale su **ogni** scrittura — un campo di uno spot, un'impostazione, una voce
 * del magazzino, un file importato — e non solo sulla casella dove qualcuno si
 * era ricordato di metterlo.
 */
export function sembraSegreta(valore) {
  const testo = String(valore || '');
  return /service_role|sb_secret|^eyJ[\w-]+\.[\w-]+\.[\w-]+$/.test(testo) && !testo.startsWith('sb_publishable');
}

/** Il segnaposto che prende il posto di un valore che non deve uscire. */
export const OSCURATO = '«valore oscurato dal pannello»';

/** Sostituisce il valore se sembra segreto; lascia stare tutto il resto. */
export function oscura(valore) {
  return typeof valore === 'string' && sembraSegreta(valore) ? OSCURATO : valore;
}

/** Il tipo di controllo giusto per un valore singolo. */
function tipoDi(valore) {
  if (typeof valore === 'boolean') return 'booleano';
  if (typeof valore === 'number') return 'numero';
  if (valore !== null && typeof valore === 'object') return 'json';
  return 'testo';
}

/** Un valore può stare in un menù, o è troppo lungo o è un indirizzo? */
function staInUnMenu(valore) {
  const testo = String(valore);
  return testo.length <= LUNGHEZZA_MASSIMA_SCELTA && !testo.includes('://');
}

/**
 * Le foglie di un albero di impostazioni: `[{via, tipo}]`.
 *
 * `via` è il percorso con i punti (`tiles.mappa.url`), che resta anche
 * l'etichetta mostrata: è la convenzione del pannello, e dice a chi legge
 * dove andare a cercare quel valore nel codice.
 */
export function foglie(oggetto, prefisso = '') {
  const trovate = [];
  for (const [nome, valore] of Object.entries(oggetto || {})) {
    const via = prefisso ? `${prefisso}.${nome}` : nome;
    if (valore !== null && typeof valore === 'object' && !Array.isArray(valore)) {
      trovate.push(...foglie(valore, via));
    } else {
      trovate.push({ via, tipo: tipoDi(valore), gruppo: via.includes('.') ? via.split('.')[0] : null });
    }
  }
  return trovate;
}

/**
 * Lo schema di una collezione, dedotto dalle voci che ci sono davvero.
 *
 * Restituisce `[{nome, tipo, valori?, presenti, soloLettura?}]` in ordine di
 * quanto spesso il campo compare: i campi che ci sono sempre stanno in cima,
 * quelli di un record su 1.706 in fondo, che è l'ordine in cui servono.
 *
 * `presenti` conta in quante voci il campo c'è: serve all'esportazione, che
 * deve saper distinguere «campo assente» da «campo vuoto» e non inventare un
 * `rating: 0` dove nel file non c'era niente.
 */
export function campi(voci, vincoli = {}) {
  const quante = new Map();
  const valoriDi = new Map();
  const tipiDi = new Map();

  for (const voce of voci || []) {
    for (const [nome, valore] of Object.entries(voce || {})) {
      if (CAMPI_DERIVATI.has(nome)) continue;
      quante.set(nome, (quante.get(nome) || 0) + 1);
      if (valore === null || valore === undefined) continue;
      if (!valoriDi.has(nome)) valoriDi.set(nome, new Set());
      if (!tipiDi.has(nome)) tipiDi.set(nome, new Set());
      tipiDi.get(nome).add(tipoDi(valore));
      const distinti = valoriDi.get(nome);
      // Oltre la soglia non serve continuare a contare: è già testo libero.
      if (distinti.size <= SOGLIA_SCELTA + 1) {
        distinti.add(typeof valore === 'object' ? JSON.stringify(valore) : valore);
      }
    }
  }

  const fuori = [];
  for (const [nome, presenti] of [...quante.entries()].sort((a, b) => b[1] - a[1])) {
    const vincolo = vincoli[nome] || {};
    const distinti = valoriDi.get(nome) || new Set();
    const tipi = tipiDi.get(nome) || new Set();
    const tipo = tipi.size === 1 ? [...tipi][0] : 'testo';

    let definizione = { nome, tipo, presenti };
    if (vincolo.soloLettura) definizione.soloLettura = true;

    if (vincolo.valori) {
      definizione = { ...definizione, tipo: 'scelta', valori: [...vincolo.valori] };
    } else if (
      tipo !== 'booleano' &&
      tipo !== 'json' &&
      distinti.size >= MINIMO_SCELTA &&
      distinti.size <= SOGLIA_SCELTA &&
      [...distinti].every(staInUnMenu)
    ) {
      definizione = { ...definizione, tipo: 'scelta', valori: [...distinti].sort() };
    }
    fuori.push(definizione);
  }
  return fuori;
}

/**
 * Riporta un valore scritto a mano al tipo che quel campo vuole.
 *
 * Restituisce `{ok, valore}` invece di sollevare: un JSON scritto storto è una
 * cosa che capita a chi corregge dati, e merita un messaggio, non un errore
 * che ferma il salvataggio di tutto il resto.
 */
export function pulisci(valore, tipo) {
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
