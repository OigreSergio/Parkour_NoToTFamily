/* La mappa: i colori del masterplan, i gomitoli, le tessere tinte, i gesti.
 *
 * I gesti si provano sul motore vero (app/public/js/map.js) montato in una
 * tela di misura nota, con eventi di puntatore costruiti a mano: è l'unico
 * modo per dire con certezza «questo trascinamento lento non deve aprire
 * niente», che a colpi di click sul telefono emulato resterebbe un forse.
 */

import { expect, test } from '@playwright/test';

/**
 * Una tessera di un grigio-azzurro: è il colore medio di una mappa disegnata,
 * ed è la prova giusta per un filtro — sul bianco puro non si vedrebbe niente,
 * perché il bianco resta bianco.
 */
const TESSERA_FINTA = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mOomLblPwAGDgLCyvs2hAAAAABJRU5ErkJggg==',
  'base64'
);

/** Il colore che occupa più tela: con una tessera piena, è la tessera. */
function dominante(page) {
  return page.locator('.pk-map__canvas').evaluate((tela) => {
    const d = tela.getContext('2d').getImageData(0, 0, tela.width, tela.height).data;
    const conti = new Map();
    for (let i = 0; i < d.length; i += 4 * 53) {
      const chiave = `${d[i] >> 3},${d[i + 1] >> 3},${d[i + 2] >> 3}`;
      conti.set(chiave, (conti.get(chiave) || 0) + 1);
    }
    const [vincitore] = [...conti.entries()].sort((a, b) => b[1] - a[1])[0];
    const [r, g, b] = vincitore.split(',').map((n) => Number(n) * 8);
    return { r, g, b };
  });
}

/**
 * Il fondo chiaro di una mappa disegnata: serve alla prova del tema scuro,
 * perché è il chiaro che deve diventare notte. Un grigio medio, ribaltato,
 * resterebbe un grigio medio.
 */
const TESSERA_CHIARA = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP4DwQACfsD/Wj6HMwAAAAASUVORK5CYII=',
  'base64'
);

function serviTessere(contesto, corpo) {
  return contesto.route(/tile\.openstreetmap\.org|arcgisonline\.com/, (rotta) =>
    rotta.fulfill({
      status: 200,
      contentType: 'image/png',
      headers: { 'access-control-allow-origin': '*' },
      body: corpo,
    })
  );
}

async function attendiPronta(page) {
  await page.goto('/index.html');
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 20_000 });
}

/**
 * Monta il motore della mappa da solo e gli parla con eventi di puntatore.
 * `azione` gira dentro la pagina e riceve {mappa, tela, gesti}.
 */
function conMotore(page, azione) {
  return page.evaluate(async (sorgenteAzione) => {
    const { creaMappa } = await import('./js/map.js');

    const scatola = document.createElement('div');
    scatola.style.cssText = 'position:fixed;left:0;top:0;width:360px;height:640px;z-index:-1';
    document.body.append(scatola);

    const mappa = creaMappa(scatola);
    const tela = scatola.querySelector('canvas');
    const disegnato = () =>
      new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

    const evento = (tipo, id, x, y) =>
      tela.dispatchEvent(
        new PointerEvent(tipo, {
          pointerId: id,
          clientX: x,
          clientY: y,
          bubbles: true,
          pointerType: 'touch',
        })
      );

    const gesti = {
      tocca: async (x, y) => {
        evento('pointerdown', 1, x, y);
        evento('pointerup', 1, x, y);
        await disegnato();
      },
      trascinaPiano: async (x, y, passi) => {
        evento('pointerdown', 1, x, y);
        for (let i = 1; i <= passi; i++) evento('pointermove', 1, x + i, y + i);
        evento('pointerup', 1, x + passi, y + passi);
        await disegnato();
      },
      pizzica: async (da, a) => {
        evento('pointerdown', 1, da[0].x, da[0].y);
        evento('pointerdown', 2, da[1].x, da[1].y);
        evento('pointermove', 1, a[0].x, a[0].y);
        evento('pointermove', 2, a[1].x, a[1].y);
        evento('pointerup', 1, a[0].x, a[0].y);
        evento('pointerup', 2, a[1].x, a[1].y);
        await disegnato();
      },
    };

    const risultato = await new Function('return ' + sorgenteAzione)()({
      mappa,
      tela,
      gesti,
      disegnato,
    });
    mappa.distruggi();
    scatola.remove();
    return risultato;
  }, azione.toString());
}

