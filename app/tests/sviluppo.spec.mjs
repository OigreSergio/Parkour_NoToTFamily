/* La beta e la modalità sviluppatore: la fascia che avvisa, il pannello che
 * modifica, e il fatto che quello che si modifica resti locale.
 */

import { expect, test } from '@playwright/test';

async function attendiPronta(page) {
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 20_000 });
}

/** Accende la modalità sviluppatore passando da dove passa una persona. */
async function accendiSviluppo(page) {
  await page.locator('.pk-nav__tab[data-vai="#/tu"]').click();
  await page.locator('#pk-tu').getByRole('button', { name: 'Accendi la modalità sviluppatore' }).click();
  await page.locator('.pk-modal').getByRole('button', { name: 'Accendi', exact: true }).click();
  await expect(page.locator('#pk-admin')).toBeVisible();
}

test('la copia di sviluppo non porta nessuna fascia', async ({ page }) => {
  await page.goto('/index.html');
  await attendiPronta(page);
  await expect(page.locator('#pk-fascia')).toBeHidden();
});

test('una beta lo dice in testa, con la sua versione', async ({ page, context }) => {
  await context.route('**/build.json', (rotta) =>
    rotta.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ canale: 'beta', versione: '0.1.0-beta.20260918', quando: '2026-09-18T22:06:37+00:00' }),
    })
  );
  await page.goto('/index.html');
  await attendiPronta(page);

  const fascia = page.locator('#pk-fascia');
  await expect(fascia).toBeVisible();
  await expect(fascia).toContainText('BETA');
  await expect(fascia).toContainText('0.1.0-beta.20260918');
});

test('la modalità sviluppatore si accende a mano e si vede', async ({ page }) => {
  await page.goto('/index.html');
  await attendiPronta(page);
  await accendiSviluppo(page);

  const fascia = page.locator('#pk-fascia');
  await expect(fascia).toBeVisible();
  await expect(fascia).toContainText('MODALITÀ SVILUPPATORE');
  await expect(page.locator('#pk-admin')).toContainText('Tutto quello che cambi resta su questo dispositivo');
});

test('senza accenderla, l’indirizzo del pannello non apre niente', async ({ page }) => {
  await page.goto('/index.html#/admin');
  await attendiPronta(page);
  // Si finisce su «Tu», non nel pannello.
  await expect(page.locator('#pk-admin')).toBeHidden();
  await expect(page.locator('#pk-titolo')).toHaveText('Tu');
});

test('si corregge uno spot, e la correzione resta locale', async ({ page }) => {
  await page.goto('/index.html');
  await attendiPronta(page);
  await accendiSviluppo(page);

  // Si cerca lo spot e lo si apre nel pannello.
  await page.locator('#pk-admin input[type="search"]').fill('EUR Laghetto');
  await page.locator('#pk-admin .pk-item').first().click();

  const nome = page.locator('#pk-admin-spot input').first();
  await expect(nome).toHaveValue(/EUR Laghetto/);
  await nome.fill('EUR Laghetto (corretto in locale)');
  await page.locator('#pk-admin').getByRole('button', { name: 'Salva', exact: true }).click();
  await expect(page.getByText('Salvato su questo dispositivo')).toBeVisible();
  await expect(page.locator('#pk-admin')).toContainText('Spot corretti: 1');

  // La correzione si vede nella lista vera, con il segno che è locale.
  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await page.locator('#pk-cerca').fill('corretto in locale');
  await expect(page.locator('#pk-lista .pk-item').first()).toContainText('EUR Laghetto (corretto in locale)');

  // Spenta la modalità, il file torna a comandare.
  await page.locator('.pk-nav__tab[data-vai="#/tu"]').click();
  await page.locator('#pk-tu').getByRole('button', { name: 'Spegni la modalità sviluppatore' }).click();
  await expect(page.locator('#pk-fascia')).toBeHidden();

  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await page.locator('#pk-cerca').fill('corretto in locale');
  await expect(page.locator('#pk-lista')).toContainText('Nessuno spot con questi filtri');
  await page.locator('#pk-cerca').fill('EUR Laghetto');
  await expect(page.locator('#pk-lista .pk-item').first()).toContainText('EUR Laghetto');
});

test('un filtro provato dal pannello arriva subito sulla mappa', async ({ page }) => {
  await page.goto('/index.html');
  await attendiPronta(page);
  await accendiSviluppo(page);

  const campo = page.locator('#pk-admin input').filter({ hasNot: page.locator('[type="search"]') });
  // Il primo campo del gruppo «Mappa e tessere» è il filtro chiaro.
  const filtroChiaro = page
    .locator('#pk-admin label', { hasText: 'filtroTessere.chiaro' })
    .locator('input');
  await expect(filtroChiaro).toHaveValue(/sepia\(0\.35\)/);
  await filtroChiaro.fill('grayscale(1)');
  await filtroChiaro.blur();
  await expect(page.locator('#pk-admin')).toContainText('Impostazioni cambiate: 1');

  // È finito davvero nella configurazione dell'app.
  const inVigore = await page.evaluate(async () => {
    const { CONFIG } = await import('./js/config.js');
    return CONFIG.filtroTessere.chiaro;
  });
  expect(inVigore).toBe('grayscale(1)');
  void campo;
});

test('una chiave segreta non entra nel pannello', async ({ page }) => {
  await page.goto('/index.html');
  await attendiPronta(page);
  await accendiSviluppo(page);

  const chiave = page
    .locator('#pk-admin label', { hasText: 'supabase.publishableKey' })
    .locator('input');
  await chiave.fill('sb_secret_questa_non_deve_entrare');
  await chiave.blur();

  await expect(page.getByText('Sembra una chiave segreta')).toBeVisible();
  await expect(chiave).toHaveValue('');
});
