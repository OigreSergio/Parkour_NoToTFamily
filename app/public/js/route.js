/* PkFAMILY — quanto manca, e come ci si arriva.
 *
 * La distanza in linea d'aria si calcola qui, sul dispositivo, e funziona
 * sempre: è il numero che serve davvero per decidere se andare a uno spot.
 * Il tragitto a piedi, invece, lo sa solo un motore di routing: si chiede
 * quando c'è rete, su richiesta esplicita, e la posizione parte arrotondata a
 * ~110 m — la stessa regola che applica il servizio del repository
 * (remote-service/pkremote/services/routing.py, masterplan 6.4).
 */

import { CONFIG } from './config.js';
import { arrotonda, distanzaM, tempoStimato } from './geo.js';

/** Distanza e tempi stimati, senza rete. */
export function stima(da, a) {
  const metri = distanzaM(da, a);
  return {
    metri,
    cammino: tempoStimato(metri, CONFIG.andature.cammino),
    corsa: tempoStimato(metri, CONFIG.andature.corsa),
  };
}

function coordinate(punto) {
  const p = arrotonda(punto, CONFIG.routing.decimali);
  return `${p.lat},${p.lng}`;
}

async function daServizio(da, a) {
  const base = CONFIG.routing.servizio.replace(/\/$/, '');
  const indirizzo = `${base}/api/v1/route?from=${coordinate(da)}&to=${coordinate(a)}`;
  const risposta = await fetch(indirizzo, { headers: { Accept: 'application/json' } });
  if (!risposta.ok) throw new Error(`percorso non disponibile (${risposta.status})`);
  const dati = await risposta.json();
  return {
    metri: dati.distance_m,
    secondi: dati.duration_s,
    precisione: dati.precision_m,
    punti: (dati.geometry?.coordinates || []).map(([lng, lat]) => ({ lat, lng })),
  };
}

async function daPubblico(da, a) {
  const p1 = arrotonda(da, CONFIG.routing.decimali);
  const p2 = arrotonda(a, CONFIG.routing.decimali);
  const indirizzo =
    `${CONFIG.routing.pubblico}${p1.lng},${p1.lat};${p2.lng},${p2.lat}` +
    '?overview=full&geometries=geojson';
  const risposta = await fetch(indirizzo);
  if (!risposta.ok) throw new Error(`percorso non disponibile (${risposta.status})`);
  const dati = await risposta.json();
  const primo = (dati.routes || [])[0];
  if (!primo) throw new Error('nessun percorso');
  return {
    metri: primo.distance,
    secondi: primo.duration,
    precisione: 111,
    punti: (primo.geometry?.coordinates || []).map(([lng, lat]) => ({ lat, lng })),
  };
}

/**
 * Il tragitto a piedi fra due punti. Richiede rete.
 * Se è configurato il servizio del repository passa da lì (cache e log
 * ripuliti); altrimenti dal server pubblico OSRM, come fa già
 * `scripts/web/pk-route.js`.
 */
export async function percorso(da, a) {
  if (!navigator.onLine) throw new Error('offline');
  return CONFIG.routing.servizio ? daServizio(da, a) : daPubblico(da, a);
}
