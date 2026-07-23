#!/usr/bin/env python3
"""Patch del bundle web PkFAMILY (gh-pages, build Expo minificata).

1. publishSpot: su errore RLS 42501 apre una mail precompilata per l'admin
   (adminpkfamily@gmail.com) invece di mostrare l'errore abbonamento.
2. Nuovo spot: conferma con dialogo browser (l'Alert RN è un no-op su web)
   sia per il percorso email sia per la pubblicazione diretta dell'admin.
3. Nuovo spot: pulsante "Cerca via o piazza" (geocoding Nominatim) accanto a
   "Usa la mia posizione"; il tap sulla mappa resta invariato.
4. Mappa: flyTo sul pin "nuovo-spot-pin" quando viene creato o spostato.
5. Nuovo spot: all'apertura chiede una volta per sessione se usare il GPS.
"""
import sys

path = sys.argv[1]
src = open(path, encoding="utf8").read()


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


# --- 1. publishSpot: mail all'admin invece dell'errore 42501 ---------------
new1 = (
    r"if(p||!u){if('42501'===p?.code){try{const _s='Proposta nuovo spot PkFAMILY: '+n.name,"
    r"_b='Ciao admin PkFAMILY!\n\nVorrei proporre questo nuovo spot:\n\n"
    r"Nome: '+n.name+'\nDescrizione: '+(n.description||'-')+'\n"
    r"Mappa: https://www.google.com/maps?q='+n.lat+','+n.lng+'\n"
    r"Coordinate: '+n.lat+', '+n.lng+'\nLivello skill: '+n.skillLevel+'\n"
    r"Affollamento: '+n.crowdLevel+'\nFontanella nei pressi: '+(n.hasFountain?'sì':'no')+'\n\n"
    r"In allegato le foto dello spot.\n';"
    r"window.location.href='mailto:adminpkfamily@gmail.com?subject='+encodeURIComponent(_s)+'&body='+encodeURIComponent(_b)}catch(_e){}"
    r"return{error:null,emailed:!0}}return{error:p?.message??'Errore sconosciuto.'}}"
)
src = replace_span(
    src,
    "if(p||!u)return'42501'===p?.code?{error:'Per pubblicare",
    "{error:p?.message??'Errore sconosciuto.'};",
    new1 + ";",
    "publishSpot mailto",
)

# --- 2. Nuovo spot: conferma via dialogo browser ---------------------------
new2 = (
    r'const{error:e,emailed:_em}=await(0,v.publishSpot)({name:p.trim(),description:R.trim(),'
    r'lat:N.lat,lng:N.lng,skillLevel:M,crowdLevel:H,hasFountain:W,photos:D},$);'
    r'G(!1),$(""),e?J(e):(window.alert(_em?'
    r'"📧 Proposta inviata!\n\nTi ho aperto una mail già compilata per l’admin '
    r'(adminpkfamily@gmail.com): allega le foto dello spot e premi Invia. '
    r'Appena verificato, lo spot comparirà sulla mappa.":'
    r'"Spot inviato! 🟡\n\nIl tuo spot \xe8 in coda di verifica: lo vedi solo tu '
    r'(marker giallo) finch\xe9 un admin non lo approva."),t.back())'
)
src = replace_span(
    src,
    "const{error:e}=await(0,v.publishSpot)",
    '[{text:"Ok",onPress:()=>t.back()}])',
    new2,
    "conferma nuovo spot",
)

# --- 3. Nuovo spot: pulsante "Cerca via o piazza" --------------------------
new3 = (
    r'(de=(0,_.jsxs)(_.Fragment,{children:['
    r'(0,_.jsx)(d.default,{style:O.secondaryButton,onPress:Z,children:'
    r'(0,_.jsx)(h.default,{style:O.secondaryButtonText,children:"📍 Usa la mia posizione"})}),'
    r'(0,_.jsx)(d.default,{style:O.secondaryButton,onPress:async function(){'
    r'''const e=window.prompt('🔎 Cerca via o piazza\n(es. "Via Giulio Tarra 34, Roma")');'''
    r'if(!e||!e.trim())return;'
    r"try{const t=await fetch('https://nominatim.openstreetmap.org/search?format=json&limit=1&accept-language=it&q='+encodeURIComponent(e.trim())),"
    r'n=await t.json();'
    r"if(!n||!n.length)return void window.alert('Via non trovata 🔎\nProva ad aggiungere la città, es. “…, Roma”.');"
    r'F({lat:parseFloat(n[0].lat),lng:parseFloat(n[0].lon)})}'
    r"catch(_e){window.alert('Ricerca non riuscita: controlla la connessione e riprova.')}},"
    r'children:(0,_.jsx)(h.default,{style:O.secondaryButtonText,children:"🔎 Cerca via o piazza"})})'
    r']}),e[29]=de)'
)
src = replace_span(
    src,
    "(de=(0,_.jsx)(d.default,{style:O.secondaryButton,onPress:Z,",
    "e[29]=de)",
    new3,
    "pulsante cerca via",
)

# --- 4a. Mappa: flyTo quando il pin nuovo-spot viene spostato ---------------
old4a = (
    r"if(e)e.marker.setLngLat([s.lng,s.lat]),e.el.style.borderColor=(0,u.markerColor)(s.status);else{"
)
new4a = (
    r"if(e){const _p=e.marker.getLngLat();e.marker.setLngLat([s.lng,s.lat]),"
    r"e.el.style.borderColor=(0,u.markerColor)(s.status),"
    r"'nuovo-spot-pin'===s.id&&(Math.abs(_p.lng-s.lng)>1e-7||Math.abs(_p.lat-s.lat)>1e-7)&&"
    r"t.flyTo({center:[s.lng,s.lat],zoom:Math.max(t.getZoom(),15),duration:700})}else{"
)
src = replace_once(src, old4a, new4a, "flyTo pin spostato")

# --- 4b. Mappa: flyTo quando il pin nuovo-spot viene creato -----------------
old4b = (
    r"const l=new n.default.Marker({element:e}).setLngLat([s.lng,s.lat]).addTo(t);"
    r"o.set(s.id,{marker:l,el:e})}"
)
new4b = (
    r"const l=new n.default.Marker({element:e}).setLngLat([s.lng,s.lat]).addTo(t);"
    r"o.set(s.id,{marker:l,el:e}),"
    r"'nuovo-spot-pin'===s.id&&t.flyTo({center:[s.lng,s.lat],zoom:Math.max(t.getZoom(),15),duration:700})}"
)
src = replace_once(src, old4b, new4b, "flyTo pin creato")

# --- 5. Nuovo spot: proposta GPS all'apertura (una volta per sessione) ------
old5 = r";const Z=Y;let ee;"
new5 = (
    r";const Z=Y;(0,s.useEffect)(()=>{const e=setTimeout(()=>{"
    r"try{if(!sessionStorage.getItem('pk_gps_ask')){sessionStorage.setItem('pk_gps_ask','1');"
    r"window.confirm('📍 Vuoi usare il GPS per trovarti subito sulla mappa?\n\n"
    r"(In alternativa puoi cercare la via 🔎 o toccare la mappa per mettere il pin)')&&Z()}}"
    r"catch(_e){}},700);return()=>clearTimeout(e)},[]);let ee;"
)
src = replace_once(src, old5, new5, "proposta GPS all'apertura")

open(path, "w", encoding="utf8").write(src)
print("bundle patchato:", path)
