#!/usr/bin/env node
// Prepara `mobile/build/web` per la pubblicazione su Cloudflare Pages.
//
//   node scripts/prepare_deploy.mjs --env=prod
//   node scripts/prepare_deploy.mjs --env=staging
//
// Va lanciato **dopo** `flutter build web`, e aggiunge all'output tre cose che
// il build Flutter non conosce: gli header HTTP, le regole di routing e i file
// che un sito pubblico deve avere (`security.txt`, `robots.txt`, `sitemap.xml`).
//
// Perché uno script e non file statici in `mobile/web/`:
//
//  1. la CSP deve nominare **l'host Supabase reale**, che cambia se il progetto
//     viene ricreato in un'altra region. Un `https://*.supabase.co` funzionerebbe
//     ma consentirebbe a un'eventuale iniezione di parlare con qualsiasi
//     progetto Supabase del mondo, che è esattamente ciò che `connect-src`
//     dovrebbe impedire;
//  2. `security.txt` **scade** (RFC 9116 rende `Expires` obbligatorio), e una
//     data scritta a mano un anno fa è peggio che non averlo;
//  3. staging e produzione vogliono `robots.txt` opposti, e sbagliarsi
//     significa far indicizzare lo staging.
//
// Esce ≠ 0 al primo problema. Meglio un deploy che non parte di un deploy senza
// header di sicurezza.

