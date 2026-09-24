/* Il modello delle sovrascritture: quello che può rompere tutto.
 *
 * Non passa dall'interfaccia: chiama i moduli dalla pagina, perché è lì che il
 * magazzino del dispositivo esiste davvero. Ogni prova qui dentro corrisponde a
 * una trappola trovata leggendo il codice, e ognuna cadeva prima della
 * correzione — non sono prove scritte sopra a quello che il codice già faceva.
 */

import { expect, test } from '@playwright/test';

async function pannelloAcceso(page) {
  await page.goto('/index.html');
  await expect(page.locator('body[data-pronta="1"]')).toBeAttached({ timeout: 20_000 });
  await page.evaluate(async () => {
    const admin = await import('./js/admin.js');
    await admin.accendi(true);
  });
}

/** Esegue del codice con `admin` e `dati` già importati. */
function dentro(page, azione) {
  return page.evaluate(async (sorgente) => {
    const admin = await import('./js/admin.js');
    const dati = await import('./js/data.js');
    const { CONFIG } = await import('./js/config.js');
    return new Function('return ' + sorgente)()({ admin, dati, CONFIG });
  }, azione.toString());
}

test('un campo che lo schema non conosce si salva invece di sparire', async ({ page }) => {
  // `ripulisci` scartava in silenzio tutto ciò che non stava nella tabella di
  // otto campi: l'app diceva «salvato» e perdeva il resto.
  await pannelloAcceso(page);
  const esito = await dentro(page, async ({ admin, dati }) => {
    const primo = dati.spot()[0];
    await admin.salva('spot', primo.id, { name: primo.name, difficolta_mia: 'alta' });
    dati.riapplica();
    const dopo = dati.spotPerId(primo.id);
    return { salvato: dopo.difficolta_mia, nelFile: admin.esporta().modificati[primo.id] };
  });
  expect(esito.salvato).toBe('alta');
  expect(esito.nelFile.difficolta_mia).toBe('alta');
});

test('i campi che l’app si attacca da sé non finiscono nelle modifiche', async ({ page }) => {
  // `cerca`, `locale` e `metri` non sono dati: sono cose che l'app aggiunge
  // agli oggetti mentre lavora. Da quando i campi sconosciuti si conservano,
  // senza una regola finirebbero dritti nell'esportazione.
  await pannelloAcceso(page);
  const modifica = await dentro(page, async ({ admin, dati }) => {
    const primo = dati.spot()[0];
    await admin.salva('spot', primo.id, {
      name: 'Con roba attaccata',
      cerca: 'non deve entrare',
      locale: true,
      metri: 42,
    });
    return admin.esporta().modificati[primo.id];
  });
  expect(modifica.name).toBe('Con roba attaccata');
  expect(modifica).not.toHaveProperty('cerca');
  expect(modifica).not.toHaveProperty('locale');
  expect(modifica).not.toHaveProperty('metri');
});

test('due spot nuovi con lo stesso nome non condividono l’identificativo', async ({ page }) => {
  // L'identificativo si costruiva da `nuovi.length + 1`: cancellato uno e
  // creato un altro con lo stesso nome, i due avevano lo stesso id.
  await pannelloAcceso(page);
  const id = await dentro(page, async ({ admin }) => {
    const primo = await admin.crea('spot', { name: 'Muretto uguale' });
    await admin.cancella('spot', primo.id);
    const secondo = await admin.crea('spot', { name: 'Muretto uguale' });
    const terzo = await admin.crea('spot', { name: 'Muretto uguale' });
    return [primo.id, secondo.id, terzo.id];
  });
  expect(new Set(id).size).toBe(3);
});

test('un’impostazione svuotata torna al valore del file, senza riavviare', async ({ page }) => {
  // `impostaConfig(via, '')` toglieva la voce ma lasciava in CONFIG il valore
  // provato: «torna com'era» funzionava solo dopo un riavvio.
  await pannelloAcceso(page);
  const zoom = await dentro(page, async ({ admin, CONFIG }) => {
    const prima = CONFIG.partenza.zoom;
    await admin.impostaConfig('partenza.zoom', 3);
    const durante = CONFIG.partenza.zoom;
    await admin.impostaConfig('partenza.zoom', '');
    return { prima, durante, dopo: CONFIG.partenza.zoom };
  });
  expect(zoom.durante).toBe(3);
  expect(zoom.dopo).toBe(zoom.prima);
});

