#!/usr/bin/env python3
"""Genera pk-scheda.js: il contesto visivo dentro la scheda dell'app PkFAMILY.

Segue il pattern di pk-route.js (gh-pages): un file JS autonomo caricato da
index.html accanto al bundle Expo. Quando la family apre la scheda di uno
spot (rotta /spot/{id}) lo script aggiunge in fondo alla scheda la sezione
"Contesto visivo": miniatura Street View puntata sullo spot, panorama 360°
apribile inline, foto della zona (Wikimedia/Flickr, con licenza) oppure
vista aerea, e il link per aprire Street View in Google Maps.

Dati: docs/demo/spots-streetview.json (generato da fetch_streetview.py,
UUID reali del DB) + le foto curate qui sotto + i due spot presenti solo
nell'app (Cipro, Trastevere) di cui recupera il panorama al volo.

Uso:
    python3 docs/demo/tools/build_pk_scheda.py [output]
    # default output: docs/demo/pk-scheda.js
"""

import json
import sys
from pathlib import Path

from fetch_streetview import bearing, distance_m, find_pano

REPO = Path(__file__).resolve().parents[3]
STREETVIEW = REPO / "docs" / "demo" / "spots-streetview.json"
DEFAULT_OUT = REPO / "docs" / "demo" / "pk-scheda.js"

# Foto di contesto curate a mano, ricontrollate una a una il 2026-09-04 (vedi
# docs/spots/PHOTO_AUDIT.md). Restano solo quelle in cui si vedono davvero le
# strutture su cui ci si allena: le altre — Colosseo per lo spot della metro,
# il laghetto dell'EUR, Villa Carpegna sotto la neve, largo Borromeo — sono
# state tolte perché mostravano il monumento o il quartiere, non lo spot, e
# per giunta prendevano il posto della seconda angolazione Street View, che è
# più utile. Torneranno le foto vere, scattate sul posto.
CURATED = {
    "Foro Italico — Stadio dei Marmi": {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Stadio_dei_marmi_009.jpg/960px-Stadio_dei_marmi_009.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Stadio_dei_marmi_009.jpg",
        "credit": "Wikimedia Commons · Pubblico dominio",
        "note": "gradoni in marmo e statue: le superfici dello spot si vedono",
    },
    "Garbatella — Scalinate": {
        "src": "https://live.staticflickr.com/34/72998499_c2311608eb_b.jpg",
        "page": "https://www.flickr.com/photos/93226994@N00/72998499",
        "credit": "antmoose (Flickr) · CC BY 2.0",
        "note": "il muro dipinto con la scalinata di fianco: la zona è riconoscibile",
    },
}

# Spot presenti solo nell'app (dati mock del bundle), non nel backup.
EXTRA_SPOTS = [
    {"id": "spot-metro-cipro", "name": "Spot verso la metro Cipro", "lat": 41.907192, "lng": 12.449997},
    {
        "id": "spot-fontanella-trastevere-gianicolo",
        "name": "Spot con fontanella - Trastevere/Gianicolo",
        "lat": 41.894056,
        "lng": 12.433333,
    },
]

