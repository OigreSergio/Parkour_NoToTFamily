/* Entrare davvero: quello che deve reggere quando l'app è su un indirizzo
 * pubblico e la gente ci entra con la propria email.
 *
 * Il progetto Supabase qui non esiste: `build.json` ne indica uno finto e le
 * sue rotte sono servite dal test. Non è una scorciatoia — è l'unico modo di
 * provare il *rifiuto* del server (codice sbagliato, gettone revocato, rete
 * che cade) senza chiedere a nessuno di rompere il progetto vero.
 *
 * Le rotte si mettono sul contesto e non sulla pagina perché in mezzo c'è il
 * service worker: `build.json` è un file precaricato, e dalla seconda apertura
 * in avanti la richiesta la fa lui. Con `page.route` la seconda apertura
 * tornerebbe al `build.json` del repository e la prova direbbe il falso.
 *
 * Ogni prova qui dentro corrisponde a un modo preciso in cui l'accesso può
 * fare danno: buttare fuori chi non ha campo, restare dentro con un gettone
 * revocato, far partire l'app in ritardo perché aspetta la rete, o — la
 * peggiore — portare una chiave segreta dentro una pagina pubblica.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { expect, test } from '@playwright/test';

const PROGETTO = 'https://progetto-di-prova.supabase.co';
const CHIAVE = 'sb_publishable_soloperleprove';

const UTENTE = {
  id: '11111111-2222-3333-4444-555555555555',
  email: 'chi.prova@esempio.it',
  is_anonymous: false,
};

const PROFILO = `/rest/v1/profiles?id=eq.${UTENTE.id}&select=display_name,role`;

function sessione(sovrascritture = {}) {
  return {
    access_token: 'gettone-di-accesso-finto',
    refresh_token: 'gettone-di-rinnovo-finto',
    expires_in: 3600,
    token_type: 'bearer',
    user: UTENTE,
    ...sovrascritture,
  };
}

/**
 * Prepara il contesto: `build.json` dice a quale progetto appartiene questa
 * copia, e le rotte del progetto rispondono da qui.
 *
 * `chiamate` registra tutto quello che l'app manda verso Supabase: serve per
 * provare le cose che si dimostrano solo per assenza — che senza progetto
 * configurato non parta niente, e che una chiave segreta non venga usata.
 */
async function prepara(page, { chiave = CHIAVE, url = PROGETTO, rotte = {} } = {}) {
  const chiamate = [];
  const contesto = page.context();

  await contesto.route('**/build.json', (percorso) =>
    percorso.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        canale: 'pubblica',
        versione: '0.0.0-prova',
        quando: '2026-01-01T00:00:00+00:00',
        ...(url ? { supabase: { url, publishableKey: chiave } } : {}),
      }),
    })
  );

  await contesto.route(`${PROGETTO}/**`, async (percorso, richiesta) => {
    const indirizzo = new URL(richiesta.url());
    const nome = indirizzo.pathname + indirizzo.search;
    chiamate.push({ nome, chiave: richiesta.headers().apikey || '' });
    const risposta = rotte[nome];
    if (!risposta) return percorso.fulfill({ status: 404, body: '{}' });
    if (risposta === 'cade') return percorso.abort('failed');
    if (risposta.attesa) await new Promise((fatto) => setTimeout(fatto, risposta.attesa));
    return percorso.fulfill({
      status: risposta.stato || 200,
      contentType: 'application/json',
      body: JSON.stringify(risposta.corpo === undefined ? {} : risposta.corpo),
    });
  });

  return chiamate;
}

async function apri(page) {
  await page.goto('/index.html');
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 20_000 });
}

/** Esegue del codice con i moduli già importati; `dato` arriva da qui. */
function dentro(page, azione, dato = null) {
  return page.evaluate(
    async ({ sorgente, dato }) => {
      const auth = await import('./js/auth.js');
      const admin = await import('./js/admin.js');
      const { CONFIG } = await import('./js/config.js');
      return new Function('return ' + sorgente)()({ auth, admin, CONFIG, dato });
    },
    { sorgente: azione.toString(), dato }
  );
}

async function vaiSuTu(page) {
  await page.locator('.pk-nav__tab[data-vai="#/tu"]').click();
  await expect(page.locator('.pk-screen[data-schermata="tu"][data-attiva="1"]')).toBeAttached();
}

/** Entra saltando l'interfaccia: serve alle prove che guardano cosa c'è dopo. */
function entra(page) {
  return dentro(page, ({ auth, dato }) => auth.verificaCodice(dato, '123456'), UTENTE.email);
}

// ---------------------------------------------------------------------------

test('senza progetto configurato l’app resta locale e non chiama nessuno', async ({ page }) => {
  const chiamate = await prepara(page, { url: '' });
  await apri(page);
  await vaiSuTu(page);

  await expect(page.getByRole('button', { name: 'Entra con l’email' })).toHaveCount(0);
  await expect(page.getByText('non è collegata a nessun account')).toBeVisible();
  expect(chiamate).toEqual([]);
});

