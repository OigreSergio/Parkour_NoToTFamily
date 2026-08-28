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
flutter build web --release --csp --no-web-resources-cdn \
  --dart-define=SUPABASE_URL=https://<project-ref>.supabase.co \
  --dart-define=SUPABASE_PUBLISHABLE_KEY=sb_publishable_...

cd ..
SUPABASE_URL=https://<project-ref>.supabase.co \
SUPABASE_PUBLISHABLE_KEY=sb_publishable_... \
node scripts/prepare_deploy.mjs --env=prod
# output pronto in mobile/build/web
```

I due flag non sono opzionali, e nessuno dei due è cosmetico:

- **`--csp`** dice a dart2js di non generare codice a runtime. Senza, la CSP
  avrebbe bisogno di `'unsafe-eval'`, che è la cosa che una CSP esiste per
  impedire.
- **`--no-web-resources-cdn`** serve CanvasKit dalla nostra origine. Senza, a
  ogni apertura il browser va a prenderlo su `www.gstatic.com`: una richiesta
  verso Google che l'informativa dichiara che **non** avviene. Non è una
  sfumatura — è la differenza fra un'informativa vera e una sbagliata.

`prepare_deploy.mjs` verifica entrambi e si rifiuta di preparare il deploy se
mancano. Verifica anche che l'host Supabase compilato nel bundle sia lo stesso
che finisce nella CSP, e che nel bundle non ci sia finita una secret key.

La **publishable key** finisce nel bundle: è pubblica per costruzione e va
bene, ma significa che **le policy RLS sono l'unica difesa del database**.
`scripts/audit_rls.mjs` le verifica in CI, ed è bloccante prima di ogni deploy
in produzione. La *secret key* non entra in nessun build, mai.

## Cosa aggiunge `prepare_deploy.mjs`

Il build Flutter non sa niente di HTTP: produce file, non header. Lo script
aggiunge le tre cose che mancano a un sito pubblico.

| File | Da dove viene | Cosa fa |
| --- | --- | --- |
| `_headers` | `deploy/_headers.template` | CSP, HSTS, `Permissions-Policy`, cache |
| `_redirects` | `deploy/_redirects` | www → apex, `/t/*` → `/`, routing SPA |
| `.well-known/security.txt` | generato | contatto, con `Expires` ricalcolato ogni volta |
| `robots.txt` | generato | permissivo in produzione, `Disallow: /` su staging |
| `sitemap.xml` | generato | solo in produzione |

Perché generati e non statici: la CSP deve nominare **l'host Supabase reale**,
che cambia se il progetto viene ricreato altrove; `security.txt` scade (RFC 9116
rende `Expires` obbligatorio) e una data vecchia è peggio del file assente; e
`robots.txt` dev'essere l'opposto fra staging e produzione, dove sbagliarsi
significa far indicizzare l'ambiente di prova.

## Deploy automatico

| Quando | Workflow | Dove va |
| --- | --- | --- |
| push su `main` | `deploy-staging.yml` | `staging.pkfamily.app` |
| tag `v*` | `deploy-prod.yml` | `pkfamily.app` |

In produzione si va **solo da tag**, perché il rollback dev'essere «ripubblica
`v1.2.3`»: una cosa che si fa in trenta secondi mentre il sito è rotto. Prima
di pubblicare, `deploy-prod.yml` rifà analyze, test e **audit RLS** — un tag si
può mettere su qualsiasi commit, anche uno che non è mai passato da una PR. Dopo
il deploy interroga il sito vero e fallisce se gli header di sicurezza non ci
sono: Cloudflare può ignorare un `_headers` con la sintassi sbagliata senza dire
niente.

Secret necessari: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`,
`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`. Sono in `docs/OPS_TODO.md`.

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

Il ricambio è pronto in `deploy/gh-pages/` e si pubblica con:

```sh
./scripts/publish_gh_pages_redirect.sh          # mostra cosa farebbe
./scripts/publish_gh_pages_redirect.sh --fallo  # lo fa
```

Lo script **controlla da sé che `https://pkfamily.app` risponda 200** e si
ferma se non lo fa. Non è una precauzione formale: finché il dominio nuovo non
è online, `gh-pages` è l'unica versione raggiungibile, e sostituirla prima
significherebbe mandare su una pagina morta tutti quelli che hanno il QR.

Una cosa da sapere e non da scoprire dopo: **GitHub Pages non può fare un 301
vero**, perché il redirect HTTP lo decide il server e quel server non è nostro.
Quello che la pagina fa è `rel=canonical` (la parte che conta per i motori di
ricerca), un meta refresh e un link visibile. Funziona, ma non è la stessa cosa
e non va raccontata come se lo fosse.

Va ricordato quello che `WEB_TEST_SPACE.md` diceva già: quel percorso è
**riservatezza, non autenticazione**. Il repository è pubblico e il gate
JavaScript ha il segreto in chiaro.

## Stato dello schema

`supabase/migrations/0001` e `0002` descrivono uno schema **mai applicato in
produzione** e sono marcate come storiche. Quello reale è ricostruito in
`0003_production_baseline.sql`, che **non è un dump**: prima del lancio va
sostituito con l'output di `scripts/dump_schema.sh`, altrimenti il disaster
recovery resta teorico.
