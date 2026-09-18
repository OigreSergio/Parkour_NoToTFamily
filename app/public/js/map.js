/* PkFAMILY — la mappa, disegnata a mano su una tela.
 *
 * Non c'è una libreria di mappe: una tela, la proiezione di Mercatore e le
 * tessere scaricate una per una. Le ragioni sono due, e sono entrambe
 * l'offline: quello che non si scarica non può mancare quando la rete non
 * c'è, e quando le tessere non arrivano la mappa non resta bianca — disegna
 * il lino con la sua trama e tiene gli spilli al loro posto, che è
 * l'informazione che serve davvero per raggiungere uno spot.
 *
 * Le tessere sono quelle di OpenStreetMap, che non hanno niente a che vedere
 * con il «ricamo su lino» del prodotto: passano quindi da un filtro di colore
 * sulla tela (`sepia .35`) che le porta verso il lino senza cancellare le
 * strade — una mappa illeggibile è più bella e meno utile. Lo stile
 * vettoriale vero (`embroidery_style.json`) richiederebbe MapLibre, cioè una
 * libreria e i suoi megabyte: fuori dai vincoli di questa app. Il satellite
 * resta a colori suoi, perché una vista satellitare tinta non serve a niente.
 *
 * Gli spilli seguono il masterplan (cap. 3.5): testa `verde` per gli spot
 * verificati, `blu-community` per quelli della community, `ambra` per quelli
 * in attesa, `filo` per quello scelto. Dove sono troppi si raccolgono in un
 * gomitolo con il numero — nessuno spot sparisce in silenzio.
 */

import { CONFIG } from './config.js';
import { LATO_TESSERA, latLngAPixel, pixelALatLng } from './geo.js';

const ZOOM_MIN = 2;
const TESSERE_IN_MEMORIA = 360;

/** Quanto lontano possono cadere due tocchi perché siano un doppio tocco. */
const RAGGIO_DOPPIO_TOCCO = 34;

/** Quanto deve muoversi il dito perché sia un trascinamento e non un tocco. */
const SOGLIA_TRASCINAMENTO = 7;

/** Quanto si aspetta prima di riprovare una tessera che non è arrivata. */
const ATTESA_PRIMA = 20_000;
const ATTESA_MASSIMA = 5 * 60_000;

/** L'ora, in millisecondi: una sola funzione, così è facile da provare. */
function orologio() {
  return Date.now();
}

// Il filtro che porta le tessere verso il lino: le stringhe stanno in
// config.js, così la modalità sviluppatore può provarne altre dal vivo.
//
// Al chiaro basta scaldarle: `sepia .35` con un po' meno saturazione le porta
// sul lino lasciando leggere le strade. Al buio abbassare la luce non basta —
// viene fuori una nebbia grigia — e si ribalta invece la tessera
// (`invert` + `hue-rotate 180°`): il fondo diventa notte, le strade restano
// chiare, i parchi restano verdi. È il modo in cui sono fatte tutte le mappe
// scure, ed è l'unico che qui non costi una libreria.

