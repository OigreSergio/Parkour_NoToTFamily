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

import * as admin from './admin.js';
import * as auth from './auth.js';
import { CONFIG } from './config.js';
import * as dati from './data.js';
import * as i18n from './i18n.js';
import { sembraSegreta } from './ispettore.js';
import { leggi, scrivi } from './store.js';
import { el, svuota } from './ui.js';

import * as schermataMappa from './screens/map.js';
import * as schermataSpot from './screens/spots.js';
import * as schermataDettaglio from './screens/detail.js';
import * as schermataTutorial from './screens/tutorials.js';
import * as schermataTu from './screens/you.js';
import * as schermataAdmin from './screens/admin.js';

const SCHERMATE = {
  mappa: schermataMappa,
  spot: schermataSpot,
  dettaglio: schermataDettaglio,
  tutorial: schermataTutorial,
  tu: schermataTu,
  admin: schermataAdmin,
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
  aggiornaFascia() {
    disegnaFascia();
  },
};

/** Da dove viene questa copia: sviluppo dal repository, oppure una beta. */
let costruzione = { canale: 'sviluppo', versione: '', quando: '' };

/** Che cosa scrive la fascia per ogni canale. `sviluppo` non ne ha: è il caso normale. */
const FASCE = new Map([
  ['beta', 'band.beta'],
  ['demo', 'band.demo'],
  ['python', 'band.python'],
  ['apk', 'band.apk'],
  ['mac', 'band.mac'],
  ['pubblica', 'band.pubblica'],
]);

/**
 * La fascia in testa dice sempre che cosa stai guardando: una beta, la
 * modalità sviluppatore, o tutte e due. Toccandola si va dove si agisce.
 */
function disegnaFascia() {
  const fascia = document.getElementById('pk-fascia');
  if (!fascia) return;
  const pezzi = [];
  if (FASCE.has(costruzione.canale)) {
    pezzi.push(i18n.t(FASCE.get(costruzione.canale), { v: costruzione.versione || '?' }));
  }
  if (admin.attiva()) pezzi.push(i18n.t('band.dev'));

  if (!pezzi.length) {
    fascia.hidden = true;
    return;
  }
  fascia.hidden = false;
  fascia.textContent = pezzi.join(' · ');
  fascia.dataset.canale = admin.attiva() ? 'sviluppo' : costruzione.canale;
  fascia.onclick = () => contesto.vaiA(admin.attiva() ? '#/admin' : '#/tu');
}

/**
 * Punta l'app al motore in Python, e dice al pannello che quello è il valore
 * «di fabbrica».
 *
 * Serve perché `build.json` si legge **dopo** `admin.inizializza()`, che ha già
 * guardato CONFIG per sapere com'era prima di sovrascriverlo. Senza dirglielo,
 * un azzeramento delle sovrascritture rimetterebbe la stringa vuota e
 * spegnerebbe il motore della demo.
 */
function accendiMotore(indirizzo) {
  CONFIG.motore = indirizzo;
  admin.aggiornaFabbrica('motore', indirizzo);
}

/**
 * Collega l'app al progetto Supabase indicato dalla costruzione.
 *
 * Stesso motivo di `accendiMotore`: i valori arrivano dopo che il pannello ha
 * già fotografato CONFIG. Qui però c'è anche una regola di sicurezza — una
 * chiave che sembra segreta non viene messa in CONFIG per niente, così non
 * finisce in un'esportazione, in un avviso o in una chiamata. Meglio un'app
 * che resta locale di un'app che pubblica una chiave.
 */
function accendiSupabase(impostazioni) {
  const url = String(impostazioni.url || '');
  const chiave = String(impostazioni.publishableKey || '');
  if (!url || !chiave || sembraSegreta(chiave)) return;
  CONFIG.supabase.url = url;
  CONFIG.supabase.publishableKey = chiave;
  admin.aggiornaFabbrica('supabase.url', url);
  admin.aggiornaFabbrica('supabase.publishableKey', chiave);
}

