#!/usr/bin/env node
// Carica su Supabase il catalogo tutorial, verificando ogni video.
//
//   node scripts/seed_videos.mjs --check        # verifica e basta
//   node scripts/seed_videos.mjs --check --veloce   # solo un campione
//   SUPABASE_URL=… SUPABASE_SECRET_KEY=… node scripts/seed_videos.mjs
//
// La selezione è quella di `docs/TUTORIAL_CATALOG.md`: 124 video scelti su
// 1.234 censiti, da quattro canali, con il criterio scritto lì — tutorial con
// scomposizione del movimento, non showreel.
//
// Vale la stessa regola di `seed_starter_path.mjs`, ed è la ragione per cui
// questo script esiste invece di un semplice INSERT: **non carica niente che
// non abbia verificato.** Ogni id passa da oEmbed, che dice tre cose:
//
//   * il video esiste ancora — un canale può cancellare, e un catalogo scritto
//     mesi fa invecchia in silenzio;
//   * come si chiama e chi l'ha fatto, con le parole di YouTube e non con
//     quelle trascritte a mano nel JSON;
//   * che l'autore ne consente l'incorporamento: oEmbed risponde solo per i
//     video con l'embed abilitato, e quella è la sua autorizzazione esplicita.
//
// I video che non passano vengono **saltati e elencati**, non caricati a metà.
//
// Idempotente: fa upsert su `url` (migration 0011), quindi rilanciarlo
// aggiorna le righe invece di duplicarle. Richiede la secret key, perché sta
// scrivendo un catalogo che nessun utente potrebbe scrivere: da lanciare dal
// tuo PC, mai da una CI.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const RADICE = join(dirname(fileURLToPath(import.meta.url)), '..');
const catalogo = JSON.parse(
  readFileSync(join(RADICE, 'scripts/data/tutorial_catalog.json'), 'utf8'),
);

const SOLO_CHECK = process.argv.includes('--check');
const VELOCE = process.argv.includes('--veloce');
const URL_BASE = process.env.SUPABASE_URL;
const SECRET = process.env.SUPABASE_SECRET_KEY;

if (!SOLO_CHECK && (!URL_BASE || !SECRET)) {
  console.error(
    'Servono SUPABASE_URL e SUPABASE_SECRET_KEY.\n' +
      'Con --check si verificano i video senza scrivere niente.',
  );
  process.exit(1);
}

if (!SOLO_CHECK && !SECRET?.startsWith('sb_secret_')) {
  console.error(
    'SUPABASE_SECRET_KEY non sembra una secret key. Serve quella: il catalogo\n' +
      'è scritto da chi amministra, non da un utente.',
  );
  process.exit(1);
}

const FORMA_ID = /^[A-Za-z0-9_-]{11}$/;

/** Il video esiste, è incorporabile, e questi sono titolo e autore veri. */
async function verifica(id) {
  if (!FORMA_ID.test(id)) return { ok: false, perche: 'non è un id YouTube' };

  const url =
    'https://www.youtube.com/oembed?format=json&url=' +
    encodeURIComponent(`https://www.youtube.com/watch?v=${id}`);

  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(20_000) });
    if (res.status === 404) return { ok: false, perche: 'non esiste più' };
    if (res.status === 401 || res.status === 403) {
      return { ok: false, perche: "l'autore non ne consente l'incorporamento" };
    }
    if (res.status === 429) return { ok: false, perche: 'oEmbed: troppe richieste' };
    if (!res.ok) return { ok: false, perche: `oEmbed ha risposto ${res.status}` };
    const dati = await res.json();
    return { ok: true, titolo: dati.title, autore: dati.author_name };
  } catch (err) {
    return { ok: false, perche: `${err.name}: ${err.message}` };
  }
}

const elenco = VELOCE ? catalogo.videos.slice(0, 12) : catalogo.videos;

console.log(
  `\nVerifico ${elenco.length} video${VELOCE ? ' (campione)' : ''}. ` +
    'Ci vuole qualche minuto: è una richiesta per video.\n',
);

const righe = [];
const saltati = [];
const rititolati = [];

for (const [i, v] of elenco.entries()) {
  const esito = await verifica(v.youtube_id);
  const avanzamento = `${String(i + 1).padStart(3)}/${elenco.length}`;

  if (!esito.ok) {
    saltati.push({ ...v, perche: esito.perche });
    console.log(`  ✗ ${avanzamento}  ${v.title.slice(0, 58)} — ${esito.perche}`);
    continue;
  }

  // Il titolo nel catalogo è stato trascritto a mano: se YouTube ne dà un
  // altro, quello di YouTube è il vero. Vale la pena dirlo, perché di solito
  // significa che l'autore ha rinominato il video.
  if (esito.titolo !== v.title) rititolati.push({ prima: v.title, ora: esito.titolo });

  righe.push({
    title: esito.titolo,
    description: v.description,
    // youtube-nocookie: nessun cookie di profilazione prima della riproduzione.
    // Il video si apre comunque fuori dall'app, non incorporato.
    url: `https://www.youtube-nocookie.com/watch?v=${v.youtube_id}`,
    // `thumbnail_url` resta null di proposito — vedi la migration 0011.
    category: v.category,
    level: v.level,
    trick_category: v.trick_category,
    difficulty: v.difficulty,
    duration_seconds: v.duration_seconds,
    author: esito.autore,
    source: 'youtube',
    is_starter: false,
  });

  console.log(`  ✓ ${avanzamento}  ${esito.titolo.slice(0, 58)}`);
}

console.log(`\n${righe.length} verificati · ${saltati.length} saltati`);

if (rititolati.length > 0) {
  console.log(`\n${rititolati.length} hanno un titolo diverso da quello nel catalogo:`);
  for (const r of rititolati.slice(0, 10)) {
    console.log(`  «${r.prima.slice(0, 46)}»\n    → «${r.ora.slice(0, 46)}»`);
  }
  console.log('  (carico quello di YouTube: è il vero)');
}

if (saltati.length > 0) {
  console.log('\nQuesti restano fuori, e va aggiornato docs/TUTORIAL_CATALOG.md:');
  for (const s of saltati) console.log(`  - ${s.title} (${s.youtube_id}) — ${s.perche}`);
}

if (SOLO_CHECK) {
  console.log('\n--check: niente è stato scritto.\n');
  process.exit(saltati.length > 0 ? 1 : 0);
}

if (righe.length === 0) {
  console.error('\nNiente da caricare.');
  process.exit(1);
}

// A blocchi: 117 righe in una POST sola funzionano, ma un errore a metà
// lascerebbe senza sapere cosa è passato.
const BLOCCO = 25;
let scritte = 0;

for (let i = 0; i < righe.length; i += BLOCCO) {
  const parte = righe.slice(i, i + BLOCCO);
  const res = await fetch(`${URL_BASE}/rest/v1/videos?on_conflict=url`, {
    method: 'POST',
    headers: {
      apikey: SECRET,
      Authorization: `Bearer ${SECRET}`,
      'Content-Type': 'application/json',
      Prefer: 'resolution=merge-duplicates,return=minimal',
    },
    body: JSON.stringify(parte),
  });

  if (!res.ok) {
    console.error(
      `\nBlocco ${i / BLOCCO + 1} fallito: ${res.status} ${await res.text()}\n` +
        `${scritte} righe erano già passate. Rilancia: è idempotente.`,
    );
    process.exit(1);
  }
  scritte += parte.length;
  console.log(`  scritte ${scritte}/${righe.length}`);
}

console.log('\nCatalogo caricato.\n');
