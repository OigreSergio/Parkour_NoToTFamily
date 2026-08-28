#!/usr/bin/env node
// Carica il percorso «Inizia da qui» su Supabase, verificando i video.
//
//   node scripts/seed_starter_path.mjs --check      # verifica e basta
//   SUPABASE_URL=… SUPABASE_SECRET_KEY=… node scripts/seed_starter_path.mjs
//
// La regola che governa questo script: **non carica niente che non abbia
// verificato**. Ogni id YouTube passa da oEmbed, che dice tre cose:
//
//   * il video esiste (un id inventato dà 404);
//   * come si chiama e chi l'ha fatto — titolo e autore reali, non trascritti
//     a mano da chi compila il file;
//   * che l'autore ne consente l'incorporamento, perché oEmbed risponde solo
//     per i video con l'embed abilitato. Quella è la sua autorizzazione
//     esplicita, non una nostra interpretazione.
//
// Le tappe senza `youtube_id` vengono caricate lo stesso, **senza video**:
// titolo, descrizione e nota di sicurezza valgono già da soli, e l'app mostra
// «video in arrivo» invece di far sparire la tappa. Meglio un percorso
// dichiaratamente incompleto di uno finto completo.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const path = JSON.parse(
  readFileSync(join(root, 'scripts/data/starter_path.json'), 'utf8'),
);

const CHECK_ONLY = process.argv.includes('--check');
const URL_BASE = process.env.SUPABASE_URL;
const SECRET = process.env.SUPABASE_SECRET_KEY;

if (!CHECK_ONLY && (!URL_BASE || !SECRET)) {
  console.error(
    'Servono SUPABASE_URL e SUPABASE_SECRET_KEY.\n' +
      'Con --check si verificano i video senza scrivere niente.',
  );
  process.exit(1);
}

/** Un id YouTube è esattamente 11 caratteri fra lettere, cifre, `-` e `_`. */
const ID_SHAPE = /^[A-Za-z0-9_-]{11}$/;

/** Il video esiste, è incorporabile, e questi sono titolo e autore veri. */
async function verify(id) {
  if (!ID_SHAPE.test(id)) {
    return { ok: false, why: `«${id}» non ha la forma di un id YouTube` };
  }

  const url =
    'https://www.youtube.com/oembed?format=json&url=' +
    encodeURIComponent(`https://www.youtube.com/watch?v=${id}`);

  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(20_000) });
    if (res.status === 404) {
      return { ok: false, why: 'il video non esiste' };
    }
    if (res.status === 401 || res.status === 403) {
      // oEmbed rifiuta i video con l'embed disabilitato: è l'autore che ha
      // detto di no, e non c'è modo legittimo di aggirarlo.
      return { ok: false, why: "l'autore non ne consente l'incorporamento" };
    }
    if (!res.ok) return { ok: false, why: `oEmbed ha risposto ${res.status}` };

    const data = await res.json();
    return { ok: true, title: data.title, author: data.author_name };
  } catch (err) {
    return { ok: false, why: `${err.name}: ${err.message}` };
  }
}

const rows = [];
const problems = [];
let missing = 0;

for (const stage of path.stages) {
  const id = (stage.youtube_id ?? '').trim();

  let video = null;
  if (id === '') {
    missing++;
    console.log(`  ·  ${stage.order_index}. ${stage.title} — nessun video`);
  } else {
    const found = await verify(id);
    if (!found.ok) {
      problems.push(`${stage.title}: ${found.why}`);
      console.log(`  ✗  ${stage.order_index}. ${stage.title} — ${found.why}`);
      continue;
    }
    video = found;
    console.log(
      `  ✓  ${stage.order_index}. ${stage.title} — «${found.title}» di ${found.author}`,
    );
  }

  rows.push({
    // Il titolo della tappa è quello curato, non quello del video: «Atterrare
    // e rullare» dice a chi inizia cosa sta per imparare, il titolo YouTube no.
    title: stage.title,
    description: stage.description,
    safety_note: stage.safety_note,
    category: stage.category,
    level: stage.level,
    stage: stage.stage,
    is_starter: true,
    order_index: stage.order_index,
    // youtube-nocookie: nessun cookie di profilazione prima della riproduzione.
    url: video ? `https://www.youtube-nocookie.com/watch?v=${id}` : null,
    author: video?.author ?? null,
    source: 'youtube',
  });
}

console.log(
  `\n${rows.length} tappe · ${rows.length - missing} con video · ${missing} da riempire`,
);

if (problems.length > 0) {
  console.error('\nNon carico niente finché questi non sono risolti:');
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}

if (missing > 0) {
  console.log(
    '\nLe tappe senza video vengono caricate lo stesso: descrizione e nota di\n' +
      'sicurezza valgono già da sole, e l\'app mostra «video in arrivo».\n' +
      'Per completarle: scripts/data/starter_path.json, campo youtube_id.',
  );
}

if (CHECK_ONLY) {
  console.log('\n--check: niente è stato scritto.');
  process.exit(0);
}

const res = await fetch(`${URL_BASE}/rest/v1/videos?on_conflict=stage`, {
  method: 'POST',
  headers: {
    apikey: SECRET,
    Authorization: `Bearer ${SECRET}`,
    'Content-Type': 'application/json',
    Prefer: 'resolution=merge-duplicates',
  },
  body: JSON.stringify(rows),
});

if (!res.ok) {
  console.error(`\nScrittura fallita: ${res.status} ${await res.text()}`);
  process.exit(1);
}

console.log('\nPercorso caricato.');
