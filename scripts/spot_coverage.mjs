#!/usr/bin/env node
// Quanto è utilizzabile la mappa, e dove.
//
// È la misura del gate di lancio del BLOCCO 3-bis: «fuori da Roma la gente non
// può sfruttare l'app» non è un'impressione, è un numero, e questo lo stampa.
//
//   node scripts/spot_coverage.mjs            # riepilogo
//   node scripts/spot_coverage.mjs --paesi    # dettaglio per paese
//   node scripts/spot_coverage.mjs --json     # per la CI
//
// Gli stati, dal più povero al più ricco:
//   da_completare  solo coordinate e un nome. Nessuno c'è ancora stato.
//   arricchito     toponimo reale, contesto OSM, almeno una foto con licenza.
//   verificato     una persona c'è stata e l'ha descritto.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const spots = JSON.parse(
  readFileSync(join(root, 'scripts/data/webapp_fixed_spots.json'), 'utf8'),
);

const STATES = ['verificato', 'arricchito', 'da_completare'];

/** Il paese è un campo vero, estratto da `clean_spots.py`. */
function country(spot) {
  return spot.country?.trim() || 'sconosciuto';
}

function tally(list) {
  const t = Object.fromEntries(STATES.map((s) => [s, 0]));
  for (const s of list) t[s.completeness ?? 'da_completare']++;
  return t;
}

function bar(t, total, width = 28) {
  if (total === 0) return '';
  const cells = STATES.map((s) => Math.round((t[s] / total) * width));
  return '█'.repeat(cells[0]) + '▓'.repeat(cells[1]) + '░'.repeat(cells[2]);
}

const total = tally(spots);
const usable = total.verificato + total.arricchito;

if (process.argv.includes('--json')) {
  console.log(
    JSON.stringify(
      { totale: spots.length, ...total, utilizzabili: usable },
      null,
      2,
    ),
  );
  process.exit(0);
}

console.log(`\n${spots.length} spot sulla mappa\n`);
console.log(`  █ verificato     ${String(total.verificato).padStart(5)}`);
console.log(`  ▓ arricchito     ${String(total.arricchito).padStart(5)}`);
console.log(`  ░ da completare  ${String(total.da_completare).padStart(5)}`);
console.log(`\n  ${bar(total, spots.length, 48)}`);

const pct = ((usable / spots.length) * 100).toFixed(1);
console.log(`\n  Con qualcosa da mostrare: ${usable} su ${spots.length} (${pct}%)`);

// I contenuti si concentrano dove qualcuno c'è stato. Se sono tutti in una
// città, chi apre l'app altrove trova una mappa di puntini muti — che è
// esattamente il problema che questo blocco deve risolvere.
const byCountry = new Map();
for (const s of spots) {
  const c = country(s);
  if (!byCountry.has(c)) byCountry.set(c, []);
  byCountry.get(c).push(s);
}

const rows = [...byCountry.entries()]
  .map(([name, list]) => {
    const t = tally(list);
    return { name, n: list.length, ...t, usable: t.verificato + t.arricchito };
  })
  .sort((a, b) => b.n - a.n);

const show = process.argv.includes('--paesi') ? rows : rows.slice(0, 10);

console.log('\nPer paese:\n');
console.log(
  `  ${'paese'.padEnd(20)}${'spot'.padStart(6)}${'pronti'.padStart(8)}   distribuzione`,
);
for (const r of show) {
  console.log(
    `  ${r.name.slice(0, 20).padEnd(20)}${String(r.n).padStart(6)}` +
      `${String(r.usable).padStart(8)}   ${bar(r, r.n)}`,
  );
}
if (show.length < rows.length) {
  console.log(`  … e altri ${rows.length - show.length} paesi (--paesi per tutti)`);
}

const barren = rows.filter((r) => r.usable === 0 && r.n >= 10);
if (barren.length > 0) {
  console.log(
    `\n  ${barren.length} paesi con almeno 10 spot e nessuno pronto: ` +
      barren
        .slice(0, 6)
        .map((r) => `${r.name} (${r.n})`)
        .join(', '),
  );
  console.log('  Lì la mappa è una griglia di puntini muti.');
}

console.log(
  '\nCosa sposta l\'ago, in ordine:\n' +
    '  1. MAPILLARY_TOKEN + `python3 scripts/enrich_spots.py` → foto e toponimi reali\n' +
    '  2. Il contributo della community: è l\'unica fonte di livello, affollamento\n' +
    '     e "cosa ci si allena". Nessuna API li conosce.\n',
);
