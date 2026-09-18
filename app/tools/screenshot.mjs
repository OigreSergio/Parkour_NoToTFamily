/* Fotografa l'app schermata per schermata, chiara e scura.
 *
 *   node tools/screenshot.mjs                    # in docs/design/screens/
 *   node tools/screenshot.mjs --cartella /tmp
 *
 * Serve a guardare l'app tutta insieme senza aprirla, e a vedere in una
 * riga di `git diff --stat` se una modifica al design ha spostato qualcosa
 * che non doveva. È la consegna 5 del capitolo grafica del masterplan.
 *
 * Le tessere di mappa non vengono scaricate: le fotografie mostrano il lino,
 * che è anche quello che si vede senza rete.
 */

import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { chromium, devices } from '@playwright/test';

const RADICE_APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PORTA = 8321;

const argomenti = process.argv.slice(2);
const indiceCartella = argomenti.indexOf('--cartella');
const CARTELLA =
  indiceCartella >= 0
    ? path.resolve(argomenti[indiceCartella + 1])
    : path.resolve(RADICE_APP, '..', 'docs', 'design', 'screens');

const attesa = (millisecondi) => new Promise((risolvi) => setTimeout(risolvi, millisecondi));

const SCHERMATE = [
  ['mappa', '#/mappa'],
  ['spot', '#/spot'],
  ['scheda', null],
  ['tutorial', '#/tutorial'],
  ['tu', '#/tu'],
];

async function avviaServer() {
  const processo = spawn('python3', ['tools/serve.py', '--porta', String(PORTA), '--solo-locale'], {
    cwd: RADICE_APP,
    stdio: 'ignore',
  });
  for (let tentativo = 0; tentativo < 80; tentativo++) {
    try {
      const risposta = await fetch(`http://127.0.0.1:${PORTA}/index.html`);
      if (risposta.ok) return processo;
    } catch {
      // non ancora
    }
    await attesa(150);
  }
  processo.kill('SIGKILL');
  throw new Error('il server non è partito');
}

async function fotografa(browser, tema) {
  const contesto = await browser.newContext({
    ...devices['Pixel 7'],
    // Il telefono vero disegna a 2,6 pixel per punto: per delle fotografie di
    // riferimento sono megabyte in più a ogni ritocco del design. Due bastano.
    deviceScaleFactor: 2,
    locale: 'it-IT',
    colorScheme: tema === 'scuro' ? 'dark' : 'light',
  });
  // Nessuna tessera: le fotografie devono essere sempre uguali.
  await contesto.route(/tile|arcgisonline/, (rotta) => rotta.abort());
  const pagina = await contesto.newPage();

  await pagina.goto(`http://127.0.0.1:${PORTA}/index.html`);
  await pagina.waitForFunction(() => document.body.dataset.pronta === '1', null, {
    timeout: 30000,
  });

  for (const [nome, rotta] of SCHERMATE) {
    if (rotta) {
      await pagina.evaluate((r) => {
        location.hash = r;
      }, rotta);
    } else {
      // La scheda: si arriva dalla lista, passando dall'avviso sui rischi.
      await pagina.evaluate(() => {
        location.hash = '#/spot';
      });
      await pagina.locator('#pk-cerca').fill('EUR Laghetto');
      await pagina.locator('#pk-lista .pk-item').first().click();
      const avviso = pagina.locator('.pk-modal');
      // L'avviso compare solo la prima volta, e compare dopo un giro di
      // eventi: va aspettato, non contato subito.
      await avviso.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});
      if (await avviso.count()) {
        await pagina.screenshot({ path: path.join(CARTELLA, `telefono-${tema}-avviso.png`) });
        await avviso.getByRole('button', { name: /procedo/i }).click();
        await avviso.waitFor({ state: 'detached', timeout: 5000 }).catch(() => {});
      }
    }
    await attesa(500);
    await pagina.screenshot({ path: path.join(CARTELLA, `telefono-${tema}-${nome}.png`) });
    process.stdout.write(`  telefono-${tema}-${nome}.png\n`);
  }

  await contesto.close();
}

const server = await avviaServer();
await mkdir(CARTELLA, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.PK_CHROMIUM });
try {
  for (const tema of ['chiaro', 'scuro']) await fotografa(browser, tema);
} finally {
  await browser.close();
  server.kill('SIGKILL');
}
console.log(`\n  Fotografie in ${CARTELLA}`);
