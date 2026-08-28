#!/usr/bin/env node
// Cosa risponde davvero il sito, header per header.
//
//   node scripts/check_headers.mjs https://staging.pkfamily.app
//   node scripts/check_headers.mjs https://pkfamily.app
//
// `deploy/_headers.template` dice cosa vorremmo servire. Questo script chiede
// al sito cosa serve davvero, e sono due cose diverse: Cloudflare Pages, se la
// sintassi di `_headers` non gli piace, **scarta la regola in silenzio**. Il
// file resta nel repo, il deploy riesce, e il sito va online senza CSP.
//
// Non guarda solo se un header c'è: guarda cosa dice. Una CSP con dentro
// `'unsafe-eval'` è presente e inutile, e un `Strict-Transport-Security` con
// `max-age=60` è presente e non protegge da niente.
//
// Esce ≠ 0 al primo controllo fallito.

const base = (process.argv[2] || '').replace(/\/$/, '');

if (!base) {
  console.error(
    '\nManca l\'indirizzo.\n\n  node scripts/check_headers.mjs https://pkfamily.app\n',
  );
  process.exit(1);
}

let falliti = 0;

function ok(nome, dettaglio = '') {
  console.log(`  ✓  ${nome}${dettaglio ? ` — ${dettaglio}` : ''}`);
}

function no(nome, dettaglio) {
  console.log(`  ✗  ${nome}${dettaglio ? ` — ${dettaglio}` : ''}`);
  falliti++;
}

async function chiedi(percorso) {
  try {
    return await fetch(`${base}${percorso}`, { redirect: 'manual' });
  } catch (errore) {
    console.error(
      `\n✗ Non riesco a raggiungere ${base}${percorso}\n\n  ` +
        `${errore.cause?.message ?? errore.message}\n`,
    );
    process.exit(2);
  }
}

console.log(`\nCosa risponde ${base}\n`);

const home = await chiedi('/');
const h = (nome) => home.headers.get(nome) || '';

if (home.status >= 400) {
  no(`la home risponde ${home.status}`, 'gli altri controlli non dicono niente');
}

// --- Content-Security-Policy -------------------------------------------------

console.log('Content-Security-Policy');
{
  const csp = h('content-security-policy');

  if (!csp) {
    no('la CSP non c\'è', 'Cloudflare ha scartato `_headers`, o non è stato pubblicato');
  } else {
    const direttive = Object.fromEntries(
      csp
        .split(';')
        .map((d) => d.trim())
        .filter(Boolean)
        .map((d) => {
          const [nome, ...valori] = d.split(/\s+/);
          return [nome.toLowerCase(), valori.join(' ')];
        }),
    );

    const script = direttive['script-src'] ?? direttive['default-src'] ?? '';

    // `'unsafe-eval'` rimette in piedi proprio ciò che la CSP esiste per
    // togliere. `'wasm-unsafe-eval'` è un'altra cosa e serve a CanvasKit:
    // consente WebAssembly e nient'altro.
    if (script.includes("'unsafe-eval'")) {
      no('script-src consente `unsafe-eval`', 'ricompila con --csp');
    } else {
      ok('script-src senza `unsafe-eval`', script.trim() || '(da default-src)');
    }

    if (script.includes("'unsafe-inline'")) {
      no("script-src consente `unsafe-inline`", 'basta uno script iniettato');
    } else {
      ok('script-src senza `unsafe-inline`');
    }

    for (const [direttiva, atteso, perche] of [
      ['default-src', "'self'", 'tutto ciò che non è nominato altrove'],
      ['object-src', "'none'", 'niente plugin: è superficie e basta'],
      ['frame-ancestors', "'none'", 'nessuno può incorniciare il sito (clickjacking)'],
      ['base-uri', "'self'", 'un `<base>` iniettato dirotterebbe ogni URL relativo'],
    ]) {
      const valore = direttive[direttiva];
      if (valore === undefined) no(`manca ${direttiva}`, perche);
      else if (!valore.includes(atteso)) no(`${direttiva}: «${valore}»`, `atteso ${atteso}`);
      else ok(`${direttiva} ${atteso}`);
    }

    // Se `connect-src` non nomina un host Supabase, l'app non parlerà col
    // proprio database — e lo si scopre solo aprendo la console del browser.
    const connect = direttive['connect-src'] ?? '';
    if (/supabase\.co/.test(connect)) {
      const jolly = /\*\.supabase\.co/.test(connect);
      if (jolly) {
        no(
          'connect-src usa `*.supabase.co`',
          'consente di parlare con qualsiasi progetto Supabase, non solo il nostro',
        );
      } else {
        ok('connect-src nomina il progetto Supabase');
      }
    } else {
      no('connect-src non nomina nessun host Supabase', 'l\'app non caricherà i dati');
    }

    if (/gstatic\.com/.test(csp)) {
      no(
        'la CSP consente gstatic.com',
        'significa che CanvasKit arriva dal CDN di Google: ricompila con ' +
          '--no-web-resources-cdn. L\'informativa dice che non succede',
      );
    } else {
      ok('nessun dominio Google consentito');
    }
  }
}

