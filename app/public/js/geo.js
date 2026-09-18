/* PkFAMILY — geometria: distanze, proiezione, formattazione.
 *
 * Tutto si calcola sul dispositivo. La posizione di chi usa l'app non esce
 * da qui: l'unico punto in cui può partire è il calcolo di un percorso, che
 * si chiede esplicitamente e parte arrotondato (vedi js/route.js).
 */

const RAGGIO_TERRA_M = 6371000;
const RAD = Math.PI / 180;

/** Distanza in metri fra due punti, formula dell'emisenoverso. */
export function distanzaM(a, b) {
  const dLat = (b.lat - a.lat) * RAD;
  const dLng = (b.lng - a.lng) * RAD;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(a.lat * RAD) * Math.cos(b.lat * RAD) * Math.sin(dLng / 2) ** 2;
  return 2 * RAGGIO_TERRA_M * Math.asin(Math.sqrt(s));
}

/** Metri → "840 m" oppure "12,3 km". Unità metriche ovunque (masterplan 3.9). */
export function formattaDistanza(metri, lingua = 'it') {
  if (!Number.isFinite(metri)) return '';
  if (metri < 1000) return `${Math.round(metri)} m`;
  const km = metri / 1000;
  return `${km.toLocaleString(lingua, { maximumFractionDigits: km < 10 ? 1 : 0 })} km`;
}

/** Secondi → "18 min" oppure "1 h 05 min". */
export function formattaDurata(secondi) {
  const minuti = Math.max(1, Math.round(secondi / 60));
  if (minuti < 60) return `${minuti} min`;
  return `${Math.floor(minuti / 60)} h ${String(minuti % 60).padStart(2, '0')} min`;
}

/** Tempo stimato per percorrere `metri` a una data andatura (km/h). */
export function tempoStimato(metri, kmh) {
  return (metri / 1000 / kmh) * 3600;
}

// --- proiezione di Mercatore ------------------------------------------------
// x e y sono in "pixel del mondo" al livello di zoom richiesto: la mappa non
// fa altro che spostare e ritagliare questo piano.

export const LATO_TESSERA = 256;

export function latLngAPixel(lat, lng, zoom) {
  const scala = LATO_TESSERA * 2 ** zoom;
  const x = ((lng + 180) / 360) * scala;
  const seno = Math.sin(Math.max(-85.05112878, Math.min(85.05112878, lat)) * RAD);
  const y = (0.5 - Math.log((1 + seno) / (1 - seno)) / (4 * Math.PI)) * scala;
  return { x, y };
}

export function pixelALatLng(x, y, zoom) {
  const scala = LATO_TESSERA * 2 ** zoom;
  const lng = (x / scala) * 360 - 180;
  const n = Math.PI - 2 * Math.PI * (y / scala);
  const lat = (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
  return { lat, lng };
}

/** Arrotonda un punto a `decimali` cifre: si usa prima di mandarlo fuori. */
export function arrotonda(punto, decimali) {
  const fattore = 10 ** decimali;
  return {
    lat: Math.round(punto.lat * fattore) / fattore,
    lng: Math.round(punto.lng * fattore) / fattore,
  };
}

/** Il punto sta dentro il rettangolo? */
export function dentro(punto, riquadro) {
  return (
    punto.lat >= riquadro.sud &&
    punto.lat <= riquadro.nord &&
    punto.lng >= riquadro.ovest &&
    punto.lng <= riquadro.est
  );
}
