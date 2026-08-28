#!/usr/bin/env node
// Cosa può fare chi ha solo la chiave pubblica.
//
//   SUPABASE_URL=https://<ref>.supabase.co \
//   SUPABASE_PUBLISHABLE_KEY=sb_publishable_… \
//   node scripts/audit_rls.mjs
//
//   # e prima di un tag, anche la seconda fase:
//   node scripts/audit_rls.mjs --sessione
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
// ## Due fasi, e la seconda è quella che conta
//
// **Fase 1** (sempre, anche in CI): cosa vede chi non ha fatto login.
//
// **Fase 2** (solo con `--sessione`): cosa può fare chi *un account ce l'ha*.
// È la domanda più pericolosa delle due — un estraneo senza account può poco
// per costruzione, mentre un utente registrato è dentro, e le policy sono
// l'unica cosa che gli impedisce di leggere i messaggi altrui o di nominarsi
// amministratore. La fase 2 apre una sessione anonima e prova a farlo davvero.
//
// Perché non è accesa di default: **lascia dietro di sé un utente anonimo** nel
// progetto, uno per esecuzione. Nell'uso normale ne nasce uno per visitatore
// (è documentato nell'informativa), quindi non è niente di nuovo — ma farlo a
// ogni push sarebbe sporcare il database per abitudine. Va lanciata a mano
// prima di un tag, dove serve davvero.
//
// Esce ≠ 0 al primo controllo fallito.

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const RADICE = join(dirname(fileURLToPath(import.meta.url)), '..');

const URL_BASE = process.env.SUPABASE_URL;
const KEY = process.env.SUPABASE_PUBLISHABLE_KEY;
const CON_SESSIONE = process.argv.includes('--sessione');

if (!URL_BASE || !KEY) {
  console.error(
    'Servono SUPABASE_URL e SUPABASE_PUBLISHABLE_KEY (la chiave pubblica,\n' +
      'non la secret: qui serve proprio vedere cosa vede un estraneo).',
  );
  process.exit(1);
}

if (KEY.startsWith('sb_secret_')) {
  console.error(
    'Quella è la secret key. Con quella passa tutto, quindi l\'audit direbbe\n' +
      'che va tutto bene qualunque sia lo stato delle policy — il contrario di\n' +
      'quello che serve. Usa la publishable key.',
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

/** Le intestazioni di chi non ha fatto login, o di un utente con un token. */
function intestazioni(token) {
  return token ? { apikey: KEY, Authorization: `Bearer ${token}` } : headers;
}

/**
 * `fetch` con un messaggio leggibile quando la rete non collabora.
 *
 * Senza, un URL sbagliato o un progetto in pausa producono uno stack trace di
 * undici — che sembra un bug dello script e manda a cercare nel posto sbagliato.
 */
async function chiamata(url, opzioni) {
  try {
    return await fetch(url, opzioni);
  } catch (errore) {
    console.error(
      `\n✗ Non riesco a raggiungere ${URL_BASE}\n\n  ${errore.cause?.message ?? errore.message}\n\n` +
        '  Controlla SUPABASE_URL, e che il progetto non sia in pausa\n' +
        '  (i progetti gratuiti si fermano dopo una settimana di inattività).\n',
    );
    process.exit(2);
  }
}

async function get(path, token) {
  const res = await chiamata(`${URL_BASE}/rest/v1/${path}`, {
    headers: intestazioni(token),
  });
  const text = await res.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    /* una risposta non-JSON è comunque un dato: la teniamo come testo */
  }
  return { status: res.status, body, text };
}

async function scrivi(metodo, path, payload, token, prefer) {
  const res = await chiamata(`${URL_BASE}/rest/v1/${path}`, {
    method: metodo,
    headers: {
      ...intestazioni(token),
      'Content-Type': 'application/json',
      ...(prefer ? { Prefer: prefer } : {}),
    },
    body: JSON.stringify(payload),
  });
  const text = await res.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    /* idem */
  }
  return { status: res.status, body, text };
}

const post = (path, payload, token) => scrivi('POST', path, payload, token);
const patch = (path, payload, token, prefer) =>
  scrivi('PATCH', path, payload, token, prefer);

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

