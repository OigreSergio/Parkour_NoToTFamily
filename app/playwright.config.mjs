/* Prove automatiche dell'app PkFAMILY.
 *
 * Il computer serve a questo: provare l'app come se fosse un telefono, e
 * accorgersi dei guasti prima che se ne accorga chi la usa davvero. Il
 * dispositivo emulato è un Pixel (schermo verticale, tocco, niente mouse).
 *
 * Il server è `tools/serve.py` su localhost: è l'unico modo in cui il
 * browser accende il service worker senza un certificato, ed è il service
 * worker che rende vere le prove sull'offline.
 *
 * `PK_CHROMIUM` permette di puntare a un eseguibile Chromium già presente
 * (utile dove Playwright non può scaricare il proprio).
 */

import { defineConfig, devices } from '@playwright/test';

const PORTA = 8123;
const eseguibile = process.env.PK_CHROMIUM;

export default defineConfig({
  testDir: './tests',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${PORTA}`,
    ...devices['Pixel 7'],
    // L'app segue la lingua del browser: i test parlano italiano, come la
    // lingua di partenza del prodotto.
    locale: 'it-IT',
    // Il permesso di posizione si concede nei test che lo usano.
    permissions: [],
    launchOptions: eseguibile ? { executablePath: eseguibile } : {},
  },
  webServer: {
    command: `python3 tools/serve.py --porta ${PORTA} --solo-locale`,
    url: `http://127.0.0.1:${PORTA}/index.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
