#!/usr/bin/env python3
"""Patch del bundle web PkFAMILY (gh-pages) per la fase di test.

1. Mappa "ricamo": stile MapLibre che disegna il mondo come un ricamo su
   lino — punti filza tratteggiati per le strade, patch di stoffa per parchi
   e palazzi, cuciture sui confini. Le sorgenti tile e glyphs restano quelle
   pubbliche OpenFreeMap ma sono sovrascrivibili dal server locale via
   ``globalThis.__PK_TILES__`` / ``__PK_GLYPHS__`` (vedi infra/localmap/).
2. Marker a spillo da cucito (SVG, testa colorata per stato, punta sul punto
   esatto dello spot).
3. Spot fissi: MOCK_SPOTS sostituito con scripts/data/webapp_fixed_spots.json
   e fetchSpots li fonde sempre con quelli di Supabase.
4. App gratuita: entitlements sempre veri e banner "Iscriviti" disattivato.
5. Distanza & percorso: espone l'istanza MapLibre e aggiunge il pulsante
   sulla scheda spot (logica in scripts/web/pk-route.js).

Uso: python3 scripts/patch-gh-pages-test-free.py <path-al-bundle-entry.js>
Non idempotente: applicare a un bundle appena esportato.
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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


# --- 1. Mappa "ricamo" ------------------------------------------------------
# Palette e layer vivono in pk_embroidery_style.py, condivisi con l'app Flutter
# (scripts/build_embroidery_style.py).
from pk_embroidery_style import EMB_LAYERS  # noqa: E402

src = replace_span(
    src,
    "sources:{openmaptiles:{type:'vector',url:'https://tiles.openfreemap.org/planet'}},layers:[",
    "'text-halo-width':1.5}}]",
    "sources:{openmaptiles:{type:'vector',"
    "url:globalThis.__PK_TILES__||'https://tiles.openfreemap.org/planet'}},"
    "layers:" + json.dumps(EMB_LAYERS, separators=(",", ":")),
    "stile ricamo",
)
src = replace_once(
    src,
    "glyphs:'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf'",
    "glyphs:globalThis.__PK_GLYPHS__||'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf'",
    "glyphs sovrascrivibili",
)

# --- 2. Marker a spillo da cucito ------------------------------------------
PIN_SVG = (
    '<svg viewBox="0 0 34 52" xmlns="http://www.w3.org/2000/svg">'
    '<polygon points="16,13 18,13 17.6,46 17,51 16.4,46" fill="#aeb4bd"/>'
    '<line x1="16.5" y1="14" x2="16.5" y2="44" stroke="#e8ebef" stroke-width="0.6"/>'
    '<circle cx="17" cy="9" r="7.5" fill="currentColor" stroke="rgba(0,0,0,.25)"/>'
    '<circle cx="14.2" cy="6.4" r="2.2" fill="#fff" opacity=".55"/>'
    "</svg>"
)

i = src.find("const p=`")
j = src.find("`", i + len("const p=`"))
if i < 0 or j < 0:
    sys.exit("ERRORE css marker: template non trovato")
src = (
    src[:i]
    + "const p=`.pk-marker{width:34px;height:52px;display:block;cursor:pointer;"
    "transition:transform .15s;transform-origin:bottom center;"
    "filter:drop-shadow(0 3px 2px rgba(0,0,0,.35))}"
    ".pk-marker svg{width:100%;height:100%;display:block;pointer-events:none}"
    ".pk-marker.selected{transform:scale(1.25)}"
    ".pk-user-dot{width:18px;height:18px;border-radius:50%;background:#2d7ff9;"
    "border:3px solid ${s.Colors.paper};box-shadow:0 1px 4px rgba(0,0,0,.35)}`"
    + src[j + 1 :]
)
print("ok: css marker a spillo")

src = replace_once(
    src,
    "e.className='pk-marker',e.style.borderColor=(0,u.markerColor)(s.status),"
    "e.textContent='\\ud83e\\udd38',",
    "e.className='pk-marker',e.style.color=(0,u.markerColor)(s.status),"
    "e.innerHTML='" + PIN_SVG + "',",
    "marker a spillo (creazione)",
)
src = replace_once(
    src,
    "e.el.style.borderColor=(0,u.markerColor)(s.status)",
    "e.el.style.color=(0,u.markerColor)(s.status)",
    "marker a spillo (aggiornamento stato)",
)
src = replace_once(
    src,
    "new n.default.Marker({element:e})",
    "new n.default.Marker({element:e,anchor:'bottom'})",
    "marker a spillo (punta sul punto esatto)",
)

# --- 3a. MOCK_SPOTS = elenco completo degli spot fissi ---------------------
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

# --- 3b. fetchSpots: fonde sempre gli spot fissi con quelli Supabase -------
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

# --- 4a. Niente banner "Iscriviti" sulla mappa -----------------------------
src = replace_once(
    src,
    "if((0,l.useEffect)(_,j),!f||y)return null;",
    "if((0,l.useEffect)(_,j),1)return null;",
    "SignupBanner disattivato",
)

# --- 4b. Tutto gratuito: entitlements sempre veri --------------------------
src = replace_once(
    src,
    "B={entitlements:_,loading:v,hasBase:S,hasChat:E,hasVideo:P,hasAny:j,isAdmin:o,isLoggedIn:q}",
    "B={entitlements:_,loading:v,hasBase:!0,hasChat:!0,hasVideo:!0,hasAny:!0,isAdmin:o,isLoggedIn:q}",
    "app gratuita (useEntitlements)",
)

# --- 5a. Espone l'istanza MapLibre per pk-route.js -------------------------
src = replace_once(
    src,
    "S.current=t,()=>{t.remove(),S.current=null,e.remove()}",
    "S.current=t,globalThis.__pkMap=t,"
    "()=>{t.remove(),S.current=null,globalThis.__pkMap=null,e.remove()}",
    "espone __pkMap",
)

# --- 5b. Pulsante "Distanza & percorso" sulla scheda spot ------------------
pk_btn = (
    "(0,h.jsx)(n.default,{onPress:()=>{globalThis.__pkRoute&&globalThis.__pkRoute("
    "{id:p.id,name:p.name,lat:p.lat,lng:p.lng})},hitSlop:8,"
    "children:(0,h.jsx)(l.default,{style:j.openLink,children:'🧭 Distanza & percorso'})})"
)
src = replace_once(
    src,
    "children:[F,P,W,H]}",
    "children:[F,P,W,H," + pk_btn + "]}",
    "pulsante percorso su SpotPreviewCard",
)

path.write_text(src, encoding="utf8")
print(f"Bundle aggiornato: {path}")

# --- 5c. pk-route.js accanto al bundle + script tag in index.html ----------
app_root = path.parents[4]
index_html = app_root / "index.html"
if index_html.is_file():
    shutil.copy(Path(__file__).parent / "web" / "pk-route.js", app_root / "pk-route.js")
    html = index_html.read_text(encoding="utf8")
    if "pk-route.js" not in html:
        html = html.replace("</body>", '<script src="./pk-route.js" defer></script>\n</body>')
        index_html.write_text(html, encoding="utf8")
    print(f"ok: pk-route.js copiato e collegato in {index_html}")
else:
    sys.exit(f"ERRORE: index.html non trovato in {app_root}")
