/* PkFAMILY — la mappa, disegnata a mano su una tela.
 *
 * Non c'è una libreria di mappe: una tela, la proiezione di Mercatore e le
 * tessere scaricate una per una. Le ragioni sono due, e sono entrambe
 * l'offline: quello che non si scarica non può mancare quando la rete non
 * c'è, e quando le tessere non arrivano la mappa non resta bianca — disegna
 * il lino con la sua trama e tiene gli spilli al loro posto, che è
 * l'informazione che serve davvero per raggiungere uno spot.
 *
 * Le tessere già viste restano nella cache del service worker: ripassare in
 * un posto dove si è già stati funziona anche in aereo.
 */

import { CONFIG } from './config.js';
import { LATO_TESSERA, latLngAPixel, pixelALatLng } from './geo.js';

const ZOOM_MIN = 2;
const TESSERE_IN_MEMORIA = 360;

/** Colori presi dal foglio di stile: la mappa segue il tema come il resto. */
function colore(nome, ripiego) {
  const valore = getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  return valore || ripiego;
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
  const tessere = new Map(); // chiave "z/x/y" → {img, pronta, fallita}
  let sorgente = opzioni.sorgente || 'mappa';
  let centro = { lat: CONFIG.partenza.lat, lng: CONFIG.partenza.lng };
  let zoom = CONFIG.partenza.zoom;
  let spot = [];
  let selezionato = null;
  let posizione = null;
  let percorso = null;
  let larghezza = 0;
  let altezza = 0;
  let daRidisegnare = false;
  let vivo = true;

  const ascoltatori = { selezione: [], movimento: [] };

  // --- dimensioni ---------------------------------------------------------

  function ridimensiona() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    larghezza = contenitore.clientWidth;
    altezza = contenitore.clientHeight;
    if (!larghezza || !altezza) return;
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

  function aSchermo(punto) {
    const o = origine();
    const p = latLngAPixel(punto.lat, punto.lng, zoom);
    return { x: p.x - o.x, y: p.y - o.y };
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
    return CONFIG.tiles[sorgente].url
      .replace('{z}', z)
      .replace('{x}', x)
      .replace('{y}', y);
  }

  function tessera(z, x, y) {
    const chiave = `${sorgente}/${z}/${x}/${y}`;
    let voce = tessere.get(chiave);
    if (voce) return voce;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.decoding = 'async';
    voce = { img, pronta: false, fallita: false };
    img.onload = () => {
      voce.pronta = true;
      chiediDisegno();
    };
    img.onerror = () => {
      // Senza rete succede subito: si smette di insistere e si disegna il lino.
      voce.fallita = true;
      chiediDisegno();
    };
    img.src = indirizzoTessera(z, x, y);

    tessere.set(chiave, voce);
    if (tessere.size > TESSERE_IN_MEMORIA) {
      const piuVecchia = tessere.keys().next().value;
      tessere.delete(piuVecchia);
    }
    return voce;
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
    ctx.fillStyle = colore('--lino', '#f4ece0');
    ctx.fillRect(x, y, lato, lato);
    ctx.strokeStyle = colore('--cucitura', '#e0d4bd');
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

    for (let ty = primoY; ty <= ultimoY; ty++) {
      if (ty < 0 || ty >= n) continue;
      for (let tx = primoX; tx <= ultimoX; tx++) {
        const x = Math.floor(tx * lato - o.x);
        const y = Math.floor(ty * lato - o.y);
        const lar = Math.ceil(lato) + 1;
        const avvolto = ((tx % n) + n) % n;
        const voce = tessera(z, avvolto, ty);
        if (voce.pronta) {
          ctx.drawImage(voce.img, x, y, lar, lar);
        } else {
          disegnaLino(x, y, lar);
        }
      }
    }
  }

  /** Uno spillo: testa tonda, punta verso il punto esatto. */
  function disegnaSpillo(x, y, tinta, grande) {
    const r = grande ? 11 : 7;
    const altezzaPunta = grande ? 17 : 11;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x - r * 0.62, y - altezzaPunta * 0.58);
    ctx.lineTo(x + r * 0.62, y - altezzaPunta * 0.58);
    ctx.closePath();
    ctx.fillStyle = tinta;
    ctx.fill();

    ctx.beginPath();
    ctx.arc(x, y - altezzaPunta * 0.58 - r * 0.62, r, 0, Math.PI * 2);
    ctx.fillStyle = tinta;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = colore('--carta', '#fbf7ef');
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(x, y - altezzaPunta * 0.58 - r * 0.62, r * 0.38, 0, Math.PI * 2);
    ctx.fillStyle = colore('--carta', '#fbf7ef');
    ctx.fill();
    ctx.restore();
  }

  function disegnaPercorso() {
    if (!percorso || percorso.length < 2) return;
    ctx.save();
    ctx.lineWidth = 4;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.setLineDash([9, 7]);
    ctx.strokeStyle = colore('--filo-scuro', '#a8543e');
    ctx.beginPath();
    percorso.forEach((punto, indice) => {
      const p = aSchermo(punto);
      if (indice === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.stroke();
    ctx.restore();
  }

  function disegnaPosizione() {
    if (!posizione) return;
    const p = aSchermo(posizione);
    ctx.save();
    ctx.beginPath();
    ctx.arc(p.x, p.y, 16, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(99, 134, 74, .18)';
    ctx.fill();
    ctx.beginPath();
    ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
    ctx.fillStyle = colore('--verde', '#63864a');
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#fff';
    ctx.stroke();
    ctx.restore();
  }

  function disegna() {
    if (!larghezza || !altezza) return;
    ctx.clearRect(0, 0, larghezza, altezza);
    disegnaTessere();
    disegnaPercorso();

    const tintaVerificato = colore('--filo', '#c26a52');
    const tintaCommunity = colore('--blu-community', '#52809e');
    let scelto = null;
    for (const voce of spot) {
      const p = aSchermo(voce);
      if (p.x < -24 || p.y < -34 || p.x > larghezza + 24 || p.y > altezza + 24) continue;
      if (voce.id === selezionato) {
        scelto = { voce, p };
        continue;
      }
      disegnaSpillo(p.x, p.y, voce.status === 'verified' ? tintaVerificato : tintaCommunity, false);
    }
    if (scelto) {
      disegnaSpillo(
        scelto.p.x,
        scelto.p.y,
        scelto.voce.status === 'verified' ? tintaVerificato : tintaCommunity,
        true
      );
    }

    disegnaPosizione();
    crediti.textContent = CONFIG.tiles[sorgente].crediti;
    daRidisegnare = false;
  }

  function chiediDisegno() {
    if (daRidisegnare || !vivo) return;
    daRidisegnare = true;
    requestAnimationFrame(() => {
      if (vivo) disegna();
    });
  }

  function avvisaMovimento() {
    for (const fn of ascoltatori.movimento) fn({ centro: { ...centro }, zoom, riquadro: riquadro() });
  }

  // --- interazione --------------------------------------------------------

  const puntatori = new Map();
  let trascinato = false;
  let ultimaDistanza = 0;
  let ultimoTocco = 0;

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

  function spotSotto(x, y) {
    let migliore = null;
    let minima = 26 * 26;
    for (const voce of spot) {
      const p = aSchermo(voce);
      // Lo spillo sta sopra il punto: il bersaglio si sposta in alto con lui.
      const dx = p.x - x;
      const dy = p.y - 12 - y;
      const d = dx * dx + dy * dy;
      if (d < minima) {
        minima = d;
        migliore = voce;
      }
    }
    return migliore;
  }

  tela.addEventListener('pointerdown', (evento) => {
    tela.setPointerCapture(evento.pointerId);
    puntatori.set(evento.pointerId, { x: evento.clientX, y: evento.clientY });
    trascinato = false;
    ultimaDistanza = 0;
  });

  tela.addEventListener('pointermove', (evento) => {
    const precedente = puntatori.get(evento.pointerId);
    if (!precedente) return;
    const attuale = { x: evento.clientX, y: evento.clientY };
    puntatori.set(evento.pointerId, attuale);

    if (puntatori.size === 1) {
      const dx = attuale.x - precedente.x;
      const dy = attuale.y - precedente.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) trascinato = true;
      sposta(dx, dy);
      return;
    }

    if (puntatori.size === 2) {
      trascinato = true;
      const [a, b] = [...puntatori.values()];
      const distanza = Math.hypot(a.x - b.x, a.y - b.y);
      if (ultimaDistanza) {
        const rettangolo = tela.getBoundingClientRect();
        cambiaZoom(
          zoom + Math.log2(distanza / ultimaDistanza),
          (a.x + b.x) / 2 - rettangolo.left,
          (a.y + b.y) / 2 - rettangolo.top
        );
      }
      ultimaDistanza = distanza;
    }
  });

  function finePuntatore(evento) {
    const era = puntatori.get(evento.pointerId);
    puntatori.delete(evento.pointerId);
    if (puntatori.size < 2) ultimaDistanza = 0;
    if (!era || trascinato || puntatori.size > 0) return;

    const rettangolo = tela.getBoundingClientRect();
    const x = era.x - rettangolo.left;
    const y = era.y - rettangolo.top;

    const adesso = Date.now();
    if (adesso - ultimoTocco < 300) {
      ultimoTocco = 0;
      cambiaZoom(zoom + 1, x, y);
      return;
    }
    ultimoTocco = adesso;

    const scelto = spotSotto(x, y);
    selezionato = scelto ? scelto.id : null;
    chiediDisegno();
    for (const fn of ascoltatori.selezione) fn(scelto);
  }

  tela.addEventListener('pointerup', finePuntatore);
  tela.addEventListener('pointercancel', (evento) => {
    puntatori.delete(evento.pointerId);
    ultimaDistanza = 0;
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
    aSchermo,
    vai({ lat, lng, zoom: z }) {
      centro = { lat, lng };
      if (z !== undefined) zoom = Math.max(ZOOM_MIN, Math.min(zoomMassimo(), z));
      chiediDisegno();
      avvisaMovimento();
    },
    zoomAvanti: () => cambiaZoom(zoom + 1),
    zoomIndietro: () => cambiaZoom(zoom - 1),
    mostraSpot(elenco) {
      spot = elenco;
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
    riprova,
    su(evento, fn) {
      if (ascoltatori[evento]) ascoltatori[evento].push(fn);
    },
    ridisegna: chiediDisegno,
    distruggi() {
      vivo = false;
      osservatore.disconnect();
      window.removeEventListener('online', riprova);
      tela.remove();
    },
  };
}
