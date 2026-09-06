/* PkFAMILY — accesso con codice via email e domande di profilo.
 *
 * Va caricato dopo pk-legal.js (ne riusa lo stile e i pop-up dei rischi).
 *
 *   PkOnboarding.open()      → apre il flusso e risolve true quando è completo
 *   PkOnboarding.session()/signOut()
 *   PkOnboarding.guestKey()  → la chiave dell'account anonimo, se ce n'è uno
 *
 * Si entra in due modi: con l'email (codice a sei cifre) oppure senza dire
 * niente. Il guest non fornisce email né nome — glieli dà il server — ma
 * risponde alle stesse domande, perché vede gli stessi spot e gli stessi
 * tutorial. La chiave che riceve alla creazione è l'unico modo per ritrovare
 * quell'account: senza, le risposte e i livelli sbloccati morirebbero con la
 * scheda del browser.
 *
 * Il flusso lo decide il server: si chiede GET /onboarding/state, si disegna
 * la schermata per `next_step` con le opzioni che arrivano, si manda la
 * risposta, si ripete. Le etichette dei pulsanti non sono scritte qui — così
 * una build vecchia non può proporre scelte che il server non riconosce più,
 * né saltare un passaggio.
 */
(function () {
  'use strict';

  var API = globalThis.__PK_API__ || 'https://api.notot.family';
  var SESSION = 'pkfam.session';
  var GUEST_KEY = 'pkfam.guestKey';

  function read(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } }
  function write(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* privata */ } }
  function session() { return read(SESSION); }
  function guestKey() { return read(GUEST_KEY); }
  function token() { var s = session(); return (s && s.access_token) || null; }

  function api(path, options) {
    options = options || {};
    var headers = options.headers || {};
    if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
    var t = token();
    if (t) headers.Authorization = 'Bearer ' + t;
    return fetch(API + '/api/v1' + path, {
      method: options.method || 'GET',
      headers: headers,
      body: options.body instanceof FormData ? options.body : (options.body ? JSON.stringify(options.body) : undefined)
    }).then(function (r) {
      return r.text().then(function (text) {
        var payload = null;
        try { payload = text ? JSON.parse(text) : null; } catch (e) { payload = null; }
        if (!r.ok) {
          var err = new Error('http ' + r.status);
          err.status = r.status;
          err.payload = payload;
          throw err;
        }
        return payload;
      });
    });
  }

  function message(err) {
    if (err && err.payload && err.payload.error && err.payload.error.message) {
      return err.payload.error.message;
    }
    if (err && err.status === 429) return 'Troppi tentativi. Riprova fra un minuto.';
    return 'Qualcosa non ha funzionato. Riprova.';
  }

  // --- guscio ----------------------------------------------------------------

  function injectStyle() {
    // Il guscio (sfondo scuro, card, pulsanti) è quello di pk-legal.js: va
    // iniettato anche quando si entra dall'accesso senza aver visto prima un
    // pop-up, che è il caso normale di chi apre l'app per la prima volta.
    if (globalThis.PkLegal && globalThis.PkLegal.injectStyle) {
      globalThis.PkLegal.injectStyle();
    }
    if (document.getElementById('pk-onb-style')) return;
    var css = [
      '.pk-onb-field{display:block;width:100%;font:inherit;font-size:16px;padding:12px 14px;',
      'border:1px solid #d9cfba;border-radius:12px;background:#fff;color:#1c1a17;margin:0 0 12px;box-sizing:border-box}',
      '.pk-onb-code{letter-spacing:.4em;text-align:center;font-size:24px}',
      '.pk-onb-label{display:block;font-size:13px;color:#5c554a;margin:0 0 6px}',
      '.pk-onb-choice{display:block;width:100%;text-align:left;font:inherit;font-size:15px;padding:14px 16px;',
      'margin:0 0 9px;border:1px solid #e0d6c2;border-radius:12px;background:#fff;color:#1c1a17;cursor:pointer}',
      '.pk-onb-choice:hover{border-color:#cd7862}',
      '.pk-onb-choice[aria-pressed="true"]{border-color:#cd7862;background:#fdeee9}',
      '.pk-onb-error{color:#a8392a;font-size:13px;margin:0 0 12px;min-height:1em}',
      '.pk-onb-note{color:#6b645a;font-size:12px;line-height:1.5;margin:12px 0 0}',
      '.pk-onb-clue{font-size:15px;line-height:1.5;margin:0 0 14px}',
      '.pk-onb-step{font-size:12px;color:#8a8378;margin:0 0 4px;text-transform:uppercase;letter-spacing:.08em}'
    ].join('');
    var el = document.createElement('style');
    el.id = 'pk-onb-style';
    el.textContent = css;
    document.head.appendChild(el);
  }

  function shell() {
    injectStyle();
    var backdrop = document.createElement('div');
    backdrop.className = 'pk-legal-backdrop';
    backdrop.setAttribute('role', 'dialog');
    backdrop.setAttribute('aria-modal', 'true');
    var card = document.createElement('div');
    card.className = 'pk-legal-card';
    backdrop.appendChild(card);
    document.body.appendChild(backdrop);
    return {
      card: card,
      close: function () { backdrop.remove(); }
    };
  }

  function render(card, parts) {
    card.textContent = '';
    parts.forEach(function (node) { if (node) card.appendChild(node); });
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function button(label, onClick, className) {
    var b = el('button', className || 'pk-legal-accept', label);
    b.addEventListener('click', onClick);
    return b;
  }

  function actions(children) {
    var wrap = el('div', 'pk-legal-actions');
    children.forEach(function (c) { if (c) wrap.appendChild(c); });
    return wrap;
  }

  // --- passaggi --------------------------------------------------------------

  function askEntry(card) {
    return new Promise(function (resolve, reject) {
      render(card, [
        el('p', 'pk-onb-step', 'Accesso'),
        el('h2', null, 'Come vuoi entrare?'),
        el('p', 'pk-sum', 'In entrambi i casi ti facciamo le stesse domande: servono a proporti esercizi adatti.'),
        button('Con la mia email', function () { resolve('email'); }, 'pk-onb-choice'),
        button('Senza account, resto anonimo', function () { resolve('guest'); }, 'pk-onb-choice'),
        actions([button('Annulla', function () { reject(new Error('cancelled')); }, 'pk-legal-decline')]),
        el('p', 'pk-onb-note', 'Senza account non chiediamo né email né nome: te ne diamo uno noi. Ti daremo una chiave da conservare, perché è l’unico modo per ritrovare questo profilo.')
      ]);
    });
  }

  function startGuest(card) {
    return globalThis.PkLegal.documents()
      .then(function (docs) {
        var waiver = docs.filter(function (d) { return d.id === 'liability_waiver'; })[0];
        if (!waiver) return null;
        // Stesso gate dell'email: un guest vede gli stessi spot, quindi corre
        // lo stesso rischio.
        return globalThis.PkLegal.show(waiver).then(function (ok) {
          return ok ? [{ id: waiver.id, version: waiver.version }] : null;
        });
      })
      .then(function (acceptedDocs) {
        if (acceptedDocs === null) return null;
        return api('/auth/guest', { method: 'POST', body: { accepted_documents: acceptedDocs } });
      })
      .then(function (res) {
        if (!res) return null;
        write(SESSION, res.tokens);
        if (res.guest_key) write(GUEST_KEY, res.guest_key);
        return showGuestKey(card, res);
      });
  }

  function showGuestKey(card, res) {
    return new Promise(function (resolve) {
      var key = el('input', 'pk-onb-field');
      key.readOnly = true;
      key.value = res.guest_key || '';
      var note = el('p', 'pk-onb-note', '');

      render(card, [
        el('p', 'pk-onb-step', 'Account anonimo'),
        el('h2', null, 'Da qui in poi sei ' + res.display_name),
        el('p', 'pk-sum', 'Nome generato: non dice niente di te. Questa è la tua chiave — la vedi una volta sola.'),
        key,
        actions([
          button('Copia la chiave', function () {
            key.select();
            var copied = navigator.clipboard
              ? navigator.clipboard.writeText(key.value)
              : Promise.reject();
            copied.then(
              function () { note.textContent = 'Copiata. Incollala dove non la perdi.'; },
              function () { note.textContent = 'Selezionala e copiala a mano.'; }
            );
          }, 'pk-onb-choice'),
          button('L’ho salvata, continua', function () { resolve(res); })
        ]),
        note,
        el('p', 'pk-onb-note', 'Serve a ritrovare questo profilo su un altro dispositivo, o se cancelli i dati del browser. Senza, l’avanzamento resta solo qui.')
      ]);
    });
  }

  function askEmail(card) {
    return new Promise(function (resolve, reject) {
      var input = el('input', 'pk-onb-field');
      input.type = 'email';
      input.autocomplete = 'email';
      input.placeholder = 'nome@esempio.it';
      var error = el('p', 'pk-onb-error', '');
      var go = button('Mandami il codice', function () {
        var value = (input.value || '').trim();
        if (!value || value.indexOf('@') < 0) { error.textContent = 'Serve un indirizzo email valido.'; return; }
        go.disabled = true;
        error.textContent = '';
        api('/auth/email/request-code', { method: 'POST', body: { email: value } })
          .then(function (res) { resolve({ email: value, sent: res }); })
          .catch(function (err) { go.disabled = false; error.textContent = message(err); });
      });

      render(card, [
        el('p', 'pk-onb-step', 'Accesso'),
        el('h2', null, 'Entra con la tua email'),
        el('p', 'pk-sum', 'Niente password: ti mandiamo un codice di sei cifre, valido dieci minuti.'),
        el('label', 'pk-onb-label', 'Email'),
        input,
        error,
        actions([go, button('Annulla', function () { reject(new Error('cancelled')); }, 'pk-legal-decline')]),
        el('p', 'pk-onb-note', 'Il codice arriva da un indirizzo che non legge le risposte. Se non lo vedi, controlla lo spam.')
      ]);
      input.focus();
    });
  }

  function askCode(card, email, hint) {
    return new Promise(function (resolve, reject) {
      var input = el('input', 'pk-onb-field pk-onb-code');
      input.inputMode = 'numeric';
      input.autocomplete = 'one-time-code';
      input.maxLength = 6;
      input.placeholder = '000000';
      if (hint && hint.debug_code) input.value = hint.debug_code; // solo fuori produzione
      var error = el('p', 'pk-onb-error', '');
      var name = el('input', 'pk-onb-field');
      name.placeholder = 'Come ti chiamiamo? (facoltativo)';
      name.maxLength = 80;

      var go = button('Entra', function () {
        var code = (input.value || '').trim();
        if (code.length < 4) { error.textContent = 'Inserisci il codice che ti è arrivato.'; return; }
        go.disabled = true;
        error.textContent = '';
        // L'account nasce solo dopo l'informativa: il pop-up è il gate, non
        // una casella da spuntare in fondo a un modulo.
        globalThis.PkLegal.documents()
          .then(function (docs) {
            var waiver = docs.filter(function (d) { return d.id === 'liability_waiver'; })[0];
            if (!waiver) {
              return globalThis.PkLegal.gate('liability_waiver').then(function (ok) {
                return ok ? [] : null;
              });
            }
            // Il server vuole l'informativa a ogni accesso, non solo alla
            // creazione. A chi l'ha già letta in questo browser non si
            // rimostra: si dichiara la versione e si va avanti.
            if (globalThis.PkLegal.acceptedVersion(waiver.id) === waiver.version) {
              return [{ id: waiver.id, version: waiver.version }];
            }
            return globalThis.PkLegal.show(waiver).then(function (ok) {
              return ok ? [{ id: waiver.id, version: waiver.version }] : null;
            });
          })
          .then(function (acceptedDocs) {
            if (acceptedDocs === null) { go.disabled = false; return null; }
            return api('/auth/email/verify-code', {
              method: 'POST',
              body: {
                email: email,
                code: code,
                display_name: (name.value || '').trim() || null,
                accepted_documents: acceptedDocs
              }
            });
          })
          .then(function (res) {
            if (!res) return;
            write(SESSION, res.tokens);
            resolve(res);
          })
          .catch(function (err) { go.disabled = false; error.textContent = message(err); });
      });

      // Il server dice chi gestisce la casella (lo legge dall'MX del dominio):
      // "aprilo su Gmail" fa risparmiare il giro di cercare dove sia finita.
      var dove = (hint && hint.provider_label && hint.provider_label !== 'il tuo provider')
        ? ' Aprilo su ' + hint.provider_label + '.'
        : '';

      render(card, [
        el('p', 'pk-onb-step', 'Accesso'),
        el('h2', null, 'Il codice che ti è arrivato'),
        el('p', 'pk-sum', 'Mandato a ' + email + '. Scade fra dieci minuti.' + dove),
        input,
        name,
        error,
        actions([go, button('Cambia indirizzo', function () { reject(new Error('back')); }, 'pk-legal-decline')])
      ]);
      input.focus();
    });
  }

  function askBirthDate(card) {
    return new Promise(function (resolve) {
      var input = el('input', 'pk-onb-field');
      input.type = 'date';
      var error = el('p', 'pk-onb-error', '');

      var go = button('Continua', function () {
        var value = input.value;
        if (!value) { error.textContent = 'Serve la data di nascita.'; return; }
        go.disabled = true;
        error.textContent = '';
        var minor = ageFrom(value) < 18;
        var consent = minor
          ? globalThis.PkLegal.documents().then(function (docs) {
              var doc = docs.filter(function (d) { return d.id === 'minor_guardian'; })[0];
              if (!doc) return null;
              return globalThis.PkLegal.show(doc).then(function (ok) {
                return ok ? [{ id: doc.id, version: doc.version }] : null;
              });
            })
          : Promise.resolve([]);

        consent.then(function (docs) {
          if (docs === null) { go.disabled = false; return null; }
          return api('/onboarding/birth-date', {
            method: 'POST',
            body: { birth_date: value, accepted_documents: docs }
          });
        }).then(function (state) {
          if (state) resolve(state);
        }).catch(function (err) { go.disabled = false; error.textContent = message(err); });
      });

      render(card, [
        el('p', 'pk-onb-step', 'Profilo'),
        el('h2', null, 'Quando sei nato?'),
        el('p', 'pk-sum', 'Serve a proporti esercizi adatti. Resta sul server: non viene mostrato a nessuno, nemmeno a te.'),
        input,
        error,
        actions([go])
      ]);
      input.focus();
    });
  }

  function ageFrom(iso) {
    var d = new Date(iso + 'T00:00:00');
    var now = new Date();
    var years = now.getFullYear() - d.getFullYear();
    var before = now.getMonth() < d.getMonth() ||
      (now.getMonth() === d.getMonth() && now.getDate() < d.getDate());
    return before ? years - 1 : years;
  }

  function askChoice(card, opts) {
    return new Promise(function (resolve) {
      var error = el('p', 'pk-onb-error', '');
      var nodes = opts.options.map(function (option) {
        return button(option.label, function () {
          api(opts.path, { method: 'POST', body: opts.payload(option.value) })
            .then(resolve)
            .catch(function (err) { error.textContent = message(err); });
        }, 'pk-onb-choice');
      });
      render(card, [
        el('p', 'pk-onb-step', 'Profilo'),
        el('h2', null, opts.title),
        opts.summary ? el('p', 'pk-sum', opts.summary) : null,
        error
      ].concat(nodes));
    });
  }

  function askCertificate(card) {
    return new Promise(function (resolve) {
      var body = el('input', 'pk-onb-field');
      body.placeholder = 'Ente che ha rilasciato il certificato';
      var cert = el('input', 'pk-onb-field');
      cert.type = 'file';
      cert.accept = 'application/pdf,image/*';
      var doc = el('input', 'pk-onb-field');
      doc.type = 'file';
      doc.accept = 'application/pdf,image/*';
      var error = el('p', 'pk-onb-error', '');

      var go = button('Invia per la verifica', function () {
        if (!body.value.trim() || !cert.files[0] || !doc.files[0]) {
          error.textContent = 'Servono l’ente, il certificato e il documento.';
          return;
        }
        go.disabled = true;
        error.textContent = '';
        var form = new FormData();
        form.append('issuing_body', body.value.trim());
        form.append('certificate', cert.files[0]);
        form.append('identity_document', doc.files[0]);
        api('/onboarding/instructor-certificate', { method: 'POST', body: form })
          .then(function () { return api('/onboarding/state'); })
          .then(resolve)
          .catch(function (err) { go.disabled = false; error.textContent = message(err); });
      });

      render(card, [
        el('p', 'pk-onb-step', 'Profilo'),
        el('h2', null, 'Il tuo certificato'),
        el('p', 'pk-sum', 'Certificato rilasciato da un ente riconosciuto a livello nazionale, più un documento che confermi che è intestato a te.'),
        el('label', 'pk-onb-label', 'Ente'),
        body,
        el('label', 'pk-onb-label', 'Certificato (PDF o foto)'),
        cert,
        el('label', 'pk-onb-label', 'Documento d’identità (PDF o foto)'),
        doc,
        error,
        actions([go]),
        el('p', 'pk-onb-note', 'I due file vengono inoltrati alla casella che verifica gli spot e non restano sui nostri server. La qualifica la approva una persona.')
      ]);
      body.focus();
    });
  }

  function playQuiz(card) {
    return api('/onboarding/quiz', { method: 'POST' }).then(function (quiz) {
      return new Promise(function (resolve, reject) {
        var answers = quiz.questions.map(function () { return null; });
        var index = 0;

        function draw() {
          var q = quiz.questions[index];
          var nodes = q.options.map(function (option, i) {
            var b = button(option, function () {
              answers[index] = i;
              if (index < quiz.questions.length - 1) { index += 1; draw(); }
              else { finish(); }
            }, 'pk-onb-choice');
            b.setAttribute('aria-pressed', answers[index] === i ? 'true' : 'false');
            return b;
          });
          render(card, [
            el('p', 'pk-onb-step', 'Movimento ' + (index + 1) + ' di ' + quiz.questions.length),
            el('h2', null, quiz.title),
            index === 0 ? el('p', 'pk-sum', quiz.intro) : null,
            el('p', 'pk-onb-clue', q.clue)
          ].concat(nodes).concat([
            index > 0 ? actions([button('Indietro', function () { index -= 1; draw(); }, 'pk-legal-decline')]) : null
          ]));
        }

        function finish() {
          render(card, [el('h2', null, 'Un attimo…')]);
          api('/onboarding/quiz/answers', {
            method: 'POST',
            body: { attempt_id: quiz.attempt_id, answers: answers }
          }).then(showResult).catch(reject);
        }

        function showResult(result) {
          // Le correzioni si vedono sempre: chi sbaglia esce sapendo i nomi,
          // che è metà del motivo per cui il gioco esiste.
          var list = el('ul');
          result.corrections.forEach(function (c) {
            var suffix = c.is_correct
              ? ''
              : (c.given_answer ? ' — avevi detto ' + c.given_answer : ' — saltata');
            list.appendChild(el('li', null, (c.is_correct ? '\u2713 ' : '\u2717 ') + c.correct_answer + suffix));
          });
          render(card, [
            el('p', 'pk-onb-step', result.score + ' su ' + result.total),
            el('h2', null, result.passed ? 'Ci siamo.' : 'Ci sta.'),
            el('p', 'pk-sum', result.message),
            list,
            actions([
              button('Continua', function () { api('/onboarding/state').then(resolve, reject); }),
              button('Rigioca', function () { playQuiz(card).then(resolve, reject); }, 'pk-legal-decline')
            ])
          ]);
        }

        draw();
      });
    });
  }

  // --- ciclo -----------------------------------------------------------------

  function advance(card, state) {
    switch (state.next_step) {
      case 'birth_date':
        return askBirthDate(card).then(function (next) { return advance(card, next); });
      case 'practitioner_type':
        return askChoice(card, {
          title: 'Come ti muovi qui dentro?',
          summary: null,
          options: state.practitioner_options,
          path: '/onboarding/practitioner-type',
          payload: function (v) { return { practitioner_type: v }; }
        }).then(function (next) { return advance(card, next); });
      case 'experience':
        return askChoice(card, {
          title: 'Da quanto pratichi parkour?',
          summary: 'Da qui dipendono i livelli che ti proponiamo. Il gioco dopo serve a tararli.',
          options: state.experience_options,
          path: '/onboarding/experience',
          payload: function (v) { return { experience_band: v }; }
        }).then(function (next) { return advance(card, next); });
      case 'instructor_certificate':
        return askCertificate(card).then(function (next) { return advance(card, next); });
      case 'experience_quiz':
        return playQuiz(card).then(function (next) { return advance(card, next || { next_step: 'done' }); });
      default:
        return Promise.resolve(true);
    }
  }

  function open() {
    var view = shell();

    function withEmail() {
      return askEmail(view.card)
        .then(function (step) {
          return askCode(view.card, step.email, step.sent)
            .catch(function (err) {
              if (err && err.message === 'back') return withEmail();
              throw err;
            });
        });
    }

    function signIn() {
      return askEntry(view.card).then(function (mode) {
        if (mode === 'guest') {
          return startGuest(view.card).then(function (res) {
            // Informativa rifiutata: si torna alla scelta, non si prosegue.
            return res ? res : signIn();
          });
        }
        return withEmail();
      });
    }

    var start;
    if (token()) {
      start = api('/onboarding/state');
    } else if (guestKey()) {
      // Ritorno di un anonimo: la chiave vale al posto della password.
      start = api('/auth/guest/resume', { method: 'POST', body: { guest_key: guestKey() } })
        .then(function (res) {
          write(SESSION, res.tokens);
          return api('/onboarding/state');
        })
        .catch(function () {
          // Chiave non più valida: si riparte dalla scelta iniziale.
          write(GUEST_KEY, null);
          return signIn().then(function () { return api('/onboarding/state'); });
        });
    } else {
      start = signIn().then(function () { return api('/onboarding/state'); });
    }

    return start
      .then(function (state) { return advance(view.card, state); })
      .then(function () {
        view.close();
        return true;
      })
      .catch(function (err) {
        view.close();
        if (err && (err.message === 'cancelled' || err.message === 'back')) return false;
        throw err;
      });
  }

  globalThis.PkOnboarding = {
    open: open,
    session: session,
    guestKey: guestKey,
    // Non cancella la chiave: uscire non deve voler dire buttare via il
    // profilo anonimo, che senza chiave non si recupera più.
    signOut: function () { write(SESSION, null); },
    forgetGuest: function () { write(GUEST_KEY, null); write(SESSION, null); },
    api: api
  };
})();
