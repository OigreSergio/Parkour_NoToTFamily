# Spazio web di test (anteprima privata)

La web app (export Expo) resta sempre online su GitHub Pages, ma in modalità
anteprima privata finché non sarà pronta per il lancio pubblico.

## Com'è organizzato il branch `gh-pages`

```
/                  → pagina placeholder ("anteprima privata"), meta noindex
/404.html          → placeholder, meta noindex
/robots.txt        → User-agent: * / Disallow: /   (blocca tutti i crawler)
/t/<token>/        → la web app vera e propria, base dei percorsi riscritta
```

- **Non indicizzata**: `robots.txt` + meta `noindex, nofollow` su tutte le
  pagine (placeholder e app).
- **Accesso solo via QR**: l'URL con il token non è linkato da nessuna pagina;
  chi apre l'indirizzo base vede solo il placeholder. Il QR di accesso è
  `docs/qr/webapp-test-qr.png` (o `.svg`).

## Limite da conoscere

È *riservatezza*, non autenticazione: il repository è pubblico, quindi chi
esplora il branch `gh-pages` può risalire al percorso, e chiunque riceva
l'URL (o il QR) può aprirlo e condividerlo. Per un accesso davvero
controllato servirà un hosting con protezione (es. Cloudflare Access, basic
auth su un piccolo server) — sensato solo se il test si allarga oltre la
cerchia fidata.

## Modalità test attiva sul bundle

Sul bundle pubblicato sono applicate le patch di
`scripts/patch-gh-pages-test-free.py`:

- **mappa satellitare** (tile raster Esri World Imagery);
- **spot fissi**: gli spot di `scripts/data/webapp_fixed_spots.json` sono
  incorporati nel bundle e fusi con quelli di Supabase (la mappa è popolata
  anche se il backend è irraggiungibile). Oltre ai 26 spot della famiglia ci
  sono ~1700 spot con status `community`, importati dalla lista Google Maps
  condivisa "Parkour spot" (vedi `scripts/import_gmaps_list_spots.py`): pin
  blu, etichetta "📍 Community". Con così tanti spot i marker vengono creati
  solo per il viewport corrente (e sfoltiti su griglia a zoom bassi);
- **foto degli spot fissi**: il campo `photos` (URL) di uno spot fisso viene
  mostrato nella scheda di dettaglio; per aggiornare spot/foto sul bundle già
  pubblicato senza rifare l'export c'è `scripts/update_deployed_spots.py`;
- **tutto gratuito**: `useEntitlements` ritorna sempre `hasBase/hasChat/
  hasVideo/hasAny = true` e il banner "Iscriviti" è disattivato. Nota: le
  RLS lato Supabase restano attive, quindi le *scritture* riservate (es.
  commenti senza abbonamento) falliscono comunque lato server.

Dopo un nuovo export Expo le patch vanno riapplicate al nuovo bundle
(`python3 scripts/patch-gh-pages-test-free.py <entry.js>`) prima del push.

## Rideploy dell'app aggiornata

Ogni volta che vuoi pubblicare una nuova build web nell'anteprima:

```sh
cd mobile && npx expo export --platform web   # genera dist/
cd .. && scripts/deploy_test_web.sh mobile/dist
```

Lo script ripubblica `gh-pages` conservando placeholder, robots e percorso
riservato. Il token attuale è in cima allo script.

## Passaggio al pubblico (quando sarà il momento)

1. Spostare l'app da `/t/<token>/` alla root di `gh-pages` (o rideploy senza
   riscrittura della base).
2. Rimuovere `robots.txt` restrittivo e i meta `noindex`.
3. Rigenerare il QR "pubblico" (`docs/qr/webapp-qr.png`, che oggi porta al
   placeholder) e, volendo, collegare un dominio custom prima di pubblicizzare.
