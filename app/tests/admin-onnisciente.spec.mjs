/* Il pannello che vede tutto: le prove che passano dall'interfaccia.
 *
 * `admin-modello.spec.mjs` prova il modello chiamando i moduli dalla pagina.
 * Qui si tocca: si preme la pastiglia, si scrive nella casella, si clicca
 * Salva. Sono due prove diverse della stessa cosa, e servono tutte e due —
 * il modello può essere giusto e la schermata mandare al posto sbagliato i
 * valori che legge, che è esattamente quello che è successo scrivendola.
 */

import { expect, test } from '@playwright/test';

async function pannello(page) {
  await page.goto('/index.html');
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 20_000 });
  await page.evaluate(async () => {
    const admin = await import('./js/admin.js');
    await admin.accendi(true);
  });
  await page.goto('/index.html#/admin');
  await expect(page.locator('#pk-admin-cerca')).toBeVisible();
}

/** Esegue del codice con i moduli già importati. */
function dentro(page, azione) {
  return page.evaluate(async (sorgente) => {
    const admin = await import('./js/admin.js');
    const dati = await import('./js/data.js');
    const store = await import('./js/store.js');
    const { CONFIG } = await import('./js/config.js');
    return new Function('return ' + sorgente)()({ admin, dati, store, CONFIG });
  }, azione.toString());
}

/** Apre la prima voce che la ricerca trova nella collezione aperta. */
async function apriPrima(page, testo) {
  await page.locator('#pk-admin-cerca').fill(testo);
  await page.locator('#pk-admin .pk-item').first().click();
  await expect(page.locator('#pk-admin-spot')).toBeVisible();
}

// ---------------------------------------------------------------------------

test('le pastiglie cambiano collezione, e una fontanella si apre in sola lettura', async ({
  page,
}) => {
  // Le fontanelle non hanno una chiave propria: correggerle qui vorrebbe dire
  // inventare un identificativo che alla prima rigenerazione dei dati non
  // corrisponde più a niente. La scheda si guarda, non si tocca.
  await pannello(page);
  await page.locator('#pk-admin').getByRole('button', { name: 'Fontanelle' }).click();
  await expect(page.locator('#pk-admin-cerca')).toHaveAttribute(
    'placeholder',
    /Fontanelle/
  );

  // Le fontanelle si leggono alla prima scheda di uno spot: si chiedono qui.
  await dentro(page, ({ dati }) => dati.tutteLeFontanelle());
  await page.locator('#pk-admin').getByRole('button', { name: 'Fontanelle' }).click();
  await page.locator('#pk-admin .pk-item').first().click();

  const scheda = page.locator('#pk-admin-spot');
  await expect(scheda).toBeVisible();
  await expect(scheda).toContainText('sola lettura');
  await expect(scheda.locator('input, select, textarea')).toHaveCount(0);
  await expect(scheda.getByRole('button', { name: 'Salva', exact: true })).toHaveCount(0);
});

test('un tutorial corretto dal pannello compare nel catalogo con il segno «locale»', async ({
  page,
}) => {
  // La seconda regola — niente si finge ufficiale — valeva per gli spot e non
  // per i tutorial, da quando il pannello sa correggere anche loro.
  await pannello(page);
  await page.locator('#pk-admin').getByRole('button', { name: 'Tutorial', exact: true }).click();
  await page.locator('#pk-admin .pk-item').first().click();

  const titolo = page.locator('#pk-admin-spot input').first();
  const prima = await titolo.inputValue();
  await titolo.fill(`${prima} (corretto)`);
  await page.locator('#pk-admin').getByRole('button', { name: 'Salva', exact: true }).click();
  await expect(page.getByText('Salvato su questo dispositivo')).toBeVisible();

  await page.locator('.pk-nav__tab[data-vai="#/tutorial"]').click();
  const riga = page.locator('#pk-tutorial .pk-item').filter({ hasText: '(corretto)' }).first();
  await expect(riga).toContainText('locale');
});

test('una foglia che il pannello non esponeva si cambia e arriva in CONFIG', async ({ page }) => {
  // `partenza.zoom` non era fra le undici impostazioni scritte a mano: adesso
  // c'è perché nessuno la scrive più a mano, si leggono le foglie di CONFIG.
  await pannello(page);
  const casella = page
    .locator('#pk-admin label')
    .filter({ hasText: 'partenza.zoom' })
    .locator('input');
  await expect(casella).toHaveValue('11');
  await casella.fill('9');
  await casella.blur();
  await expect(page.getByText('Applicato.')).toBeVisible();

  expect(await dentro(page, ({ CONFIG }) => CONFIG.partenza.zoom)).toBe(9);
});