/** Da "#rrggbb" alla luminanza percepita, per capire se siamo al buio. */
function luminanza(esadecimale) {
  const pulito = (esadecimale || '').trim().replace('#', '');
  const pieno =
    pulito.length === 3
      ? pulito
          .split('')
          .map((c) => c + c)
          .join('')
      : pulito;
  if (pieno.length < 6) return 1;
  const r = parseInt(pieno.slice(0, 2), 16) / 255;
  const g = parseInt(pieno.slice(2, 4), 16) / 255;
  const b = parseInt(pieno.slice(4, 6), 16) / 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function creaMappa(contenitore, opzioni = {}) {
  const tela = document.createElement('canvas');
  tela.className = 'pk-map__canvas';
  tela.setAttribute('role', 'application');
  tela.setAttribute('aria-label', opzioni.etichetta || 'Mappa degli spot');
  contenitore.append(tela);

  const crediti = document.createElement('p');
  crediti.className = 'pk-map__credits';
  contenitore.append(crediti);

  const ctx = tela.getContext('2d');
  // Safari prima della 17 non ha i filtri sulla tela: lì le tessere restano
  // quelle di OpenStreetMap, senza tinta. Meglio una mappa cruda che nessuna.
  const filtriPossibili = 'filter' in ctx;

  const tessere = new Map(); // chiave "sorgente/z/x/y" → {img, pronta, fallita}
  let sorgente = opzioni.sorgente || 'mappa';
  let centro = { lat: CONFIG.partenza.lat, lng: CONFIG.partenza.lng };
  let zoom = CONFIG.partenza.zoom;
  let spot = [];
  let fontanelle = [];
  let selezionato = null;
  let posizione = null;
  let percorso = null;
  let larghezza = 0;
  let altezza = 0;
  let daRidisegnare = false;
  /** La tela è davvero sullo schermo? Se no, si misura lo stesso ma non si
   *  disegna: disegnare una tela nascosta è lavoro buttato. */
  let visibile = false;
  let vivo = true;

  // L'ultima disposizione disegnata: serve a capire cosa c'è sotto il dito
  // senza rifare i conti di proiezione a ogni tocco.
  let disposizione = { spilli: [], gomitoli: [] };

  const ascoltatori = { selezione: [], movimento: [], gomitolo: [], disegnato: [] };

  // --- colori -------------------------------------------------------------
  // I token stanno nel foglio di stile, ma chiederli al browser costa: durante
  // un trascinamento erano 146 letture per fotogramma. Si leggono una volta e
  // si dimenticano quando cambia il tema.

  let tavolozza = null;

  function colori() {
    if (tavolozza) return tavolozza;
    const stile = getComputedStyle(document.documentElement);
    const leggi = (nome, ripiego) => stile.getPropertyValue(nome).trim() || ripiego;
    const lino = leggi('--lino', '#f4ece0');
    tavolozza = {
      lino,
      carta: leggi('--carta', '#fbf7ef'),
      cucitura: leggi('--cucitura', '#e0d4bd'),
      inchiostro: leggi('--inchiostro', '#1f1b16'),
      filo: leggi('--filo', '#c26a52'),
      filoScuro: leggi('--filo-scuro', '#a8543e'),
      verde: leggi('--verde', '#63864a'),
      ambra: leggi('--ambra', '#b97a0e'),
      blu: leggi('--blu-community', '#6f9cb8'),
      scuro: luminanza(lino) < 0.45,
    };
    return tavolozza;
  }

  function scordaColori() {
    tavolozza = null;
    chiediDisegno();
  }

  const osservatoreTema = new MutationObserver(scordaColori);
  osservatoreTema.observe(document.documentElement, { attributeFilter: ['data-tema'] });
  const preferenzaScura = window.matchMedia('(prefers-color-scheme: dark)');
  preferenzaScura.addEventListener('change', scordaColori);

  /** Il colore della testa di uno spillo, secondo lo stato dello spot. */
  function tinta(voce, scelto) {
    const c = colori();
    if (scelto) return c.filo;
    if (voce.status === 'verified') return c.verde;
    if (voce.status === 'pending') return c.ambra;
    return c.blu;
  }

  // --- dimensioni ---------------------------------------------------------

  /**
   * Quanto è grande la mappa. Se la sua schermata è nascosta (`display:none`)
   * la tela misura zero: si guarda allora il contenitore che la ospiterà, che
   * una misura ce l'ha lo stesso, e in ultimo la finestra. Una mappa mai
   * misurata ha un riquadro grande un punto, e da lì venivano le tre tessere
   * di «prepara quest'area» quando si ricaricava stando sulla schermata «Tu».
   */
  function misura() {
    if (contenitore.clientWidth && contenitore.clientHeight) {
      return { l: contenitore.clientWidth, a: contenitore.clientHeight, vera: true };
    }
    const ospite = contenitore.closest('.pk-main') || contenitore.parentElement;
    if (ospite && ospite.clientWidth && ospite.clientHeight) {
      return { l: ospite.clientWidth, a: ospite.clientHeight, vera: false };
    }
    return { l: window.innerWidth || 360, a: Math.max(320, (window.innerHeight || 640) - 160), vera: false };
  }

  function ridimensiona() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    const { l, a, vera } = misura();
    if (!l || !a) return;
    visibile = vera;
    larghezza = l;
    altezza = a;
    tela.width = Math.round(larghezza * dpr);
    tela.height = Math.round(altezza * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    disegna();
    // Cambiando misura cambia il riquadro visibile, quindi anche quali spilli
    // vanno mostrati. La prima misura è la più importante: prima di quella la
    // tela non aveva dimensioni e il riquadro era un punto.
    avvisaMovimento();
  }

  // --- conversioni --------------------------------------------------------

  function origine() {
    const c = latLngAPixel(centro.lat, centro.lng, zoom);
    return { x: c.x - larghezza / 2, y: c.y - altezza / 2 };
  }

  function aSchermo(punto, o) {
    const base = o || origine();
    const p = latLngAPixel(punto.lat, punto.lng, zoom);
    return { x: p.x - base.x, y: p.y - base.y };
  }

  function daSchermo(x, y) {
    const o = origine();
    return pixelALatLng(o.x + x, o.y + y, zoom);
  }

  function riquadro() {
    const na = daSchermo(0, 0);
    const so = daSchermo(larghezza, altezza);
    return { nord: na.lat, ovest: na.lng, sud: so.lat, est: so.lng };
  }

  function zoomMassimo() {
    return CONFIG.tiles[sorgente].zoomMax;
  }

  // --- tessere ------------------------------------------------------------

  function indirizzoTessera(z, x, y) {
    return CONFIG.tiles[sorgente].url.replace('{z}', z).replace('{x}', x).replace('{y}', y);
  }

  function creaTessera(chiave, z, x, y, tentativi) {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.decoding = 'async';
    const nuova = { img, pronta: false, fallita: false, tentativi, prossima: 0 };
    img.onload = () => {
      nuova.pronta = true;
      chiediDisegno();
    };
    img.onerror = () => {
      // Senza rete succede subito: si disegna il lino e si riproverà più
      // tardi, con un'attesa che raddoppia. La rete torna anche quando il
      // browser non se ne accorge (una galleria, un ascensore).
      nuova.fallita = true;
      nuova.tentativi += 1;
      nuova.prossima =
        orologio() + Math.min(ATTESA_MASSIMA, ATTESA_PRIMA * 2 ** (nuova.tentativi - 1));
      programmaRiprova(nuova.prossima);
      chiediDisegno();
    };
    img.src = indirizzoTessera(z, x, y);

    tessere.set(chiave, nuova);
    if (tessere.size > TESSERE_IN_MEMORIA) {
      const piuVecchia = tessere.keys().next().value;
      tessere.delete(piuVecchia);
    }
    return nuova;
  }

  function tessera(z, x, y, soloSeCiSta) {
    const chiave = `${sorgente}/${z}/${x}/${y}`;
    const voce = tessere.get(chiave);

    if (voce) {
      if (voce.fallita && !soloSeCiSta && orologio() >= voce.prossima) {
        tessere.delete(chiave);
        return creaTessera(chiave, z, x, y, voce.tentativi);
      }
      // Rimessa in fondo alla fila: la Map tiene l'ordine di inserimento e lo
      // sfratto guarda la testa. Senza questo usciva la più vecchia di
      // arrivo, anche se era quella sotto gli occhi.
      tessere.delete(chiave);
      tessere.set(chiave, voce);
      return voce;
    }

    if (soloSeCiSta) return null;
    return creaTessera(chiave, z, x, y, 0);
  }

  let sveglia = null;
  let quandoSveglia = 0;

  /** Una sola sveglia, per la riprova più vicina nel tempo. */
  function programmaRiprova(quando) {
    if (sveglia && quandoSveglia <= quando) return;
    clearTimeout(sveglia);
    quandoSveglia = quando;
    sveglia = setTimeout(() => {
      sveglia = null;
      chiediDisegno();
    }, Math.max(1000, quando - orologio()));
  }

  const scorteInCorso = new Set();

  /**
   * Cerca una tessera fra quelle che il service worker ha già salvato, senza
   * toccare la rete. È così che l'area «preparata» a uno zoom serve anche
   * agli zoom vicini: prima la scorta guardava solo la memoria, e quello che
   * era stato scaricato apposta restava lì senza essere usato.
   */
  async function cercaNellaCache(z, x, y) {
    if (typeof caches === 'undefined') return;
    const chiave = `${sorgente}/${z}/${x}/${y}`;
    if (tessere.has(chiave) || scorteInCorso.has(chiave)) return;
    scorteInCorso.add(chiave);
    try {
      const risposta = await caches.match(indirizzoTessera(z, x, y));
      if (!risposta || !risposta.ok) return;
      const indirizzo = URL.createObjectURL(await risposta.blob());
      const img = new Image();
      img.decoding = 'async';
      const voce = { img, pronta: false, fallita: false, tentativi: 0, prossima: 0 };
      img.onload = () => {
        voce.pronta = true;
        URL.revokeObjectURL(indirizzo);
        chiediDisegno();
      };
      img.onerror = () => {
        voce.fallita = true;
        URL.revokeObjectURL(indirizzo);
      };
      img.src = indirizzo;
      tessere.set(chiave, voce);
    } catch {
      // Nessuna cache raggiungibile: si resta con il lino, che è onesto.
    } finally {
      scorteInCorso.delete(chiave);
    }
  }

  /** Riprova le tessere che erano fallite: si chiama quando torna la rete. */
  function riprova() {
    for (const [chiave, voce] of [...tessere]) {
      if (voce.fallita) tessere.delete(chiave);
    }
    chiediDisegno();
  }

  // --- disegno ------------------------------------------------------------

  /** Il lino: fondo caldo e una trama a punto croce, così l'assenza di
   *  tessere sembra una scelta e non un errore. */
  function disegnaLino(x, y, lato) {
    const c = colori();
    ctx.fillStyle = c.lino;
    ctx.fillRect(x, y, lato, lato);
    ctx.strokeStyle = c.cucitura;
    ctx.lineWidth = 1;
    const passo = 32;
    ctx.beginPath();
    for (let i = 0; i <= lato; i += passo) {
      ctx.moveTo(x + i, y);
      ctx.lineTo(x + i, y + lato);
      ctx.moveTo(x, y + i);
      ctx.lineTo(x + lato, y + i);
    }
    ctx.stroke();
  }

  function disegnaTessere() {
    const z = Math.max(0, Math.min(Math.round(zoom), zoomMassimo()));
    const scala = 2 ** (zoom - z);
    const lato = LATO_TESSERA * scala;
    const o = origine();
    const n = 2 ** z;

    const primoX = Math.floor(o.x / lato);
    const primoY = Math.floor(o.y / lato);
    const ultimoX = Math.floor((o.x + larghezza) / lato);
    const ultimoY = Math.floor((o.y + altezza) / lato);

    // Il filtro vale solo per la mappa disegnata: il satellite resta vero.
    const filtro =
      filtriPossibili && sorgente === 'mappa'
        ? CONFIG.filtroTessere[colori().scuro ? 'scuro' : 'chiaro'] || 'none'
        : 'none';

    for (let ty = primoY; ty <= ultimoY; ty++) {
      if (ty < 0 || ty >= n) continue;
      for (let tx = primoX; tx <= ultimoX; tx++) {
        const x = Math.floor(tx * lato - o.x);
        const y = Math.floor(ty * lato - o.y);
        const lar = Math.ceil(lato) + 1;
        const avvolto = ((tx % n) + n) % n;
        const voce = tessera(z, avvolto, ty);
        if (voce.pronta) {
          if (filtro !== 'none') ctx.filter = filtro;
          ctx.drawImage(voce.img, x, y, lar, lar);
          if (filtro !== 'none') ctx.filter = 'none';
        } else if (!disegnaTesseraDiScorta(z, avvolto, ty, x, y, lar, filtro)) {
          disegnaLino(x, y, lar);
        }
      }
    }
  }

  /**
   * La tessera non c'è ancora: se quella del livello sopra è già in memoria se
   * ne ritaglia il quadrante. È la ragione per cui, avendo preparato l'area a
   * uno zoom, avvicinandosi non si trova il vuoto.
   */
  function disegnaTesseraDiScorta(z, x, y, sx, sy, lato, filtro) {
    for (let salto = 1; salto <= 5; salto++) {
      const zp = z - salto;
      if (zp < 0) break;
      const fattore = 2 ** salto;
      const px = Math.floor(x / fattore);
      const py = Math.floor(y / fattore);
      const padre = tessera(zp, px, py, true);
      if (!padre || !padre.pronta) {
        // Non è in memoria: forse è fra quelle già scaricate. Si chiede alla
        // cache, senza rete; quando arriva, la mappa si ridisegna da sé.
        if (!padre && salto <= 3) cercaNellaCache(zp, px, py);
        continue;
      }
      const parte = LATO_TESSERA / fattore;
      if (filtro !== 'none') ctx.filter = filtro;
      ctx.drawImage(
        padre.img,
        (x % fattore) * parte,
        (y % fattore) * parte,
        parte,
        parte,
        sx,
        sy,
        lato,
        lato
      );
      if (filtro !== 'none') ctx.filter = 'none';
      return true;
    }
    return false;
  }

  /** Uno spillo da cucito: testa tonda con la cruna, punta esatta sul punto. */
  function disegnaSpillo(x, y, colore, grande) {
    const c = colori();
    const r = grande ? 11 : 7;
    const altezzaPunta = grande ? 17 : 11;
    const cy = y - altezzaPunta * 0.58 - r * 0.62;

    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x - r * 0.62, y - altezzaPunta * 0.58);
    ctx.lineTo(x + r * 0.62, y - altezzaPunta * 0.58);
    ctx.closePath();
    ctx.fillStyle = colore;
    ctx.fill();

    ctx.beginPath();
    ctx.arc(x, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = colore;
    ctx.fill();
    ctx.lineWidth = grande ? 2.5 : 1.5;
    ctx.strokeStyle = c.carta;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(x, cy, r * 0.38, 0, Math.PI * 2);
    ctx.fillStyle = c.carta;
    ctx.fill();
  }

  /**
   * Il gomitolo: dove gli spilli sarebbero l'uno sull'altro si mostra quanti
   * sono. Il numero è la parte che conta — lo sfoltimento silenzioso di prima
   * toglieva spot dalla mappa senza che nessuno potesse accorgersene.
   */
  function disegnaGomitolo(x, y, conta, tuttiVerificati) {
    const c = colori();
    const r = Math.min(26, 15 + Math.log10(conta) * 8);
    const etichetta = conta > 999 ? '999+' : String(conta);

    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = c.carta;
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = tuttiVerificati ? c.verde : c.blu;
    ctx.stroke();

    // Due giri di filo: è un gomitolo, non una bolla.
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, r - 1, 0, Math.PI * 2);
    ctx.clip();
    ctx.strokeStyle = c.cucitura;
    ctx.lineWidth = 1.2;
    for (const inclinazione of [-0.6, 0.6]) {
      ctx.beginPath();
      ctx.ellipse(x, y, r * 0.95, r * 0.42, inclinazione, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.restore();

    ctx.fillStyle = c.inchiostro;
    ctx.font = `700 ${r > 20 ? 14 : 12}px Karla, system-ui, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(etichetta, x, y + 0.5);
    ctx.textAlign = 'start';
    ctx.textBaseline = 'alphabetic';
  }

  /** Una fontanella: goccia verde, piccola, con i metri quando li sappiamo. */
  function disegnaFontanella(x, y, metri) {
    const c = colori();
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.quadraticCurveTo(x + 5.5, y - 6, x, y - 11);
    ctx.quadraticCurveTo(x - 5.5, y - 6, x, y);
    ctx.closePath();
    ctx.fillStyle = c.verde;
    ctx.fill();
    ctx.lineWidth = 1.2;
    ctx.strokeStyle = c.carta;
    ctx.stroke();

    if (metri === undefined || metri === null) return;
    const testo = `${Math.round(metri)} m`;
    ctx.font = '600 11px Karla, system-ui, sans-serif';
    const larghezzaTesto = ctx.measureText(testo).width;
    ctx.fillStyle = c.carta;
    ctx.beginPath();
    // roundRect è recente: dove non c'è, un rettangolo dritto dice le stesse
    // cose con un angolo in meno.
    if (ctx.roundRect) ctx.roundRect(x + 7, y - 17, larghezzaTesto + 10, 16, 8);
    else ctx.rect(x + 7, y - 17, larghezzaTesto + 10, 16);
    ctx.fill();
    ctx.strokeStyle = c.cucitura;
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = c.verde;
    ctx.fillText(testo, x + 12, y - 5.5);
  }

  function disegnaPercorso(o) {
    if (!percorso || percorso.length < 2) return;
    ctx.save();
    ctx.lineWidth = 4;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.setLineDash([9, 7]);
    ctx.strokeStyle = colori().filoScuro;
    ctx.beginPath();
    percorso.forEach((punto, indice) => {
      const p = aSchermo(punto, o);
      if (indice === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.stroke();
    ctx.restore();
  }

  /** La posizione di chi guarda: punto `blu-community` con l'alone (3.5). */
  function disegnaPosizione(o) {
    if (!posizione) return;
    const c = colori();
    const p = aSchermo(posizione, o);
    ctx.save();
    ctx.globalAlpha = 0.18;
    ctx.beginPath();
    ctx.arc(p.x, p.y, 16, 0, Math.PI * 2);
    ctx.fillStyle = c.blu;
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.beginPath();
    ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
    ctx.fillStyle = c.blu;
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = c.carta;
    ctx.stroke();
    ctx.restore();
  }

  /**
   * Raccoglie in celle di schermo gli spot visibili: una cella con un solo
   * spot diventa uno spillo, una cella affollata diventa un gomitolo. Lo spot
   * scelto non entra mai in un gomitolo — deve restare dove la persona lo ha
   * toccato.
   */
  function disponi(o) {
    const spilli = [];
    const celle = new Map();

    for (const voce of spot) {
      const p = aSchermo(voce, o);
      if (p.x < -30 || p.y < -40 || p.x > larghezza + 30 || p.y > altezza + 30) continue;
      if (voce.id === selezionato) {
        spilli.push({ voce, x: p.x, y: p.y, scelto: true });
        continue;
      }
      const cella = CONFIG.cellaGomitolo;
      const chiave = `${Math.floor(p.x / cella)},${Math.floor(p.y / cella)}`;
      const raccolta = celle.get(chiave);
      if (raccolta) {
        raccolta.voci.push(voce);
        raccolta.x += p.x;
        raccolta.y += p.y;
      } else {
        celle.set(chiave, { voci: [voce], x: p.x, y: p.y });
      }
    }

    const gomitoli = [];
    for (const raccolta of celle.values()) {
      if (raccolta.voci.length === 1) {
        spilli.push({ voce: raccolta.voci[0], x: raccolta.x, y: raccolta.y, scelto: false });
        continue;
      }
      gomitoli.push({
        x: raccolta.x / raccolta.voci.length,
        y: raccolta.y / raccolta.voci.length,
        conta: raccolta.voci.length,
        voci: raccolta.voci,
        tuttiVerificati: raccolta.voci.every((v) => v.status === 'verified'),
      });
    }

    return { spilli, gomitoli };
  }

  function disegna() {
    daRidisegnare = false;
    if (!larghezza || !altezza || !visibile) return;
    const c = colori();
    const o = origine();

    ctx.clearRect(0, 0, larghezza, altezza);
    disegnaTessere();
    disegnaPercorso(o);

    if (zoom >= CONFIG.zoomFontanelle) {
      for (const fontanella of fontanelle) {
        const p = aSchermo(fontanella, o);
        if (p.x < -20 || p.y < -30 || p.x > larghezza + 60 || p.y > altezza + 20) continue;
        disegnaFontanella(p.x, p.y, fontanella.metri);
      }
    }

    disposizione = disponi(o);
    for (const gomitolo of disposizione.gomitoli) {
      disegnaGomitolo(gomitolo.x, gomitolo.y, gomitolo.conta, gomitolo.tuttiVerificati);
    }
    // Lo scelto per ultimo: sopra a tutto il resto.
    const ordinati = [...disposizione.spilli].sort((a, b) => Number(a.scelto) - Number(b.scelto));
    for (const spillo of ordinati) {
      disegnaSpillo(spillo.x, spillo.y, tinta(spillo.voce, spillo.scelto), spillo.scelto);
    }

    disegnaPosizione(o);
    crediti.textContent = CONFIG.tiles[sorgente].crediti;
    void c;

    // Chi conta gli spilli deve contarli *dopo* che sono stati disegnati: il
    // numero nel sottotitolo, chiesto prima, era sempre quello di prima.
    for (const fn of ascoltatori.disegnato) fn(quadroAttuale());
  }

  function quadroAttuale() {
    return {
      spilli: disposizione.spilli.length,
      gomitoli: disposizione.gomitoli.length,
      raccolti: disposizione.gomitoli.reduce((somma, g) => somma + g.conta, 0),
    };
  }

  function chiediDisegno() {
    if (daRidisegnare || !vivo) return;
    daRidisegnare = true;
    requestAnimationFrame(() => {
      if (vivo) disegna();
      else daRidisegnare = false;
    });
  }

  function avvisaMovimento() {
    for (const fn of ascoltatori.movimento) {
      fn({ centro: { ...centro }, zoom, riquadro: riquadro() });
    }
  }

  // --- interazione --------------------------------------------------------

  const puntatori = new Map();
  let trascinato = false;
  let camminoTotale = 0;
  let ultimaDistanza = 0;
  let ultimoCentroDita = null;
  let ultimoTocco = null;

  function cambiaZoom(nuovo, ancoraX, ancoraY) {
    const limitato = Math.max(ZOOM_MIN, Math.min(zoomMassimo(), nuovo));
    if (limitato === zoom) return;
    const ax = ancoraX === undefined ? larghezza / 2 : ancoraX;
    const ay = ancoraY === undefined ? altezza / 2 : ancoraY;
    const sotto = daSchermo(ax, ay);

    zoom = limitato;
    // Si rimette il punto ancorato esattamente dove era sullo schermo.
    const p = latLngAPixel(sotto.lat, sotto.lng, zoom);
    centro = pixelALatLng(p.x - ax + larghezza / 2, p.y - ay + altezza / 2, zoom);
    chiediDisegno();
    avvisaMovimento();
  }

  function sposta(dx, dy) {
    const o = origine();
    const c = pixelALatLng(o.x - dx + larghezza / 2, o.y - dy + altezza / 2, zoom);
    centro = { lat: Math.max(-85, Math.min(85, c.lat)), lng: c.lng };
    chiediDisegno();
    avvisaMovimento();
  }

  /** Cosa c'è sotto il dito: uno spillo, un gomitolo, o niente. */
  function sotto(x, y) {
    let migliore = null;
    let minima = 28 * 28;
    for (const spillo of disposizione.spilli) {
      // Lo spillo sta sopra il punto: il bersaglio si sposta in alto con lui.
      const dx = spillo.x - x;
      const dy = spillo.y - (spillo.scelto ? 18 : 12) - y;
      const d = dx * dx + dy * dy;
      if (d < minima) {
        minima = d;
        migliore = { tipo: 'spot', voce: spillo.voce };
      }
    }
    if (migliore) return migliore;

    for (const gomitolo of disposizione.gomitoli) {
      const r = Math.min(26, 15 + Math.log10(gomitolo.conta) * 8);
      const dx = gomitolo.x - x;
      const dy = gomitolo.y - y;
      if (dx * dx + dy * dy <= r * r) return { tipo: 'gomitolo', gomitolo };
    }
    return null;
  }

  function centroDelle(dita) {
    const elenco = [...dita.values()];
    const somma = elenco.reduce((acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }), { x: 0, y: 0 });
    return { x: somma.x / elenco.length, y: somma.y / elenco.length };
  }

  tela.addEventListener('pointerdown', (evento) => {
    // La cattura del puntatore non è sempre concessa (eventi sintetici, dito
    // già rilasciato): senza, i gesti funzionano lo stesso.
    try {
      tela.setPointerCapture(evento.pointerId);
    } catch {
      /* va bene così */
    }
    puntatori.set(evento.pointerId, { x: evento.clientX, y: evento.clientY });
    if (puntatori.size === 1) {
      trascinato = false;
      camminoTotale = 0;
    } else {
      // Due dita: da qui in poi non è più un tocco, qualunque cosa succeda.
      trascinato = true;
    }
    ultimaDistanza = 0;
    ultimoCentroDita = null;
  });

  tela.addEventListener('pointermove', (evento) => {
    const precedente = puntatori.get(evento.pointerId);
    if (!precedente) return;
    const attuale = { x: evento.clientX, y: evento.clientY };
    puntatori.set(evento.pointerId, attuale);

    if (puntatori.size === 1) {
      const dx = attuale.x - precedente.x;
      const dy = attuale.y - precedente.y;
      // Il cammino si somma: un trascinamento lento è fatto di passi piccoli,
      // e prima veniva scambiato per un tocco fermo.
      camminoTotale += Math.abs(dx) + Math.abs(dy);
      if (camminoTotale > SOGLIA_TRASCINAMENTO) trascinato = true;
      sposta(dx, dy);
      return;
    }

    if (puntatori.size === 2) {
      trascinato = true;
      const [a, b] = [...puntatori.values()];
      const distanza = Math.hypot(a.x - b.x, a.y - b.y);
      const centroDita = centroDelle(puntatori);
      const rettangolo = tela.getBoundingClientRect();

      if (ultimoCentroDita) {
        // Il pizzico sposta anche: due dita che scorrono insieme trascinano la
        // mappa, come su qualunque mappa vera.
        sposta(centroDita.x - ultimoCentroDita.x, centroDita.y - ultimoCentroDita.y);
      }
      if (ultimaDistanza) {
        cambiaZoom(
          zoom + Math.log2(distanza / ultimaDistanza),
          centroDita.x - rettangolo.left,
          centroDita.y - rettangolo.top
        );
      }
      ultimaDistanza = distanza;
      ultimoCentroDita = centroDita;
    }
  });

  function finePuntatore(evento) {
    const era = puntatori.get(evento.pointerId);
    puntatori.delete(evento.pointerId);
    if (puntatori.size < 2) {
      ultimaDistanza = 0;
      ultimoCentroDita = null;
    }
    if (!era || trascinato || puntatori.size > 0) return;

    const rettangolo = tela.getBoundingClientRect();
    const x = era.x - rettangolo.left;
    const y = era.y - rettangolo.top;

    // Doppio tocco: due volte *nello stesso punto*. Due tocchi su due spilli
    // diversi sono due scelte, non uno zoom.
    const adesso = evento.timeStamp;
    if (
      ultimoTocco &&
      adesso - ultimoTocco.quando < 300 &&
      Math.hypot(x - ultimoTocco.x, y - ultimoTocco.y) < RAGGIO_DOPPIO_TOCCO
    ) {
      ultimoTocco = null;
      cambiaZoom(zoom + 1, x, y);
      return;
    }
    ultimoTocco = { quando: adesso, x, y };

    const scelto = sotto(x, y);
    if (scelto && scelto.tipo === 'gomitolo') {
      for (const fn of ascoltatori.gomitolo) fn(scelto.gomitolo);
      // Aprire un gomitolo vuol dire avvicinarsi finché non si sfila.
      cambiaZoom(zoom + 2, scelto.gomitolo.x, scelto.gomitolo.y);
      return;
    }
    selezionato = scelto ? scelto.voce.id : null;
    chiediDisegno();
    for (const fn of ascoltatori.selezione) fn(scelto ? scelto.voce : null);
  }

  tela.addEventListener('pointerup', finePuntatore);
  tela.addEventListener('pointercancel', (evento) => {
    puntatori.delete(evento.pointerId);
    ultimaDistanza = 0;
    ultimoCentroDita = null;
  });

  tela.addEventListener(
    'wheel',
    (evento) => {
      evento.preventDefault();
      const rettangolo = tela.getBoundingClientRect();
      cambiaZoom(
        zoom - Math.sign(evento.deltaY) * 0.5,
        evento.clientX - rettangolo.left,
        evento.clientY - rettangolo.top
      );
    },
    { passive: false }
  );

  // Con la sola tastiera la mappa si muove comunque: frecce e +/-.
  tela.tabIndex = 0;
  tela.addEventListener('keydown', (evento) => {
    const passo = 80;
    const tasti = {
      ArrowUp: () => sposta(0, passo),
      ArrowDown: () => sposta(0, -passo),
      ArrowLeft: () => sposta(passo, 0),
      ArrowRight: () => sposta(-passo, 0),
      '+': () => cambiaZoom(zoom + 1),
      '=': () => cambiaZoom(zoom + 1),
      '-': () => cambiaZoom(zoom - 1),
    };
    const azione = tasti[evento.key];
    if (azione) {
      evento.preventDefault();
      azione();
    }
  });

  const osservatore = new ResizeObserver(ridimensiona);
  osservatore.observe(contenitore);
  window.addEventListener('online', riprova);
  ridimensiona();

  return {
    get centro() {
      return { ...centro };
    },
    get zoom() {
      return zoom;
    },
    riquadro,
    /** La tela è stata misurata davvero almeno una volta? */
    get misurata() {
      return larghezza > 0 && altezza > 0;
    },
    aSchermo: (punto) => aSchermo(punto),
    vai({ lat, lng, zoom: z }) {
      centro = { lat, lng };
      if (z !== undefined) zoom = Math.max(ZOOM_MIN, Math.min(zoomMassimo(), z));
      chiediDisegno();
      avvisaMovimento();
    },
    zoomAvanti: () => cambiaZoom(zoom + 1),
    zoomIndietro: () => cambiaZoom(zoom - 1),
    /** Sposta la vista di tanti pixel: serve a togliere uno spillo da sotto il foglio. */
    spostaDi: (dx, dy) => sposta(dx, dy),
    mostraSpot(elenco) {
      spot = elenco;
      chiediDisegno();
    },
    mostraFontanelle(elenco) {
      fontanelle = elenco || [];
      chiediDisegno();
    },
    seleziona(id) {
      selezionato = id;
      chiediDisegno();
    },
    segnaPosizione(punto) {
      posizione = punto;
      chiediDisegno();
    },
    mostraPercorso(punti) {
      percorso = punti;
      chiediDisegno();
    },
    cambiaSorgente(nome) {
      if (!CONFIG.tiles[nome]) return;
      sorgente = nome;
      if (zoom > zoomMassimo()) zoom = zoomMassimo();
      chiediDisegno();
    },
    get sorgente() {
      return sorgente;
    },
    /** Quanti spilli e quanti gomitoli si vedono adesso: lo dice la schermata. */
    get quadro() {
      return quadroAttuale();
    },
    riprova,
    su(evento, fn) {
      if (ascoltatori[evento]) ascoltatori[evento].push(fn);
    },
    ridisegna: chiediDisegno,
    distruggi() {
      vivo = false;
      clearTimeout(sveglia);
      osservatore.disconnect();
      osservatoreTema.disconnect();
      preferenzaScura.removeEventListener('change', scordaColori);
      window.removeEventListener('online', riprova);
      tessere.clear();
      crediti.remove();
      tela.remove();
    },
  };
}