await ilGateNonSiAggiraSenzaFareLogin();

/**
 * Il gate di sicurezza regge anche per chi non fa login?
 *
 * Il meccanismo della migration 0005 ha una dipendenza che non si vede
 * leggendo l'SQL. La policy RESTRICTIVE su `spots` è dichiarata
 * `to authenticated`: si applica cioè al ruolo `authenticated`, non ad `anon`.
 * Chi arriva con la sola publishable key e **non** apre una sessione è `anon`,
 * quindi quella policy non lo tocca — e le policy permissive esistenti gli
 * servono gli spot con tutte le coordinate.
 *
 * Il disegno tiene perché il client apre una **sessione anonima** al primo
 * avvio, che trasforma ogni visitatore in `authenticated`. Se le sessioni
 * anonime sono spente nella dashboard, quel passaggio non avviene: il gate
 * resta una schermata, e chi interroga l'API a mano vede tutto.
 *
 * È esattamente il caso che il piano chiama «un rifiuto aggirabile
 * disattivando JavaScript non è un rifiuto», e non si scopre leggendo il
 * codice: si scopre chiedendolo al progetto vero.
 */
async function ilGateNonSiAggiraSenzaFareLogin() {
  const res = await chiamata(`${URL_BASE}/auth/v1/settings`, {
    headers: { apikey: KEY },
  });
  const impostazioni = await res.json().catch(() => null);
  const anonime = impostazioni?.external?.anonymous_users;

  const { body } = await get('spots?select=id,lat,lng&limit=1');
  const visibili = Array.isArray(body) ? body.length : 0;

  if (visibili === 0) {
    report(true, 'nessuno spot senza aver fatto login');

    // Il rovescio della medaglia, che è un problema diverso e non meno serio:
    // se il database nega gli spot a chi è `anon` **e** le sessioni anonime
    // sono spente, nessun visitatore diventa mai `authenticated` e la mappa è
    // vuota per chiunque non abbia un account. Il gate reggerebbe negando
    // tutto a tutti, che non è quello che vogliamo.
    if (anonime === false) {
      report(
        false,
        'ma la mappa sarà vuota per chi non ha un account',
        'le sessioni anonime sono spente, quindi nessun visitatore diventa ' +
          '`authenticated` e nessuno può registrare la presa d\'atto. ' +
          'Attivale in Dashboard → Authentication → Sign In / Providers',
      );
    }
    return;
  }

  if (anonime === false) {
    report(
      false,
      '🔴 gli spot si leggono senza login, e le sessioni anonime sono spente',
      'la policy della migration 0005 è `to authenticated` e non tocca chi ' +
        'resta `anon`: il gate si aggira interrogando l\'API. Attiva le ' +
        'sessioni anonime (Dashboard → Authentication → Sign In / Providers)',
    );
    return;
  }

  if (anonime === true) {
    report(
      false,
      'gli spot si leggono senza login',
      'le sessioni anonime sono attive, quindi il client ne apre una — ma chi ' +
        'chiama l\'API a mano non lo fa, e vede gli spot lo stesso. Serve una ' +
        'policy che copra anche il ruolo `anon`',
    );
    return;
  }

  unproven(
    'gate: gli spot si leggono senza login',
    'non sono riuscito a sapere se le sessioni anonime sono attive',
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

// ============================================================================
// Fase 2 — cosa può fare uno che è dentro
// ============================================================================

if (CON_SESSIONE) {
  console.log('\n\nCosa può fare un utente qualunque, appena registrato\n');

  const sessione = await apriSessioneAnonima();

  if (!sessione) {
    unproven(
      'sessione anonima: non è stato possibile aprirla',
      'attivala in Dashboard → Authentication → Sign In / Providers, oppure ' +
        'lancia la fase 2 con un account vero',
    );
  } else {
    const { token, userId } = sessione;
    console.log(`  (utente di prova: ${userId})\n`);

    await nonPuoDiventareAdmin(token, userId);
    await nonPuoToccareGliAltri(token, userId);
    await nonVedeLaCorrispondenzaAltrui(token);
    await nonSiAutoVerificaUnoSpot(token, userId);
    await ilGateValeAncheViaAPI(token, userId);
  }
}

/**
 * Apre una sessione anonima, come fa l'app al primo avvio.
 *
 * Lascia dietro un utente in `auth.users`: è il prezzo di poter controllare le
 * policy dal punto di vista che conta davvero. Vedi la nota in testa al file.
 */
async function apriSessioneAnonima() {
  const res = await chiamata(`${URL_BASE}/auth/v1/signup`, {
    method: 'POST',
    headers: { apikey: KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: {} }),
  });
  if (!res.ok) return null;
  const body = await res.json().catch(() => null);
  const token = body?.access_token;
  const userId = body?.user?.id;
  return token && userId ? { token, userId } : null;
}

/**
 * Il controllo più importante di tutti.
 *
 * `role = 'admin'` dà accesso alla coda di moderazione, alle segnalazioni con
 * dentro chi ha segnalato chi, e alla verifica degli spot. Se un utente
 * qualunque può assegnarselo da solo, tutto il resto dell'impianto non conta
 * niente. La difesa è un grant per colonna (migration 0005): `authenticated`
 * può aggiornare `username`, `avatar_url`, `chat_enabled` e
 * `deletion_requested_at`, e nient'altro.
 */
async function nonPuoDiventareAdmin(token, userId) {
  const { status } = await patch(
    `profiles?id=eq.${userId}`,
    { role: 'admin' },
    token,
  );

  // Non ci si fida del codice di stato: PostgREST può rispondere 204 avendo
  // aggiornato zero righe. L'unica risposta che vale è rileggere il ruolo.
  const { body } = await get(`profiles?id=eq.${userId}&select=role`, token);
  const ruolo = Array.isArray(body) && body[0] ? body[0].role : null;

  if (ruolo === 'admin') {
    report(
      false,
      '🔴 PROMOZIONE AD ADMIN RIUSCITA',
      'chiunque si registri può nominarsi amministratore. Non pubblicare.',
    );
    // Rimediare per quanto si può: se il grant è aperto lo è in entrambe le
    // direzioni, quindi almeno l'utente di prova non resta admin.
    await patch(`profiles?id=eq.${userId}`, { role: 'user' }, token);
    return;
  }

  report(
    true,
    'non può nominarsi admin',
    ruolo === null
      ? 'profilo non leggibile — il ruolo non è comunque cambiato'
      : `HTTP ${status}, ruolo ancora «${ruolo}»`,
  );
}

/** Il profilo di un altro non si tocca. */
async function nonPuoToccareGliAltri(token, userId) {
  const { body } = await get(`profiles?select=id&id=neq.${userId}&limit=1`, token);
  const altro = Array.isArray(body) && body[0] ? body[0].id : null;

  if (!altro) {
    unproven(
      'profilo altrui: non ce n\'è un altro da provare',
      'rilancia quando ci sarà più di un profilo',
    );
    return;
  }

  // `return=representation` fa dire a PostgREST *quali* righe ha toccato: senza,
  // un 204 su zero righe e un 204 su una riga modificata sono indistinguibili.
  const { status, body: modificate } = await patch(
    `profiles?id=eq.${altro}`,
    { username: 'audit-non-dovrebbe-passare' },
    token,
    'return=representation',
  );

  const toccate = Array.isArray(modificate) ? modificate.length : 0;
  report(
    status >= 400 || toccate === 0,
    'non può modificare il profilo di un altro',
    toccate > 0 ? `ha riscritto il nome di ${altro}` : '',
  );
}

/** Messaggi e conversazioni di chi non ha mai incontrato. */
async function nonVedeLaCorrispondenzaAltrui(token) {
  for (const [tabella, perche] of [
    ['messages', 'i messaggi privati'],
    ['chats', 'le conversazioni'],
    ['chat_members', 'chi parla con chi'],
    ['reports', 'le segnalazioni, con dentro chi ha segnalato'],
  ]) {
    const { status, body, text } = await get(`${tabella}?select=*&limit=1`, token);
    const righe = Array.isArray(body) ? body.length : 0;

    if (status >= 500) {
      report(
        false,
        `${tabella}: HTTP ${status} da autenticato`,
        text.includes('42P17') ? 'ricorsione nelle policy (migration 0004)' : 'errore server',
      );
      continue;
    }
    report(
      righe === 0,
      `non vede ${perche} degli altri`,
      righe > 0 ? `${righe} righe visibili a un utente qualunque` : '',
    );
  }
}

/**
 * Uno spot proposto nasce `pending`, e chi lo propone non può dichiararlo
 * verificato: `verificato` significa «un umano c'è stato», e se se lo può dare
 * da solo chi lo carica, la distinzione fra i 26 spot di Roma e i 1.680
 * segnaposto smette di esistere.
 */
async function nonSiAutoVerificaUnoSpot(token, userId) {
  // `return=representation`: senza, PostgREST risponde 201 e basta, e non si
  // saprebbe con quale `status` la riga è davvero nata — che è tutto il punto.
  const { status, body } = await scrivi(
    'POST',
    'spots',
    {
      name: 'audit — da cancellare',
      lat: 41.9028,
      lng: 12.4964,
      status: 'verified',
      completeness: 'verificato',
      author_id: userId,
    },
    token,
    'return=representation',
  );

  if (status >= 400) {
    report(true, 'non può inserire uno spot già verificato', `HTTP ${status}`);
    return;
  }

  const creato = Array.isArray(body) && body[0] ? body[0] : null;
  const statoFinale = creato?.status ?? '(sconosciuto)';
  report(
    statoFinale === 'pending',
    'uno spot proposto nasce in attesa',
    statoFinale === 'pending'
      ? ''
      : `è nato «${statoFinale}»: chiunque può pubblicare sulla mappa senza passare dalla moderazione`,
  );

  if (creato?.id) {
    await chiamata(`${URL_BASE}/rest/v1/spots?id=eq.${creato.id}`, {
      method: 'DELETE',
      headers: intestazioni(token),
    });
  }
}

/**
 * Il gate di sicurezza vale davvero, o è solo una schermata?
 *
 * Questo è l'unico controllo dell'intero script che è **conclusivo su una
 * tabella piena**: si guarda prima e dopo. Prima della presa d'atto gli spot
 * non devono arrivare; subito dopo sì. Se cambia, la policy RESTRICTIVE della
 * migration 0005 sta facendo il suo lavoro e il rifiuto del gate non si aggira
 * disattivando JavaScript. Se non cambia niente in nessuna delle due direzioni,
 * lo diciamo invece di far finta.
 */
async function ilGateValeAncheViaAPI(token, userId) {
  const prima = await get('spots?select=id,lat,lng&limit=1', token);
  const righePrima = Array.isArray(prima.body) ? prima.body.length : 0;

  if (righePrima > 0) {
    report(
      false,
      '🔴 gli spot arrivano SENZA la presa d\'atto',
      'la policy RESTRICTIVE della migration 0005 non è applicata: il gate è ' +
        'una schermata che si salta interrogando l\'API',
    );
    return;
  }

  const testo = readFileSync(join(RADICE, 'mobile/assets/legal/safety_notice_v1.md'));
  const accettazione = await post(
    'safety_acknowledgements',
    {
      user_id: userId,
      version: 'v1',
      text_sha256: createHash('sha256').update(testo).digest('hex'),
    },
    token,
  );

  if (accettazione.status >= 400) {
    unproven(
      'gate: non è stato possibile registrare la presa d\'atto',
      `HTTP ${accettazione.status} — migration 0005 applicata?`,
    );
    return;
  }

  const dopo = await get('spots?select=id,lat,lng&limit=1', token);
  const righeDopo = Array.isArray(dopo.body) ? dopo.body.length : 0;

  if (righeDopo > 0) {
    report(true, 'il gate è applicato dal database', 'niente spot prima, spot dopo');
  } else {
    unproven(
      'gate: niente spot né prima né dopo',
      'o la tabella `spots` è vuota, o qualcos\'altro li sta filtrando',
    );
  }

  // L'utente di prova resta, ma inerte: la presa d'atto revocata è anche il
  // modo giusto di lasciarlo, perché cancellare la riga distruggerebbe la prova
  // che a suo tempo era stata accettata.
  await patch(
    `safety_acknowledgements?user_id=eq.${userId}&version=eq.v1`,
    { revoked_at: new Date().toISOString() },
    token,
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
