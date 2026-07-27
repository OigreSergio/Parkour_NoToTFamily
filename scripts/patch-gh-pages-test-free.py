#!/usr/bin/env python3
"""Patch del bundle web PkFAMILY (gh-pages) per la fase di test.

1. Mappa satellitare: lo stile vettoriale OpenFreeMap viene sostituito da
   tile raster Esri World Imagery.
2. Spot fissi: MOCK_SPOTS viene sostituito con l'elenco completo degli spot
   raccolti (scripts/data/webapp_fixed_spots.json) e fetchSpots li fonde
   sempre con quelli di Supabase (dedupe per id o per vicinanza ~30 m),
   così la mappa è popolata anche senza backend.
3. App gratuita: useEntitlements ritorna hasBase/hasChat/hasVideo/hasAny
   sempre veri (le RLS lato Supabase restano attive per le scritture).

Uso: python3 scripts/patch-gh-pages-test-free.py <path-al-bundle-entry.js>
Idempotente no: applicare a un bundle pulito (gli anchor devono esistere).
"""

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
src = path.read_text(encoding="utf8")


def replace_span(src, start_anchor, end_anchor, new, nome):
    i = src.find(start_anchor)
    if i < 0 or src.find(start_anchor, i + 1) >= 0:
        sys.exit(f"ERRORE {nome}: anchor iniziale non univoco/assente")
    j = src.find(end_anchor, i)
    if j < 0:
        sys.exit(f"ERRORE {nome}: anchor finale assente")
    j += len(end_anchor)
    print(f"ok: {nome} ({j - i} char sostituiti)")
    return src[:i] + new + src[j:]


def replace_once(src, old, new, nome):
    n = src.count(old)
    if n != 1:
        sys.exit(f"ERRORE {nome}: {n} occorrenze (attesa 1)")
    print(f"ok: {nome}")
    return src.replace(old, new)


# --- 1. Mappa satellitare --------------------------------------------------
sat = (
    "sources:{sat:{type:'raster',"
    "tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],"
    "tileSize:256,attribution:'© Esri, Maxar, Earthstar Geographics'}},"
    "layers:[{id:'sat',type:'raster',source:'sat'}]"
)
src = replace_span(
    src,
    "sources:{openmaptiles:{type:'vector',url:'https://tiles.openfreemap.org/planet'}},layers:[",
    "'text-halo-width':1.5}}]",
    sat,
    "stile satellitare",
)

# --- 2a. MOCK_SPOTS = elenco completo degli spot fissi ---------------------
fixed = json.loads(
    (Path(__file__).parent / "data" / "webapp_fixed_spots.json").read_text(encoding="utf8")
)
fixed_js = json.dumps(fixed, ensure_ascii=False, separators=(",", ":"))
src = replace_span(
    src,
    "const t=[{id:'colle-oppio'",
    "}],n=[12.4823,41.8905]",
    f"const t={fixed_js},n=[12.4823,41.8905]",
    f"spot fissi in MOCK_SPOTS ({len(fixed)} spot)",
)

# --- 2b. fetchSpots: fonde sempre gli spot fissi con quelli Supabase -------
merge = (
    "const _l=a.map(s=>{const t=s.ratings.map(s=>s.stars),a=t.length,"
    "o=a>0?t.reduce((s,t)=>s+t,0)/a:0;"
    "return{id:s.id,name:s.name,lat:s.lat,lng:s.lng,description:s.description,"
    "skillLevel:s.skill_level,crowdLevel:s.crowd_level,hasFountain:s.has_fountain,"
    "photosCount:s.spot_photos[0]?.count??0,rating:o,ratingCount:a,status:s.status}});"
    "const _f=s.MOCK_SPOTS.filter(m=>!_l.some(x=>x.id===m.id"
    "||Math.abs(x.lat-m.lat)+Math.abs(x.lng-m.lng)<3e-4));"
    "return{spots:_l.concat(_f),fromSupabase:!0}};"
)
src = replace_span(
    src,
    "return{spots:a.map(s=>{const t=s.ratings.map(",
    ",fromSupabase:!0}};",
    merge,
    "fetchSpots con merge spot fissi",
)

# --- 3a. Niente banner "Iscriviti" sulla mappa -----------------------------
src = replace_once(
    src,
    "if((0,l.useEffect)(_,j),!f||y)return null;",
    "if((0,l.useEffect)(_,j),1)return null;",
    "SignupBanner disattivato",
)

# --- 3b. Tutto gratuito: entitlements sempre veri --------------------------
src = replace_once(
    src,
    "B={entitlements:_,loading:v,hasBase:S,hasChat:E,hasVideo:P,hasAny:j,isAdmin:o,isLoggedIn:q}",
    "B={entitlements:_,loading:v,hasBase:!0,hasChat:!0,hasVideo:!0,hasAny:!0,isAdmin:o,isLoggedIn:q}",
    "app gratuita (useEntitlements)",
)

path.write_text(src, encoding="utf8")
print(f"Bundle aggiornato: {path}")
