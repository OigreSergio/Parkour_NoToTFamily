/* La demo con il motore in Python: l'app chiede, Python risponde.
 *
 * La prova costruisce davvero il file unico con `build_demo_python.py`, lo
 * avvia come lo avvierebbe una persona, e poi guarda **chi** fa il lavoro:
 * se le domande pesanti non passano da `/api/`, il motore è decorativo.
 */

import { execFileSync, spawn } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { expect, test } from '@playwright/test';

const RADICE_APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PORTA = 8493;
const attesa = (ms) => new Promise((r) => setTimeout(r, ms));

let cartella;
let processo;
let base;

test.beforeAll(async () => {
  cartella = mkdtempSync(path.join(tmpdir(), 'pkfamily-python-'));
  execFileSync('python3', ['tools/build_demo_python.py', '--cartella', cartella], {
    cwd: RADICE_APP,
  });

  processo = spawn('python3', [path.join(cartella, 'pkfamily-demo.py'), '--api', '--porta', String(PORTA)], {
    stdio: 'ignore',
  });
  base = `http://127.0.0.1:${PORTA}`;
  for (let tentativo = 0; tentativo < 80; tentativo++) {
    try {
      const risposta = await fetch(`${base}/api/stato`);
      if (risposta.ok) return;
    } catch {
      // non è ancora in ascolto
    }
    await attesa(200);
  }
  throw new Error('la demo in Python non è partita');
});

test.afterAll(() => {
  if (processo) processo.kill('SIGKILL');
  if (cartella) rmSync(cartella, { recursive: true, force: true });
});

test('il motore risponde, e dice con quanti dati', async ({ request }) => {
  const stato = await (await request.get(`${base}/api/stato`)).json();
  expect(stato).toMatchObject({ motore: 'python', spots: 1706, verificati: 26 });

  const cerca = await (await request.get(`${base}/api/cerca?q=colosseo`)).json();
  expect(cerca.totale).toBeGreaterThan(0);
  expect(cerca.spots[0].name).toMatch(/Colosseo/i);

  // Gli stessi conti dell'app: distanza in metri e tempi a piedi.
  const vicini = await (await request.get(`${base}/api/vicini?lat=41.9028&lng=12.4964&quanti=3`)).json();
  expect(vicini.spots).toHaveLength(3);
  expect(vicini.spots[0].metri).toBeLessThan(vicini.spots[1].metri);
  expect(vicini.spots[0].cammino_s).toBeGreaterThan(0);
});

test('l’app usa il motore invece di cercare da sola', async ({ page }) => {
  const chiamate = [];
  page.on('request', (r) => {
    const indirizzo = new URL(r.url()).pathname;
    if (indirizzo.startsWith('/api/')) chiamate.push(indirizzo);
  });

  await page.goto(`${base}/index.html`);
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 25_000 });

  // Lo dice in testa.
  await expect(page.locator('#pk-fascia')).toContainText('DEMO PYTHON');

  // La mappa ha chiesto a Python chi c'è nel riquadro.
  await expect.poll(() => chiamate.filter((c) => c.startsWith('/api/riquadro')).length, {
    timeout: 15_000,
  }).toBeGreaterThan(0);
  await expect(page.locator('#pk-sottotitolo')).toContainText(/spot qui|Nessuno spot/);

  // La ricerca passa da Python.
  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await page.locator('#pk-cerca').fill('Garbatella');
  await expect(page.locator('#pk-lista .pk-item').first()).toContainText(/Garbatella/i);
  expect(chiamate.some((c) => c.startsWith('/api/cerca'))).toBe(true);

  // E la scheda chiede a Python anche le fontanelle.
  await page.locator('#pk-lista .pk-item').first().click();
  await page.locator('.pk-modal').getByRole('button', { name: /procedo/i }).click();
  await expect(page.locator('#pk-dettaglio')).toContainText('Acqua vicina');
  expect(chiamate.some((c) => c.startsWith('/api/spot/'))).toBe(true);
});

test('se il motore tace, l’app continua da sola', async ({ page }) => {
  await page.goto(`${base}/index.html`);
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 25_000 });

  // Il motore smette di rispondere: l'app non deve restare a mani vuote.
  await page.route('**/api/**', (rotta) => rotta.abort());

  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await page.locator('#pk-cerca').fill('EUR Laghetto');
  await expect(page.locator('#pk-lista .pk-item').first()).toContainText('EUR Laghetto');
});
