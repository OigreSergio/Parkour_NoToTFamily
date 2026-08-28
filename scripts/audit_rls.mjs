#!/usr/bin/env node
// Cosa vede un estraneo con la sola chiave pubblica.
//
//   SUPABASE_URL=https://<ref>.supabase.co \
//   SUPABASE_PUBLISHABLE_KEY=sb_publishable_… \
//   node scripts/audit_rls.mjs
//
// La publishable key finisce nel bundle: chiunque apra l'app ce l'ha. Le policy
// RLS sono quindi **l'unica difesa del database**, e questo script controlla
// che facciano il loro lavoro — da fuori, come lo farebbe un curioso.
//
// Non è teoria. Sondando la produzione durante il BLOCCO 6 è saltato fuori che
// `reports` era leggibile da chiunque: la tabella era vuota, ma alla prima
// segnalazione di molestie chi l'aveva scritta, e cosa, sarebbero stati
// leggibili dalla persona segnalata. È esattamente il tipo di cosa che questo
// script trova prima che succeda.
//
// Va in CI. Esce ≠ 0 al primo controllo fallito.

const URL_BASE = process.env.SUPABASE_URL;
const KEY = process.env.SUPABASE_PUBLISHABLE_KEY;

if (!URL_BASE || !KEY) {
  console.error(
    'Servono SUPABASE_URL e SUPABASE_PUBLISHABLE_KEY (la chiave pubblica,\n' +
      'non la secret: qui serve proprio vedere cosa vede un estraneo).',
  );
  process.exit(1);
}

const headers = { apikey: KEY, Authorization: `Bearer ${KEY}` };
let failures = 0;
let inconclusive = 0;

function report(ok, name, detail = '') {
  console.log(`  ${ok ? '✓' : '✗'}  ${name}${detail ? ` — ${detail}` : ''}`);
  if (!ok) failures++;
}

/**
 * Un controllo che non prova niente.
 *
 * Su una tabella vuota, «non ho ricevuto righe» non significa «la policy me le
 * nega»: significa solo che non ce n'erano. Spacciarlo per un successo è
 * peggio che non controllare, ed è precisamente così che è passata inosservata
 * la lettura aperta su `reports` — vuota, quindi apparentemente a posto.
 */
function unproven(name, detail) {
  console.log(`  ?  ${name} — ${detail}`);
  inconclusive++;
}

async function get(path) {
  const res = await fetch(`${URL_BASE}/rest/v1/${path}`, { headers });
  const text = await res.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    /* una risposta non-JSON è comunque un dato: la teniamo come testo */
  }
  return { status: res.status, body, text };
}

async function post(path, payload) {
  const res = await fetch(`${URL_BASE}/rest/v1/${path}`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return { status: res.status, text: await res.text() };
}

/** Da non autenticato la tabella non deve restituire nessuna riga. */
async function mustBeEmpty(table, why) {
  const { status, body, text } = await get(`${table}?select=*&limit=1`);

  if (status === 404) {
    report(true, `${table}: non esiste ancora`, 'migration non applicata');
    return;
  }
  if (status === 401 || status === 403) {
    report(true, `${table}: accesso negato`);
    return;
  }
  if (status >= 500) {
    const recursion = text.includes('42P17');
    report(
      false,
      `${table}: HTTP ${status}`,
      recursion
        ? 'ricorsione infinita nelle policy — manca la migration 0004'
        : 'errore lato server, da guardare',
    );
    return;
  }

  const rows = Array.isArray(body) ? body.length : 0;
  if (rows > 0) {
    report(false, `${table}: righe visibili a un estraneo`, why);
    return;
  }

  // 200 con zero righe: la richiesta è passata. Non sappiamo se la policy
  // abbia filtrato o se la tabella sia semplicemente vuota, e le due cose
  // sono molto diverse.
  unproven(
    `${table}: nessuna riga, ma la query è passata`,
    'da riverificare quando la tabella avrà dei dati',
  );
}

/** Da non autenticato la scrittura deve essere rifiutata. */
async function mustRejectWrite(table, payload) {
  const { status, text } = await post(table, payload);

  if (status < 400) {
    report(false, `${table}: scrittura ACCETTATA`, `HTTP ${status} — da chiudere subito`);
    return;
  }
  if (status >= 500) {
    report(
      false,
      `${table}: scrittura, HTTP ${status}`,
      text.includes('42P17') ? 'ricorsione nelle policy (migration 0004)' : 'errore server',
    );
    return;
  }
  // 400 con 42501 è la RLS che rifiuta: è il risultato giusto.
  report(true, `${table}: scrittura rifiutata`);
}

console.log('\nCosa vede un estraneo con la sola chiave pubblica\n');

console.log('Dati personali e di moderazione');
await mustBeEmpty(
  'reports',
  'una segnalazione esposta è chi segnala esposto: nessuno segnalerebbe più',
);
await mustBeEmpty('moderation_events', 'il registro di moderazione è interno');
await mustBeEmpty('moderation_notices', 'le motivazioni riguardano una persona sola');
await mustBeEmpty('post_saves', 'cosa uno salva sono i suoi interessi');
await mustBeEmpty('entitlements', 'lo stato di abbonamento non riguarda gli altri');
await mustBeEmpty('parent_access_requests', 'contiene email di terzi date da minori');
await mustBeEmpty('safety_acknowledgements', 'dice chi ha usato l\'app e quando');
await mustBeEmpty('blocked_users', 'sapere di essere bloccati non spetta a chi blocca');

console.log('\nChat');
await mustBeEmpty('messages', 'i messaggi privati sono privati');
await mustBeEmpty('chats', 'l\'elenco delle conversazioni altrui');
await mustBeEmpty('chat_members', 'chi parla con chi');

console.log('\nSpot');
{
  const { status, body } = await get('spots?status=eq.pending&select=id&limit=1');
  const rows = Array.isArray(body) ? body.length : 0;
  report(
    status === 404 || rows === 0,
    'spots: nessuno spot in attesa visibile',
    rows > 0 ? 'gli spot non ancora moderati non sono pubblici' : '',
  );
}

console.log('\nScritture');
await mustRejectWrite('reports', { reason: 'audit' });
await mustRejectWrite('spots', { name: 'audit', lat: 0, lng: 0 });
await mustRejectWrite('messages', { body: 'audit' });
await mustRejectWrite('profiles', { username: 'audit' });

console.log('\nCatalogo pubblico (qui il contrario: deve rispondere)');
{
  const { status } = await get('videos?select=id&limit=1');
  report(
    status === 200,
    'videos: leggibile da chiunque',
    status === 200 ? '' : `HTTP ${status} — i video devono essere aperti a tutti`,
  );
}

if (inconclusive > 0) {
  console.log(
    `\n${inconclusive} controlli non concludenti: la tabella era vuota, quindi\n` +
      'non si può dire se sia la policy a filtrare. Rilancia lo script quando\n' +
      'ci saranno dei dati, o verifica le policy nel dump dello schema.',
  );
}

console.log(
  failures === 0
    ? '\nNessun controllo fallito.\n'
    : `\n${failures} controlli falliti.\n`,
);
process.exit(failures === 0 ? 0 : 1);
