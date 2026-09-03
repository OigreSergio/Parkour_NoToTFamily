"""Stile mappa "ricamo": il mondo disegnato come un ricamo su lino.

Punti filza tratteggiati per le strade, patch di stoffa per parchi, palazzi e
acqua, cuciture sui confini. È lo stile storico della mappa PkFAMILY.

Sorgente unica di verità per i due client che lo usano:

- ``scripts/patch-gh-pages-test-free.py`` lo inietta nel bundle web (MapLibre);
- ``scripts/build_embroidery_style.py`` lo scrive in
  ``mobile/assets/map/embroidery_style.json`` per l'app Flutter, che lo rende
  con ``vector_map_tiles``.

Le sorgenti tile restano quelle pubbliche di OpenFreeMap.
"""

# Palette filo da ricamo su lino.
LINO = "#f1e7d3"
FILO_ROSSO = "#cd7862"
FILO_ARANCIO = "#d9a35e"
FILO_TAN = "#c2ad83"
FILO_MARRONE = "#8d7350"
FILO_VERDE = "#7fa05e"
FILO_BLU = "#6f9cb8"
FILO_VIOLA = "#b391b6"

def _w(stops, base=1.5):
    return ["interpolate", ["exponential", base], ["zoom"], *stops]

EMB_LAYERS = [
    {"id": "background", "type": "background", "paint": {"background-color": LINO}},
    {"id": "landuse", "type": "fill", "source": "openmaptiles", "source-layer": "landuse",
     "filter": ["in", "class", "residential", "suburb", "neighbourhood", "commercial", "industrial"],
     "paint": {"fill-color": "#eadcc0", "fill-opacity": 0.55}},
    {"id": "landcover", "type": "fill", "source": "openmaptiles", "source-layer": "landcover",
     "filter": ["in", "class", "grass", "wood", "farmland"],
     "paint": {"fill-color": "#b7cd9a", "fill-opacity": 0.5}},
    {"id": "park", "type": "fill", "source": "openmaptiles", "source-layer": "park",
     "paint": {"fill-color": "#abc98f", "fill-opacity": 0.6}},
    {"id": "park-stitch", "type": "line", "source": "openmaptiles", "source-layer": "park",
     "paint": {"line-color": FILO_VERDE, "line-width": 1.4, "line-dasharray": [1.4, 1.2]}},
    {"id": "water", "type": "fill", "source": "openmaptiles", "source-layer": "water",
     "paint": {"fill-color": "#a3c4d9"}},
    {"id": "water-stitch", "type": "line", "source": "openmaptiles", "source-layer": "water",
     "paint": {"line-color": FILO_BLU, "line-width": 1.5, "line-dasharray": [2, 1.4]}},
    {"id": "waterway", "type": "line", "source": "openmaptiles", "source-layer": "waterway",
     "paint": {"line-color": FILO_BLU, "line-width": 1.8, "line-dasharray": [2.2, 1.6]}},
    {"id": "building", "type": "fill", "source": "openmaptiles", "source-layer": "building",
     "minzoom": 13,
     "paint": {"fill-color": "#dcc9a4", "fill-opacity": 0.8, "fill-outline-color": "#c3ab7f"}},
    {"id": "road-path", "type": "line", "source": "openmaptiles", "source-layer": "transportation",
     "minzoom": 14, "filter": ["in", "class", "path", "track"],
     "paint": {"line-color": FILO_MARRONE, "line-width": 1.8, "line-dasharray": [1, 1.6]}},
    {"id": "road-minor-casing", "type": "line", "source": "openmaptiles",
     "source-layer": "transportation", "minzoom": 12, "filter": ["in", "class", "minor", "service"],
     "paint": {"line-color": "#faf3e2", "line-width": _w([12, 2.2, 18, 13]), "line-opacity": 0.85}},
    {"id": "road-minor", "type": "line", "source": "openmaptiles",
     "source-layer": "transportation", "minzoom": 12, "filter": ["in", "class", "minor", "service"],
     "paint": {"line-color": FILO_TAN, "line-width": _w([12, 1, 18, 8]),
               "line-dasharray": [2, 1.6]}},
    {"id": "road-major-casing", "type": "line", "source": "openmaptiles",
     "source-layer": "transportation",
     "filter": ["in", "class", "primary", "secondary", "tertiary", "trunk"],
     "paint": {"line-color": "#faf3e2", "line-width": _w([8, 2.5, 18, 20]), "line-opacity": 0.9}},
    {"id": "road-major", "type": "line", "source": "openmaptiles",
     "source-layer": "transportation",
     "filter": ["in", "class", "primary", "secondary", "tertiary", "trunk"],
     "paint": {"line-color": FILO_ARANCIO, "line-width": _w([8, 1.2, 18, 13]),
               "line-dasharray": [2.4, 1.8]}},
    {"id": "road-motorway-casing", "type": "line", "source": "openmaptiles",
     "source-layer": "transportation", "filter": ["==", "class", "motorway"],
     "paint": {"line-color": "#faf3e2", "line-width": _w([6, 3, 18, 24]), "line-opacity": 0.9}},
    {"id": "road-motorway", "type": "line", "source": "openmaptiles",
     "source-layer": "transportation", "filter": ["==", "class", "motorway"],
     "paint": {"line-color": FILO_ROSSO, "line-width": _w([6, 1.5, 18, 16]),
               "line-dasharray": [2.6, 2]}},
    {"id": "boundary-seam", "type": "line", "source": "openmaptiles", "source-layer": "boundary",
     "filter": ["<=", "admin_level", 4],
     "paint": {"line-color": FILO_VIOLA, "line-width": 1.6, "line-dasharray": [1, 1]}},
    {"id": "road-label", "type": "symbol", "source": "openmaptiles",
     "source-layer": "transportation_name", "minzoom": 14,
     "layout": {"symbol-placement": "line", "text-field": ["get", "name"],
                "text-font": ["Noto Sans Regular"], "text-size": 11},
     "paint": {"text-color": "#6d5638", "text-halo-color": LINO, "text-halo-width": 1.2}},
    {"id": "place-label", "type": "symbol", "source": "openmaptiles", "source-layer": "place",
     "maxzoom": 14, "filter": ["in", "class", "city", "town", "suburb"],
     "layout": {"text-field": ["get", "name"], "text-font": ["Noto Sans Bold"],
                "text-size": ["match", ["get", "class"], "city", 16, "town", 13, 11],
                "text-transform": "uppercase", "text-letter-spacing": 0.1},
     "paint": {"text-color": "#7a5a36", "text-halo-color": LINO, "text-halo-width": 1.5}},
]
