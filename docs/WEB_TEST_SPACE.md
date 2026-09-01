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

## Passaggio al pubblico

Tre passaggi, tutti automatizzati da `scripts/promote_web_public.sh`:

1. app da `/t/<token>/` alla root di `gh-pages` (base dei percorsi riscritta
   da `/Parkour_NoToTFamily/t/<token>` a `/Parkour_NoToTFamily`);
2. via il `robots.txt` restrittivo e i meta `noindex`;
3. QR pubblico — `docs/qr/webapp-qr.png` codifica già l'URL base
   `https://oigresergio.github.io/Parkour_NoToTFamily/`, quindi diventa
   valido nel momento in cui l'app arriva sulla root. Va rigenerato solo se
   l'URL cambia (dominio custom): `python3 scripts/make_qr.py --url <URL>`.

```sh
scripts/promote_web_public.sh --dry-run   # prova a vuoto: prepara il commit, non pubblica
scripts/promote_web_public.sh             # pubblica
```

Non serve un nuovo export Expo: lo script riusa il bundle già online.
Prima del push salva lo stato attuale sul branch `gh-pages-anteprima`, quindi
si torna indietro con `git push -f origin gh-pages-anteprima:gh-pages`.

### Cosa cambia esattamente

Il lavoro vero lo fa `scripts/gh_pages_public.py` (idempotente, si può anche
lanciare a mano su una copia di `gh-pages`):

- app spostata sulla root, `/t/<token>/` eliminato;
- **gate a inviti PkPASS rimosso**: il redirect su `pk_pass` rimandava alla
  root, che ora *è* l'app — lasciandolo si otterrebbe un loop di reindirizzamenti.
  Con l'app pubblica gli inviti non servono più (`admin-inviti.html` resta
  online ma fuori dagli indici);
- meta `noindex, nofollow` tolti da tutte le pagine tranne `admin-inviti.html`;
- `robots.txt` permissivo (`Allow: /`, `Disallow: /admin-inviti.html`) con
  riga `Sitemap:`, più `sitemap.xml`;
- `404.html` diventa una copia di `index.html`, così i deep link della SPA
  funzionano anche su GitHub Pages;
- meta SEO di base su `index.html`: `title`, `description`, `canonical`,
  Open Graph, Twitter card, `lang="it"`, `theme-color`.

Resta attiva la modalità test del bundle (spot fissi, tutto gratuito): è una
scelta di prodotto, non un effetto del passaggio al pubblico. Per disattivarla
serve un nuovo export senza le patch di `patch-gh-pages-test-free.py`.

### Deploy successivi

Dopo il passaggio al pubblico, i nuovi export vanno pubblicati con:

```sh
cd mobile && npx expo export --platform web
cd .. && scripts/deploy_public_web.sh mobile/dist
```

(`scripts/deploy_test_web.sh` resta per tornare all'anteprima privata.)

### Dominio custom (facoltativo)

Se in futuro colleghi un dominio, dopo averlo configurato su GitHub Pages:

```sh
python3 scripts/make_qr.py --url https://tuo-dominio.it/
# poi aggiorna SITE_URL in scripts/promote_web_public.sh e deploy_public_web.sh
```