test('azzerare riporta la configurazione com’era nel file', async ({ page }) => {
  await pannelloAcceso(page);
  const esito = await dentro(page, async ({ admin, CONFIG }) => {
    const prima = CONFIG.cellaGomitolo;
    await admin.impostaConfig('cellaGomitolo', 999);
    const durante = CONFIG.cellaGomitolo;
    await admin.azzera();
    return { prima, durante, dopo: CONFIG.cellaGomitolo };
  });
  expect(esito.durante).toBe(999);
  expect(esito.dopo).toBe(esito.prima);
});

test('una chiave segreta viene rifiutata in qualunque campo, non solo nella sua casella', async ({
  page,
}) => {
  // Bastava incollare un token nella descrizione di uno spot per aggirare il
  // controllo, che stava su una casella sola dell'interfaccia.
  await pannelloAcceso(page);
  const esito = await dentro(page, async ({ admin, dati }) => {
    const primo = dati.spot()[0];
    const prova = async (campi) => {
      try {
        await admin.salva('spot', primo.id, campi);
        return 'passata';
      } catch (errore) {
        return errore.code || errore.name;
      }
    };
    return {
      descrizione: await prova({ description: 'ecco: sb_secret_abcdef123456' }),
      nome: await prova({ name: 'eyJhbGciOi.eyJzdWIiOi.Zm9vYmFy' }),
      normale: await prova({ description: 'un muretto lungo' }),
      pubblicabile: await prova({ description: 'sb_publishable_ok' }),
    };
  });
  expect(esito.descrizione).toBe('secret_refused');
  expect(esito.nome).toBe('secret_refused');
  expect(esito.normale).toBe('passata');
  expect(esito.pubblicabile).toBe('passata');
});

test('un file importato non può puntare l’app a un motore scelto da altri', async ({ page }) => {
  // `importa` applicava qualunque percorso di configurazione. Con `motore`
  // impostato, le ricerche — e la posizione di chi le fa — partivano verso
  // l'indirizzo scritto nel file.
  await pannelloAcceso(page);
  const esito = await dentro(page, async ({ admin, CONFIG }) => {
    const prima = CONFIG.motore;
    const conto = await admin.importa({
      formato: 'pkfamily/sovrascritture',
      versione: 2,
      collezioni: { spot: { modificati: {}, nuovi: [], cancellati: [] } },
      config: { motore: 'https://qualcuno-altrove.example/api', 'partenza.zoom': 9 },
    });
    return { prima, dopo: CONFIG.motore, scartate: conto.scartate, zoom: CONFIG.partenza.zoom };
  });
  expect(esito.dopo).toBe(esito.prima);
  expect(esito.scartate).toBe(1);
  // Le impostazioni che il pannello espone davvero passano.
  expect(esito.zoom).toBe(9);
});

test('un file con una chiave segreta dentro viene rifiutato per intero', async ({ page }) => {
  await pannelloAcceso(page);
  const esito = await dentro(page, async ({ admin, dati }) => {
    const primo = dati.spot()[0];
    let codice = 'passata';
    try {
      await admin.importa({
        formato: 'pkfamily/sovrascritture',
        versione: 2,
        collezioni: {
          spot: { modificati: { [primo.id]: { description: 'sb_secret_nascosto_qui' } }, nuovi: [], cancellati: [] },
        },
        config: {},
      });
    } catch (errore) {
      codice = errore.code || errore.name;
    }
    return { codice, modificati: admin.conteggi('spot').modificati };
  });
  expect(esito.codice).toBe('secret_refused');
  // E niente è stato applicato a metà.
  expect(esito.modificati).toBe(0);
});

