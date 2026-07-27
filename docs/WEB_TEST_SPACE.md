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
