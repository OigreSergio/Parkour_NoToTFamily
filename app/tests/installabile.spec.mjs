/* Un'applicazione, non una pagina: manifest, icone, service worker. */

import { expect, test } from '@playwright/test';

test('il manifest è quello di PkFAMILY, non un avanzo del generatore', async ({ page }) => {
  await page.goto('/index.html');
  const manifest = await page.evaluate(async () => {
    const risposta = await fetch('manifest.webmanifest');
    return risposta.json();
  });

  expect(manifest.name).toContain('PkFAMILY');
  expect(manifest.short_name).toBe('PkFAMILY');
  expect(manifest.display).toBe('standalone');
  expect(manifest.orientation).toBe('portrait');
  expect(manifest.theme_color).toBe('#C26A52');
  expect(manifest.description).not.toContain('Flutter');
  expect(manifest.lang).toBe('it');

  const misure = manifest.icons.map((icona) => `${icona.sizes}/${icona.purpose || 'any'}`);
  expect(misure).toContain('192x192/any');
  expect(misure).toContain('512x512/any');
  expect(misure).toContain('512x512/maskable');
});

test('le icone dichiarate esistono davvero', async ({ page, request }) => {
  await page.goto('/index.html');
  const icone = await page.evaluate(async () => {
    const risposta = await fetch('manifest.webmanifest');
    const manifest = await risposta.json();
    return manifest.icons.map((icona) => icona.src);
  });

  for (const percorso of icone) {
    const risposta = await request.get(`/${percorso}`);
    expect(risposta.status(), percorso).toBe(200);
    expect(risposta.headers()['content-type']).toContain('image/png');
  }
});

test('il service worker si registra e prende il controllo', async ({ page }) => {
  await page.goto('/index.html');
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 20_000 });

  await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller), null, {
    timeout: 30_000,
  });

  const stato = await page.evaluate(async () => {
    const registrazione = await navigator.serviceWorker.getRegistration();
    return { attivo: Boolean(registrazione && registrazione.active), scope: registrazione.scope };
  });
  expect(stato.attivo).toBe(true);
});

test('la pagina dichiara colore, tema e icona per iOS', async ({ page }) => {
  await page.goto('/index.html');
  await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute('content', '#C26A52');
  await expect(page.locator('link[rel="manifest"]')).toHaveAttribute(
    'href',
    'manifest.webmanifest'
  );
  await expect(page.locator('link[rel="apple-touch-icon"]')).toHaveCount(1);
  await expect(page.locator('meta[name="mobile-web-app-capable"]')).toHaveAttribute(
    'content',
    'yes'
  );
});