import { existsSync, mkdirSync, readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const BUILD = join(ROOT, 'mobile', 'build', 'web');
const DEPLOY = join(ROOT, 'deploy');

const DOMAINS = {
  prod: 'pkfamily.app',
  staging: 'staging.pkfamily.app',
};

function die(message, hint) {
  console.error(`\n✗ ${message}`);
  if (hint) console.error(`\n  ${hint}`);
  console.error('');
  process.exit(1);
}

const args = process.argv.slice(2);
const env = (args.find((a) => a.startsWith('--env=')) || '--env=staging').slice(6);
if (!DOMAINS[env]) {
  die(`Ambiente sconosciuto: «${env}».`, 'Usa --env=prod oppure --env=staging.');
}
const domain = DOMAINS[env];

// --- 1. L'host Supabase ------------------------------------------------------

const supabaseUrl = process.env.SUPABASE_URL || '';
if (!supabaseUrl) {
  die(
    'SUPABASE_URL non è impostata.',
    'Serve per scrivere `connect-src` nella CSP: senza, l\'app pubblicata non\n' +
      '  riuscirebbe a parlare col proprio database.',
  );
}

let supabaseHost;
try {
  const parsed = new URL(supabaseUrl);
  if (parsed.protocol !== 'https:') throw new Error('non è https');
  supabaseHost = parsed.host;
} catch (error) {
  die(`SUPABASE_URL non è un URL https valido: ${error.message}`);
}

// --- 2. Il build c'è, ed è quello giusto -------------------------------------

if (!existsSync(join(BUILD, 'index.html'))) {
  die(
    `Non trovo un build in ${BUILD}.`,
    'Lancia prima:\n' +
      '  cd mobile && flutter build web --release --csp --no-web-resources-cdn \\\n' +
      '    --dart-define=SUPABASE_URL=… --dart-define=SUPABASE_PUBLISHABLE_KEY=…',
  );
}

const bundle = readFileSync(join(BUILD, 'main.dart.js'), 'utf8');

// La CSP che stiamo per scrivere e l'host compilato dentro il bundle devono
// essere lo stesso. Se divergono l'app si pubblica e poi non carica niente, con
// un errore di CSP in console che nessun utente leggerà.
if (!bundle.includes(supabaseHost)) {
  die(
    `Il build non contiene «${supabaseHost}».`,
    'Il bundle è stato compilato con un --dart-define=SUPABASE_URL diverso da\n' +
      '  quello passato adesso. La CSP bloccherebbe ogni richiesta al database.',
  );
}

// Rete di sicurezza, non teatro: la secret key bypassa ogni policy RLS, e un
// build che la contenesse consegnerebbe il database intero — messaggi privati
// compresi — a chiunque apra la pagina.
//
// Cerchiamo una chiave **con un valore dentro**, non il prefisso da solo: la
// stringa `sb_secret_` compare legittimamente nel bundle perché è
// `supabase_flutter` stesso a controllare di non aver ricevuto una secret key.
// Un controllo che scattasse su quella sarebbe un allarme che suona sempre, e
// un allarme che suona sempre viene disattivato.
const segreto = bundle.match(/sb_secret_[A-Za-z0-9_-]{16,}/);
if (segreto) {
  die(
    `Il build contiene una secret key (${segreto[0].slice(0, 18)}…).`,
    'Non pubblicare, e ruota subito quella chiave dalla dashboard Supabase.',
  );
}

// E la chiave che stiamo pubblicando dev'essere davvero quella pubblica.
const chiave = process.env.SUPABASE_PUBLISHABLE_KEY || '';
if (chiave.startsWith('sb_secret_')) {
  die(
    'SUPABASE_PUBLISHABLE_KEY contiene una secret key.',
    'Il nome della variabile dice «publishable»; il valore no. Ruota la chiave.',
  );
}
if (chiave && !bundle.includes(chiave)) {
  die(
    'La chiave passata adesso non è quella compilata nel bundle.',
    'Il build è stato fatto con --dart-define diversi: l\'app pubblicata userebbe\n' +
      '  la chiave vecchia, e nessuno se ne accorgerebbe finché non smette di\n' +
      '  funzionare.',
  );
}

// CanvasKit dal CDN di Google significa una richiesta a gstatic.com a ogni
// apertura — cioè esattamente ciò che l'informativa dice che non succede.
// `--no-web-resources-cdn` la elimina servendo la copia locale.
const bootstrap = readFileSync(join(BUILD, 'flutter_bootstrap.js'), 'utf8');
if (!bootstrap.includes('useLocalCanvasKit":true')) {
  die(
    'Il build carica CanvasKit dal CDN di Google.',
    'Ricompila con `--no-web-resources-cdn`. Senza, a ogni apertura parte una\n' +
      '  richiesta verso www.gstatic.com: la CSP la bloccherebbe (schermo bianco),\n' +
      '  e allentare la CSP renderebbe falso quello che scrive l\'informativa.',
  );
}

// --- 3. Header ---------------------------------------------------------------

let headers = readFileSync(join(DEPLOY, '_headers.template'), 'utf8').replaceAll(
  '__SUPABASE_HOST__',
  supabaseHost,
);

if (headers.includes('__')) {
  const rimasto = headers.match(/__[A-Z_]+__/)?.[0];
  die(`Segnaposto non sostituito nel template degli header: ${rimasto}`);
}

if (env === 'staging') {
  // Lo staging sta dietro Cloudflare Access, quindi un crawler non ci arriva.
  // Questo header è la seconda serratura: se un giorno Access venisse tolto per
  // una prova, lo staging non finisce comunque nei risultati di ricerca —
  // dove farebbe concorrenza al sito vero e mostrerebbe dati di prova.
  headers = headers.replace(
    '  Cache-Control: no-cache',
    '  X-Robots-Tag: noindex, nofollow\n  Cache-Control: no-cache',
  );
}

writeFileSync(join(BUILD, '_headers'), headers);

// --- 4. Redirect -------------------------------------------------------------

let redirects = readFileSync(join(DEPLOY, '_redirects'), 'utf8');
if (env === 'staging') {
  // Su staging non esiste un www, e la regola punterebbe alla produzione: chi
  // sbaglia host si ritroverebbe sul sito vero senza accorgersene.
  redirects = redirects
    .split('\n')
    .filter((line) => !line.includes('www.pkfamily.app'))
    .join('\n');
}
writeFileSync(join(BUILD, '_redirects'), redirects);

// --- 5. security.txt ---------------------------------------------------------

const scadenza = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000);
scadenza.setUTCHours(0, 0, 0, 0);

