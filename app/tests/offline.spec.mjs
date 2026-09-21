/* La prova che conta: togliere di mezzo il server e trovare l'app ancora lì.
 *
 * Qui l'offline non è simulato con un interruttore: per ogni prova si avvia
 * un server, si lascia che l'app si installi, e poi **il server viene
 * ucciso**. Quello che continua a funzionare, funziona perché è davvero sul
 * dispositivo — che è la promessa dell'app.
 *
 * Il service worker si accende solo su localhost o https: `127.0.0.1` lo è.
 */

import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { expect, test } from '@playwright/test';

const RADICE_APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function attesa(millisecondi) {
  return new Promise((risolvi) => setTimeout(risolvi, millisecondi));
}

async function avviaServer(porta) {
  const processo = spawn(
    'python3',
    ['tools/serve.py', '--porta', String(porta), '--solo-locale'],
    { cwd: RADICE_APP, stdio: 'ignore' }
  );
  for (let tentativo = 0; tentativo < 80; tentativo++) {
    try {
      const risposta = await fetch(`http://127.0.0.1:${porta}/index.html`);
      if (risposta.ok) return processo;
    } catch {
      // non è ancora in ascolto
    }
    await attesa(150);
  }
  processo.kill('SIGKILL');
  throw new Error(`il server di prova sulla porta ${porta} non è partito`);
}

async function fermaServer(processo, porta) {
  processo.kill('SIGKILL');
  for (let tentativo = 0; tentativo < 60; tentativo++) {
    try {
      await fetch(`http://127.0.0.1:${porta}/index.html`, {
        signal: AbortSignal.timeout(300),
      });
    } catch {
      return; // la porta non risponde più: siamo davvero senza server
    }
    await attesa(150);
  }
  throw new Error(`il server sulla porta ${porta} non si è fermato`);
}

async function attendiPronta(page) {
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 25_000 });
}

/**
 * Aspetta che il service worker abbia finito di mettere via tutto.
 *
 * Si usa `expect.poll` e non `waitForFunction`: quest'ultima non aspetta la
 * promessa restituita dalla funzione, e una promessa è sempre "vera" — la
 * prova passerebbe subito, prima che l'app abbia salvato un solo file.
 */
async function attendiPrecache(page) {
  await expect
    .poll(
      () =>
        page.evaluate(async () => {
          if (!navigator.serviceWorker.controller) return 0;
          const nomi = await caches.keys();
          const nome = nomi.find((n) => n.startsWith('pkfamily-app-'));
          if (!nome) return 0;
          const cache = await caches.open(nome);
          return (await cache.keys()).length;
        }),
      { timeout: 60_000, intervals: [250, 500, 1000] }
    )
    .toBeGreaterThan(20);
}

/** Apre l'app, aspetta che si installi, poi spegne il server e ricarica. */
async function apriPoiStacca(page, porta) {
  const server = await avviaServer(porta);
  try {
    await page.goto(`http://127.0.0.1:${porta}/index.html`);
    await attendiPronta(page);
    await attendiPrecache(page);
  } catch (errore) {
    await fermaServer(server, porta);
    throw errore;
  }
  await fermaServer(server, porta);
  await page.reload();
  await attendiPronta(page);
}

test('spento il server, l’app si riapre lo stesso', async ({ page }) => {
  await apriPoiStacca(page, 8201);

  await expect(page.locator('.pk-map__canvas')).toBeVisible();
  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await expect(page.locator('#pk-lista .pk-item').first()).toBeVisible();
  await page.locator('#pk-cerca').fill('EUR');
  await expect(page.locator('#pk-lista .pk-item').first()).toContainText(/EUR/i);
});

test('spento il server, la scheda di uno spot resta completa', async ({ page }) => {
  await apriPoiStacca(page, 8202);

  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await page.locator('#pk-cerca').fill('EUR Laghetto');
  await page.locator('#pk-lista .pk-item').first().click();
  await page.locator('.pk-modal').getByRole('button', { name: /procedo/i }).click();

  await expect(page.locator('#pk-dettaglio h1')).toContainText('EUR Laghetto');
  await expect(page.locator('#pk-dettaglio')).toContainText('Quanto manca');
  // Le fontanelle stanno in un file che l'app ha con sé: restano anche adesso.
  await expect(page.locator('#pk-dettaglio')).toContainText('Acqua vicina');
});

test('spento il server, il video dello spot si riproduce lo stesso', async ({ page }) => {
  // Il filmato viaggia dentro il pacchetto, non su un sito: è la differenza
  // fra lui e le foto, che senza rete non ci sono.
  await apriPoiStacca(page, 8205);

  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await page.locator('#pk-cerca').fill('Metro Colosseo');
  await page.locator('#pk-lista .pk-item').first().click();
  await page.locator('.pk-modal').getByRole('button', { name: /procedo/i }).click();

  const filmato = page.locator('#pk-dettaglio video');
  await expect(filmato).toBeVisible();
  const letto = await filmato.evaluate(async (nodo) => {
    await nodo.play().catch(() => {});
    await new Promise((r) => setTimeout(r, 900));
    return { durata: nodo.duration, avanzato: nodo.currentTime > 0, errore: nodo.error?.code ?? null };
  });
  expect(letto.errore).toBeNull();
  expect(letto.durata).toBeGreaterThan(4);
  expect(letto.avanzato).toBe(true);
});