test('un JSON storto viene rifiutato, e il valore di prima resta dov’era', async ({ page }) => {
  await pannello(page);
  await apriPrima(page, 'EUR Laghetto');

  const foto = page
    .locator('#pk-admin-spot label')
    .filter({ hasText: 'photos' })
    .locator('textarea');
  const prima = await foto.inputValue();
  expect(prima.startsWith('[')).toBe(true);

  await foto.fill('["questa lista non si chiude"');
  await page.locator('#pk-admin').getByRole('button', { name: 'Salva', exact: true }).click();
  await expect(page.getByText('Non è JSON valido')).toBeVisible();

  const salvato = await dentro(page, ({ admin, dati }) => {
    const voce = dati.spot().find((v) => v.name.startsWith('EUR Laghetto'));
    return { photos: voce.photos, modificati: admin.conteggi('spot').modificati };
  });
  expect(Array.isArray(salvato.photos)).toBe(true);
  expect(salvato.modificati).toBe(0);
});

test('l’ispettore aggiunge una chiave che lo schema non conosce', async ({ page }) => {
  await pannello(page);
  await apriPrima(page, 'EUR Laghetto');

  await page.locator('#pk-admin-spot').getByRole('button', { name: 'Aggiungi una chiave' }).click();
  await page.getByRole('textbox', { name: 'Aggiungi una chiave' }).fill('appiglio_bagnato');
  await page.locator('.pk-modal__box').getByRole('button', { name: 'Aggiungi una chiave' }).click();

  const nuova = page
    .locator('#pk-admin-spot label')
    .filter({ hasText: 'appiglio_bagnato' })
    .locator('input');
  await expect(nuova).toBeVisible();
  await expect(
    page.locator('#pk-admin-spot').getByText('l’app non la conosce').first()
  ).toBeVisible();
  await nuova.fill('con la pioggia scivola');

  // Il riquadro delle conseguenze dice che quella chiave non la legge nessuno,
  // e lascia salvare lo stesso: il pannello avvisa, non impedisce.
  await page.locator('#pk-admin').getByRole('button', { name: 'Salva', exact: true }).click();
  await expect(page.getByText('Questa chiave non la legge nessuna schermata')).toBeVisible();
  await page.locator('.pk-modal__box').getByRole('button', { name: 'Salva lo stesso' }).click();
  await expect(page.getByText('Salvato su questo dispositivo')).toBeVisible();

  const esportato = await dentro(page, ({ admin }) => JSON.stringify(admin.esporta().modificati));
  expect(esportato).toContain('appiglio_bagnato');
  expect(esportato).toContain('con la pioggia scivola');
});

test('il riquadro delle conseguenze compare solo per quello che è cambiato', async ({ page }) => {
  // «EUR Laghetto» è uno dei 26 verificati dalla famiglia. Avvisare che
  // «verified messo a mano vale solo su questo telefono» a chi ha corretto una
  // virgola è un riquadro da chiudere ogni volta, e un avviso che compare
  // sempre è un avviso che non si legge più.
  await pannello(page);
  await apriPrima(page, 'EUR Laghetto');

  const nome = page.locator('#pk-admin-spot input').first();
  await nome.fill('EUR Laghetto (virgola corretta)');
  await page.locator('#pk-admin').getByRole('button', { name: 'Salva', exact: true }).click();
  await expect(page.getByText('Salvato su questo dispositivo')).toBeVisible();
  await expect(page.locator('.pk-modal__box')).toHaveCount(0);

  // Toccando davvero lo stato, invece, lo dice: «revisionato» non è uno stato
  // che l'app conosce, e il distintivo direbbe «community».
  await apriPrima(page, 'EUR Laghetto');
  const stato = page
    .locator('#pk-admin-spot label')
    .filter({ hasText: /^status/ })
    .locator('select');
  await stato.selectOption('\u0000altro');
  await page.locator('#pk-admin-spot label').filter({ hasText: /^status/ }).locator('input').fill('revisionato');
  await page.locator('#pk-admin').getByRole('button', { name: 'Salva', exact: true }).click();
  await expect(page.getByText('non è uno stato che l’app conosce')).toBeVisible();
  await page.locator('.pk-modal__box').getByRole('button', { name: 'Salva lo stesso' }).click();
  await expect(page.getByText('Salvato su questo dispositivo')).toBeVisible();
});