/** Legge `build.json`: c'è sempre, ed è precaricato con il resto dell'app. */
async function leggiCostruzione() {
  const dentro = globalThis.__PK_INLINE__ && globalThis.__PK_INLINE__['build.json'];
  if (dentro) {
    costruzione = { ...costruzione, ...dentro };
    if (costruzione.motore) accendiMotore(costruzione.motore);
    if (costruzione.supabase) accendiSupabase(costruzione.supabase);
    contesto.costruzione = costruzione;
    return;
  }
  try {
    const risposta = await fetch('build.json');
    if (risposta.ok) costruzione = { ...costruzione, ...(await risposta.json()) };
  } catch {
    // Senza il file resta «sviluppo»: nessuna fascia, nessun danno.
  }
  // La demo con il motore in Python dice qui dove trovarlo: da quel momento
  // le domande pesanti non le fa più il browser.
  if (costruzione.motore) accendiMotore(costruzione.motore);
  // La copia pubblicata porta qui l'indirizzo del progetto e la sola chiave
  // pubblicabile: è il motivo per cui la stessa app, servita da un indirizzo
  // pubblico, sa dove far entrare le persone.
  if (costruzione.supabase) accendiSupabase(costruzione.supabase);
  contesto.costruzione = costruzione;
}

/** Da "#/spot/abc" a {nome: 'dettaglio', parametri: {id: 'abc'}}. */
function rotta(indirizzo) {
  const pezzi = (indirizzo || '#/mappa').replace(/^#\/?/, '').split('/').filter(Boolean);
  const primo = pezzi[0] || 'mappa';
  const secondo = pezzi[1];

  if (primo === 'spot') return secondo ? { nome: 'dettaglio', parametri: { id: secondo } } : { nome: 'spot', parametri: {} };
  if (primo === 'mappa') return { nome: 'mappa', parametri: secondo ? { id: secondo } : {} };
  if (primo === 'tutorial') return { nome: 'tutorial', parametri: {} };
  if (primo === 'tu') return { nome: 'tu', parametri: {} };
  if (primo === 'admin') {
    // Il pannello si apre solo se la modalità è accesa: un indirizzo scritto
    // a mano non deve dare poteri a nessuno.
    if (!admin.attiva()) return { nome: 'tu', parametri: {} };
    return { nome: 'admin', parametri: secondo ? { id: secondo } : {} };
  }
  return { nome: 'mappa', parametri: {} };
}

const TAB_DI = {
  mappa: '#/mappa',
  spot: '#/spot',
  dettaglio: '#/spot',
  tutorial: '#/tutorial',
  tu: '#/tu',
  admin: '#/tu',
};

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
  // Aperta come file (la demo in un file solo) non c'è niente da mettere in
  // cache: l'app è già tutta nella pagina.
  if (location.protocol === 'file:') return;
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

  // La modalità sviluppatore va letta prima dei dati: se è accesa, quello che
  // l'app mostra è il file più le modifiche locali.
  await admin.inizializza();
  await dati.carica();

  document.getElementById('app').hidden = false;
  await schermataMappa.inizializza(contesto);
  await schermataSpot.inizializza(contesto);
  schermataDettaglio.inizializza(contesto);
  schermataTutorial.inizializza(contesto);
  schermataTu.inizializza(contesto);
  schermataAdmin.inizializza(contesto);

  collegaNavigazione();
  seguiLaRete();
  raccogliInvitoInstallazione();
  await leggiCostruzione();
  // Dopo la costruzione, perché è lì che la copia pubblicata dice a quale
  // progetto appartiene. Legge la sessione dal dispositivo e non aspetta la
  // rete: senza campo si resta dentro come si era.
  await auth.inizializza();
  disegnaFascia();

  if (!location.hash) location.hash = '#/mappa';
  // La prima schermata si apre, ma non la si aspetta. Aprendo di filato la
  // scheda di uno spot — è quello che fa un QR che punta a uno spot — `apri`
  // resta in attesa che una persona accetti l'avviso sui rischi, e può
  // restarci per sempre. L'avviso deve comparire sopra l'app, non sopra il
  // guscio d'avvio, che altrimenti se ne sta lì a dire «sto cucendo la
  // mappa» mentre l'app è in piedi da un pezzo.
  const primaSchermata = apri(location.hash);

  const splash = document.getElementById('pk-splash');
  splash.dataset.via = '1';
  setTimeout(() => splash.remove(), 300);

  // Da qui in poi niente è più necessario per usare l'app.
  registraServiceWorker();
  scrivi('ultimoAvvio', new Date().toISOString());
  document.body.dataset.pronta = '1';

  // Aspettata in fondo, non prima: se la prima schermata fallisce, l'errore
  // deve arrivare a chi ha chiamato `avvia`.
  await primaSchermata;
}

avvia().catch((errore) => {
  console.error('PkFAMILY non è riuscita ad avviarsi', errore);
  mostraErrore(errore);
});
