/* PkFAMILY — galleria foto dello spot (modalità test).
 *
 * Caricato da index.html accanto al bundle Expo, come pk-route.js. Il bundle
 * patchato espone:
 *   - globalThis.__PK_PHOTOS__  → { <id spot>: [ {url, kind, caption, …} ] },
 *     costruito da scripts/data/webapp_fixed_spots.json in fase di patch
 *   - il pulsante "Foto" sulla scheda spot, che chiama
 *     globalThis.__pkPhotos({id, name})
 *
 * Ogni foto porta con sé autore, licenza e link all'originale: le immagini
 * riusate da Wikimedia Commons sono CC BY / CC BY-SA, che obbligano a citarli
 * ovunque l'immagine venga mostrata. Il badge "zona" distingue una foto del
 * contesto da una foto degli ostacoli veri, così nessuno scende in strada
 * aspettandosi qualcosa che nella foto non c'era.
 */
(function () {
  'use strict';

  var overlay = null;
  var index = 0;
  var photos = [];

  function el(tag, style, text) {
    var e = document.createElement(tag);
    if (style) e.style.cssText = style;
    if (text) e.textContent = text;
    return e;
  }

  function close() {
    if (overlay) { overlay.remove(); overlay = null; }
    document.removeEventListener('keydown', onKey);
  }

  function onKey(e) {
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowRight') show(index + 1);
    else if (e.key === 'ArrowLeft') show(index - 1);
  }

  var img, caption, credit, counter;

  function show(i) {
    if (!photos.length) return;
    index = (i + photos.length) % photos.length;
    var p = photos[index];
    img.src = p.url;
    img.alt = p.caption || '';
    caption.textContent = (p.kind === 'area' ? '📍 zona · ' : '') + (p.caption || '');
    credit.textContent = '';
    // Attribuzione: autore + licenza, con link alla pagina originale quando c'è.
    var bits = [];
    if (p.author) bits.push(p.author);
    if (p.license) bits.push(p.license);
    if (p.source) bits.push(p.source);
    if (bits.length) {
      if (p.source_url) {
        var a = document.createElement('a');
        a.href = p.source_url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.textContent = bits.join(' · ');
        a.style.cssText = 'color:#9ab;text-decoration:underline';
        credit.appendChild(a);
      } else {
        credit.textContent = bits.join(' · ');
      }
    }
    counter.textContent = (index + 1) + ' / ' + photos.length;
  }

  function empty(name) {
    var box = el('div',
      'max-width:420px;text-align:center;color:#ddd;font:15px system-ui,sans-serif;' +
      'line-height:1.5;padding:0 24px');
    box.appendChild(el('div', 'font-size:40px;margin-bottom:10px', '📷'));
    box.appendChild(el('div', 'font-weight:700;margin-bottom:6px',
      'Ancora nessuna foto di ' + name));
    box.appendChild(el('div', 'color:#aaa;font-size:13px',
      'Questo spot è in mappa ma non l’ha ancora fotografato nessuno. ' +
      'Se ci passi, mandaci uno scatto: finisce qui.'));
    return box;
  }

  globalThis.__pkPhotos = function (spot) {
    close();
    photos = (globalThis.__PK_PHOTOS__ || {})[spot.id] || [];

    overlay = el('div',
      'position:fixed;inset:0;z-index:10000;background:#000000ee;' +
      'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px');
    overlay.onclick = function (e) { if (e.target === overlay) close(); };

    var head = el('div',
      'position:absolute;top:0;left:0;right:0;display:flex;align-items:center;gap:8px;' +
      'padding:calc(10px + env(safe-area-inset-top)) 14px 10px;' +
      'color:#eee;font:600 15px system-ui,sans-serif');
    head.appendChild(el('div', 'flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;' +
      'white-space:nowrap', spot.name));
    counter = el('div', 'color:#999;font-size:13px;font-weight:400');
    head.appendChild(counter);
    var x = el('button',
      'background:none;border:0;color:#aaa;font-size:22px;cursor:pointer;padding:2px 8px', '✕');
    x.onclick = close;
    head.appendChild(x);
    overlay.appendChild(head);

    if (!photos.length) {
      overlay.appendChild(empty(spot.name));
      document.body.appendChild(overlay);
      document.addEventListener('keydown', onKey);
      return;
    }

    img = document.createElement('img');
    img.style.cssText = 'max-width:94vw;max-height:66vh;border-radius:12px;' +
      'object-fit:contain;background:#111';
    overlay.appendChild(img);

    caption = el('div',
      'color:#ddd;font:14px system-ui,sans-serif;max-width:90vw;text-align:center;' +
      'line-height:1.4;padding:0 12px');
    overlay.appendChild(caption);

    credit = el('div',
      'color:#888;font:11px system-ui,sans-serif;max-width:90vw;text-align:center;padding:0 12px');
    overlay.appendChild(credit);

    if (photos.length > 1) {
      var nav = el('div', 'display:flex;gap:10px;margin-top:4px');
      var prev = el('button',
        'padding:9px 18px;border:0;border-radius:10px;background:#333;color:#eee;' +
        'font:600 13px system-ui,sans-serif;cursor:pointer', '‹ Prec');
      var next = el('button',
        'padding:9px 18px;border:0;border-radius:10px;background:#333;color:#eee;' +
        'font:600 13px system-ui,sans-serif;cursor:pointer', 'Succ ›');
      prev.onclick = function () { show(index - 1); };
      next.onclick = function () { show(index + 1); };
      nav.appendChild(prev);
      nav.appendChild(next);
      overlay.appendChild(nav);
    }

    document.body.appendChild(overlay);
    document.addEventListener('keydown', onKey);
    show(0);
  };
})();
