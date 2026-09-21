/* L'app si apre, si naviga, si cerca: le cose che deve fare sempre. */

import { expect, test } from '@playwright/test';

/** L'app è pronta quando `avvia()` ha finito: lo dice il body. */
async function attendiPronta(page) {
  await page.goto('/index.html');
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 20_000 });
}

test('si apre sulla mappa, con la tela disegnata', async ({ page }) => {
  await attendiPronta(page);

  await expect(page.locator('#pk-splash')).toHaveCount(0);
  await expect(page.locator('.pk-map__canvas')).toBeVisible();
  await expect(page.locator('#pk-titolo')).toHaveText('Mappa');
  await expect(page.locator('.pk-nav__tab[aria-current="page"]')).toHaveText(/Mappa/);

  // La tela ha davvero dei pixel: se la mappa non si disegnasse sarebbe 0.
  const misure = await page.locator('.pk-map__canvas').evaluate((tela) => ({
    w: tela.width,
    h: tela.height,
  }));
  expect(misure.w).toBeGreaterThan(300);
  expect(misure.h).toBeGreaterThan(300);

  // E soprattutto: ci sono gli spilli, nei colori del masterplan (3.5) —
  // `verde` per i verificati, `blu-community` per gli altri. Una mappa senza
  // spot è il guasto più facile da non vedere.
  const spilli = await page.locator('.pk-map__canvas').evaluate((tela) => {
    const dati = tela.getContext('2d').getImageData(0, 0, tela.width, tela.height).data;
    const vicino = (i, r, g, b) =>
      Math.abs(dati[i] - r) < 24 && Math.abs(dati[i + 1] - g) < 24 && Math.abs(dati[i + 2] - b) < 24;
    let verde = 0;
    let blu = 0;
    for (let i = 0; i < dati.length; i += 4) {
      if (vicino(i, 0x63, 0x86, 0x4a)) verde++;
      else if (vicino(i, 0x6f, 0x9c, 0xb8)) blu++;
    }
    return { verde, blu };
  });
  expect(spilli.verde).toBeGreaterThan(40);
  expect(spilli.blu).toBeGreaterThan(40);
});

test('la lista mostra gli spot e la ricerca li filtra', async ({ page }) => {
  await attendiPronta(page);
  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();

  await expect(page.locator('#pk-lista .pk-item').first()).toBeVisible();
  const primi = await page.locator('#pk-lista .pk-item').count();
  expect(primi).toBeGreaterThan(10);

  await page.locator('#pk-cerca').fill('Borghese');
  await expect(page.locator('#pk-lista .pk-item').first()).toContainText(/Borghese/i);
  expect(await page.locator('#pk-lista .pk-item').count()).toBeLessThan(primi);
});

test('la scheda di uno spot passa dall’avviso sui rischi', async ({ page }) => {
  await attendiPronta(page);
  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await page.locator('#pk-cerca').fill('Borghese');
  await page.locator('#pk-lista .pk-item').first().click();

  const avviso = page.locator('.pk-modal');
  await expect(avviso).toBeVisible();
  await expect(avviso).toContainText('rischio reale');
  await avviso.getByRole('button', { name: /procedo sotto la mia responsabilità/i }).click();

  await expect(page.locator('#pk-dettaglio h1')).toContainText(/Borghese/i);
  await expect(page.locator('#pk-dettaglio')).toContainText('Quanto manca');
  await expect(page.locator('#pk-dettaglio')).toContainText('Dove');
  // Un pezzo di scheda che manca deve sparire, non diventare la parola «null».
  await expect(page.locator('#pk-dettaglio')).not.toContainText('null');
  await expect(page.locator('#pk-dettaglio')).not.toContainText('undefined');

  // Una volta accettato, l'avviso non ricompare a ogni spot.
  await page.locator('#pk-indietro').click();
  await page.locator('#pk-lista .pk-item').first().click();
  await expect(page.locator('.pk-modal')).toHaveCount(0);
});

test('i filtri della lista lavorano insieme', async ({ page }) => {
  await attendiPronta(page);
  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();

  const tutti = await page.locator('#pk-lista').textContent();
  await page.locator('#pk-filtri .pk-chip', { hasText: 'Verificati' }).click();
  const verificati = await page.locator('#pk-lista').textContent();

  expect(verificati).not.toEqual(tutti);
  await expect(page.locator('#pk-lista')).toContainText('26 spot');
});

test('i tutorial si filtrano per livello', async ({ page }) => {
  await attendiPronta(page);
  await page.locator('.pk-nav__tab[data-vai="#/tutorial"]').click();

  await expect(page.locator('#pk-tutorial .pk-item').first()).toBeVisible();
  await page.locator('#pk-filtri-tutorial .pk-chip', { hasText: 'Avanzato' }).click();
  await expect(page.locator('#pk-tutorial')).toContainText('18 tutorial');
});