test('una chiave che sembra segreta non entra nemmeno in CONFIG', async ({ page }) => {
  // Il caso che non deve succedere mai: qualcuno incolla la service_role fra
  // le variabili della pubblicazione. `build_pubblica.py` si ferma prima, ma
  // se quel controllo saltasse, l'app non deve comunque usarla — altrimenti la
  // chiave finisce in ogni intestazione che manda.
  const chiamate = await prepara(page, { chiave: 'sb_secret_questanonvapubblicata' });
  await apri(page);
  const stato = await dentro(page, ({ auth, CONFIG }) => ({
    configurato: auth.configurato(),
    inConfig: CONFIG.supabase.publishableKey,
  }));
  expect(stato.configurato).toBe(false);
  expect(stato.inConfig).toBe('');
  expect(chiamate).toEqual([]);
});

test('il codice via email apre una sessione vera, dal pulsante fino al nome', async ({ page }) => {
  await prepara(page, {
    rotte: {
      '/auth/v1/otp': { corpo: {} },
      '/auth/v1/verify': { corpo: sessione() },
      [PROFILO]: { corpo: [{ display_name: 'Cornicione-7K4Q', role: 'user' }] },
    },
  });
  await apri(page);
  await vaiSuTu(page);

  await page.getByRole('button', { name: 'Entra con l’email' }).click();
  await page.getByLabel('Indirizzo email').fill(UTENTE.email);
  await page.getByRole('button', { name: 'Mandami il codice' }).click();

  await expect(page.getByText(`Codice mandato a ${UTENTE.email}`)).toBeVisible();
  await page.getByLabel('Il codice').fill('123456');
  await page.getByRole('button', { name: 'Entra', exact: true }).click();

  await expect(page.getByText('Sei dentro come Cornicione-7K4Q.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Esci' })).toBeVisible();
});

test('un codice sbagliato lo dice e lascia riprovare senza ricominciare', async ({ page }) => {
  // Sei cifre si sbagliano a copiare. Se un codice errato chiudesse la
  // finestra, bisognerebbe rifarsi mandare il codice: la casella di posta si
  // riempie e la richiesta successiva la ferma il limite di frequenza.
  let tentativi = 0;
  await prepara(page, {
    rotte: {
      '/auth/v1/otp': { corpo: {} },
      [PROFILO]: { corpo: [] },
    },
  });
  await page.context().route(`${PROGETTO}/auth/v1/verify`, (percorso) => {
    tentativi += 1;
    if (tentativi === 1) {
      return percorso.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error_code: 'otp_invalid', msg: 'Token has invalid claims' }),
      });
    }
    return percorso.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(sessione()),
    });
  });

  await apri(page);
  await vaiSuTu(page);
  await page.getByRole('button', { name: 'Entra con l’email' }).click();
  await page.getByLabel('Indirizzo email').fill(UTENTE.email);
  await page.getByRole('button', { name: 'Mandami il codice' }).click();

  await page.getByLabel('Il codice').fill('000000');
  await page.getByRole('button', { name: 'Entra', exact: true }).click();
  await expect(page.getByText('Il codice non è quello giusto.')).toBeVisible();

  // La finestra è ancora lì: si riscrive e basta.
  await page.getByLabel('Il codice').fill('123456');
  await page.getByRole('button', { name: 'Entra', exact: true }).click();
  await expect(page.getByText(`Sei dentro come ${UTENTE.email}.`)).toBeVisible();
  expect(tentativi).toBe(2);
});

test('l’ospite è un account vero, non una finzione locale', async ({ page }) => {
  const chiamate = await prepara(page, {
    rotte: {
      '/auth/v1/signup': {
        corpo: sessione({ user: { ...UTENTE, email: '', is_anonymous: true } }),
      },
      [PROFILO]: { corpo: [{ display_name: 'Muretto-9PQ2', role: 'user' }] },
    },
  });
  await apri(page);
  await vaiSuTu(page);

  await page.getByRole('button', { name: 'Entra come ospite' }).click();
  await expect(page.getByText('Sei dentro come Muretto-9PQ2.')).toBeVisible();
  await expect(page.getByText('Sei entrato come ospite')).toBeVisible();
  // La sessione arriva da una riga in auth.users, non da qualcosa inventato qui.
  expect(chiamate.map((c) => c.nome)).toContain('/auth/v1/signup');
});

test('la sessione sopravvive alla chiusura dell’app', async ({ page }) => {
  await prepara(page, {
    rotte: {
      '/auth/v1/otp': { corpo: {} },
      '/auth/v1/verify': { corpo: sessione() },
      [PROFILO]: { corpo: [] },
    },
  });
  await apri(page);
  await entra(page);

  await page.reload();
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 20_000 });
  expect(await dentro(page, ({ auth }) => auth.dentro())).toBe(true);
});

