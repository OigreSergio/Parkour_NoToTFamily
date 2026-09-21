/* La demo in un file solo: si costruisce, si apre con un doppio clic, e ha
 * dentro gli stessi spot.
 *
 * Qui non c'è nessun server: la pagina viene aperta come `file://`, che è
 * esattamente quello che succede a chi se la salva sul computer. È anche il
 * caso più severo — niente moduli ES, niente `fetch`, niente service worker —
 * ed è il motivo per cui questa prova esiste.
 */

import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { expect, test } from '@playwright/test';

const RADICE_APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

let cartella;
let file;

test.beforeAll(() => {
  cartella = mkdtempSync(path.join(tmpdir(), 'pkfamily-demo-'));
  execFileSync('python3', ['tools/build_demo.py', '--cartella', cartella], { cwd: RADICE_APP });
  file = `file://${path.join(cartella, 'pkfamily-demo.html')}`;
});

test.afterAll(() => {
  if (cartella) rmSync(cartella, { recursive: true, force: true });
});

async function apriDemo(page) {
  await page.goto(file);
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 30_000 });
}

test('si apre da un file, senza server e senza moduli', async ({ page }) => {
  await apriDemo(page);

  await expect(page.locator('#pk-fascia')).toContainText('DEMO');
  await expect(page.locator('.pk-map__canvas')).toBeVisible();

  // Niente viene chiesto a un server: i dati sono nella pagina.
  const dentro = await page.evaluate(() => Object.keys(globalThis.__PK_INLINE__ || {}));
  expect(dentro).toContain('data/spots.json');
  expect(dentro).toContain('data/fountains.json');
  expect(dentro).toContain('i18n/it.json');
});

test('ci sono gli stessi spot, e si cercano', async ({ page }) => {
  await apriDemo(page);

  const quanti = await page.evaluate(
    () => globalThis.__PK_INLINE__['data/spots.json'].count
  );
  expect(quanti).toBe(1706);

  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await page.locator('#pk-cerca').fill('Colosseo');
  await expect(page.locator('#pk-lista .pk-item').first()).toContainText(/Colosseo/i);

  await page.locator('#pk-lista .pk-item').first().click();
  await page.locator('.pk-modal').getByRole('button', { name: /procedo/i }).click();
  await expect(page.locator('#pk-dettaglio h1')).toContainText(/Colosseo/i);
  // Le fontanelle viaggiano nel file come tutto il resto.
  await expect(page.locator('#pk-dettaglio')).toContainText('Acqua vicina');
});

test('dice com’è fatta invece di fingere una cache', async ({ page }) => {
  await apriDemo(page);
  await page.locator('.pk-nav__tab[data-vai="#/tu"]').click();
  await expect(page.locator('#pk-tu')).toContainText('un solo file', { timeout: 10_000 });
  await expect(page.locator('#pk-tu')).not.toContainText('Prepara quest');
});

test('anche da un file si corregge uno spot', async ({ page }) => {
  await apriDemo(page);
  await page.locator('.pk-nav__tab[data-vai="#/tu"]').click();
  await page.locator('#pk-tu').getByRole('button', { name: 'Accendi la modalità sviluppatore' }).click();
  await page.locator('.pk-modal').getByRole('button', { name: 'Accendi', exact: true }).click();

  await page.locator('#pk-admin input[type="search"]').fill('EUR Laghetto');
  await page.locator('#pk-admin .pk-item').first().click();
  await page.locator('#pk-admin-spot input').first().fill('EUR Laghetto (dalla demo)');
  await page.locator('#pk-admin').getByRole('button', { name: 'Salva', exact: true }).click();

  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await page.locator('#pk-cerca').fill('dalla demo');
  await expect(page.locator('#pk-lista .pk-item').first()).toContainText('EUR Laghetto (dalla demo)');
});

test('nella demo il video non c’è, e non lascia un riquadro vuoto', async ({ page }) => {
  // Il filmato di uno spot è un file accanto all'app: in un file solo non c'è
  // posto per lui. La scheda deve restare intera lo stesso, senza il buco
  // nero di un video che non parte.
  await apriDemo(page);

  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await page.locator('#pk-cerca').fill('Metro Colosseo');
  await page.locator('#pk-lista .pk-item').first().click();
  await page.locator('.pk-modal').getByRole('button', { name: /procedo/i }).click();

  await expect(page.locator('#pk-dettaglio h1')).toHaveText('Spot Metro Colosseo');
  await expect(page.locator('#pk-dettaglio video')).toBeHidden();
  await expect(page.locator('#pk-dettaglio')).toContainText('Quanto manca');
});