test('gli spilli hanno i colori del masterplan, e il gomitolo il numero', async ({ page }) => {
  await attendiPronta(page);

  const esito = await conMotore(page, async ({ mappa, disegnato }) => {
    // Tre spot distanti fra loro: tre spilli distinti.
    mappa.vai({ lat: 41.9, lng: 12.48, zoom: 14 });
    mappa.mostraSpot([
      { id: 'v', name: 'verificato', lat: 41.902, lng: 12.476, status: 'verified' },
      { id: 'c', name: 'community', lat: 41.898, lng: 12.484, status: 'community' },
      { id: 'a', name: 'attesa', lat: 41.9045, lng: 12.4855, status: 'pending' },
    ]);
    await disegnato();
    const tela = document.querySelector('div[style*="640px"] canvas');
    const ctx = tela.getContext('2d');
    const conta = () => {
      const d = ctx.getImageData(0, 0, tela.width, tela.height).data;
      const vicino = (i, r, g, b) =>
        Math.abs(d[i] - r) < 22 && Math.abs(d[i + 1] - g) < 22 && Math.abs(d[i + 2] - b) < 22;
      const q = { verde: 0, blu: 0, ambra: 0, filo: 0 };
      for (let i = 0; i < d.length; i += 4) {
        if (vicino(i, 0x63, 0x86, 0x4a)) q.verde++;
        else if (vicino(i, 0x6f, 0x9c, 0xb8)) q.blu++;
        else if (vicino(i, 0xb9, 0x7a, 0x0e)) q.ambra++;
        else if (vicino(i, 0xc2, 0x6a, 0x52)) q.filo++;
      }
      return q;
    };
    const separati = conta();

    // Lo stesso spot scelto: passa a `filo`.
    mappa.seleziona('v');
    await disegnato();
    const conScelto = conta();

    // Gli stessi tre spot a zoom basso: si raccolgono in un gomitolo.
    mappa.seleziona(null);
    mappa.vai({ lat: 41.9, lng: 12.48, zoom: 9 });
    await disegnato();
    const quadro = mappa.quadro;

    return { separati, conScelto, quadro };
  });

  expect(esito.separati.verde).toBeGreaterThan(30);
  expect(esito.separati.blu).toBeGreaterThan(30);
  expect(esito.separati.ambra).toBeGreaterThan(30);
  expect(esito.separati.filo).toBe(0);

  // Scelto uno spot, compare il colore `filo` e il verde di quello scelto se ne va.
  expect(esito.conScelto.filo).toBeGreaterThan(30);

  // A zoom basso i tre non spariscono: stanno in un gomitolo che li conta.
  expect(esito.quadro.gomitoli).toBe(1);
  expect(esito.quadro.spilli + esito.quadro.raccolti).toBe(3);
});

test('nessuno spot sparisce: quello che è nel riquadro è disegnato o contato', async ({ page }) => {
  await attendiPronta(page);

  const esito = await page.evaluate(async () => {
    const dati = await import('./js/data.js');
    const { creaMappa } = await import('./js/map.js');
    const scatola = document.createElement('div');
    scatola.style.cssText = 'position:fixed;left:0;top:0;width:360px;height:640px;z-index:-1';
    document.body.append(scatola);
    const mappa = creaMappa(scatola);
    // Tutto il Lazio in uno schermo: è il caso in cui prima si sfoltiva.
    mappa.vai({ lat: 41.9, lng: 12.5, zoom: 8 });
    const riquadro = mappa.riquadro();
    const dentro = dati.nelRiquadro(riquadro);
    mappa.mostraSpot(dentro);
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    const quadro = mappa.quadro;
    mappa.distruggi();
    scatola.remove();
    return { dentro: dentro.length, mostrati: quadro.spilli + quadro.raccolti, gomitoli: quadro.gomitoli };
  });

  // A questo zoom, in 360x640, il Lazio ne porta dentro qualche decina: sono
  // già molti più di quanti ne stiano senza accavallarsi.
  expect(esito.dentro).toBeGreaterThan(50);
  expect(esito.mostrati).toBe(esito.dentro);
  expect(esito.gomitoli).toBeGreaterThan(0);
});

test('un trascinamento lento sposta la mappa e non sceglie niente', async ({ page }) => {
  await attendiPronta(page);

  const esito = await conMotore(page, async ({ mappa, gesti }) => {
    mappa.vai({ lat: 41.9, lng: 12.48, zoom: 16 });
    // Uno spot esattamente al centro della tela: 180, 320.
    mappa.mostraSpot([{ id: 'x', name: 'x', lat: 41.9, lng: 12.48, status: 'verified' }]);
    const scelte = [];
    mappa.su('selezione', (v) => scelte.push(v ? v.id : null));
    const primaLng = mappa.centro.lng;

    // Venti passi da un pixel: prima veniva letto come un tocco fermo.
    await gesti.trascinaPiano(180, 310, 20);

    return { scelte, spostata: Math.abs(mappa.centro.lng - primaLng) > 1e-6 };
  });

  expect(esito.spostata).toBe(true);
  expect(esito.scelte).toEqual([]);
});

