/* PkFAMILY — distanza & percorso verso lo spot (modalità test).
 *
 * Caricato da index.html accanto al bundle Expo. Il bundle patchato espone:
 *   - globalThis.__pkMap   → istanza MapLibre della mappa principale
 *   - il pulsante "Distanza & percorso" sulla scheda spot, che chiama
 *     globalThis.__pkRoute({id, name, lat, lng})
 *
 * Percorso "PK": profilo pedonale OSRM (server pubblico FOSSGIS) che, a
 * differenza dei percorsi in auto, passa per scalinate, vicoli, ponti
 * pedonali e attraversa i parchi — lo spostamento urbano vero. Il motore
 * self-hosted con pesi parkour è descritto in docs/ROUTING_PK.md.
 */
(function () {
  'use strict';

  var ROUTER = 'https://routing.openstreetmap.de/routed-foot/route/v1/foot/';
  var WALK_KMH = 4.5;
  var RUN_KMH = 9;
  var panel = null;
  var watchId = null;
  var lastPos = null;

  function haversineM(a, b) {
    var R = 6371000, rad = Math.PI / 180;
    var dLat = (b.lat - a.lat) * rad, dLng = (b.lng - a.lng) * rad;
    var s = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(a.lat * rad) * Math.cos(b.lat * rad) *
      Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.sqrt(s));
  }

  function fmtDist(m) {
    return m < 1000 ? Math.round(m) + ' m' : (m / 1000).toFixed(m < 10000 ? 1 : 0) + ' km';
  }

  function fmtEta(m, kmh) {
    var min = Math.round((m / 1000) / kmh * 60);
    if (min < 60) return min + ' min';
    return Math.floor(min / 60) + ' h ' + (min % 60) + ' min';
  }

  function clearRoute() {
    var map = globalThis.__pkMap;
    if (!map) return;
    try {
      if (map.getLayer('pk-route-line')) map.removeLayer('pk-route-line');
      if (map.getLayer('pk-route-casing')) map.removeLayer('pk-route-casing');
      if (map.getSource('pk-route')) map.removeSource('pk-route');
    } catch (e) { /* stile non pronto: niente da pulire */ }
  }

  function drawRoute(coords, dashed) {
    var map = globalThis.__pkMap;
    if (!map) return;
    clearRoute();
    map.addSource('pk-route', {
      type: 'geojson',
      data: { type: 'Feature', geometry: { type: 'LineString', coordinates: coords } }
    });
    map.addLayer({
      id: 'pk-route-casing', type: 'line', source: 'pk-route',
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#000', 'line-width': 7, 'line-opacity': 0.55 }
    });
    map.addLayer({
      id: 'pk-route-line', type: 'line', source: 'pk-route',
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: dashed
        ? { 'line-color': '#ffd166', 'line-width': 3.5, 'line-dasharray': [1.2, 1.6] }
        : { 'line-color': '#ffd166', 'line-width': 4 }
    });
    var lats = coords.map(function (c) { return c[1]; });
    var lngs = coords.map(function (c) { return c[0]; });
    map.fitBounds(
      [[Math.min.apply(null, lngs), Math.min.apply(null, lats)],
       [Math.max.apply(null, lngs), Math.max.apply(null, lats)]],
      { padding: { top: 70, bottom: 220, left: 40, right: 40 }, duration: 900 }
    );
  }

  function el(tag, style, text) {
    var e = document.createElement(tag);
    if (style) e.style.cssText = style;
    if (text) e.textContent = text;
    return e;
  }

  function button(label, primary) {
    return el('button',
      'flex:1;min-width:0;padding:10px 8px;border:0;border-radius:10px;' +
      'font:600 13px system-ui,sans-serif;cursor:pointer;' +
      (primary ? 'background:#ffd166;color:#1a1a1a;' : 'background:#333;color:#eee;'),
      label);
  }

  function closePanel() {
    if (watchId !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchId);
    watchId = null;
    if (panel) { panel.remove(); panel = null; }
    clearRoute();
  }

  globalThis.__pkRoute = function (spot) {
    closePanel();
    panel = el('div',
      'position:fixed;left:10px;right:10px;bottom:calc(84px + env(safe-area-inset-bottom));' +
      'z-index:9999;background:#1c1c1eee;backdrop-filter:blur(6px);border-radius:14px;' +
      'padding:12px 14px;color:#eee;font:14px system-ui,sans-serif;' +
      'box-shadow:0 6px 24px rgba(0,0,0,.5);display:flex;flex-direction:column;gap:8px');

    var head = el('div', 'display:flex;align-items:center;gap:8px');
    head.appendChild(el('div', 'font-weight:800;flex:1;font-size:15px', '🧭 ' + spot.name));
    var x = el('button', 'background:none;border:0;color:#aaa;font-size:18px;cursor:pointer;padding:2px 6px', '✕');
    x.onclick = closePanel;
    head.appendChild(x);
    panel.appendChild(head);

    var info = el('div', 'color:#ccc;line-height:1.45', 'Cerco la tua posizione… 📡');
    panel.appendChild(info);

    var row = el('div', 'display:flex;gap:8px');
    var pkBtn = button('🥾 Percorso PK', true);
    var gmBtn = button('🗺️ Google Maps', false);
    row.appendChild(pkBtn);
    row.appendChild(gmBtn);
    panel.appendChild(row);
    var credit = el('div', 'color:#777;font-size:10px', 'Percorso pedonale © OpenStreetMap / FOSSGIS — scale e scorciatoie incluse');
    panel.appendChild(credit);
    document.body.appendChild(panel);

    gmBtn.onclick = function () {
      window.open('https://www.google.com/maps/dir/?api=1&destination=' +
        spot.lat + ',' + spot.lng + '&travelmode=walking', '_blank');
    };

    function updateInfo() {
      if (!lastPos) return;
      var d = haversineM(lastPos, spot);
      info.textContent = '📏 ' + fmtDist(d) + ' in linea d’aria · \u{1F6B6} ' +
        fmtEta(d, WALK_KMH) + ' · \u{1F3C3} ' + fmtEta(d, RUN_KMH);
    }

    if (!navigator.geolocation) {
      info.textContent = 'GPS non disponibile su questo dispositivo.';
    } else {
      watchId = navigator.geolocation.watchPosition(function (p) {
        lastPos = { lat: p.coords.latitude, lng: p.coords.longitude };
        updateInfo();
      }, function () {
        info.textContent = 'Posizione negata: attiva il GPS per distanza e percorso.';
      }, { enableHighAccuracy: true, maximumAge: 15000, timeout: 12000 });
    }

    pkBtn.onclick = function () {
      if (!lastPos) { info.textContent = 'Aspetto il GPS… riprova tra un attimo. 📱'; return; }
      pkBtn.disabled = true;
      pkBtn.textContent = '⏳ Calcolo…';
      var url = ROUTER + lastPos.lng + ',' + lastPos.lat + ';' + spot.lng + ',' + spot.lat +
        '?overview=full&geometries=geojson&steps=false';
      var signal = (typeof AbortSignal !== 'undefined' && AbortSignal.timeout)
        ? AbortSignal.timeout(12000) : undefined;
      fetch(url, { signal: signal }).then(function (r) { return r.json(); }).then(function (j) {
        var route = j && j.routes && j.routes[0];
        if (!route) throw new Error('no route');
        drawRoute(route.geometry.coordinates, false);
        info.textContent = '🤾 Percorso PK: ' + fmtDist(route.distance) +
          ' · 🚶 ' + fmtEta(route.distance, WALK_KMH) +
          ' · 🏃 ' + fmtEta(route.distance, RUN_KMH);
      }).catch(function () {
        drawRoute([[lastPos.lng, lastPos.lat], [spot.lng, spot.lat]], true);
        info.textContent = 'Router non raggiungibile: linea diretta indicativa. ⚠️';
      }).finally(function () {
        pkBtn.disabled = false;
        pkBtn.textContent = '🥾 Percorso PK';
      });
    };
  };
})();
