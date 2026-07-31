/* PkFAMILY — contesto visivo nella scheda spot.
 *
 * Generato da docs/demo/tools/build_pk_scheda.py — NON modificare a mano.
 * Caricato da index.html accanto al bundle Expo (stesso pattern di
 * pk-route.js). Interviene SOLO sulla rotta /spot/{id}: quando la family
 * apre la scheda, in fondo compaiono la miniatura Street View puntata
 * sullo spot come COPERTINA al posto di \u201CAncora nessuna foto\u201D, il
 * panorama 360\u00B0 apribile inline, una foto della zona (con licenza) o la
 * vista aerea come immagine di contesto, e il link a Google Street View.
 * Se lo spot ha gi\u00E0 foto proprie nella galleria, la copertina non viene
 * toccata. Nessuna API key: stessi endpoint pubblici della pagina demo.
 */
(function () {
  'use strict';

  var SPOTS = {"0f9ac7ae-0dd1-4827-84ac-3f1874507b5e": {"name": "EUR Laghetto", "lat": 41.8305, "lng": 12.4703, "sv": {"pano_id": "TPBKfMbblYg9aX2p7xH_Nw", "pano_lat": 41.83052208708717, "pano_lng": 12.4703204266273, "yaw": 214.6, "date": "2024-06", "distance_m": 3}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Roma_EUR_Laghetto_vista_dal_basso.jpg/960px-Roma_EUR_Laghetto_vista_dal_basso.jpg", "page": "https://commons.wikimedia.org/wiki/File:Roma_EUR_Laghetto_vista_dal_basso.jpg", "credit": "Wikimedia Commons · CC BY-SA 3.0 IT"}}, "c1f8bcc4-e5e7-4ddd-bf8f-d5c080c1f082": {"name": "Villa Borghese — Piazza di Siena", "lat": 41.9142, "lng": 12.4849, "sv": {"pano_id": "Rx8AqZz-p7uLjUJyZlIpJQ", "pano_lat": 41.91385317860745, "pano_lng": 12.484470822088, "yaw": 42.6, "date": "2015-09", "distance_m": 52}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/Plaza_de_Siena%2C_Villa_Borghese%2C_Roma%2C_Italia%2C_2022-09-14%2C_DD_14.jpg/960px-Plaza_de_Siena%2C_Villa_Borghese%2C_Roma%2C_Italia%2C_2022-09-14%2C_DD_14.jpg", "page": "https://commons.wikimedia.org/wiki/File:Plaza_de_Siena,_Villa_Borghese,_Roma,_Italia,_2022-09-14,_DD_14.jpg", "credit": "Wikimedia Commons · CC BY-SA 4.0"}}, "8b0b9c9b-a6b8-42ba-8013-3686281d443e": {"name": "Foro Italico — Stadio dei Marmi", "lat": 41.9317, "lng": 12.4547, "sv": {"pano_id": "cGJf698SxV9_NS00EjjKjg", "pano_lat": 41.93148089713848, "pano_lng": 12.45424538270189, "yaw": 57.1, "date": "2017-06", "distance_m": 45}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Stadio_dei_marmi_009.jpg/960px-Stadio_dei_marmi_009.jpg", "page": "https://commons.wikimedia.org/wiki/File:Stadio_dei_marmi_009.jpg", "credit": "Wikimedia Commons · Pubblico dominio"}}, "7afa8505-b5b3-4781-8e25-d42897f5353e": {"name": "Garbatella — Scalinate", "lat": 41.8622, "lng": 12.4823, "sv": {"pano_id": "qNRSxLQakVwGqy2FLcEQSg", "pano_lat": 41.86216744602794, "pano_lng": 12.48233150070373, "yaw": 324.2, "date": "2022-02", "distance_m": 4}, "photo": {"src": "https://live.staticflickr.com/34/72998499_c2311608eb_b.jpg", "page": "https://www.flickr.com/photos/93226994@N00/72998499", "credit": "antmoose (Flickr) · CC BY 2.0"}}, "e117b08f-7cd9-4f98-b3b3-983944ab4155": {"name": "MA Spot — Largo Emanuele Ruspoli", "lat": 41.858017, "lng": 12.455528, "sv": {"pano_id": "GxknKtEM3aMz5ZKsK0agVA", "pano_lat": 41.85793768195444, "pano_lng": 12.45533957282683, "yaw": 60.5, "date": "2015-07", "distance_m": 18}, "photo": null}, "d6668114-4fb1-46a2-b23b-02c3ed2d2d13": {"name": "Spot Metro Colosseo", "lat": 41.891806, "lng": 12.491545, "sv": {"pano_id": "DtoulutpPZxIRrfX-6A5vw", "pano_lat": 41.89184691512483, "pano_lng": 12.49153162875579, "yaw": 166.3, "date": "2018-06", "distance_m": 5}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Colosseo_-_panoramio_%2810%29.jpg/960px-Colosseo_-_panoramio_%2810%29.jpg", "page": "https://commons.wikimedia.org/wiki/File:Colosseo_-_panoramio_(10).jpg", "credit": "Wikimedia Commons · CC BY 3.0"}}, "af810dbb-3109-4974-82c7-6cbdd5054efa": {"name": "Parkour Park Municipio Roma III", "lat": 41.960813, "lng": 12.539902, "sv": {"pano_id": "7ASDd0jbZ1llpPynE7_StA", "pano_lat": 41.96075536956421, "pano_lng": 12.53971779209702, "yaw": 67.2, "date": "2026-04", "distance_m": 17}, "photo": null}, "1aaaa16f-66a6-4888-8fd2-29618bcd7f90": {"name": "Spot EUR", "lat": 41.829641, "lng": 12.466853, "sv": {"pano_id": "51CGqz-wF7GOkxQc4Herpg", "pano_lat": 41.82958154467747, "pano_lng": 12.46678060936479, "yaw": 42.2, "date": "2022-07", "distance_m": 9}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bd/2024-05-06-Palazzo-dello-Sport-2.jpg/960px-2024-05-06-Palazzo-dello-Sport-2.jpg", "page": "https://commons.wikimedia.org/wiki/File:2024-05-06-Palazzo-dello-Sport-2.jpg", "credit": "Wikimedia Commons · CC BY-SA 4.0"}}, "3660d036-5be3-4044-b2fc-b6cc35c5a9b6": {"name": "Spot Rooftop Casal Lumbroso", "lat": 41.862819, "lng": 12.363478, "sv": {"pano_id": "QVW0A2SHgY6KGxagnXYkvQ", "pano_lat": 41.86339265162889, "pano_lng": 12.36283098028132, "yaw": 140.0, "date": "2025-07", "distance_m": 83}, "photo": null}, "a6487801-aa3b-47e1-92b1-7c88069cb08f": {"name": "Spot Pizzeria Massimina", "lat": 41.877788, "lng": 12.349671, "sv": {"pano_id": "EMjz0OVSkt-f31-1sNp99g", "pano_lat": 41.87780538429979, "pano_lng": 12.34962572178195, "yaw": 117.3, "date": "2025-07", "distance_m": 4}, "photo": null}, "6411a98b-594b-4d5e-8f0f-ba5ec243e6b5": {"name": "Spot Scuola Massimina", "lat": 41.882734, "lng": 12.360117, "sv": {"pano_id": "lX4dCfIvkq-IE5E7uMjdfw", "pano_lat": 41.8828742384333, "pano_lng": 12.36064265433101, "yaw": 250.3, "date": "2025-07", "distance_m": 46}, "photo": null}, "58ca88db-1761-4aa5-b34a-48a6968c6176": {"name": "Spot Massimina Parco Nord", "lat": 41.87995, "lng": 12.359791, "sv": {"pano_id": "7ElPP3PlCeaDw2W-NBogRg", "pano_lat": 41.8800533139586, "pano_lng": 12.36021946753247, "yaw": 252.1, "date": "2025-07", "distance_m": 37}, "photo": null}, "dfb21f27-574e-40da-a767-4a4b6fba767f": {"name": "Spot Massimina Parco Sud", "lat": 41.869537, "lng": 12.356947, "sv": {"pano_id": "HT_1ExiBdITjyPjRrfCQaw", "pano_lat": 41.86954065320352, "pano_lng": 12.35716220442339, "yaw": 268.7, "date": "2025-07", "distance_m": 18}, "photo": null}, "9bc3566a-374b-4be8-a7ed-a34beb385024": {"name": "Spot Corviale 1", "lat": 41.851164, "lng": 12.413137, "sv": {"pano_id": "oxz0piHxD7QaqM6zLgdIMg", "pano_lat": 41.85100398130709, "pano_lng": 12.41367350829766, "yaw": 291.8, "date": "2025-10", "distance_m": 48}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Corviale_%285582072620%29.jpg/960px-Corviale_%285582072620%29.jpg", "page": "https://commons.wikimedia.org/wiki/File:Corviale_(5582072620).jpg", "credit": "Wikimedia Commons · Pubblico dominio"}}, "ab93fa95-6329-43f7-84b2-bd69ca07b57e": {"name": "Spot Corviale 2", "lat": 41.850893, "lng": 12.41161, "sv": {"pano_id": "o0G1TNJUZ_ZeI94i66c5EA", "pano_lat": 41.85089248839245, "pano_lng": 12.41147125360772, "yaw": 89.7, "date": "2022-08", "distance_m": 11}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Municipio_XI_%28Roma%29_in_2020.03.jpg/960px-Municipio_XI_%28Roma%29_in_2020.03.jpg", "page": "https://commons.wikimedia.org/wiki/File:Municipio_XI_(Roma)_in_2020.03.jpg", "credit": "Wikimedia Commons · CC BY-SA 4.0"}}, "c9cb7a8e-f7c9-4462-b0a0-81bcb9fbbf6f": {"name": "Spot Corviale 3", "lat": 41.851311, "lng": 12.412888, "sv": {"pano_id": "SvJ-2_r2bpn8yJS_WuWkjQ", "pano_lat": 41.85136123714386, "pano_lng": 12.41254422002827, "yaw": 101.1, "date": "2024-06", "distance_m": 29}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Municipio_XI_%28Roma%29_in_2020.02.jpg/960px-Municipio_XI_%28Roma%29_in_2020.02.jpg", "page": "https://commons.wikimedia.org/wiki/File:Municipio_XI_(Roma)_in_2020.02.jpg", "credit": "Wikimedia Commons · CC BY-SA 4.0"}}, "1b76da0f-5c17-4c3f-a0db-d780bc708f96": {"name": "Spot Tufello", "lat": 41.95479, "lng": 12.532099, "sv": {"pano_id": "hJbExIhWQe51VSWJ3syH7A", "pano_lat": 41.95488971325576, "pano_lng": 12.53196268464158, "yaw": 134.5, "date": "2026-04", "distance_m": 16}, "photo": null}, "d967cfe9-fddd-4b87-9711-d3a0fedaad73": {"name": "Spot Via Giovanni Prati", "lat": 41.87381, "lng": 12.462786, "sv": {"pano_id": "nNpVBrMm5KfbZokabELPjA", "pano_lat": 41.87383431073942, "pano_lng": 12.46272722830311, "yaw": 119.1, "date": "2023-05", "distance_m": 6}, "photo": null}, "2b1be419-9c83-4244-9e06-9e1213c1aedd": {"name": "Spot Primavalle", "lat": 41.90608, "lng": 12.415025, "sv": {"pano_id": "2MLVf2fPPWcmCHlWWb7b4A", "pano_lat": 41.90619794309863, "pano_lng": 12.41521894206098, "yaw": 230.7, "date": "2025-07", "distance_m": 21}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Largo_borromeo_primavalle_roma.jpg/960px-Largo_borromeo_primavalle_roma.jpg", "page": "https://commons.wikimedia.org/wiki/File:Largo_borromeo_primavalle_roma.jpg", "credit": "Wikimedia Commons · CC BY-SA 4.0"}}, "f5f25a61-5ba0-4083-87fc-d7c978d054b5": {"name": "Spot Villa Carpegna", "lat": 41.895616, "lng": 12.427432, "sv": {"pano_id": "Wc_e2LbJnPMdCIYMbqKW4Q", "pano_lat": 41.89600563075266, "pano_lng": 12.4288038235655, "yaw": 249.1, "date": "2025-07", "distance_m": 122}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Roma_-_Villa_Carpegna_innevata_-_panoramio.jpg/960px-Roma_-_Villa_Carpegna_innevata_-_panoramio.jpg", "page": "https://commons.wikimedia.org/wiki/File:Roma_-_Villa_Carpegna_innevata_-_panoramio.jpg", "credit": "Wikimedia Commons · CC BY 3.0"}}, "6d816f11-19d8-4a01-a671-cd071c5450b6": {"name": "Spot Colosseo — Monte Oppio", "lat": 41.890649, "lng": 12.497617, "sv": {"pano_id": "yujmpiLuOOjWCD-VLTBNVQ", "pano_lat": 41.89079510080654, "pano_lng": 12.49759819745326, "yaw": 174.5, "date": "2019-08", "distance_m": 16}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Parc_Colle_Oppio_-_Rome_%28IT62%29_-_2021-08-29_-_1.jpg/960px-Parc_Colle_Oppio_-_Rome_%28IT62%29_-_2021-08-29_-_1.jpg", "page": "https://commons.wikimedia.org/wiki/File:Parc_Colle_Oppio_-_Rome_(IT62)_-_2021-08-29_-_1.jpg", "credit": "Wikimedia Commons · CC BY-SA 4.0"}}, "85e0af17-1566-4583-b6f6-32f356504f6f": {"name": "Spot NoToT Game", "lat": 41.865012, "lng": 12.44643, "sv": {"pano_id": "h6Nw_NfQR_-dU9U5ykH7wA", "pano_lat": 41.86499062261667, "pano_lng": 12.44630531946302, "yaw": 77.0, "date": "2024-06", "distance_m": 11}, "photo": null}, "2fb275b8-0643-43c9-b855-0be9abc46d57": {"name": "Spot Colonne Colosseo", "lat": 41.890839, "lng": 12.494949, "sv": {"pano_id": "_q4apootAkm9znhoPDkIgQ", "pano_lat": 41.89065674169301, "pano_lng": 12.4949926747537, "yaw": 349.9, "date": "2019-08", "distance_m": 21}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Colonne_Tempio_Venere_Colosseo_Roma_09feb08.jpg/960px-Colonne_Tempio_Venere_Colosseo_Roma_09feb08.jpg", "page": "https://commons.wikimedia.org/wiki/File:Colonne_Tempio_Venere_Colosseo_Roma_09feb08.jpg", "credit": "Wikimedia Commons · CC BY-SA 3.0"}}, "2f8b8f1d-bb9f-4eca-9bc2-0d10dc5100a2": {"name": "Colle Oppio Park", "lat": 41.8925, "lng": 12.4966, "sv": {"pano_id": "0EO69nnDIQr50WKa-hKa4g", "pano_lat": 41.89247800037813, "pano_lng": 12.49683541787556, "yaw": 277.2, "date": "2016-10", "distance_m": 20}, "photo": {"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Parco_Del_Colle_Oppio_-_panoramio.jpg/960px-Parco_Del_Colle_Oppio_-_panoramio.jpg", "page": "https://commons.wikimedia.org/wiki/File:Parco_Del_Colle_Oppio_-_panoramio.jpg", "credit": "Wikimedia Commons · CC BY 3.0"}}, "spot-metro-cipro": {"name": "Spot verso la metro Cipro", "lat": 41.907192, "lng": 12.449997, "sv": {"pano_id": "hjtmyxsVElvlnC3hB2QFGw", "pano_lat": 41.90734181756203, "pano_lng": 12.44985735673935, "yaw": 145.3, "date": "2024-06", "distance_m": 20}, "photo": null}, "spot-fontanella-trastevere-gianicolo": {"name": "Spot con fontanella - Trastevere/Gianicolo", "lat": 41.894056, "lng": 12.433333, "sv": {"pano_id": "py8fBA01POKMlyOXmq4gNA", "pano_lat": 41.89390165018952, "pano_lng": 12.43323397556814, "yaw": 25.5, "date": "2024-07", "distance_m": 19}, "photo": null}};

  var MONTHS = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];
  var current = null; // id spot attualmente iniettato
  var tries = 0;

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
      '\uD83D\uDCF8 Contesto visivo'));

    // La miniatura Street View fa da copertina in testa alla scheda (vedi
    // ensureCover): qui resta la seconda immagine — foto della zona o aerea.
    if (spot.photo) {
      box.appendChild(media(spot.photo.src, 'Foto: ' + spot.photo.credit, spot.photo.page));
    } else {
      box.appendChild(media(aerial(spot), 'Vista aerea \u00B7 \u00A9 Esri, Maxar'));
    }

    var row = el('div', 'display:flex;gap:8px;flex-wrap:wrap');
    function btn(label, primary) {
      return el('button',
        'flex:1;min-width:120px;padding:10px 8px;border:0;border-radius:10px;cursor:pointer;' +
        'font:600 13px system-ui,sans-serif;' +
        (primary ? 'background:#ffd166;color:#1a1a1a' : 'background:#333;color:#eee'), label);
    }
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
      var bOpen = btn('\uD83D\uDEB6 Apri in Street View', false);
      bOpen.onclick = function () { window.open(svOpen(spot), '_blank'); };
      row.appendChild(b360);
      row.appendChild(bOpen);
      box.appendChild(row);
      box.appendChild(pano);
    }

    box.appendChild(el('div', 'color:#777;font-size:10px;margin-top:10px',
      'Immagini \u00A9 Google Street View \u00B7 foto Wikimedia/Flickr con licenza \u00B7 aeree \u00A9 Esri'));
    return box;
  }

  function ensureCover(spot) {
    // Copertina: se la galleria nativa \u00E8 vuota (placeholder \u201CAncora
    // nessuna foto\u201D), la prima immagine \u2014 la Street View puntata sullo
    // spot \u2014 prende il suo posto. Con foto vere gi\u00E0 presenti non tocca nulla.
    if (!spot.sv) return;
    if (document.getElementById('pk-scheda-cover')) return;
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
    var host = findScrollHost(spot.name) || findScrollHost(null);
    var section = buildSection(spot);
    if (host) {
      (host.firstElementChild || host).appendChild(section);
    } else {
      // fallback: pannello fisso sopra la tab bar, come pk-route
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
    var id = currentSpotId();
    if (!id) {
      current = null;
      removeInjected();
      return;
    }
    if (id !== current) removeInjected(); // cambiato spot: via i pezzi vecchi
    var spot = SPOTS[id];
    if (!spot) { current = id; return; }
    current = id;
    ensureCover(spot); // copertina: pu\u00F2 comparire dopo il caricamento dati
    if (!document.getElementById('pk-scheda-context')) {
      inject(spot); // se la scheda non \u00E8 ancora montata, riprova il polling
    }
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
