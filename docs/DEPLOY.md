# Build e deploy

Sostituisce `WEB_TEST_SPACE.md`, che descriveva il mondo precedente: un export
Expo pubblicato su `gh-pages` e modificato con string-replace su JavaScript
minificato. Quel sorgente non è mai esistito nel repo e la catena di patch era
dichiaratamente non idempotente. Ora la web app **si builda da Flutter**, dallo
stesso codice di iOS e Android.

## Build locale

```sh
cd mobile
flutter pub get
flutter run -d chrome \
  --dart-define=SUPABASE_URL=https://<project-ref>.supabase.co \
  --dart-define=SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

Senza `--dart-define` l'app parte lo stesso e mostra una schermata che spiega
cosa manca, invece di una mappa vuota e una pila di errori in console.

## Build di produzione

```sh
cd mobile
flutter build web --release \
  --dart-define=SUPABASE_URL=https://<project-ref>.supabase.co \
  --dart-define=SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
# output in mobile/build/web
```

La **publishable key** finisce nel bundle: è pubblica per costruzione e va
bene, ma significa che **le policy RLS sono l'unica difesa del database**.
`scripts/audit_rls.mjs` (BLOCCO 9) le verifica in CI. La *secret key* non entra
in nessun build, mai.

## Dove va

| Ambiente | URL | Accesso |
| --- | --- | --- |
| Produzione | `https://pkfamily.app` | pubblico |
| Staging | `https://staging.pkfamily.app` | Cloudflare Access, su invito |
| Legacy | `oigresergio.github.io/Parkour_NoToTFamily` | redirect 301 al dominio nuovo |

Hosting su **Cloudflare Pages**, non GitHub Pages: servono header HTTP veri
(CSP, HSTS, `Permissions-Policy`) e uno staging protetto a livello di edge,
che GitHub Pages non offre. Vedi [`LAUNCH_PLAN.md`](LAUNCH_PLAN.md) §1.2.

I workflow di deploy (`deploy-staging.yml`, `deploy-prod.yml`) arrivano col
BLOCCO 8: staging a ogni push su `main`, produzione **solo da tag** — così
tornare indietro è ripubblicare il tag precedente.

## L'anteprima privata attuale

Il branch `gh-pages` serve ancora il vecchio bundle Expo sotto
`/t/<token>/`, per chi ha il QR. Resta lì finché il nuovo sito non è online,
poi diventa un redirect. Non è più aggiornabile: gli script che lo facevano
sono stati rimossi.

Va ricordato quello che `WEB_TEST_SPACE.md` diceva già: quel percorso è
**riservatezza, non autenticazione**. Il repository è pubblico e il gate
JavaScript ha il segreto in chiaro.

## Stato dello schema

`supabase/migrations/0001` e `0002` descrivono uno schema **mai applicato in
produzione** e sono marcate come storiche. Quello reale è ricostruito in
`0003_production_baseline.sql`, che **non è un dump**: prima del lancio va
sostituito con l'output di `scripts/dump_schema.sh`, altrimenti il disaster
recovery resta teorico.
