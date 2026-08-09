#!/usr/bin/env python3
"""Aggiorna il bundle già pubblicato su gh-pages senza rifare l'export Expo.

Da applicare all'entry-*.js deployato (già passato per
patch-gh-pages-test-free.py). Fa quattro cose:

1. sostituisce l'elenco di spot fissi incorporato con l'attuale
   scripts/data/webapp_fixed_spots.json;
2. marker solo nel viewport: con ~1700 spot creare un marker DOM per ognuno
   blocca la mappa, quindi il sync dei marker filtra sui bounds correnti
   (con margine), si riaggancia a moveend/zoomend e — quando gli spot in
   vista sono comunque troppi — li sfoltisce su una griglia;
3. dettaglio spot: il fallback sui MOCK_SPOTS restituisce ``photos``
   dall'oggetto spot (campo ``photos`` degli spot fissi) invece di [];
4. status "community" per gli spot importati dalla lista Google Maps:
   colore pin dedicato e etichetta "📍 Community" nella scheda.

Uso: python3 scripts/update_deployed_spots.py <path-al-bundle-entry.js>
Idempotente sul punto 1 (riapplicabile quando cambia il JSON); i punti 2-4
vengono saltati se già applicati.
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
    if new in src:
        print(f"già applicato: {nome}")
        return src
    n = src.count(old)
    if n != 1:
        sys.exit(f"ERRORE {nome}: {n} occorrenze (attesa 1)")
    print(f"ok: {nome}")
    return src.replace(old, new)


# --- 1. Elenco spot fissi aggiornato ---------------------------------------
fixed = json.loads(
    (Path(__file__).parent / "data" / "webapp_fixed_spots.json").read_text(encoding="utf8")
)
fixed_js = json.dumps(fixed, ensure_ascii=False, separators=(",", ":"))
src = replace_span(
    src,
    'const t=[{"id"',
    ",n=[12.4823,41.8905]",
    f"const t={fixed_js},n=[12.4823,41.8905]",
    f"spot fissi aggiornati ({len(fixed)} spot)",
)

# --- 2. Marker solo nel viewport -------------------------------------------
PIN_SVG = (
    '<svg viewBox="0 0 34 52" xmlns="http://www.w3.org/2000/svg">'
    '<polygon points="16,13 18,13 17.6,46 17,51 16.4,46" fill="#aeb4bd"/>'
    '<line x1="16.5" y1="14" x2="16.5" y2="44" stroke="#e8ebef" stroke-width="0.6"/>'
    '<circle cx="17" cy="9" r="7.5" fill="currentColor" stroke="rgba(0,0,0,.25)"/>'
    '<circle cx="14.2" cy="6.4" r="2.2" fill="#fff" opacity=".55"/>'
    "</svg>"
)

OLD_EFFECT = (
    "(0,o.useEffect)(()=>{const t=S.current;if(!t)return;const o=h.current,"
    "s=new Set(e.map(e=>e.id));for(const[e,t]of o)s.has(e)||(t.marker.remove(),o.delete(e));"
    "for(const s of e){const e=o.get(s.id);if(e){const _p=e.marker.getLngLat();"
    "e.marker.setLngLat([s.lng,s.lat]),e.el.style.color=(0,u.markerColor)(s.status),"
    "'nuovo-spot-pin'===s.id&&(Math.abs(_p.lng-s.lng)>1e-7||Math.abs(_p.lat-s.lat)>1e-7)"
    "&&t.flyTo({center:[s.lng,s.lat],zoom:Math.max(t.getZoom(),15),duration:700})}"
    "else{const e=document.createElement('div');e.className='pk-marker',"
    "e.style.color=(0,u.markerColor)(s.status),e.innerHTML='" + PIN_SVG + "',"
    "e.addEventListener('click',e=>{e.stopPropagation(),C.current.onSelectSpot(s.id)});"
    "const l=new n.default.Marker({element:e,anchor:'bottom'})"
    ".setLngLat([s.lng,s.lat]).addTo(t);o.set(s.id,{marker:l,el:e}),"
    "'nuovo-spot-pin'===s.id&&t.flyTo({center:[s.lng,s.lat],"
    "zoom:Math.max(t.getZoom(),15),duration:700})}}},[e])"
)

NEW_EFFECT = (
    "(0,o.useEffect)(()=>{const t=S.current;if(!t)return;const o=h.current,"
    "_sync=()=>{"
    "const _b=t.getBounds(),_w=_b.getWest(),_e=_b.getEast(),_s=_b.getSouth(),_n=_b.getNorth(),"
    "_mx=(_e-_w)*.15,_my=(_n-_s)*.15;"
    "let _vis=[];for(const s of e)"
    "('nuovo-spot-pin'===s.id||s.lng>_w-_mx&&s.lng<_e+_mx&&s.lat>_s-_my&&s.lat<_n+_my)"
    "&&_vis.push(s);"
    "if(_vis.length>250){const _cell=(_e-_w)/24,_seen=new Set(),_thin=[];"
    "for(const s of _vis){if('nuovo-spot-pin'===s.id){_thin.push(s);continue}"
    "const _k=Math.round(s.lng/_cell)+':'+Math.round(s.lat/_cell);"
    "_seen.has(_k)||(_seen.add(_k),_thin.push(s))}_vis=_thin}"
    "const _ids=new Set(_vis.map(s=>s.id));"
    "for(const[_id,_m]of o)_ids.has(_id)||(_m.marker.remove(),o.delete(_id));"
    "for(const s of _vis){const _x=o.get(s.id);if(_x){const _p=_x.marker.getLngLat();"
    "_x.marker.setLngLat([s.lng,s.lat]),_x.el.style.color=(0,u.markerColor)(s.status),"
    "'nuovo-spot-pin'===s.id&&(Math.abs(_p.lng-s.lng)>1e-7||Math.abs(_p.lat-s.lat)>1e-7)"
    "&&t.flyTo({center:[s.lng,s.lat],zoom:Math.max(t.getZoom(),15),duration:700})}"
    "else{const _el=document.createElement('div');_el.className='pk-marker',"
    "_el.style.color=(0,u.markerColor)(s.status),_el.innerHTML='" + PIN_SVG + "',"
    "_el.addEventListener('click',_ev=>{_ev.stopPropagation(),C.current.onSelectSpot(s.id)});"
    "const _mk=new n.default.Marker({element:_el,anchor:'bottom'})"
    ".setLngLat([s.lng,s.lat]).addTo(t);o.set(s.id,{marker:_mk,el:_el}),"
    "'nuovo-spot-pin'===s.id&&t.flyTo({center:[s.lng,s.lat],"
    "zoom:Math.max(t.getZoom(),15),duration:700})}}};"
    "_sync();t.on('moveend',_sync);t.on('zoomend',_sync);"
    "return()=>{t.off('moveend',_sync),t.off('zoomend',_sync)}},[e])"
)

src = replace_once(src, OLD_EFFECT, NEW_EFFECT, "marker solo nel viewport")

# --- 3. Foto degli spot fissi nel dettaglio --------------------------------
# Due percorsi usano il fallback sui MOCK_SPOTS: Supabase non configurato e
# spot non trovato/errore. Entrambi devono restituire le foto dello spot fisso.
_OLD_FALLBACK = (
    "return o?{spot:o,photos:[],comments:[],rejectionReason:null,fromSupabase:!1}:null"
)
_NEW_FALLBACK = (
    "return o?{spot:o,photos:o.photos||[],comments:[],rejectionReason:null,fromSupabase:!1}:null"
)
if _NEW_FALLBACK in src:
    print("già applicato: foto spot fissi nel dettaglio")
elif src.count(_OLD_FALLBACK) != 2:
    sys.exit(f"ERRORE foto spot fissi: {src.count(_OLD_FALLBACK)} occorrenze (attese 2)")
else:
    src = src.replace(_OLD_FALLBACK, _NEW_FALLBACK)
    print("ok: foto spot fissi nel dettaglio (2 percorsi)")

# --- 4. Status "community" --------------------------------------------------
src = replace_once(
    src,
    "function u(e){return'verified'===e?l.Colors.primary:l.Colors.pending}",
    "function u(e){return'verified'===e?l.Colors.primary:"
    "'community'===e?'#6f9cb8':l.Colors.pending}",
    "colore pin community",
)
src = replace_once(
    src,
    "e.statusEmoji=function(t){return'verified'===t?"
    "'\\ud83d\\udfe2 Verificato':'\\ud83d\\udfe1 In attesa'}",
    "e.statusEmoji=function(t){return'verified'===t?"
    "'\\ud83d\\udfe2 Verificato':'community'===t?"
    "'\\ud83d\\udccd Community':'\\ud83d\\udfe1 In attesa'}",
    "etichetta status community",
)

src = replace_once(
    src,
    'children:"\\ud83d\\udfe2 verificato \\xb7 \\ud83d\\udfe1 in attesa"',
    'children:"\\ud83d\\udfe2 verificato \\xb7 '
    '\\ud83d\\udd35 community \\xb7 \\ud83d\\udfe1 in attesa"',
    "legenda con community",
)

path.write_text(src, encoding="utf8")
print(f"Bundle aggiornato: {path}")
