#!/usr/bin/env python3
"""Genera pk-scheda.js (+ pk-scheda-spots.json): il contesto visivo dentro la
scheda dell'app PkFAMILY.

Segue il pattern di pk-route.js (gh-pages): un file JS autonomo caricato da
index.html accanto al bundle Expo. Quando la family apre la scheda di uno
spot (rotta /spot/{id}) lo script aggiunge in fondo alla scheda la sezione
"Contesto visivo": miniatura Street View puntata sullo spot (come copertina
se la galleria è vuota), seconda angolazione o foto della zona con licenza,
vista aerea, panorama 360° inline, link a Google Street View, e i contenuti
Instagram collegati allo spot (post/reel incorporabili, profili, pagina del
luogo con le foto geotaggate lì).

La struttura vale per TUTTI gli spot della mappa, non solo per i 26 della
family:

- i 26 spot della family stanno inline in pk-scheda.js (scheda immediata,
  funziona anche se il file dati non si carica);
- tutti gli spot fissi (family + ~1700 community della lista Google Maps)
  stanno in pk-scheda-spots.json, che lo script scarica una sola volta alla
  prima scheda aperta;
- uno spot che non è in nessuno dei due (es. segnalato dalla family dopo
  l'ultimo build) viene risolto al volo: dati dello spot da Supabase (chiave
  pubblica, RLS attive) e panorama dallo stesso endpoint pubblico usato da
  fetch_streetview.py, direttamente dal browser (JSONP).

Dati in ingresso:
    docs/demo/spots-streetview.json       panorami dei 24 spot del backup (con override manuali)
    docs/demo/spots-streetview-all.json   panorami di tutti gli spot fissi (fetch_streetview_all.py)
    scripts/data/webapp_fixed_spots.json  nomi, descrizioni (→ città) e status
    docs/spots/instagram.json             contenuti Instagram collegati agli spot
    + le foto curate qui sotto (CURATED)

Uso:
    python3 docs/demo/tools/build_pk_scheda.py
    # scrive docs/demo/pk-scheda.js e docs/demo/pk-scheda-spots.json
    # (entrambi da copiare nella root di gh-pages: scripts/deploy_pk_scheda.sh)
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
STREETVIEW = REPO / "docs" / "demo" / "spots-streetview.json"
STREETVIEW_ALL = REPO / "docs" / "demo" / "spots-streetview-all.json"
FIXED = REPO / "scripts" / "data" / "webapp_fixed_spots.json"
INSTAGRAM = REPO / "docs" / "spots" / "instagram.json"
OUT_JS = REPO / "docs" / "demo" / "pk-scheda.js"
OUT_JSON = REPO / "docs" / "demo" / "pk-scheda-spots.json"

# Progetto Supabase dell'app: URL e chiave *publishable* (la stessa che il
# bundle web espone a ogni visitatore; le RLS restano attive, solo lettura
# pubblica degli spot). Serve al fallback per gli spot nati dopo il build.
SUPABASE_URL = "https://gkdzdtxqkftebrxhgway.supabase.co"
SUPABASE_KEY = "sb_publishable_Xi0aGU8lnV182kEKpsmU3w__uAkFVXg"

# Foto di contesto curate a mano (le stesse della pagina demo e del seed),
# verificate una a una: solo dove mostrano davvero la zona dello spot.
CURATED = {
    "Foro Italico — Stadio dei Marmi": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Stadio_dei_marmi_009.jpg/960px-Stadio_dei_marmi_009.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Stadio_dei_marmi_009.jpg",
        "credit": "Wikimedia Commons · Pubblico dominio",
    },
    "EUR Laghetto": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Roma_EUR_Laghetto_vista_dal_basso.jpg/960px-Roma_EUR_Laghetto_vista_dal_basso.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Roma_EUR_Laghetto_vista_dal_basso.jpg",
        "credit": "Wikimedia Commons · CC BY-SA 3.0 IT",
    },
    "Colle Oppio Park": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Parco_Del_Colle_Oppio_-_panoramio.jpg/960px-Parco_Del_Colle_Oppio_-_panoramio.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Parco_Del_Colle_Oppio_-_panoramio.jpg",
        "credit": "Wikimedia Commons · CC BY 3.0",
    },
    "Villa Borghese — Piazza di Siena": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/Plaza_de_Siena%2C_Villa_Borghese%2C_Roma%2C_Italia%2C_2022-09-14%2C_DD_14.jpg/960px-Plaza_de_Siena%2C_Villa_Borghese%2C_Roma%2C_Italia%2C_2022-09-14%2C_DD_14.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Plaza_de_Siena,_Villa_Borghese,_Roma,_Italia,_2022-09-14,_DD_14.jpg",
        "credit": "Wikimedia Commons · CC BY-SA 4.0",
    },
    "Spot Colonne Colosseo": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Colonne_Tempio_Venere_Colosseo_Roma_09feb08.jpg/960px-Colonne_Tempio_Venere_Colosseo_Roma_09feb08.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Colonne_Tempio_Venere_Colosseo_Roma_09feb08.jpg",
        "credit": "Wikimedia Commons · CC BY-SA 3.0",
    },
    "Garbatella — Scalinate": {
        "src": "https://live.staticflickr.com/34/72998499_c2311608eb_b.jpg",
        "page": "https://www.flickr.com/photos/93226994@N00/72998499",
        "credit": "antmoose (Flickr) · CC BY 2.0",
    },
    "Spot Metro Colosseo": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Colosseo_-_panoramio_%2810%29.jpg/960px-Colosseo_-_panoramio_%2810%29.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Colosseo_-_panoramio_(10).jpg",
        "credit": "Wikimedia Commons · CC BY 3.0",
    },
    "Spot EUR": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bd/2024-05-06-Palazzo-dello-Sport-2.jpg/960px-2024-05-06-Palazzo-dello-Sport-2.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:2024-05-06-Palazzo-dello-Sport-2.jpg",
        "credit": "Wikimedia Commons · CC BY-SA 4.0",
    },
    "Spot Corviale 1": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Corviale_%285582072620%29.jpg/960px-Corviale_%285582072620%29.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Corviale_(5582072620).jpg",
        "credit": "Wikimedia Commons · Pubblico dominio",
    },
    "Spot Corviale 2": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Municipio_XI_%28Roma%29_in_2020.03.jpg/960px-Municipio_XI_%28Roma%29_in_2020.03.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Municipio_XI_(Roma)_in_2020.03.jpg",
        "credit": "Wikimedia Commons · CC BY-SA 4.0",
    },
    "Spot Corviale 3": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Municipio_XI_%28Roma%29_in_2020.02.jpg/960px-Municipio_XI_%28Roma%29_in_2020.02.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Municipio_XI_(Roma)_in_2020.02.jpg",
        "credit": "Wikimedia Commons · CC BY-SA 4.0",
    },
    "Spot Primavalle": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Largo_borromeo_primavalle_roma.jpg/960px-Largo_borromeo_primavalle_roma.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Largo_borromeo_primavalle_roma.jpg",
        "credit": "Wikimedia Commons · CC BY-SA 4.0",
    },
    "Spot Villa Carpegna": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Roma_-_Villa_Carpegna_innevata_-_panoramio.jpg/960px-Roma_-_Villa_Carpegna_innevata_-_panoramio.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Roma_-_Villa_Carpegna_innevata_-_panoramio.jpg",
        "credit": "Wikimedia Commons · CC BY 3.0",
    },
    "Spot Colosseo — Monte Oppio": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Parc_Colle_Oppio_-_Rome_%28IT62%29_-_2021-08-29_-_1.jpg/960px-Parc_Colle_Oppio_-_Rome_%28IT62%29_-_2021-08-29_-_1.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Parc_Colle_Oppio_-_Rome_(IT62)_-_2021-08-29_-_1.jpg",
        "credit": "Wikimedia Commons · CC BY-SA 4.0",
    },
}

TEMPLATE = r"""/* PkFAMILY — contesto visivo nella scheda spot.
 *
 * Generato da docs/demo/tools/build_pk_scheda.py — NON modificare a mano.
 * Caricato da index.html accanto al bundle Expo (stesso pattern di
 * pk-route.js). Interviene SOLO sulla rotta /spot/{id}: quando la family
 * apre la scheda, in fondo compaiono la miniatura Street View puntata
 * sullo spot come COPERTINA al posto di \u201CAncora nessuna foto\u201D, il
 * panorama 360\u00B0 apribile inline, una foto della zona (con licenza) o una
 * seconda angolazione Street View, la vista aerea, il link a Google Street
 * View e i contenuti Instagram collegati allo spot (post incorporabili,
 * profili, pagina del luogo con le foto geotaggate l\u00EC).
 * Se lo spot ha gi\u00E0 foto proprie nella galleria, la copertina non viene
 * toccata. Nessuna API key: stessi endpoint pubblici della pagina demo.
 *
 * Copre TUTTI gli spot: i 26 della family sono inline (SPOTS), gli altri
 * ~1700 arrivano da pk-scheda-spots.json (scaricato una volta alla prima
 * scheda), e uno spot nato dopo il build viene risolto al volo (Supabase
 * con chiave pubblica + ricerca del panorama dal browser).
 */
