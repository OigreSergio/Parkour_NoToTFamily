/* PkFAMILY — quello che resta sul dispositivo, e che non esce di lì.
 *
 * IndexedDB tiene le preferenze, i preferiti, le note personali su uno spot e
 * la coda dei contributi scritti offline. Se IndexedDB non è disponibile
 * (finestra anonima, dati del sito bloccati) si ripiega su localStorage e, se
 * manca anche quello, sulla memoria: l'app deve aprirsi lo stesso.
 *
 * Niente di ciò che sta qui viene inviato da solo a nessuno. La coda parte
 * solo quando una persona tocca "invia" e Supabase è configurato.
 */

const NOME_DB = 'pkfamily';
const VERSIONE_DB = 1;
const DEPOSITI = ['kv', 'preferiti', 'note', 'coda'];

let promessaDb = null;
const memoria = new Map();

function apri() {
  if (promessaDb) return promessaDb;
  promessaDb = new Promise((risolvi) => {
    let richiesta;
    try {
      richiesta = indexedDB.open(NOME_DB, VERSIONE_DB);
    } catch {
      risolvi(null);
      return;
    }
    richiesta.onupgradeneeded = () => {
      const db = richiesta.result;
      if (!db.objectStoreNames.contains('kv')) db.createObjectStore('kv');
      if (!db.objectStoreNames.contains('preferiti')) db.createObjectStore('preferiti');
      if (!db.objectStoreNames.contains('note')) db.createObjectStore('note');
      if (!db.objectStoreNames.contains('coda')) {
        db.createObjectStore('coda', { keyPath: 'id', autoIncrement: true });
      }
    };
    richiesta.onsuccess = () => risolvi(richiesta.result);
    richiesta.onerror = () => risolvi(null);
    richiesta.onblocked = () => risolvi(null);
  });
  return promessaDb;
}

function chiaveRipiego(deposito, chiave) {
  return `pkfamily.${deposito}.${chiave}`;
}

function daRipiego(deposito, chiave) {
  const k = chiaveRipiego(deposito, chiave);
  try {
    const grezzo = localStorage.getItem(k);
    return grezzo === null ? undefined : JSON.parse(grezzo);
  } catch {
    return memoria.get(k);
  }
}

function inRipiego(deposito, chiave, valore) {
  const k = chiaveRipiego(deposito, chiave);
  try {
    if (valore === undefined) localStorage.removeItem(k);
    else localStorage.setItem(k, JSON.stringify(valore));
  } catch {
    if (valore === undefined) memoria.delete(k);
    else memoria.set(k, valore);
  }
}

async function transazione(deposito, modo, azione) {
  const db = await apri();
  if (!db) return { ripiego: true };
  return new Promise((risolvi) => {
    let tx;
    try {
      tx = db.transaction(deposito, modo);
    } catch {
      risolvi({ ripiego: true });
      return;
    }
    const richiesta = azione(tx.objectStore(deposito));
    tx.onabort = () => risolvi({ ripiego: true });
    tx.onerror = () => risolvi({ ripiego: true });
    tx.oncomplete = () => risolvi({ valore: richiesta ? richiesta.result : undefined });
  });
}

/** Legge un valore, o `predefinito` se non c'è. */
export async function leggi(chiave, predefinito = undefined) {
  const esito = await transazione('kv', 'readonly', (deposito) => deposito.get(chiave));
  if (esito.ripiego) {
    const valore = daRipiego('kv', chiave);
    return valore === undefined ? predefinito : valore;
  }
  return esito.valore === undefined ? predefinito : esito.valore;
}

/** Scrive un valore. `undefined` lo cancella. */
export async function scrivi(chiave, valore) {
  const esito = await transazione('kv', 'readwrite', (deposito) =>
    valore === undefined ? deposito.delete(chiave) : deposito.put(valore, chiave)
  );
  if (esito.ripiego) inRipiego('kv', chiave, valore);
}

/** Tutti gli id degli spot messi da parte. */
export async function preferiti() {
  const esito = await transazione('preferiti', 'readonly', (deposito) => deposito.getAllKeys());
  if (esito.ripiego) return daRipiego('preferiti', 'elenco') || [];
  return esito.valore || [];
}

export async function segnaPreferito(id, attivo) {
  const esito = await transazione('preferiti', 'readwrite', (deposito) =>
    attivo ? deposito.put({ id, quando: Date.now() }, id) : deposito.delete(id)
  );
  if (esito.ripiego) {
    const elenco = new Set(daRipiego('preferiti', 'elenco') || []);
    if (attivo) elenco.add(id);
    else elenco.delete(id);
    inRipiego('preferiti', 'elenco', [...elenco]);
  }
}

/** La nota personale su uno spot: sta qui e basta. */
export async function nota(id) {
  const esito = await transazione('note', 'readonly', (deposito) => deposito.get(id));
  if (esito.ripiego) return daRipiego('note', id) || '';
  return esito.valore || '';
}

export async function salvaNota(id, testo) {
  const pulito = (testo || '').trim();
  const esito = await transazione('note', 'readwrite', (deposito) =>
    pulito ? deposito.put(pulito, id) : deposito.delete(id)
  );
  if (esito.ripiego) inRipiego('note', id, pulito || undefined);
}

/** Mette in coda un contributo scritto offline (nuovo spot, correzione). */
export async function accoda(voce) {
  const completa = { ...voce, quando: new Date().toISOString(), stato: 'in_coda' };
  const esito = await transazione('coda', 'readwrite', (deposito) => deposito.add(completa));
  if (esito.ripiego) {
    const elenco = daRipiego('coda', 'elenco') || [];
    elenco.push({ ...completa, id: elenco.length + 1 });
    inRipiego('coda', 'elenco', elenco);
  }
}

export async function coda() {
  const esito = await transazione('coda', 'readonly', (deposito) => deposito.getAll());
  if (esito.ripiego) return daRipiego('coda', 'elenco') || [];
  return esito.valore || [];
}

export async function svuotaCoda() {
  const esito = await transazione('coda', 'readwrite', (deposito) => deposito.clear());
  if (esito.ripiego) inRipiego('coda', 'elenco', []);
}

/** Cancella tutto il deposito locale: è il "ricomincia da zero". */
export async function dimenticaTutto() {
  const db = await apri();
  if (db) {
    await Promise.all(
      DEPOSITI.map(
        (nome) =>
          new Promise((risolvi) => {
            try {
              const tx = db.transaction(nome, 'readwrite');
              tx.objectStore(nome).clear();
              tx.oncomplete = risolvi;
              tx.onerror = risolvi;
              tx.onabort = risolvi;
            } catch {
              risolvi();
            }
          })
      )
    );
  }
  try {
    for (const chiave of Object.keys(localStorage)) {
      if (chiave.startsWith('pkfamily.')) localStorage.removeItem(chiave);
    }
  } catch {
    memoria.clear();
  }
}