TEMPLATE = """/* PkFAMILY — contesto visivo nella scheda spot.
 *
 * Generato da docs/demo/tools/build_pk_scheda.py — NON modificare a mano.
 * Caricato da index.html accanto al bundle Expo (stesso pattern di
 * pk-route.js). Interviene SOLO sulla rotta /spot/{id}: quando la family
 * apre la scheda, in fondo compaiono la miniatura Street View puntata
 * sullo spot come COPERTINA al posto di \\u201CAncora nessuna foto\\u201D, il
 * panorama 360\\u00B0 apribile inline, una foto della zona (con licenza) o la
 * vista aerea come immagine di contesto, e il link a Google Street View.
 * Se lo spot ha gi\\u00E0 foto proprie nella galleria, la copertina non viene
 * toccata. Nessuna API key: stessi endpoint pubblici della pagina demo.
 */
(function () {
  'use strict';

  var SPOTS = __DATA__;

  var MONTHS = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];
  var current = null; // id spot attualmente iniettato
  var COVER_TRIES = 20;   // ~14 s di ricerca del placeholder, poi stop
  var INJECT_TRIES = 8;   // ~5.6 s per l'aggancio inline prima del fallback
  var FALLBACK_TRIES = 4; // ulteriori tentativi col pannello flottante
  var attempts = { cover: 0, inject: 0 };

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
    return 'https://www.google.com/maps/@?api=1&map_action=pano' +
      '&pano=' + encodeURIComponent(spot.sv.pano_id) +
      '&viewpoint=' + spot.lat + ',' + spot.lng + '&heading=' + spot.sv.yaw;
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

  function buildSection(spot) {
    var box = el('div',
      'margin:14px 16px calc(28px + env(safe-area-inset-bottom));padding:14px;border-radius:14px;' +
      'background:#1c1c1e;color:#eee;font:14px system-ui,sans-serif;' +
      'box-shadow:0 2px 10px rgba(0,0,0,.35)');
    box.id = 'pk-scheda-context';

    box.appendChild(el('div', 'font:800 15px system-ui,sans-serif;margin-bottom:10px',
      '\\uD83D\\uDCF8 Contesto visivo'));

    // La miniatura Street View fa da copertina in testa alla scheda (vedi
    // ensureCover): qui le altre foto del posto — quella trovata online se
    // esiste, altrimenti una seconda Street View da un'angolazione diversa —
    // più la vista aerea.
    if (spot.photo) {
      box.appendChild(media(spot.photo.src,
        'Foto della zona \\u00B7 ' + spot.photo.credit, spot.photo.page));
    } else if (spot.sv2) {
      box.appendChild(media(svThumb(spot.sv2),
        'Street View \\u00B7 altra angolazione \\u00B7 ~' + spot.sv2.distance_m + ' m dallo spot'));
    }
    box.appendChild(media(aerial(spot), 'Vista aerea \\u00B7 \\u00A9 Esri, Maxar'));

    var row = el('div', 'display:flex;gap:8px;flex-wrap:wrap');
    function btn(label, primary) {
      return el('button',
        'flex:1;min-width:120px;padding:10px 8px;border:0;border-radius:10px;cursor:pointer;' +
        'font:600 13px system-ui,sans-serif;' +
        (primary ? 'background:#ffd166;color:#1a1a1a' : 'background:#333;color:#eee'), label);
    }
    if (spot.sv) {
      var pano = el('div', 'display:none;margin-top:10px;border-radius:12px;overflow:hidden');
      var b360 = btn('\\uD83C\\uDF10 Esplora a 360\\u00B0', true);
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
        b360.textContent = open ? '\\uD83C\\uDF10 Esplora a 360\\u00B0' : '\\u2715 Chiudi il 360\\u00B0';
      };
      var bOpen = btn('\\uD83D\\uDEB6 Apri in Street View', false);
      bOpen.onclick = function () { window.open(svOpen(spot), '_blank'); };
      row.appendChild(b360);
      row.appendChild(bOpen);
      box.appendChild(row);
      box.appendChild(pano);
    }

    // Contenuti della community: foto e video degli spot vivono su Instagram
    // e YouTube ma non sono incorporabili (URL firmati/scadenza) — questi
    // pulsanti aprono la ricerca gi\\u00E0 compilata per QUESTO spot.
    var q = spot.name.replace(/^Spot /, '') + ' parkour Roma';
    var row2 = el('div', 'display:flex;gap:8px;flex-wrap:wrap;margin-top:8px');
    var bIg = btn('\\uD83D\\uDCF7 Su Instagram', false);
    bIg.onclick = function () {
      window.open('https://www.instagram.com/explore/search/keyword/?q=' +
        encodeURIComponent(q), '_blank');
    };
    var bYt = btn('\\uD83C\\uDFAC Video community', false);
    bYt.onclick = function () {
      window.open('https://www.youtube.com/results?search_query=' +
        encodeURIComponent(q), '_blank');
    };
    row2.appendChild(bIg);
    row2.appendChild(bYt);
    box.appendChild(row2);

    box.appendChild(el('div', 'color:#777;font-size:10px;margin-top:10px',
      'Immagini \\u00A9 Google Street View \\u00B7 foto Wikimedia/Flickr con licenza \\u00B7 aeree \\u00A9 Esri'));
    return box;
  }

  function ensureCover(spot) {
    // Copertina: se la galleria nativa \\u00E8 vuota (placeholder \\u201CAncora
    // nessuna foto\\u201D), la prima immagine \\u2014 la Street View puntata sullo
    // spot \\u2014 prende il suo posto. Con foto vere gi\\u00E0 presenti non tocca nulla.
    // Le scansioni del DOM sono LIMITATE (attempts): senza placeholder \\u2014
    // galleria piena o scheda lenta \\u2014 dopo un po' si smette, niente lavoro
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
      'Street View \\u00B7 ' + svDate(spot.sv) + ' \\u00B7 ~' + spot.sv.distance_m + ' m dallo spot');
    tag.id = 'pk-scheda-cover-tag';
    boxEl.appendChild(img);
    boxEl.appendChild(tag);
  }

  function findScrollHost(name) {
    // La scheda \\u00E8 una ScrollView (div con overflow-y auto) che contiene
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
    var m = location.pathname.match(/\\/spot\\/([^\\/?#]+)/);
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
    var spot = SPOTS[id];
    if (!spot) { current = id; return; }
    current = id;
    ensureCover(spot); // copertina: pu\\u00F2 comparire dopo il caricamento dati
    inject(spot); // se la scheda non \\u00E8 ancora montata, riprova il polling
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


def main() -> int:
    data = json.loads(STREETVIEW.read_text())
    spots: dict[str, dict] = {}
    for s in data["spots"]:
        spots[s["id"]] = {
            "name": s["name"],
            "lat": s["lat"],
            "lng": s["lng"],
            "sv": s["streetview"],
            "sv2": s.get("streetview_alt"),
            "photo": CURATED.get(s["name"]),
        }

    def to_sv(pano, lat, lng):
        pano_id, plat, plng, date = pano
        return {
            "pano_id": pano_id,
            "pano_lat": plat,
            "pano_lng": plng,
            "yaw": round(bearing(plat, plng, lat, lng), 1),
            "date": date,
            "distance_m": round(distance_m(plat, plng, lat, lng)),
        }

    for extra in EXTRA_SPOTS:
        found, alt = find_pano(extra["lat"], extra["lng"], with_alt=True)
        sv = to_sv(found, extra["lat"], extra["lng"]) if found else None
        sv2 = to_sv(alt, extra["lat"], extra["lng"]) if alt else None
        print(f"{'✓' if sv else '✗'} {extra['name']}: pano {sv['pano_id'] if sv else '—'}"
              + (" + alt" if sv2 else ""))
        spots[extra["id"]] = {
            "name": extra["name"],
            "lat": extra["lat"],
            "lng": extra["lng"],
            "sv": sv,
            "sv2": sv2,
            "photo": None,
        }

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    js = TEMPLATE.replace("__DATA__", json.dumps(spots, ensure_ascii=False))
    out.write_text(js)
    print(f"Scritto {out} ({len(spots)} spot)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