(function () {
  'use strict';

  var SPOTS = __INLINE__;
  var DATA_FILE = 'pk-scheda-spots.json';
  var SUPABASE_URL = '__SUPABASE_URL__';
  var SUPABASE_KEY = '__SUPABASE_KEY__';
  var SCRIPT_BASE = (function () {
    var s = document.currentScript;
    var src = s && s.src ? s.src : '';
    return src ? src.slice(0, src.lastIndexOf('/') + 1) : './';
  })();

  var MONTHS = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];
  var current = null; // id spot attualmente iniettato
  var COVER_TRIES = 20;   // ~14 s di ricerca del placeholder, poi stop
  var INJECT_TRIES = 8;   // ~5.6 s per l'aggancio inline prima del fallback
  var FALLBACK_TRIES = 4; // ulteriori tentativi col pannello flottante
  var attempts = { cover: 0, inject: 0 };
  var extra = null;       // tutti gli spot fissi, da pk-scheda-spots.json
  var extraState = 0;     // 0 da caricare \u00B7 1 in corso \u00B7 2 pronto \u00B7 3 fallito
  var runtime = {};       // id \u2192 spot risolto al volo (false = in corso, null = impossibile)
  var jsonpN = 0;

  function svThumb(sv) {
    return 'https://streetviewpixels-pa.googleapis.com/v1/thumbnail' +
      '?panoid=' + encodeURIComponent(sv.pano_id) + '&cb_client=maps_sv.tactile.gps' +
      '&w=640&h=360&yaw=' + sv.yaw + '&pitch=0&thumbfov=100';
  }
  function svEmbed(sv) {
    return 'https://www.google.com/maps/embed?pb=' +
      '!4v1!6m8!1m7!1s' + sv.pano_id + '!2m2!1d' + sv.pano_lat + '!2d' + sv.pano_lng +
      '!3f' + sv.yaw + '!4f0!5f0.7820865974627469';
  }
  function svOpen(spot) {
    // con un panorama noto apre proprio quello; altrimenti Street View
    // scelto da Google sul punto dello spot
    var u = 'https://www.google.com/maps/@?api=1&map_action=pano' +
      '&viewpoint=' + spot.lat + ',' + spot.lng;
    if (spot.sv) u += '&pano=' + encodeURIComponent(spot.sv.pano_id) + '&heading=' + spot.sv.yaw;
    return u;
  }
  function aerial(spot) {
    var dlng = 0.0015, dlat = 0.0006;
    return 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export' +
      '?bbox=' + (spot.lng - dlng) + ',' + (spot.lat - dlat) + ',' +
      (spot.lng + dlng) + ',' + (spot.lat + dlat) +
      '&bboxSR=4326&size=640,360&imageSR=3857&format=jpg&f=image';
  }
  function svDate(sv) {
    if (!sv.date) return '';
    var p = sv.date.split('-');
    return MONTHS[parseInt(p[1], 10) - 1] + ' ' + p[0];
  }

  // --- geometria (stesse formule di fetch_streetview.py) -------------------
  function bearing(lat1, lng1, lat2, lng2) {
    var rad = Math.PI / 180, p1 = lat1 * rad, p2 = lat2 * rad, dl = (lng2 - lng1) * rad;
    var y = Math.sin(dl) * Math.cos(p2);
    var x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
    return (Math.atan2(y, x) / rad + 360) % 360;
  }
  function distM(lat1, lng1, lat2, lng2) {
    var rad = Math.PI / 180, R = 6371000;
    var dp = (lat2 - lat1) * rad, dl = (lng2 - lng1) * rad;
    var a = Math.sin(dp / 2) * Math.sin(dp / 2) +
      Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dl / 2) * Math.sin(dl / 2);
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  // --- dati: file per tutti gli spot fissi + fallback al volo --------------
  function loadExtra() {
    if (extraState) return;
    extraState = 1;
    fetch(SCRIPT_BASE + DATA_FILE)
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (j) { extra = (j && j.spots) || {}; extraState = 2; })
      .catch(function () { extraState = 3; });
  }

  function jsonp(url) {
    // l'endpoint di ricerca panorami risponde solo in JSONP: tag <script>
    // con callback univoca, timeout di sicurezza, niente residui nel DOM
    return new Promise(function (resolve, reject) {
      var name = '__pkSv' + (++jsonpN);
      var s = document.createElement('script');
      var done = false;
      var timer = setTimeout(function () { finish(); reject(new Error('timeout')); }, 8000);
      function finish() {
        if (done) return;
        done = true;
        clearTimeout(timer);
        window[name] = function () {}; // se arriva tardi non deve rompere nulla
        if (s.parentNode) s.parentNode.removeChild(s);
      }
      window[name] = function (data) { finish(); resolve(data); };
      s.onerror = function () { finish(); reject(new Error('script')); };
      s.src = url + '&callback=' + name;
      document.head.appendChild(s);
    });
  }

  var SV_SEARCH = 'https://maps.googleapis.com/maps/api/js/GeoPhotoService.SingleImageSearch' +
    '?pb=!1m5!1sapiv3!5sUS!11m2!1m1!1b0!2m4!1m2!3d{lat}!4d{lng}!2d{r}' +
    '!3m10!2m2!1sen!2sUS!9m1!1e2!11m4!1m3!1e2!2b1!3e2!4m10!1e1!1e2!1e3!1e4!1e8!1e6!5m1!1e2!6m1!1e2';

  function mkSv(id, plat, plng, date, lat, lng) {
    return {
      pano_id: id, pano_lat: plat, pano_lng: plng,
      yaw: Math.round(bearing(plat, plng, lat, lng) * 10) / 10,
      date: date, distance_m: Math.round(distM(plat, plng, lat, lng))
    };
  }

  function parsePanos(data, lat, lng) {
    // stesso parsing di fetch_streetview.py, sulla forma serializzata
    var blob = JSON.stringify(data);
    var pano = /\[2,"([A-Za-z0-9_-]{20,24})"\]/.exec(blob);
    var coords = /\[null,null,(-?\d{1,2}\.\d+),(-?\d{1,3}\.\d+)\]/.exec(blob);
    if (!pano || !coords) return null;
    var dates = blob.match(/\[(20\d\d),(\d{1,2})\]/g), date = null;
    if (dates) {
      var d = /\[(20\d\d),(\d{1,2})\]/.exec(dates[dates.length - 1]);
      date = d[1] + '-' + (d[2].length < 2 ? '0' + d[2] : d[2]);
    }
    var plat = parseFloat(coords[1]), plng = parseFloat(coords[2]);
    var sv = mkSv(pano[1], plat, plng, date, lat, lng);
    var sv2 = null, best = Infinity, m;
    var re = /\[\[2,"([A-Za-z0-9_-]{20,24})"\],null,\[\[null,null,(-?\d{1,2}\.\d+),(-?\d{1,3}\.\d+)\]/g;
    while ((m = re.exec(blob))) {
      var alat = parseFloat(m[2]), alng = parseFloat(m[3]);
      if (m[1] === pano[1] || distM(plat, plng, alat, alng) < 8) continue; // stessa inquadratura
      var d2 = distM(alat, alng, lat, lng);
      if (d2 < best) { best = d2; sv2 = mkSv(m[1], alat, alng, null, lat, lng); }
    }
    return { sv: sv, sv2: sv2 };
  }

  function findPano(lat, lng) {
    var radii = [50, 120, 300, 600], i = 0;
    function next() {
      if (i >= radii.length) return Promise.resolve(null);
      var url = SV_SEARCH.replace('{lat}', lat).replace('{lng}', lng).replace('{r}', radii[i++]);
      return jsonp(url).then(function (data) { return parsePanos(data, lat, lng) || next(); });
    }
    return next();
  }

  function fetchSpotFromDb(id) {
    if (!SUPABASE_URL || !/^[0-9a-f-]{36}$/.test(id)) return Promise.resolve(null);
    return fetch(SUPABASE_URL + '/rest/v1/spots?select=id,name,lat,lng&id=eq.' + encodeURIComponent(id),
      { headers: { apikey: SUPABASE_KEY, Authorization: 'Bearer ' + SUPABASE_KEY } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (rows) { return rows && rows[0] ? rows[0] : null; });
  }

  function resolveRuntime(id) {
    runtime[id] = false; // in corso
    fetchSpotFromDb(id).then(function (row) {
      var lat = row && Number(row.lat), lng = row && Number(row.lng);
      if (!row || !isFinite(lat) || !isFinite(lng)) { runtime[id] = null; return; }
      var spot = { name: row.name || 'Spot', lat: lat, lng: lng, city: null,
        sv: null, sv2: null, photo: null, ig: null };
      return findPano(lat, lng).catch(function () { return null; }).then(function (p) {
        if (p) { spot.sv = p.sv; spot.sv2 = p.sv2; }
        runtime[id] = spot;
      });
    }).catch(function () { runtime[id] = null; });
  }

  function spotFor(id) {
    if (SPOTS[id]) return SPOTS[id];
    if (extraState === 2 && extra[id]) return extra[id];
    if (runtime[id]) return runtime[id];
    if (extraState === 0) loadExtra();
    if (extraState >= 2 && runtime[id] === undefined) resolveRuntime(id);
    return null; // dati in arrivo: si riprova al prossimo tick
  }

  // --- DOM ------------------------------------------------------------------
  function el(tag, css, text) {
    var e = document.createElement(tag);
    if (css) e.style.cssText = css;
    if (text) e.textContent = text;
    return e;
  }

  function media(src, tagText, tagHref) {
    var wrap = el('div', 'position:relative;border-radius:12px;overflow:hidden;background:#222;margin:0 0 10px');
    var img = el('img', 'width:100%;aspect-ratio:16/9;object-fit:cover;display:block');
    img.loading = 'lazy';
    img.src = src;
    img.onerror = function () { wrap.remove(); };
    wrap.appendChild(img);
    var tag;
    if (tagHref) {
      tag = el('a', '', tagText);
      tag.href = tagHref;
      tag.target = '_blank';
      tag.rel = 'noopener';
    } else {
      tag = el('span', '', tagText);
    }
    tag.style.cssText += 'position:absolute;left:8px;bottom:8px;background:rgba(0,0,0,.62);' +
      'color:#fff;font:11px system-ui,sans-serif;padding:3px 8px;border-radius:6px;text-decoration:none';
    wrap.appendChild(tag);
    return wrap;
  }

  function btn(label, primary) {
    return el('button',
      'flex:1;min-width:120px;padding:10px 8px;border:0;border-radius:10px;cursor:pointer;' +
      'font:600 13px system-ui,sans-serif;' +
      (primary ? 'background:#ffd166;color:#1a1a1a' : 'background:#333;color:#eee'), label);
  }

  // --- Instagram ------------------------------------------------------------
  function igQuery(spot) {
    // "Spot Tor Tre Teste 2" \u2192 "Tor Tre Teste parkour"; la citt\u00E0 si aggiunge
    // solo se non \u00E8 gi\u00E0 nel nome
    var base = spot.name.replace(/^Spot /, '').replace(/\s+\d+$/, '');
    var city = spot.city || '';
    if (city && base.toLowerCase().indexOf(city.toLowerCase()) === -1) base += ' ' + city;
    return base + ' parkour';
  }
  function igLink(spot) {
    // hashtag della family > pagina del luogo (post geotaggati l\u00EC) > ricerca
    var ig = spot.ig;
    if (ig && ig.hashtags && ig.hashtags.length) {
      return 'https://www.instagram.com/explore/tags/' + encodeURIComponent(ig.hashtags[0]) + '/';
    }
    if (ig && ig.location && ig.location.id) {
      return 'https://www.instagram.com/explore/locations/' + ig.location.id + '/' +
        (ig.location.slug ? ig.location.slug + '/' : '');
    }
    return 'https://www.instagram.com/explore/search/keyword/?q=' + encodeURIComponent(igQuery(spot));
  }
  function igEmbedUrl(url) {
    // https://www.instagram.com/[utente/](p|reel)/CODICE/ \u2192 .../CODICE/embed/captioned/
    var m = /instagram\.com\/(?:[^\/]+\/)?(p|reel|tv)\/([A-Za-z0-9_-]+)/.exec(url);
    return m ? 'https://www.instagram.com/' + m[1] + '/' + m[2] + '/embed/captioned/' : url;
  }
  function igPost(p) {
    var card = el('div', 'background:#262628;border-radius:10px;padding:8px 10px;margin:0 0 8px');
    var head = el('div', 'display:flex;align-items:center;gap:8px');
    head.appendChild(el('div', 'flex:1;font:13px/1.3 system-ui,sans-serif;color:#ddd',
      (p.kind === 'reel' ? '\uD83C\uDFAC ' : '\uD83D\uDCF7 ') + (p.title || 'Post Instagram')));
    var open = el('a', 'color:#ffd166;font:600 12px system-ui,sans-serif;text-decoration:none;white-space:nowrap',
      'Apri \u2197');
    open.href = p.url;
    open.target = '_blank';
    open.rel = 'noopener';
    head.appendChild(open);
    card.appendChild(head);
    // il post vero e proprio si carica solo su richiesta (iframe ufficiale
    // di Instagram, pesante): chi vuole dare un'occhiata lo apre qui dentro
    var holder = el('div', 'display:none;margin-top:8px;border-radius:8px;overflow:hidden;background:#fff');
    var show = el('button',
      'margin-top:6px;padding:7px 10px;border:0;border-radius:8px;cursor:pointer;' +
      'background:#333;color:#eee;font:600 12px system-ui,sans-serif', '\u25B6 Mostra il post qui');
    show.onclick = function () {
      if (!holder.firstChild) {
        var f = document.createElement('iframe');
        f.src = igEmbedUrl(p.url);
        f.style.cssText = 'width:100%;height:560px;border:0;display:block';
        f.setAttribute('scrolling', 'no');
        f.setAttribute('allowtransparency', 'true');
        holder.appendChild(f);
      }
      var shown = holder.style.display !== 'none';
      holder.style.display = shown ? 'none' : 'block';
      show.textContent = shown ? '\u25B6 Mostra il post qui' : '\u2715 Nascondi il post';
    };
    card.appendChild(show);
    card.appendChild(holder);
    return card;
  }
  function igBlock(spot) {
    var ig = spot.ig;
    var posts = (ig && ig.posts) || [], accounts = (ig && ig.accounts) || [];
    if (!posts.length && !accounts.length) return null;
    var wrap = el('div', 'margin-top:12px;padding-top:10px;border-top:1px solid #333');
    wrap.appendChild(el('div', 'font:700 13px system-ui,sans-serif;margin-bottom:8px',
      '\uD83D\uDCF7 Dalla community su Instagram'));
    posts.forEach(function (p) { wrap.appendChild(igPost(p)); });
    if (accounts.length) {
      var row = el('div', 'display:flex;gap:6px;flex-wrap:wrap;margin-top:2px');
      accounts.forEach(function (a) {
        var chip = el('a', 'background:#333;color:#eee;font:600 12px system-ui,sans-serif;' +
          'padding:6px 10px;border-radius:999px;text-decoration:none', '@' + a.handle);
        chip.href = 'https://www.instagram.com/' + encodeURIComponent(a.handle) + '/';
        chip.target = '_blank';
        chip.rel = 'noopener';
        if (a.name) chip.title = a.name + (a.why ? ' \u2014 ' + a.why : '');
        row.appendChild(chip);
      });
      wrap.appendChild(row);
    }
    return wrap;
  }
  // altezza reale dei post incorporati (protocollo MEASURE di embed.js)
  window.addEventListener('message', function (e) {
    if (e.origin !== 'https://www.instagram.com') return;
    var d = e.data;
    try { if (typeof d === 'string') d = JSON.parse(d); } catch (err) { return; }
    if (!d || d.type !== 'MEASURE' || !d.details || !d.details.height) return;
    var frames = document.querySelectorAll('#pk-scheda-context iframe');
    for (var i = 0; i < frames.length; i++) {
      if (frames[i].contentWindow === e.source) frames[i].style.height = d.details.height + 'px';
    }
  });

  // --- la sezione ------------------------------------------------------------
  function buildSection(spot) {
    var box = el('div',
      'margin:14px 16px calc(28px + env(safe-area-inset-bottom));padding:14px;border-radius:14px;' +
      'background:#1c1c1e;color:#eee;font:14px system-ui,sans-serif;' +
      'box-shadow:0 2px 10px rgba(0,0,0,.35)');
    box.id = 'pk-scheda-context';

    box.appendChild(el('div', 'font:800 15px system-ui,sans-serif;margin-bottom:10px',
      '\uD83D\uDCF8 Contesto visivo'));

    // La miniatura Street View fa da copertina in testa alla scheda (vedi
    // ensureCover): qui le altre foto del posto \u2014 quella trovata online se
    // esiste, altrimenti una seconda Street View da un'angolazione diversa \u2014
    // pi\u00F9 la vista aerea.
    if (spot.photo) {
      box.appendChild(media(spot.photo.src, 'Foto: ' + spot.photo.credit, spot.photo.page));
    } else if (spot.sv2) {
      box.appendChild(media(svThumb(spot.sv2),
        'Street View \u00B7 altra angolazione \u00B7 ~' + spot.sv2.distance_m + ' m dallo spot'));
    } else if (spot.sv) {
      box.appendChild(media(svThumb(spot.sv),
        'Street View \u00B7 ' + svDate(spot.sv) + ' \u00B7 ~' + spot.sv.distance_m + ' m dallo spot'));
    }
    box.appendChild(media(aerial(spot), 'Vista aerea \u00B7 \u00A9 Esri, Maxar'));

    var row = el('div', 'display:flex;gap:8px;flex-wrap:wrap');
    if (spot.sv) {
      var pano = el('div', 'display:none;margin-top:10px;border-radius:12px;overflow:hidden');
      var b360 = btn('\uD83C\uDF10 Esplora a 360\u00B0', true);
      b360.onclick = function () {
        if (!pano.firstChild) {
          var f = document.createElement('iframe');
          f.src = svEmbed(spot.sv);
          f.style.cssText = 'width:100%;height:300px;border:0;display:block';
          f.allowFullscreen = true;
          pano.appendChild(f);
        }
        var open = pano.style.display !== 'none';
        pano.style.display = open ? 'none' : 'block';
        b360.textContent = open ? '\uD83C\uDF10 Esplora a 360\u00B0' : '\u2715 Chiudi il 360\u00B0';
      };
      row.appendChild(b360);
    }
    var bOpen = btn('\uD83D\uDEB6 Apri in Street View', !spot.sv);
    bOpen.onclick = function () { window.open(svOpen(spot), '_blank'); };
    row.appendChild(bOpen);
    box.appendChild(row);
    if (spot.sv) box.appendChild(pano);

    // Contenuti della community: "Su Instagram" apre la pagina del luogo
    // (le foto geotaggate proprio l\u00EC) quando la conosciamo, altrimenti la
    // ricerca gi\u00E0 compilata per QUESTO spot; i video restano su YouTube.
    var row2 = el('div', 'display:flex;gap:8px;flex-wrap:wrap;margin-top:8px');
    var bIg = btn('\uD83D\uDCF7 Su Instagram', false);
    bIg.title = spot.ig && spot.ig.hashtags && spot.ig.hashtags.length ? '#' + spot.ig.hashtags[0] :
      spot.ig && spot.ig.location ? 'Foto geotaggate: ' + spot.ig.location.name : 'Cerca lo spot su Instagram';
    bIg.onclick = function () { window.open(igLink(spot), '_blank'); };
    var bYt = btn('\uD83C\uDFAC Video community', false);
    bYt.onclick = function () {
      window.open('https://www.youtube.com/results?search_query=' +
        encodeURIComponent(igQuery(spot)), '_blank');
    };
    row2.appendChild(bIg);
    row2.appendChild(bYt);
    box.appendChild(row2);

    var ig = igBlock(spot);
    if (ig) box.appendChild(ig);

    box.appendChild(el('div', 'color:#777;font-size:10px;margin-top:10px',
      'Immagini \u00A9 Google Street View \u00B7 foto Wikimedia/Flickr con licenza \u00B7 aeree \u00A9 Esri' +
      (ig ? ' \u00B7 post Instagram \u00A9 dei rispettivi autori' : '')));
    return box;
  }

  function ensureCover(spot) {
    // Copertina: se la galleria nativa \u00E8 vuota (placeholder \u201CAncora
    // nessuna foto\u201D), la prima immagine \u2014 la Street View puntata sullo
    // spot \u2014 prende il suo posto. Con foto vere gi\u00E0 presenti non tocca nulla.
    // Le scansioni del DOM sono LIMITATE (attempts): senza placeholder \u2014
    // galleria piena o scheda lenta \u2014 dopo un po' si smette, niente lavoro
    // inutile a ogni tick su telefoni lenti.
    if (!spot.sv) return;
    if (attempts.cover >= COVER_TRIES) return;
    if (document.getElementById('pk-scheda-cover')) return;
    attempts.cover++;
    var root = document.getElementById('root');
    if (!root) return;
    var nodes = root.querySelectorAll('div,span');
    var textEl = null;
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].children.length === 0 &&
          nodes[i].textContent.trim() === 'Ancora nessuna foto') { textEl = nodes[i]; break; }
    }
    if (!textEl) return;
    var boxEl = textEl.parentElement; // il placeholder con emoji + testo
    if (!boxEl) return;
    boxEl.style.position = 'relative';
    var img = el('img', 'position:absolute;inset:0;width:100%;height:100%;' +
      'object-fit:cover;display:block;z-index:1');
    img.id = 'pk-scheda-cover';
    img.alt = 'Street View: ' + spot.name;
    img.src = svThumb(spot.sv);
    img.onerror = function () { img.remove(); };
    var tag = el('span',
      'position:absolute;left:10px;bottom:10px;z-index:2;background:rgba(0,0,0,.62);' +
      'color:#fff;font:11px system-ui,sans-serif;padding:3px 8px;border-radius:6px',
      'Street View \u00B7 ' + svDate(spot.sv) + ' \u00B7 ~' + spot.sv.distance_m + ' m dallo spot');
    tag.id = 'pk-scheda-cover-tag';
    boxEl.appendChild(img);
    boxEl.appendChild(tag);
  }

  function findScrollHost(name) {
    // La scheda \u00E8 una ScrollView (div con overflow-y auto) che contiene
    // il nome dello spot: agganciamo quella, in fondo al contenuto.
    var root = document.getElementById('root');
    if (!root) return null;
    var divs = root.querySelectorAll('div');
    var best = null;
    for (var i = 0; i < divs.length; i++) {
      var s = getComputedStyle(divs[i]);
      if (s.overflowY !== 'auto' && s.overflowY !== 'scroll') continue;
      if (name && divs[i].textContent.indexOf(name) === -1) continue;
      best = divs[i];
    }
    return best;
  }

  function inject(spot) {
    if (document.getElementById('pk-scheda-context')) return true;
    if (attempts.inject >= INJECT_TRIES + FALLBACK_TRIES) return true; // basta
    attempts.inject++;
    var host = findScrollHost(spot.name) || findScrollHost(null);
    if (!host && attempts.inject <= INJECT_TRIES) {
      // scheda non ancora montata (dispositivo lento): riprova al prossimo
      // tick invece di ripiegare subito sul pannello flottante
      return false;
    }
    var section = buildSection(spot);
    if (host) {
      (host.firstElementChild || host).appendChild(section);
    } else {
      // fallback dopo INJECT_TRIES tentativi: pannello fisso sopra la tab bar
      section.style.cssText += ';position:fixed;left:10px;right:10px;' +
        'bottom:calc(84px + env(safe-area-inset-bottom));z-index:9999;max-height:55vh;overflow:auto';
      document.body.appendChild(section);
    }
    return true;
  }

  function currentSpotId() {
    var m = location.pathname.match(/\/spot\/([^\/?#]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function removeInjected() {
    ['pk-scheda-context', 'pk-scheda-cover', 'pk-scheda-cover-tag'].forEach(function (id) {
      var n = document.getElementById(id);
      if (n) n.remove();
    });
  }

  function tick() {
    if (document.hidden) return; // tab in background: zero lavoro
    var id = currentSpotId();
    if (!id) {
      current = null;
      removeInjected();
      return;
    }
    if (id !== current) {
      removeInjected(); // cambiato spot: via i pezzi vecchi
      attempts = { cover: 0, inject: 0 };
    }
    current = id;
    var spot = spotFor(id);
    if (!spot) return; // dati non ancora disponibili (o spot sconosciuto)
    ensureCover(spot); // copertina: pu\u00F2 comparire dopo il caricamento dati
    inject(spot); // se la scheda non \u00E8 ancora montata, riprova il polling
  }

  // route-change: pushState/replaceState + popstate + polling di sicurezza
  ['pushState', 'replaceState'].forEach(function (fn) {
    var orig = history[fn];
    history[fn] = function () {
      var r = orig.apply(this, arguments);
      setTimeout(tick, 120);
      return r;
    };
  });
  window.addEventListener('popstate', function () { setTimeout(tick, 120); });
  setInterval(tick, 700);
})();
"""


def city_of(spot: dict) -> str | None:
    """Città per la ricerca Instagram/YouTube: 'Roma' per la family; per gli
    spot community il nome del luogo GeoNames con cui inizia la descrizione
    ("Giardinetti-Tor Vergata, Italia. …")."""
    if spot.get("status") != "community":
        return "Roma"
    head = (spot.get("description") or "").split(".")[0]
    city = head.split(",")[0].strip()
    return city or None


def ig_entry(raw: dict | None) -> dict | None:
    """Voce Instagram compatta per lo script (solo i campi che usa)."""
    if not raw:
        return None
    entry: dict = {}
    if raw.get("location"):
        loc = raw["location"]
        entry["location"] = {
            "id": str(loc["id"]), "slug": loc.get("slug") or "", "name": loc.get("name") or "",
        }
    if raw.get("hashtags"):
        entry["hashtags"] = list(raw["hashtags"])
    posts = [
        {"url": p["url"], "kind": p.get("kind", "post"), "title": p.get("title") or ""}
        for p in raw.get("posts", [])
    ]
    if posts:
        entry["posts"] = posts
    accounts = [
        {"handle": a["handle"], "name": a.get("name") or "", "why": a.get("why") or ""}
        for a in raw.get("accounts", [])
    ]
    if accounts:
        entry["accounts"] = accounts
    return entry or None


def js_literal(obj) -> str:
    """JSON dentro un file JS: U+2028/2029 vanno escapati."""
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def main() -> int:
    fixed = json.loads(FIXED.read_text(encoding="utf8"))
    backup_sv = {s["id"]: s for s in json.loads(STREETVIEW.read_text(encoding="utf8"))["spots"]}
    all_sv = {}
    if STREETVIEW_ALL.exists():
        all_sv = json.loads(STREETVIEW_ALL.read_text(encoding="utf8")).get("spots", {})
    else:
        print(f"ATTENZIONE: manca {STREETVIEW_ALL.name} (fetch_streetview_all.py): "
              "solo gli spot del backup avranno Street View", file=sys.stderr)
    instagram = {}
    if INSTAGRAM.exists():
        instagram = json.loads(INSTAGRAM.read_text(encoding="utf8")).get("spots", {})

    spots: dict[str, dict] = {}
    inline: dict[str, dict] = {}
    for s in fixed:
        sid = s["id"]
        if sid in backup_sv:  # panorami scelti (e corretti a mano) per il backup
            sv, sv2 = backup_sv[sid]["streetview"], backup_sv[sid].get("streetview_alt")
        else:
            raw = all_sv.get(sid) or {}
            sv, sv2 = raw.get("sv"), raw.get("sv2")
        entry = {
            "name": s["name"],
            "lat": s["lat"],
            "lng": s["lng"],
            "city": city_of(s),
            "sv": sv,
            "sv2": sv2,
            "photo": CURATED.get(s["name"]),
            "ig": ig_entry(instagram.get(sid)),
        }
        # niente chiavi nulle nel file dati: 1700 spot, ogni byte conta
        # (lo script tratta chiave assente e null allo stesso modo)
        entry = {k: v for k, v in entry.items() if v is not None}
        spots[sid] = entry
        if s.get("status") != "community":
            inline[sid] = entry

    unknown_ig = sorted(set(instagram) - set(spots))
    if unknown_ig:
        print(f"ATTENZIONE: voci Instagram senza spot: {', '.join(unknown_ig)}", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(spots),
        "with_streetview": sum(1 for e in spots.values() if e.get("sv")),
        "with_instagram": sum(1 for e in spots.values() if e.get("ig")),
        "spots": dict(sorted(spots.items())),
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
                        encoding="utf8")

    js = (TEMPLATE
          .replace("__INLINE__", js_literal(inline))
          .replace("__SUPABASE_URL__", SUPABASE_URL)
          .replace("__SUPABASE_KEY__", SUPABASE_KEY))
    OUT_JS.write_text(js, encoding="utf8")

    print(f"Scritto {OUT_JS.relative_to(REPO)} ({len(inline)} spot inline, "
          f"{OUT_JS.stat().st_size // 1024} KB)")
    print(f"Scritto {OUT_JSON.relative_to(REPO)} ({payload['count']} spot, "
          f"{payload['with_streetview']} con Street View, "
          f"{payload['with_instagram']} con Instagram, {OUT_JSON.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
