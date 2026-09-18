/* PkFAMILY — l'avvio dell'applicazione.
 *
 * Ordine delle cose, e il perché: prima il tema e la lingua (altrimenti
 * l'app lampeggia), poi i dati che porta con sé, poi le schermate, e solo
 * alla fine il service worker — che serve dalla seconda apertura in avanti e
 * non deve rallentare la prima.
 *
 * Non c'è nessuna chiamata di rete obbligatoria in questo percorso: se il
 * telefono è in modalità aereo l'app si apre uguale.
 */

import * as dati from './data.js';
import * as i18n from './i18n.js';
import { leggi, scrivi } from './store.js';
import { el, svuota } from './ui.js';

import * as schermataMappa from './screens/map.js';
import * as schermataSpot from './screens/spots.js';
import * as schermataDettaglio from './screens/detail.js';
import * as schermataTutorial from './screens/tutorials.js';
import * as schermataTu from './screens/you.js';

const SCHERMATE = {
  mappa: schermataMappa,
  spot: schermataSpot,
  dettaglio: schermataDettaglio,
  tutorial: schermataTutorial,
  tu: schermataTu,
};

const contesto = {
  mappa: null,
  invitoInstallazione: null,
  aggiornamentoPronto: false,
  vaiA(indirizzo) {
    if (location.hash === indirizzo) apri(indirizzo);
    else location.hash = indirizzo;
  },
  indietro() {
    if (history.length > 1) history.back();
    else contesto.vaiA('#/mappa');
  },
  applicaAggiornamento() {
    if (contesto.registrazione && contesto.registrazione.waiting) {
      contesto.registrazione.waiting.postMessage({ type: 'skip-waiting' });
    }
  },
};

/** Da "#/spot/abc" a {nome: 'dettaglio', parametri: {id: 'abc'}}. */
function rotta(indirizzo) {
  const pezzi = (indirizzo || '#/mappa').replace(/^#\/?/, '').split('/').filter(Boolean);
  const primo = pezzi[0] || 'mappa';
  const secondo = pezzi[1];

  if (primo === 'spot') return secondo ? { nome: 'dettaglio', parametri: { id: secondo } } : { nome: 'spot', parametri: {} };
  if (primo === 'mappa') return { nome: 'mappa', parametri: secondo ? { id: secondo } : {} };
  if (primo === 'tutorial') return { nome: 'tutorial', parametri: {} };
  if (primo === 'tu') return { nome: 'tu', parametri: {} };
  return { nome: 'mappa', parametri: {} };
}

const TAB_DI = { mappa: '#/mappa', spot: '#/spot', dettaglio: '#/spot', tutorial: '#/tutorial', tu: '#/tu' };

function mostraSchermata(nome) {
  for (const sezione of document.querySelectorAll('.pk-screen')) {
    sezione.dataset.attiva = sezione.dataset.schermata === nome ? '1' : '0';
  }
  for (const tab of document.querySelectorAll('.pk-nav__tab')) {
    const attiva = tab.dataset.vai === TAB_DI[nome];
    if (attiva) tab.setAttribute('aria-current', 'page');
    else tab.removeAttribute('aria-current');
  }
}

async function apri(indirizzo) {
  const { nome, parametri } = rotta(indirizzo);
  const schermata = SCHERMATE[nome];
  mostraSchermata(nome);

  if (schermata.entra) await schermata.entra(parametri);

  const intestazione = schermata.titolo ? schermata.titolo(parametri) : { titolo: 'PkFAMILY' };
  document.getElementById('pk-titolo').textContent = intestazione.titolo;
  document.getElementById('pk-sottotitolo').textContent = intestazione.sotto || '';
  document.getElementById('pk-indietro').hidden = !intestazione.indietro;
}

function collegaNavigazione() {
  for (const tab of document.querySelectorAll('.pk-nav__tab')) {
    tab.addEventListener('click', () => contesto.vaiA(tab.dataset.vai));
  }
  document.getElementById('pk-indietro').addEventListener('click', () => contesto.indietro());
  window.addEventListener('hashchange', () => apri(location.hash));
}

function seguiLaRete() {
  const aggiorna = () => {
    document.body.dataset.rete = navigator.onLine ? 'su' : 'giu';
  };
  window.addEventListener('online', aggiorna);
  window.addEventListener('offline', aggiorna);
  aggiorna();
}

function raccogliInvitoInstallazione() {
  window.addEventListener('beforeinstallprompt', (evento) => {
    evento.preventDefault();
    contesto.invitoInstallazione = evento;
    const bottone = document.getElementById('pk-installa');
    bottone.hidden = false;
    bottone.onclick = async () => {
      const invito = contesto.invitoInstallazione;
      if (!invito) return;
      contesto.invitoInstallazione = null;
      bottone.hidden = true;
      invito.prompt();
      await invito.userChoice;
    };
  });
}

async function registraServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  // Alla primissima apertura il worker prende il controllo appena installato:
  // è un cambio di controllore che NON deve ricaricare la pagina, altrimenti
  // l'app riparte da sola sotto le mani di chi la sta usando. Si ricarica solo
  // quando un worker nuovo sostituisce uno che c'era già.
  const controllavaGiaQualcuno = Boolean(navigator.serviceWorker.controller);
  try {
    const registrazione = await navigator.serviceWorker.register('sw.js', { scope: './' });
    contesto.registrazione = registrazione;

    registrazione.addEventListener('updatefound', () => {
      const nuovo = registrazione.installing;
      if (!nuovo) return;
      nuovo.addEventListener('statechange', () => {
        if (nuovo.state === 'installed' && navigator.serviceWorker.controller) {
          contesto.aggiornamentoPronto = true;
        }
      });
    });

    let ricaricato = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!controllavaGiaQualcuno || ricaricato) return;
      ricaricato = true;
      location.reload();
    });
  } catch {
    // Senza HTTPS (o senza localhost) il browser non registra nulla: l'app
    // resta usabile, ma non offline. Lo dice la schermata "Tu".
  }
}

