/* PkFAMILY — pop-up informativi sui rischi.
 *
 * Caricato accanto al bundle Expo, come pk-route.js. Non dipende da niente:
 * niente framework, niente CSS esterno, nessuna build.
 *
 * I testi arrivano da GET /api/v1/legal/documents e sono versionati lato
 * server: alzare la versione di un documento lo rimette davanti a tutti senza
 * toccare una riga di questo file. L'accettazione si registra su
 * POST /api/v1/legal/accept quando c'è una sessione, e comunque in
 * localStorage — così un utente non si ritrova lo stesso pop-up a ogni tap.
 *
 *   PkLegal.gate('spot_risk')      → Promise<boolean>, blocca finché non si sceglie
 *   PkLegal.gateSpot()             → prima di aprire la scheda di uno spot
 *   PkLegal.gateTutorial()         → prima di far partire un tutorial
 *   PkLegal.reset()                → dimentica le accettazioni locali (debug)
 *
 * Se il backend non risponde il pop-up compare lo stesso, con il testo minimo
 * qui sotto: un avviso sui rischi che fallisce in silenzio non è un avviso.
 */
(function () {
  'use strict';

  var API = globalThis.__PK_API__ || 'https://api.notot.family';
  var STORE = 'pkfam.notices';
  var SESSION = 'pkfam.session';

  // Rete irraggiungibile: si mostra questo. Dice solo la frase che conta, così
  // non può divergere dal testo vero — che resta quello servito dall'API.
  var FALLBACK = {
    id: 'liability_offline',
    version: 0,
    title: 'Prima di allenarti',
    summary: 'Non riusciamo a caricare l’informativa completa. Il punto, però, è questo.',
    bullets: [
      'Il parkour comporta un rischio reale e non eliminabile di infortunio, anche grave.',
      'La responsabilità di un infortunio in uno spot segnalato qui, o mentre segui un tutorial pubblicato qui, è esclusivamente tua.',
      'Gli spot sono luoghi di terzi: non li gestiamo, non li controlliamo e non garantiamo che siano sicuri.',
      'La piattaforma si impegna solo a rendere disponibili le informazioni in modo gratuito e facilmente accessibile.'
    ],
    body: '',
    blocking: true,
    accept_label: 'Ho capito, procedo sotto la mia responsabilità',
    decline_label: 'Torna indietro'
  };

  var docsPromise = null;

  // --- storage ---------------------------------------------------------------

  function read(key) {
    try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch (e) { return null; }
  }

  function write(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* modalità privata */ }
  }

  function accepted(id, version) {
    var seen = read(STORE) || {};
    return seen[id] === version;
  }

  function remember(id, version) {
    var seen = read(STORE) || {};
    seen[id] = version;
    write(STORE, seen);
  }

  function token() {
    var s = read(SESSION);
    return (s && s.access_token) || null;
  }

  // --- rete ------------------------------------------------------------------

  function loadDocuments() {
    if (docsPromise) return docsPromise;
    docsPromise = fetch(API + '/api/v1/legal/documents')
      .then(function (r) { return r.ok ? r.json() : []; })
      .catch(function () { return []; });
    return docsPromise;
  }

  function reportAcceptance(doc) {
    var t = token();
    if (!t || !doc.version) return;
    fetch(API + '/api/v1/legal/accept', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + t },
      body: JSON.stringify({ documents: [{ id: doc.id, version: doc.version }] })
    }).catch(function () { /* riprova al prossimo avvio: la copia locale c'è */ });
  }

  // --- interfaccia -----------------------------------------------------------

  function injectStyle() {
    if (document.getElementById('pk-legal-style')) return;
    var css = [
      '.pk-legal-backdrop{position:fixed;inset:0;z-index:99999;background:rgba(8,8,10,.72);',
      'display:flex;align-items:flex-end;justify-content:center;padding:0;',
      'font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;-webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px)}',
      '@media (min-width:560px){.pk-legal-backdrop{align-items:center;padding:24px}}',
      '.pk-legal-card{background:#fbf7ef;color:#1c1a17;width:100%;max-width:520px;max-height:88vh;',
      'overflow:auto;border-radius:18px 18px 0 0;padding:22px 20px 20px;box-shadow:0 -8px 40px rgba(0,0,0,.4)}',
      '@media (min-width:560px){.pk-legal-card{border-radius:18px}}',
      '.pk-legal-card h2{margin:0 0 6px;font-size:19px;line-height:1.25}',
      '.pk-legal-card p.pk-sum{margin:0 0 14px;color:#5c554a;font-size:14px;line-height:1.45}',
      '.pk-legal-card ul{margin:0 0 16px;padding-left:20px}',
      '.pk-legal-card li{margin:0 0 9px;font-size:14px;line-height:1.5}',
      '.pk-legal-full{border-top:1px solid #e4dccb;margin-top:6px;padding-top:12px}',
      '.pk-legal-full summary{cursor:pointer;font-size:13px;color:#8a6a3d;font-weight:600}',
      '.pk-legal-body{font-size:13px;line-height:1.6;white-space:pre-wrap;color:#3a352e;margin-top:10px}',
      '.pk-legal-actions{display:flex;flex-direction:column;gap:9px;margin-top:18px}',
      '.pk-legal-actions button{font:inherit;font-size:15px;padding:13px 16px;border-radius:12px;border:0;cursor:pointer}',
      '.pk-legal-accept{background:#cd7862;color:#fff;font-weight:600}',
      '.pk-legal-accept:active{background:#b96a55}',
      '.pk-legal-decline{background:transparent;color:#6b645a;text-decoration:underline}'
    ].join('');
    var el = document.createElement('style');
    el.id = 'pk-legal-style';
    el.textContent = css;
    document.head.appendChild(el);
  }

  function show(doc) {
    injectStyle();
    return new Promise(function (resolve) {
      var backdrop = document.createElement('div');
      backdrop.className = 'pk-legal-backdrop';
      backdrop.setAttribute('role', 'dialog');
      backdrop.setAttribute('aria-modal', 'true');

      var card = document.createElement('div');
      card.className = 'pk-legal-card';

      var h = document.createElement('h2');
      h.textContent = doc.title;
      card.appendChild(h);

      var sum = document.createElement('p');
      sum.className = 'pk-sum';
      sum.textContent = doc.summary;
      card.appendChild(sum);

      var ul = document.createElement('ul');
      (doc.bullets || []).forEach(function (b) {
        var li = document.createElement('li');
        li.textContent = b;
        ul.appendChild(li);
      });
      card.appendChild(ul);

      if (doc.body) {
        var details = document.createElement('details');
        details.className = 'pk-legal-full';
        var summary = document.createElement('summary');
        summary.textContent = 'Leggi il testo completo';
        var body = document.createElement('div');
        body.className = 'pk-legal-body';
        body.textContent = doc.body;
        details.appendChild(summary);
        details.appendChild(body);
        card.appendChild(details);
      }

      var actions = document.createElement('div');
      actions.className = 'pk-legal-actions';

      var ok = document.createElement('button');
      ok.className = 'pk-legal-accept';
      ok.textContent = doc.accept_label || 'Ho letto e accetto';

      var no = document.createElement('button');
      no.className = 'pk-legal-decline';
      no.textContent = doc.decline_label || 'Non accetto';

      function close(result) {
        backdrop.remove();
        resolve(result);
      }

      ok.addEventListener('click', function () {
        if (doc.version) {
          remember(doc.id, doc.version);
          reportAcceptance(doc);
        }
        close(true);
      });
      no.addEventListener('click', function () { close(false); });

      // Niente chiusura con Esc o tap fuori: è un avviso da leggere, non un
      // banner cookie. L'unica via d'uscita è una delle due scelte.
      actions.appendChild(ok);
      actions.appendChild(no);
      card.appendChild(actions);
      backdrop.appendChild(card);
      document.body.appendChild(backdrop);
      ok.focus();
    });
  }

  // --- API pubblica ----------------------------------------------------------

  function gate(documentId) {
    return loadDocuments().then(function (docs) {
      var doc = null;
      for (var i = 0; i < docs.length; i++) {
        if (docs[i].id === documentId) { doc = docs[i]; break; }
      }
      if (!doc) doc = FALLBACK;
      if (doc.version && accepted(doc.id, doc.version)) return true;
      return show(doc);
    });
  }

  globalThis.PkLegal = {
    gate: gate,
    // Esposta perché pk-onboarding.js disegna le sue schermate con queste
    // stesse classi: senza, la prima finestra che si apre — l'accesso, per chi
    // arriva dal QR — uscirebbe senza stile, perché fin lì nessun pop-up è
    // stato mostrato e il foglio non è mai stato iniettato.
    injectStyle: injectStyle,
    // La versione già accettata in questo browser, o null. Serve a chi deve
    // *dichiarare* l'accettazione al server senza rimostrare il pop-up a chi
    // l'ha già letto.
    acceptedVersion: function (documentId) {
      var seen = read(STORE) || {};
      return Object.prototype.hasOwnProperty.call(seen, documentId) ? seen[documentId] : null;
    },
    gateSpot: function () { return gate('spot_risk'); },
    gateTutorial: function () { return gate('tutorial_risk'); },
    documents: loadDocuments,
    show: show,
    reset: function () { write(STORE, {}); },
    FALLBACK: FALLBACK
  };
})();
