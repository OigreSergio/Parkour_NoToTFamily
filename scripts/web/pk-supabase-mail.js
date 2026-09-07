/* Invio vero del codice, via Supabase Auth.
 *
 * La pagina è statica: non può spedire posta da sola, e una chiave di un
 * provider messa qui dentro sarebbe pubblica per chiunque apra la pagina —
 * cioè regalata. Supabase invece è già l'auth della web app, la sua
 * publishable key è fatta apposta per stare nei client (le RLS restano), e il
 * suo mailer manda una mail vera. Quindi il codice arriva in casella, non a
 * schermo.
 *
 * Due conseguenze da conoscere, e sono scritte anche nella pagina:
 *  - l'account che nasce è un account vero sul progetto Supabase;
 *  - il mailer integrato di Supabase è limitato (poche mail all'ora) ed è
 *    pensato per le prove: in produzione va configurato un SMTP o l'API di un
 *    provider, che è quello che fa il backend di questo repo.
 */
(function () {
  'use strict';

  var SUPABASE_URL = 'https://gkdzdtxqkftebrxhgway.supabase.co';
  var SUPABASE_KEY = 'sb_publishable_Xi0aGU8lnV182kEKpsmU3w__uAkFVXg';

  function chiama(path, corpo) {
    return fetch(SUPABASE_URL + '/auth/v1' + path, {
      method: 'POST',
      headers: {
        apikey: SUPABASE_KEY,
        Authorization: 'Bearer ' + SUPABASE_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(corpo)
    }).then(function (r) {
      return r.text().then(function (testo) {
        var dati = null;
        try { dati = testo ? JSON.parse(testo) : null; } catch (e) { dati = null; }
        return { ok: r.ok, status: r.status, dati: dati };
      });
    });
  }

  function messaggio(esito, ripiego) {
    var d = esito.dati || {};
    var testo = d.msg || d.message || d.error_description || d.error || '';
    if (esito.status === 429) {
      return 'Supabase limita le mail di prova a poche all’ora. Riprova più ' +
        'tardi, oppure collega un backend con ?api= (vedi docs/PROVA_DA_TELEFONO.md).';
    }
    return testo || ripiego;
  }

  globalThis.PkSupabaseMail = {
    url: SUPABASE_URL,

    /** Chiede il codice: Supabase spedisce la mail. */
    chiediCodice: function (email) {
      return chiama('/otp', { email: email, create_user: true }).then(function (esito) {
        if (!esito.ok) {
          var e = new Error(messaggio(esito, 'non siamo riusciti a mandare la mail'));
          e.status = esito.status;
          throw e;
        }
        return true;
      });
    },

    /** Verifica il codice ricevuto per posta. */
    verificaCodice: function (email, codice) {
      return chiama('/verify', {
        type: 'email', email: email, token: codice
      }).then(function (esito) {
        if (!esito.ok) {
          var e = new Error(messaggio(esito, 'codice non valido o scaduto'));
          e.status = esito.status;
          throw e;
        }
        return esito.dati;
      });
    }
  };
})();