test('la schermata Tu racconta lo stato dell’offline', async ({ page }) => {
  await attendiPronta(page);
  await page.locator('.pk-nav__tab[data-vai="#/tu"]').click();

  await expect(page.locator('#pk-tu')).toContainText('Installa');
  await expect(page.locator('#pk-tu')).toContainText('Senza rete');
  await expect(page.locator('#pk-tu')).toContainText('Prepara quest');
  await expect(page.locator('#pk-tu')).toContainText('1706 spot nell');
});

test('il tema scuro si sceglie e resta', async ({ page }) => {
  await attendiPronta(page);
  await page.locator('.pk-nav__tab[data-vai="#/tu"]').click();
  await page.locator('#pk-tu .pk-chip', { hasText: 'Scuro' }).click();

  await expect(page.locator('html')).toHaveAttribute('data-tema', 'scuro');
  await page.reload();
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 20_000 });
  await expect(page.locator('html')).toHaveAttribute('data-tema', 'scuro');
});

/** Apre la scheda di uno spot cercandolo, e toglie di mezzo l'avviso sui rischi. */
async function apriScheda(page, cerca) {
  await attendiPronta(page);
  await page.locator('.pk-nav__tab[data-vai="#/spot"]').click();
  await page.locator('#pk-cerca').fill(cerca);
  await page.locator('#pk-lista .pk-item').first().click();
  // L'avviso arriva un attimo dopo il tocco: si aspetta, non si conta.
  const avviso = page.locator('.pk-modal');
  await expect(avviso).toBeVisible();
  await avviso.getByRole('button', { name: /procedo sotto la mia responsabilità/i }).click();
  await expect(page.locator('#pk-dettaglio h1')).toBeVisible();
}

test('lo spot con un video lo mostra, e il video si riproduce davvero', async ({ page }) => {
  await apriScheda(page, 'Metro Colosseo');
  await expect(page.locator('#pk-dettaglio h1')).toHaveText('Spot Metro Colosseo');

  const filmato = page.locator('#pk-dettaglio video');
  await expect(filmato).toBeVisible();
  await expect(filmato).toHaveJSProperty('controls', true);
  // La locandina si vede prima di premere play: senza, il riquadro è nero.
  await expect(filmato).toHaveAttribute('poster', /colosseo-metro\.jpg$/);

  // Non è un riquadro vuoto: il browser lo ha letto, sa quanto dura e va avanti.
  const letto = await filmato.evaluate(async (nodo) => {
    await nodo.play().catch(() => {});
    await new Promise((r) => setTimeout(r, 800));
    return {
      durata: nodo.duration,
      larghezza: nodo.videoWidth,
      altezza: nodo.videoHeight,
      avanzato: nodo.currentTime > 0,
      errore: nodo.error ? nodo.error.code : null,
    };
  });
  expect(letto.errore).toBeNull();
  expect(letto.durata).toBeGreaterThan(4);
  expect(letto.larghezza).toBe(960);
  expect(letto.altezza).toBe(550);
  expect(letto.avanzato).toBe(true);
});

test('aperta di filato su uno spot, l’app non resta sotto il guscio d’avvio', async ({ page }) => {
  // È quello che fa un QR puntato a uno spot. L'avviso sui rischi ferma la
  // scheda finché una persona non risponde: giusto. Ma l'app dietro deve
  // esserci, e il guscio d'avvio deve essersene andato.
  const METRO_COLOSSEO = 'd6668114-4fb1-46a2-b23b-02c3ed2d2d13';
  await page.goto(`/index.html#/spot/${METRO_COLOSSEO}`);

  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 20_000 });
  await expect(page.locator('#pk-splash')).toHaveCount(0);
  await expect(page.locator('#pk-nav')).toBeVisible();

  // L'avviso è lì, sopra l'app e non sopra il guscio.
  const avviso = page.locator('.pk-modal');
  await expect(avviso).toBeVisible();
  await expect(avviso).toContainText('rischio reale');

  await avviso.getByRole('button', { name: /procedo sotto la mia responsabilità/i }).click();
  await expect(page.locator('#pk-dettaglio h1')).toHaveText('Spot Metro Colosseo');
  await expect(page.locator('#pk-dettaglio video')).toBeVisible();
});

test('gli spot senza video non mostrano un riquadro vuoto', async ({ page }) => {
  await apriScheda(page, 'Borghese');
  await expect(page.locator('#pk-dettaglio video')).toHaveCount(0);
});
