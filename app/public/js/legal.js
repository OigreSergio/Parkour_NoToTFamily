/* PkFAMILY — l'avviso sui rischi, prima di uno spot o di un tutorial.
 *
 * Il testo è lo stesso che `scripts/web/pk-legal.js` mostra quando il backend
 * non risponde: il punto che conta non può dipendere dalla rete, e in un'app
 * che nasce per funzionare offline deve essere sempre disponibile. Sta nei
 * file delle lingue, non qui dentro.
 *
 * L'accettazione resta sul dispositivo. Alzando `VERSIONE` l'avviso torna
 * davanti a tutti: è il motivo per cui è un numero e non un booleano.
 */

import { t } from './i18n.js';
import { leggi, scrivi } from './store.js';
import { modale } from './ui.js';

export const VERSIONE = 1;

const in_corso = new Map();

/**
 * Mostra l'avviso se non è già stato accettato in questa versione.
 * `tipo` è 'spot' o 'tutorial'. Restituisce true se si può procedere.
 */
export async function avvisa(tipo) {
  const chiave = `legale.${tipo}`;
  const accettata = await leggi(chiave, 0);
  if (accettata >= VERSIONE) return true;

  // Due tap ravvicinati non devono aprire due volte la stessa finestra.
  if (in_corso.has(tipo)) return in_corso.get(tipo);

  const promessa = modale({
    titolo: t('legal.title'),
    sommario: t(`legal.summary.${tipo}`),
    punti: [t('legal.point.risk'), t('legal.point.liability'), t('legal.point.places'), t('legal.point.role')],
    azioni: [
      { testo: t('legal.accept'), valore: true, primaria: true },
      { testo: t('legal.decline'), valore: false },
    ],
  }).then(async (accettato) => {
    if (accettato) await scrivi(chiave, VERSIONE);
    in_corso.delete(tipo);
    return Boolean(accettato);
  });

  in_corso.set(tipo, promessa);
  return promessa;
}

/** Dimentica le accettazioni: serve alla voce "ricomincia da zero". */
export async function dimentica() {
  await scrivi('legale.spot', undefined);
  await scrivi('legale.tutorial', undefined);
}