// --- Trasporto e il resto ----------------------------------------------------

console.log('\nTrasporto');
{
  const hsts = h('strict-transport-security');
  const eta = Number(/max-age=(\d+)/.exec(hsts)?.[1] ?? 0);

  if (!hsts) no('manca Strict-Transport-Security');
  else if (eta < 31536000) no(`HSTS con max-age=${eta}`, 'sotto un anno non vale il preload');
  else if (!/includesubdomains/i.test(hsts)) no('HSTS senza includeSubDomains');
  else ok('HSTS', `${Math.round(eta / 86400)} giorni${/preload/i.test(hsts) ? ', preload' : ''}`);
}

console.log('\nGli altri');
for (const [nome, atteso, perche] of [
  ['x-content-type-options', 'nosniff', 'il browser non indovina il tipo di un file'],
  ['referrer-policy', 'strict-origin', 'non spedire il percorso a siti terzi'],
  ['permissions-policy', 'geolocation', 'geolocation=(self), il resto negato'],
]) {
  const valore = h(nome);
  if (!valore) no(`manca ${nome}`, perche);
  else if (!valore.toLowerCase().includes(atteso)) no(`${nome}: «${valore}»`, `atteso ${atteso}`);
  else ok(nome, valore.length > 60 ? `${valore.slice(0, 57)}…` : valore);
}

// `camera=()` e compagnia: se la Permissions-Policy nomina solo geolocation,
// tutto il resto resta consentito per omissione.
{
  const pp = h('permissions-policy').toLowerCase();
  const negati = ['camera=()', 'microphone=()', 'payment=()'];
  const mancanti = negati.filter((n) => !pp.includes(n.replace(/\s/g, '')));
  if (pp && mancanti.length) {
    no(`Permissions-Policy non nega ${mancanti.join(', ')}`, 'omettere è consentire');
  } else if (pp) {
    ok('Permissions-Policy nega camera, microfono e pagamenti');
  }
}

// --- I file che un sito pubblico deve avere ----------------------------------

console.log('\nFile');
{
  const res = await chiedi('/.well-known/security.txt');
  if (res.status !== 200) {
    no(`security.txt: HTTP ${res.status}`);
  } else {
    const testo = await res.text();
    const scadenza = /^Expires:\s*(.+)$/m.exec(testo)?.[1]?.trim();
    const data = scadenza ? new Date(scadenza) : null;

    if (!data || Number.isNaN(data.getTime())) {
      no('security.txt senza `Expires` valido', 'RFC 9116 lo rende obbligatorio');
    } else if (data < new Date()) {
      no(`security.txt scaduto il ${data.toISOString().slice(0, 10)}`, 'peggio che assente');
    } else {
      ok('security.txt', `valido fino al ${data.toISOString().slice(0, 10)}`);
    }

    if (!/^Contact:/m.test(testo)) no('security.txt senza `Contact`');
  }
}

{
  const res = await chiedi('/robots.txt');
  const testo = res.status === 200 ? await res.text() : '';
  const chiuso = /^\s*Disallow:\s*\/\s*$/m.test(testo);
  const staging = base.includes('staging');

  if (res.status !== 200) {
    no(`robots.txt: HTTP ${res.status}`);
  } else if (staging && !chiuso) {
    no('lo staging è indicizzabile', 'due siti uguali nei risultati di ricerca');
  } else if (!staging && chiuso) {
    no('la produzione è chiusa ai motori di ricerca', 'robots.txt da staging?');
  } else {
    ok('robots.txt', staging ? 'staging chiuso' : 'produzione aperta');
  }
}

// Una SPA senza rewrite risponde 404 a ogni link profondo, e nessuno se ne
// accorge finché qualcuno non condivide un URL che non sia la home.
{
  const res = await chiedi('/questo-percorso-non-esiste');
  if (res.status === 200) ok('i percorsi profondi arrivano all\'app (rewrite SPA)');
  else no(`un percorso profondo risponde ${res.status}`, 'manca la rewrite in `_redirects`');
}

console.log(
  falliti === 0
    ? '\nTutto a posto.\n'
    : `\n${falliti} controlli falliti. Il sito è online lo stesso: gli header non\n` +
        'sono bloccanti per il browser, sono bloccanti per chi ti attacca.\n',
);
process.exit(falliti === 0 ? 0 : 1);