function mostraErrore(errore) {
  const splash = document.getElementById('pk-splash');
  svuota(splash).append(
    el('div', { class: 'pk-card', style: 'max-width:320px' }, [
      el('h2', { testo: 'PkFAMILY' }),
      el('p', { testo: i18n.t('boot.failed') }),
      el('p', { class: 'pk-mono pk-small pk-muted', testo: String(errore && errore.message) }),
      el(
        'button',
        { class: 'pk-btn pk-btn--largo', onclick: () => location.reload() },
        [i18n.t('boot.retry')]
      ),
    ])
  );
}

async function avvia() {
  const tema = await leggi('tema', 'sistema');
  document.documentElement.dataset.tema = tema;

  const lingua = await leggi('lingua', null);
  await i18n.inizializza(lingua);
  i18n.applica(document);

  await dati.carica();

  document.getElementById('app').hidden = false;
  await schermataMappa.inizializza(contesto);
  await schermataSpot.inizializza(contesto);
  schermataDettaglio.inizializza(contesto);
  schermataTutorial.inizializza(contesto);
  schermataTu.inizializza(contesto);

  collegaNavigazione();
  seguiLaRete();
  raccogliInvitoInstallazione();

  if (!location.hash) location.hash = '#/mappa';
  await apri(location.hash);

  const splash = document.getElementById('pk-splash');
  splash.dataset.via = '1';
  setTimeout(() => splash.remove(), 300);

  // Da qui in poi niente è più necessario per usare l'app.
  registraServiceWorker();
  scrivi('ultimoAvvio', new Date().toISOString());
  document.body.dataset.pronta = '1';
}

avvia().catch((errore) => {
  console.error('PkFAMILY non è riuscita ad avviarsi', errore);
  mostraErrore(errore);
});