test('«da rivedere» senza toccare niente arriva lo stesso nel file da rivedere', async ({
  page,
}) => {
  await pannello(page);
  await apriPrima(page, 'EUR Laghetto');

  await page.getByLabel('Perché va rivista').fill('la foto non è di questo posto');
  await page.locator('#pk-admin').getByRole('button', { name: 'Salva', exact: true }).click();
  await expect(page.getByText('Salvato su questo dispositivo')).toBeVisible();
  await expect(page.locator('#pk-admin-conti')).toContainText('Da rivedere: 1');

  const file = await dentro(page, ({ admin, dati }) => ({
    tutto: JSON.stringify(admin.esporta()),
    repository: admin.esportaPerIlRepository(dati.spotDelFile()),
  }));
  expect(file.tutto).toContain('la foto non è di questo posto');

  // Nel file per il repository il motivo sta **accanto allo spot**, in
  // `da_rivedere_perche`. Il piano diceva di tenerlo fuori dal record; il file
  // si chiama «spot da rivedere» e chi lo apre deve leggere il motivo lì, non
  // in un elenco a parte da incrociare a mano. È un campo che nessuna
  // schermata legge: non finisce nei dati dell'app, finisce sotto gli occhi di
  // chi rivede.
  const toccato = (file.repository.da_rivedere || []).find(
    (s) => s.da_rivedere_perche === 'la foto non è di questo posto'
  );
  expect(toccato, 'il motivo non è arrivato accanto allo spot').toBeTruthy();
  expect(toccato.status_cambiato_in_locale).toBeUndefined();
});

test('il magazzino mostra quello che c’è, e rifiuta le due chiavi del pannello', async ({
  page,
}) => {
  // `mappa.vista` è l'ultima vista della mappa: dove è stata una persona. Si
  // deve poter vedere — è il solo modo di controllare la promessa «resta sul
  // dispositivo» — e non deve entrare in nessun file esportato.
  await pannello(page);
  await dentro(page, ({ store }) => store.scrivi('mappa.vista', { lat: 41.9, lng: 12.48, zoom: 14 }));

  await page.locator('#pk-admin summary').filter({ hasText: 'Magazzino' }).click();
  const magazzino = page.locator('#pk-admin details[data-sezione="magazzino"]');
  await expect(magazzino).toContainText('mappa.vista');
  await expect(magazzino).toContainText('admin.attiva');
  await expect(magazzino).toContainText('Questa chiave la usa il pannello');

  const esportato = await dentro(page, ({ admin }) => JSON.stringify(admin.esporta()));
  expect(esportato).not.toContain('mappa.vista');

  expect(
    await dentro(page, ({ admin }) => [
      admin.chiaveMagazzinoBloccata('admin.attiva'),
      admin.chiaveMagazzinoBloccata('admin.sovrascritture'),
      admin.chiaveMagazzinoBloccata('tema'),
    ])
  ).toEqual([true, true, false]);
});

test('salvare dal pannello non fa partire nessuna richiesta di rete', async ({ page }) => {
  await pannello(page);
  await apriPrima(page, 'EUR Laghetto');

  const partite = [];
  page.on('request', (richiesta) => partite.push(richiesta.url()));

  const nome = page.locator('#pk-admin-spot input').first();
  await nome.fill('EUR Laghetto (senza rete)');
  await page.locator('#pk-admin').getByRole('button', { name: 'Salva', exact: true }).click();
  await expect(page.getByText('Salvato su questo dispositivo')).toBeVisible();
  await dentro(page, ({ admin }) => JSON.stringify(admin.esporta()));
  await page.waitForTimeout(300);

  // Le tessere della mappa non contano: quelle le chiede la mappa, non il
  // pannello, e sono immagini pubbliche senza niente di personale dentro.
  const nostre = partite.filter((u) => !u.includes('tile') && !u.startsWith('data:'));
  expect(nostre, `sono partite: ${nostre.join(', ')}`).toEqual([]);
});

test('salvare non riporta in cima, e le sezioni chiuse restano chiuse', async ({ page }) => {
  await pannello(page);
  await apriPrima(page, 'EUR Laghetto');

  // Si chiude Configurazione: deve restare chiusa anche dopo il ridisegno.
  await page.locator('#pk-admin summary').filter({ hasText: 'Configurazione' }).click();
  await expect(page.locator('#pk-admin details[data-sezione="config"]')).not.toHaveAttribute(
    'open',
    ''
  );

  await page.locator('#pk-admin').evaluate((nodo) => {
    nodo.scrollTop = 200;
  });
  const prima = await page.locator('#pk-admin').evaluate((nodo) => nodo.scrollTop);
  expect(prima).toBeGreaterThan(0);

  const nome = page.locator('#pk-admin-spot input').first();
  await nome.fill('EUR Laghetto (non saltare in cima)');
  // `dispatchEvent` e non `click`: Playwright, prima di cliccare, porta il
  // pulsante in vista e sposta lo scorrimento — sarebbe la prova a muovere
  // quello che la prova vuole misurare.
  await page
    .locator('#pk-admin')
    .getByRole('button', { name: 'Salva', exact: true })
    .dispatchEvent('click');
  await expect(page.getByText('Salvato su questo dispositivo')).toBeVisible();

  const dopo = await page.locator('#pk-admin').evaluate((nodo) => nodo.scrollTop);
  expect(dopo).toBe(prima);
  await expect(page.locator('#pk-admin details[data-sezione="config"]')).not.toHaveAttribute(
    'open',
    ''
  );
});
