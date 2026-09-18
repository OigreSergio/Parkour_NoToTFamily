/* PkFAMILY — dove sei.
 *
 * La posizione resta sul dispositivo (principio 3 del masterplan): non viene
 * salvata su disco, non finisce in nessun registro, non viene inviata a
 * nessuno. Vive in memoria finché l'app è aperta, e serve solo a ordinare gli
 * spot per vicinanza e a disegnare il puntino sulla mappa. L'unico momento in
 * cui può uscire è il calcolo di un percorso, arrotondata (js/route.js).
 */

let ultima = null;
let osservazione = null;

export function ultimaNota() {
  return ultima;
}

/** Chiede la posizione una volta sola. Rifiuta se il permesso non c'è. */
export function chiedi(opzioni = {}) {
  return new Promise((risolvi, rifiuta) => {
    if (!navigator.geolocation) {
      rifiuta(new Error('geolocalizzazione non disponibile'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (posizione) => {
        ultima = {
          lat: posizione.coords.latitude,
          lng: posizione.coords.longitude,
          precisione: posizione.coords.accuracy,
        };
        risolvi(ultima);
      },
      (errore) => rifiuta(errore),
      {
        enableHighAccuracy: opzioni.precisa !== false,
        timeout: opzioni.attesa || 10000,
        maximumAge: 30000,
      }
    );
  });
}

/** Segue la posizione mentre ci si muove verso uno spot. */
export function segui(quandoCambia) {
  if (!navigator.geolocation || osservazione !== null) return;
  osservazione = navigator.geolocation.watchPosition(
    (posizione) => {
      ultima = {
        lat: posizione.coords.latitude,
        lng: posizione.coords.longitude,
        precisione: posizione.coords.accuracy,
      };
      quandoCambia(ultima);
    },
    () => {},
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
  );
}

export function smetti() {
  if (osservazione !== null) {
    navigator.geolocation.clearWatch(osservazione);
    osservazione = null;
  }
}