test('spento il server, la mappa si disegna comunque', async ({ page }) => {
  // Dove le tessere non arrivano la tela mostra il lino con la sua trama, e
  // gli spilli restano al loro posto: la tela non è mai vuota.
  await apriPoiStacca(page, 8203);

  const opachi = await page.locator('.pk-map__canvas').evaluate((tela) => {
    const ctx = tela.getContext('2d');
    const dati = ctx.getImageData(0, 0, tela.width, tela.height).data;
    let conta = 0;
    for (let i = 3; i < dati.length; i += 4 * 97) if (dati[i] > 0) conta++;
    return conta;
  });
  expect(opachi).toBeGreaterThan(100);
});

test('la schermata Tu conta quello che c’è davvero sul dispositivo', async ({ page }) => {
  await apriPoiStacca(page, 8204);

  await page.locator('.pk-nav__tab[data-vai="#/tu"]').click();
  await expect(page.locator('#pk-tu')).toContainText("file dell'app già sul dispositivo");
  await expect(page.locator('#pk-tu')).toContainText('Prepara quest');
});

test('quello che riguarda le persone non finisce in cache', async ({ page }) => {
  await page.goto('/index.html');
  await attendiPronta(page);
  await attendiPrecache(page);

  const chiavi = await page.evaluate(async () => {
    const nomi = await caches.keys();
    const tutte = [];
    for (const nome of nomi) {
      const cache = await caches.open(nome);
      for (const richiesta of await cache.keys()) tutte.push(richiesta.url);
    }
    return tutte;
  });

  expect(chiavi.some((url) => url.includes('supabase'))).toBe(false);
  expect(chiavi.some((url) => url.includes('/api/v1/route'))).toBe(false);
  expect(chiavi.some((url) => url.includes('youtube'))).toBe(false);
});

/** Una tessera qualunque: serve solo a far finire qualcosa nella cache. */
const TESSERA = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mOomLblPwAGDgLCyvs2hAAAAABJRU5ErkJggg==',
  'base64'
);

test('«prepara quest’area» sa cosa stai guardando anche arrivando da «Tu»', async ({ page }) => {
  // Si apre l'app direttamente sulla schermata Tu: la mappa non è mai stata
  // mostrata. Prima, in questo caso, il riquadro era un punto e il pulsante
  // scaricava tre tessere facendo credere di aver preparato una città.
  await page.goto('/index.html#/tu');
  await attendiPronta(page);

  await page.locator('#pk-tu').getByRole('button', { name: /Prepara quest/ }).click();
  const finestra = page.locator('.pk-modal');
  await expect(finestra).toBeVisible();

  const testo = await finestra.textContent();
  const quante = Number((testo.match(/(\d+)\s+tessere/) || [])[1] || 0);
  expect(quante).toBeGreaterThan(50);
  expect(testo).toContain('zoom');

  // Non si scarica niente: si voleva solo sapere cosa avrebbe scaricato.
  await finestra.getByRole('button', { name: 'Annulla' }).click();
});

test('le tessere preparate finiscono in una cache che non viene sfrattata', async ({
  page,
  context,
}) => {
  await context.route(/tile\.openstreetmap\.org/, (rotta) =>
    rotta.fulfill({
      status: 200,
      contentType: 'image/png',
      headers: { 'access-control-allow-origin': '*' },
      body: TESSERA,
    })
  );
  await page.goto('/index.html');
  await attendiPronta(page);

  // Poche tessere: la prova deve essere veloce, non esaustiva.
  await page.evaluate(async () => {
    const { CONFIG } = await import('./js/config.js');
    CONFIG.tettoPrefetch = 12;
  });

  await page.locator('.pk-nav__tab[data-vai="#/tu"]').click();
  await page.locator('#pk-tu').getByRole('button', { name: /Prepara quest/ }).click();
  await page.locator('.pk-modal').getByRole('button', { name: 'Scarica' }).click();

  await expect
    .poll(
      () =>
        page.evaluate(async () => {
          if (!(await caches.has('pkfamily-area'))) return 0;
          const cache = await caches.open('pkfamily-area');
          return (await cache.keys()).length;
        }),
      { timeout: 20_000 }
    )
    .toBeGreaterThan(0);

  await expect(page.locator('#pk-tu')).toContainText('preparate apposta');
});

test('il riquadro che scavalca il 180° non fa il giro del mondo', async ({ page }) => {
  await page.goto('/index.html');
  await attendiPronta(page);

  const conti = await page.evaluate(async () => {
    const offline = await import('./js/offline.js');
    // Un riquadro stretto a cavallo dell'antimeridiano (Figi, Kiribati).
    const scavalca = offline.tessereDelRiquadro(
      { nord: -17.5, sud: -18.5, ovest: 179.5, est: -179.5 },
      'mappa',
      8,
      8,
      5000
    );
    // Lo stesso riquadro, ma largo uguale e lontano dal bordo.
    const normale = offline.tessereDelRiquadro(
      { nord: -17.5, sud: -18.5, ovest: 10, est: 11 },
      'mappa',
      8,
      8,
      5000
    );
    return { scavalca: scavalca.totale, normale: normale.totale };
  });

  // Prima ne contava centinaia: tutta la fascia dall'altra parte del mondo.
  expect(conti.scavalca).toBeLessThanOrEqual(conti.normale + 2);
});