test('due tocchi su spilli diversi scelgono, non zoomano', async ({ page }) => {
  await attendiPronta(page);

  const esito = await conMotore(page, async ({ mappa, gesti, disegnato }) => {
    mappa.vai({ lat: 41.9, lng: 12.48, zoom: 16 });
    mappa.mostraSpot([
      { id: 'uno', name: 'uno', lat: 41.9, lng: 12.48, status: 'verified' },
      { id: 'due', name: 'due', lat: 41.9, lng: 12.4815, status: 'community' },
    ]);
    await disegnato();
    const scelte = [];
    mappa.su('selezione', (v) => scelte.push(v ? v.id : null));
    const zoomPrima = mappa.zoom;

    const uno = mappa.aSchermo({ lat: 41.9, lng: 12.48 });
    const due = mappa.aSchermo({ lat: 41.9, lng: 12.4815 });
    await gesti.tocca(uno.x, uno.y - 11);
    await gesti.tocca(due.x, due.y - 11);

    return { scelte, zoomPrima, zoomDopo: mappa.zoom };
  });

  expect(esito.scelte).toEqual(['uno', 'due']);
  expect(esito.zoomDopo).toBe(esito.zoomPrima);
});

test('due tocchi nello stesso punto avvicinano', async ({ page }) => {
  await attendiPronta(page);

  const esito = await conMotore(page, async ({ mappa, gesti }) => {
    mappa.vai({ lat: 41.9, lng: 12.48, zoom: 12 });
    mappa.mostraSpot([]);
    const zoomPrima = mappa.zoom;
    await gesti.tocca(180, 320);
    await gesti.tocca(181, 321);
    return { zoomPrima, zoomDopo: mappa.zoom };
  });

  expect(esito.zoomDopo).toBeGreaterThan(esito.zoomPrima);
});

test('il pizzico avvicina e trascina insieme', async ({ page }) => {
  await attendiPronta(page);

  const esito = await conMotore(page, async ({ mappa, gesti }) => {
    mappa.vai({ lat: 41.9, lng: 12.48, zoom: 13 });
    mappa.mostraSpot([]);
    const prima = { ...mappa.centro, zoom: mappa.zoom };
    // Due dita che si allargano e insieme scendono: zoom più vicino e mappa
    // che scorre verso il basso.
    await gesti.pizzica(
      [
        { x: 150, y: 300 },
        { x: 210, y: 340 },
      ],
      [
        { x: 120, y: 380 },
        { x: 240, y: 460 },
      ]
    );
    return {
      zoomCresciuto: mappa.zoom > prima.zoom,
      centroSpostato: Math.abs(mappa.centro.lat - prima.lat) > 1e-6,
    };
  });

  expect(esito.zoomCresciuto).toBe(true);
  expect(esito.centroSpostato).toBe(true);
});

test('le tessere della mappa si scaldano verso il lino, il satellite resta vero', async ({
  page,
  context,
}) => {
  await serviTessere(context, TESSERA_FINTA);
  await attendiPronta(page);

  // La stessa tessera, servita a tutte e due le sorgenti. Sulla mappa passa
  // dal filtro, sul satellite no: il confronto è la prova.
  const calore = (c) => c.r - c.b;
  await expect.poll(() => dominante(page).then(calore), { timeout: 15_000 }).toBeGreaterThan(-45);
  const conFiltro = await dominante(page);

  await page.locator('.pk-map__tool[aria-label="Cambia sfondo"]').click();
  await expect.poll(() => dominante(page).then(calore), { timeout: 15_000 }).toBeLessThan(-45);
  const crudo = await dominante(page);

  // Il filtro scalda: sulla mappa il rosso guadagna sul blu di almeno venti
  // livelli rispetto alla tessera cruda.
  expect(calore(conFiltro) - calore(crudo)).toBeGreaterThan(20);
});

test('al buio la mappa è scura: niente lampada in faccia', async ({ page, context }) => {
  await serviTessere(context, TESSERA_CHIARA);
  await attendiPronta(page);
  await expect.poll(() => dominante(page).then((c) => c.r), { timeout: 15_000 }).toBeGreaterThan(220);

  // Si passa al tema scuro come farebbe una persona dalla schermata "Tu": il
  // motore se ne accorge da solo e ridisegna, ribaltando le tessere. Il fondo
  // chiaro della mappa diventa notte.
  await page.evaluate(() => {
    document.documentElement.dataset.tema = 'scuro';
  });
  await expect.poll(() => dominante(page).then((c) => c.r), { timeout: 15_000 }).toBeLessThan(90);
});