mkdirSync(join(BUILD, '.well-known'), { recursive: true });
writeFileSync(
  join(BUILD, '.well-known', 'security.txt'),
  [
    '# Come segnalare un problema di sicurezza in PkFAMILY.',
    '# https://www.rfc-editor.org/rfc/rfc9116',
    '',
    'Contact: mailto:security@pkfamily.app',
    `Expires: ${scadenza.toISOString().replace(/\.\d{3}Z$/, 'Z')}`,
    'Preferred-Languages: it, en',
    `Canonical: https://${domain}/.well-known/security.txt`,
    'Policy: https://github.com/OigreSergio/Parkour_NoToTFamily/blob/main/SECURITY.md',
    '',
    '# Risponde una persona sola, non un team. Vedi SECURITY.md per i tempi',
    '# realistici: prometterne di più sarebbe solo un modo elegante di mancarli.',
    '',
  ].join('\n'),
);

// --- 6. robots e sitemap -----------------------------------------------------

if (env === 'prod') {
  writeFileSync(
    join(BUILD, 'robots.txt'),
    [
      '# PkFAMILY è pubblico e vogliamo che si trovi.',
      'User-agent: *',
      'Allow: /',
      '',
      `Sitemap: https://${domain}/sitemap.xml`,
      '',
    ].join('\n'),
  );

  // Una SPA ha un URL solo lato server: il resto del routing avviene nel
  // browser e nessun crawler lo vedrebbe comunque. Una sitemap con dentro
  // percorsi finti non aiuta l'indicizzazione, la peggiora.
  const oggi = new Date().toISOString().slice(0, 10);
  writeFileSync(
    join(BUILD, 'sitemap.xml'),
    [
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
      '  <url>',
      `    <loc>https://${domain}/</loc>`,
      `    <lastmod>${oggi}</lastmod>`,
      '    <changefreq>weekly</changefreq>',
      '  </url>',
      '</urlset>',
      '',
    ].join('\n'),
  );
} else {
  writeFileSync(
    join(BUILD, 'robots.txt'),
    ['# Ambiente di prova. Non è il sito.', 'User-agent: *', 'Disallow: /', ''].join('\n'),
  );
}

// --- 7. Riepilogo ------------------------------------------------------------

function peso(dir) {
  let totale = 0;
  for (const voce of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, voce.name);
    totale += voce.isDirectory() ? peso(p) : statSync(p).size;
  }
  return totale;
}

// I file `.symbols` sotto `canvaskit/` pesano ~4 MB e non servono a runtime:
// viene voglia di cancellarli. **Non farlo.** Il service worker generato da
// Flutter li elenca fra le risorse e ne scarica l'insieme completo alla prima
// attivazione: uno che manca fa fallire quella fase, e l'app smette di
// funzionare offline senza dire perché.
const totale = peso(BUILD) / 1024 / 1024;

console.log(`
Pronto per il deploy — ${env}

  dominio        ${domain}
  Supabase       ${supabaseHost}
  CanvasKit      locale (nessuna richiesta a gstatic.com)
  security.txt   scade il ${scadenza.toISOString().slice(0, 10)}
  robots.txt     ${env === 'prod' ? 'indicizzabile' : 'Disallow: /'}
  peso           ${totale.toFixed(1)} MB
`);

if (totale > 20) {
  // Alla prima apertura il browser ne scarica una frazione (~10 MB: un solo
  // motore di rendering). Ma il service worker di Flutter, appena attivato,
  // si porta giù **tutto** per l'uso offline — su rete mobile, che è dove
  // questa app viene aperta davvero. Vedi `docs/OPS_TODO.md`.
  console.log(
    `⚠️  ${totale.toFixed(0)} MB è tanto per chi apre l'app in strada: il service\n` +
      '   worker precarica l\'intero pacchetto per l\'uso offline. È una decisione\n' +
      '   da prendere, non da subire — le opzioni sono in docs/OPS_TODO.md.\n',
  );
}

console.log(
  'Gli header non si vedono finché il sito non è online: dopo il deploy,\n' +
    `  curl -sI https://${domain} | grep -iE 'content-security|strict-transport|permissions'\n`,
);