test('un file di formato vecchio si legge ancora, e quello nuovo resta leggibile dal vecchio', async ({
  page,
}) => {
  // Le copie già consegnate (APK, beta, bundle del Mac) leggono la versione 1:
  // un formato consegnato è un contratto.
  await pannelloAcceso(page);
  const esito = await dentro(page, async ({ admin, dati }) => {
    const primo = dati.spot()[0];
    const conto = await admin.importa({
      formato: 'pkfamily/sovrascritture',
      versione: 1,
      modificati: { [primo.id]: { name: 'Nome da un file vecchio' } },
      nuovi: [],
      cancellati: [],
      config: {},
    });
    dati.riapplica();
    const file = admin.esporta();
    return {
      conto: conto.modificati,
      migrato: conto.migrato,
      nome: dati.spotPerId(primo.id).name,
      versione: file.versione,
      rispecchiato: Boolean(file.modificati[primo.id]),
      perCollezione: Boolean(file.collezioni.spot.modificati[primo.id]),
    };
  });
  expect(esito.conto).toBe(1);
  expect(esito.migrato).toBe(true);
  expect(esito.nome).toBe('Nome da un file vecchio');
  expect(esito.versione).toBe(2);
  expect(esito.rispecchiato).toBe(true);
  expect(esito.perCollezione).toBe(true);
});

test('l’esportazione per il repository non inventa valutazioni', async ({ page }) => {
  // Nessuno dei 1.706 spot ha `rating`: riemetterlo a zero vorrebbe dire
  // scrivere nella fonte un dato che non è mai esistito.
  await pannelloAcceso(page);
  const voce = await dentro(page, async ({ admin, dati }) => {
    const primo = dati.spot()[0];
    await admin.salva('spot', primo.id, { status: 'verified' });
    const file = admin.esportaPerIlRepository(dati.spotDelFile(), { source: 'prova', count: 1 });
    return file.da_rivedere.find((v) => v.id === primo.id);
  });
  expect(voce).not.toHaveProperty('rating');
  expect(voce).not.toHaveProperty('ratingCount');
  // E dice che lo stato è stato toccato a mano, invece di lavarlo.
  expect(voce.campi_toccati).toContain('status');
  expect(voce.status_cambiato_in_locale).toBe(true);
});

test('un tutorial si corregge, e nel catalogo si vede che è locale', async ({ page }) => {
  // Prima i tutorial non si toccavano: la regola «niente si finge verificato»
  // valeva per gli spot e non per loro.
  await pannelloAcceso(page);
  const esito = await dentro(page, async ({ admin, dati }) => {
    const primo = dati.tutorial()[0];
    await admin.salva('tutorial', primo.id, { title: 'Titolo corretto in locale' });
    dati.riapplica();
    const dopo = dati.tutorial().find((v) => v.id === primo.id);
    return { titolo: dopo.title, locale: dopo.locale, quanti: dati.tutorial().length };
  });
  expect(esito.titolo).toBe('Titolo corretto in locale');
  expect(esito.locale).toBe(true);
  expect(esito.quanti).toBe(124);
});

test('riportare al file un campo solo lascia corretti gli altri', async ({ page }) => {
  await pannelloAcceso(page);
  const esito = await dentro(page, async ({ admin, dati }) => {
    const primo = dati.spot()[0];
    const originale = primo.name;
    await admin.salva('spot', primo.id, { name: 'Nome cambiato', crowd: 'affollato' });
    await admin.ripristinaCampo('spot', primo.id, 'name');
    dati.riapplica();
    const dopo = dati.spotPerId(primo.id);
    return { originale, nome: dopo.name, crowd: dopo.crowd };
  });
  expect(esito.nome).toBe(esito.originale);
  expect(esito.crowd).toBe('affollato');
});

test('lo schema si deduce dalle collezioni registrate', async ({ page }) => {
  await pannelloAcceso(page);
  const schema = await dentro(page, async ({ admin }) => ({
    spot: admin.campiDi('spot').map((c) => c.nome),
    tutorial: admin.campiDi('tutorial').map((c) => c.nome),
    stato: admin.campiDi('spot').find((c) => c.nome === 'status'),
    id: admin.campiDi('spot').find((c) => c.nome === 'id'),
    config: admin.campiConfig().length,
  }));
  // Dodici campi, non gli otto scritti a mano di prima.
  expect(schema.spot).toEqual(
    expect.arrayContaining(['id', 'name', 'lat', 'lng', 'status', 'description', 'level', 'crowd', 'photos', 'fountain', 'video', 'videoPoster'])
  );
  expect(schema.tutorial).toEqual(expect.arrayContaining(['title', 'category', 'trick', 'channel']));
  // `pending` non compare in nessuno dei 1.706 spot, ma è lo stato dei nuovi.
  expect(schema.stato.valori).toContain('pending');
  expect(schema.id.soloLettura).toBe(true);
  // Ventiquattro foglie di configurazione, non le undici esposte prima.
  expect(schema.config).toBe(24);
});