test('senza rete non si viene buttati fuori', async ({ page }) => {
  // È la promessa dell'app: funziona senza campo. Un rinnovo che non parte
  // perché non c'è rete non è un rifiuto del server, e non deve cancellare
  // niente — chi è in metropolitana deve restare dentro.
  await prepara(page, {
    rotte: {
      '/auth/v1/otp': { corpo: {} },
      '/auth/v1/verify': { corpo: sessione({ expires_in: 1 }) },
      [PROFILO]: { corpo: [] },
      '/auth/v1/token?grant_type=refresh_token': 'cade',
    },
  });
  await apri(page);
  await entra(page);

  const esito = await dentro(page, async ({ auth }) => {
    let errore = '';
    try {
      await auth.intestazioni();
    } catch (e) {
      errore = e.codice || String(e);
    }
    return { dentro: auth.dentro(), errore };
  });
  expect(esito.dentro).toBe(true);
  expect(esito.errore).toBe('');
});

test('un gettone di rinnovo revocato fa uscire davvero', async ({ page }) => {
  // L'altra faccia della prova qui sopra. Se un rifiuto esplicito del server
  // lasciasse la sessione dov'è, l'app resterebbe a mostrare un nome e a
  // prendersi un rifiuto a ogni chiamata, senza mai dire di uscire e rientrare.
  await prepara(page, {
    rotte: {
      '/auth/v1/otp': { corpo: {} },
      '/auth/v1/verify': { corpo: sessione({ expires_in: 1 }) },
      [PROFILO]: { corpo: [] },
      '/auth/v1/token?grant_type=refresh_token': {
        stato: 400,
        corpo: { error_code: 'refresh_token_not_found' },
      },
    },
  });
  await apri(page);
  await entra(page);

  const esito = await dentro(page, async ({ auth }) => {
    let errore = '';
    try {
      await auth.intestazioni();
    } catch (e) {
      errore = e.codice || String(e);
    }
    return { dentro: auth.dentro(), errore };
  });
  expect(esito.dentro).toBe(false);
  expect(esito.errore).toBe('rifiutato');
});

test('i gettoni non escono in quello che il pannello esporta', async ({ page }) => {
  // Il pannello esporta un file che una persona si passa. Un gettone di
  // accesso dentro quel file è una sessione regalata a chiunque lo apra.
  await prepara(page, {
    rotte: {
      '/auth/v1/otp': { corpo: {} },
      '/auth/v1/verify': { corpo: sessione() },
      [PROFILO]: { corpo: [] },
    },
  });
  await apri(page);
  const fuori = await dentro(
    page,
    async ({ auth, admin, dato }) => {
      await admin.accendi(true);
      await auth.verificaCodice(dato, '123456');
      return {
        esportato: JSON.stringify(admin.esporta()),
        utente: JSON.stringify(auth.utente()),
      };
    },
    UTENTE.email
  );

  expect(fuori.esportato).not.toContain('gettone-di-accesso-finto');
  expect(fuori.esportato).not.toContain('gettone-di-rinnovo-finto');
  // Nemmeno chi chiede chi sei si porta via un gettone.
  expect(fuori.utente).not.toContain('gettone');
});

test('l’app non aspetta il progetto per aprirsi', async ({ page }) => {
  // L'accesso non deve stare sul percorso d'avvio. Con una sessione salvata e
  // scaduta, e un progetto che ci mette otto secondi a rispondere, l'app deve
  // comparire subito: è il motivo per cui `inizializza` non aspetta il rinnovo.
  await prepara(page, {
    rotte: {
      '/auth/v1/otp': { corpo: {} },
      '/auth/v1/verify': { corpo: sessione({ expires_in: 1 }) },
      [PROFILO]: { corpo: [] },
      '/auth/v1/token?grant_type=refresh_token': { attesa: 8000, corpo: sessione() },
    },
  });
  await apri(page);
  await entra(page);

  const partenza = Date.now();
  await page.reload();
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 6000 });
  expect(Date.now() - partenza).toBeLessThan(6000);
});

test('il controllo sulle chiavi segrete è lo stesso in JavaScript e in Python', async () => {
  // `build_pubblica.py` riscrive a mano la regola di `ispettore.js` perché
  // deve valere prima che esista un browser. Due copie della stessa regola
  // divergono: questa prova è il motivo per cui non lo faranno in silenzio.
  const radice = fileURLToPath(new URL('../..', import.meta.url));
  const js = readFileSync(`${radice}app/public/js/ispettore.js`, 'utf8');
  const py = readFileSync(`${radice}app/tools/build_pubblica.py`, 'utf8');

  const daJs = js.match(/\/(service_role\|[^/]+)\/\.test/);
  const daPy = py.match(/re\.compile\(r"([^"]+)"\)/);
  expect(daJs, 'la regola in ispettore.js non si riconosce più').not.toBeNull();
  expect(daPy, 'la regola in build_pubblica.py non si riconosce più').not.toBeNull();
  expect(daPy[1]).toBe(daJs[1]);
});
