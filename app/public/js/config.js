/* PkFAMILY — le poche cose che si cambiano senza toccare il codice.
 *
 * Nessun segreto qui dentro: la chiave pubblicabile di Supabase può stare in
 * un client (è fatta per quello, le RLS restano), la chiave segreta no, mai.
 * Finché `supabase.url` è vuoto l'app resta locale: mostra i dati che porta
 * con sé e non chiama nessuno.
 */

export const CONFIG = {
  /** Sorgenti di tessere. La prima è quella predefinita. */
  tiles: {
    mappa: {
      nome: 'Mappa',
      url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      zoomMax: 19,
      crediti: '© OpenStreetMap contributors',
    },
    satellite: {
      nome: 'Satellite',
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      zoomMax: 19,
      crediti: 'Esri, Maxar, Earthstar Geographics',
    },
  },

  /** Percorsi a piedi. Il servizio di supporto del repo, se configurato,
   *  ha la precedenza: arrotonda le coordinate e non le scrive nei log
   *  (remote-service/pkremote/services/routing.py). */
  routing: {
    servizio: '', // es. 'https://pkremote.esempio' → GET /api/v1/route
    pubblico: 'https://routing.openstreetmap.de/routed-foot/route/v1/foot/',
    /** Cifre decimali con cui la posizione parte da qui: 3 = ~110 m. */
    decimali: 3,
  },

  /** Velocità usate per la stima dei tempi, in km/h. */
  andature: { cammino: 4.5, corsa: 9 },

  supabase: { url: '', publishableKey: '' },

  /** Dove si apre la mappa la prima volta: Roma, dove stanno gli spot della famiglia. */
  partenza: { lat: 41.9, lng: 12.48, zoom: 11 },

  /** Quante tessere al massimo scarica il pulsante "prepara l'area". */
  tettoPrefetch: 900,
};
