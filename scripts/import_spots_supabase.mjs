#!/usr/bin/env node
// Porta gli spot ripuliti dentro Supabase.
//
// Fino a ieri i 1.706 spot vivevano **dentro il bundle JavaScript**, incollati
// da uno script di patch su codice minificato. Voleva dire che ogni correzione
// a uno spot richiedeva un rebuild e un rideploy, che nessun utente poteva
// contribuire, e che i dati non erano interrogabili. Il posto di questi dati è
// il database.
//
//   SUPABASE_URL=https://<ref>.supabase.co \
//   SUPABASE_SECRET_KEY=sb_secret_... \
//   node scripts/import_spots_supabase.mjs [--dry-run]
//
// Serve la **secret key**: l'import scrive spot `community` che le policy RLS
// non lascerebbero inserire a nessun client, ed è giusto così. Lanciarlo dal PC
// dell'admin, mai da una CI.
//
// È idempotente: gli spot già presenti vengono aggiornati, non duplicati. La
// chiave è `external_id`, l'id stabile della lista di origine.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

const URL_BASE = process.env.SUPABASE_URL;
const SECRET = process.env.SUPABASE_SECRET_KEY;
const DRY = process.argv.includes('--dry-run');

if (!DRY && (!URL_BASE || !SECRET)) {
  console.error(
    'Servono SUPABASE_URL e SUPABASE_SECRET_KEY.\n' +
      'Con --dry-run si vede cosa verrebbe scritto senza toccare niente.',
  );
  process.exit(1);
}

const spots = JSON.parse(
  readFileSync(join(root, 'scripts/data/webapp_fixed_spots.json'), 'utf8'),
);

/** Da riga del dataset a riga della tabella `spots`. */
function toRow(spot) {
  return {
    external_id: spot.id,
    name: spot.name,
    lat: spot.lat,
    lng: spot.lng,
    description: spot.description || '',
    // Null resta null: è il punto di tutta la pulizia. Un `?? 'intermedio'`
    // qui rimetterebbe dentro esattamente i dati inventati appena tolti.
    skill_level: spot.skillLevel ?? null,
    crowd_level: spot.crowdLevel ?? null,
    has_fountain: spot.hasFountain ?? null,
    locality: spot.locality ?? null,
    country: spot.country ?? null,
    completeness: spot.completeness ?? 'da_completare',
    status: spot.status === 'verified' ? 'verified' : 'community',
  };
}

/** Le foto di uno spot, solo quelle con crediti in regola. */
function photoRows(spot) {
  return (spot.photos ?? [])
    .filter((p) => typeof p === 'object' && p.url)
    .filter(
      // Il database ha lo stesso vincolo: qui si scartano prima, per non far
      // fallire l'intero batch per una foto sola.
      (p) => p.source === 'community' || (p.author && p.license),
    )
    .map((p, i) => ({
      url: p.url,
      source: p.source ?? null,
      author: p.author ?? null,
      license: p.license ?? null,
      source_url: p.source_url ?? null,
      position: i,
    }));
}

async function post(path, body, prefer) {
  const res = await fetch(`${URL_BASE}/rest/v1/${path}`, {
    method: 'POST',
    headers: {
      apikey: SECRET,
      Authorization: `Bearer ${SECRET}`,
      'Content-Type': 'application/json',
      Prefer: prefer,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.status === 200 ? res.json() : [];
}

const rows = spots.map(toRow);
const withPhotos = spots.filter((s) => photoRows(s).length > 0);

console.log(`${rows.length} spot da importare.`);
console.log(`  verificati:    ${rows.filter((r) => r.status === 'verified').length}`);
console.log(`  community:     ${rows.filter((r) => r.status === 'community').length}`);
console.log(`  non valutati:  ${rows.filter((r) => r.skill_level === null).length}`);
console.log(`  con foto:      ${withPhotos.length}`);

if (DRY) {
  console.log('\n--dry-run: niente è stato scritto. Esempio di riga:\n');
  console.log(JSON.stringify(rows.find((r) => r.status === 'community'), null, 2));
  process.exit(0);
}

// A blocchi: 1.700 righe in una sola richiesta fanno scadere il timeout del
// gateway, e un errore a metà lascerebbe l'import in uno stato ambiguo.
const CHUNK = 200;
let done = 0;

for (let i = 0; i < rows.length; i += CHUNK) {
  const batch = rows.slice(i, i + CHUNK);
  await post('spots?on_conflict=external_id', batch, 'resolution=merge-duplicates');
  done += batch.length;
  process.stdout.write(`\r  scritti ${done}/${rows.length}`);
}
console.log();

// Le foto arrivano dopo, quando gli spot hanno un id: servono i loro uuid.
const ids = await post(
  'spots?select=id,external_id&on_conflict=external_id',
  [],
  'return=representation',
).catch(() => []);

const byExternal = new Map(ids.map((r) => [r.external_id, r.id]));
let photos = 0;

for (const spot of withPhotos) {
  const spotId = byExternal.get(spot.id);
  if (!spotId) continue;
  const batch = photoRows(spot).map((p) => ({ ...p, spot_id: spotId }));
  await post('spot_photos?on_conflict=spot_id,url', batch, 'resolution=merge-duplicates');
  photos += batch.length;
}

console.log(`  foto:    ${photos}`);
console.log('\nFatto. Verifica con: node scripts/spot_coverage.mjs');
