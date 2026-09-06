# Provare dal telefono

Tre modi, dal più veloce al più fedele. Il primo non installa niente ma è una
simulazione; gli altri due parlano con un backend vero.

## 1. La pagina di anteprima — zero installazioni

<https://oigresergio.github.io/Parkour_NoToTFamily/t/prova-accesso/>

Sta su GitHub Pages accanto all'anteprima della web app, sotto `/t/` che
`robots.txt` già tiene fuori dai motori di ricerca. Si apre nel browser come
qualunque sito — niente account, niente app da installare — e all'arrivo parte
dritta sull'accesso, come farebbe l'app aperta per la prima volta.

Il QR per il telefono è `docs/qr/prova-accesso-qr.png`.

Fa girare **gli stessi due moduli** che finiscono nella web app —
`scripts/web/pk-legal.js` e `scripts/web/pk-onboarding.js` — con un backend
finto dentro la pagina. Le informative, i nomi degli scavalcamenti, le tabelle
dei tetti e le regole del gioco sono generate dal codice Python, non riscritte
a mano.

Il codice di accesso **non si compila da solo**: la pagina mostra la mail
no-reply che sarebbe partita — mittente, oggetto e corpo veri, presi dal
servizio — e il codice va letto e ricopiato, come si fa col telefono in mano.

Cosa **non** fa: non manda email davvero (non ha un server), non salva niente
da nessuna parte, e non è l'app Flutter.

Da provare almeno una volta: entra come ospite, metti una data di nascita da
quindicenne, dichiara «più di 10 anni». Il catalogo in fondo si accorcia, e in
nessun punto compare qualcosa che spieghi perché — che è esattamente il
comportamento che la versione sicura deve avere.

## 2. L'app Flutter sul telefono, contro il backend sul PC

Serve che telefono e computer stiano sulla stessa Wi-Fi.

**Il backend, in ascolto su tutta la rete e non solo su sé stesso:**

```sh
docker compose up db redis -d          # dalla radice del repo
cd backend
cp .env.example .env
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` è la riga che conta: con il default (`127.0.0.1`) il telefono
non lo vede, e sembra un problema dell'app.

**L'indirizzo del computer sulla rete locale:**

```sh
hostname -I | awk '{print $1}'   # Linux
ipconfig getifaddr en0           # macOS, Wi-Fi
ipconfig                         # Windows → "Indirizzo IPv4"
```

Prima di toccare l'app, aprilo dal browser del telefono:
`http://<indirizzo>:8000/healthz` deve rispondere `{"status":"ok"}`. Se non
risponde è il firewall del computer, non il codice.

**L'app:**

```sh
cd mobile
flutter run --dart-define=API_BASE_URL=http://<indirizzo>:8000
```

Sull'emulatore Android il flag non serve: il default `10.0.2.2:8000` è già
l'alias del computer. Sul simulatore iOS usa `http://localhost:8000`.

> **HTTP in chiaro.** Da Android 9 il traffico non cifrato è bloccato. Le build
> di *debug* lo permettono (`usesCleartextTraffic` sta nel manifest di debug,
> `mobile/android/app/src/debug/AndroidManifest.xml`); quelle di release no, di
> proposito.

**Cosa vedi:** «Continua senza account» → l'informativa sui rischi → il nome
generato e la chiave → data di nascita (e, sotto i 18, il consenso di un
genitore) → da quanto pratichi → il gioco degli scavalcamenti. Poi chiudi
l'app e riaprila: rientra da sola con la chiave, senza chiedere niente.

## 3. Il browser del telefono, contro lo stesso backend

È il flusso web, quello che finirà nel bundle della web app.

```sh
cd scripts/web && python3 -m http.server 8080
```

Il browser fa richieste da un'origine diversa, quindi va aggiunta ai CORS in
`backend/.env`:

```
CORS_ORIGINS=http://<indirizzo>:8080
```

Poi, dal telefono:

```
http://<indirizzo>:8080/prova.html?api=http://<indirizzo>:8000
```

`prova.html` è una pagina di servizio, non fa parte della web app: serve a
provare `pk-legal.js` e `pk-onboarding.js` senza dover riesportare il bundle
Expo.

## Il codice via email

Il codice torna nella risposta (`debug_code`, che `prova.html` precompila)
**solo finché nessun messaggio parte davvero**: cioè con `MAIL_BACKEND=console`
o `memory`. Serve a poter entrare senza un server di posta.

Appena configuri un SMTP il campo diventa `null` e il codice viaggia solo per
email, anche fuori produzione. È la parte che conta: se il codice arrivasse
comunque nella risposta, aprire la casella non sarebbe mai necessario e la
mail non proverebbe niente sull'indirizzo.

Per provare la mail vera:

```
MAIL_BACKEND=smtp
MAIL_FROM=noreply@iltuodominio
MAIL_FROM_NAME=PkFAMILY
SMTP_HOST=smtp.iltuoprovider
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_STARTTLS=true
```

Va bene qualunque SMTP: il tuo provider, oppure una casella di prova tipo
Mailtrap se non vuoi spedire a indirizzi veri mentre sviluppi. Il mittente è
no-reply per costruzione — le intestazioni `Auto-Submitted: auto-generated` e
`X-Auto-Response-Suppress: All` scoraggiano risposte automatiche, e il corpo
indirizza alla casella che le persone leggono davvero (`MODERATION_EMAIL`).

In produzione `MAIL_BACKEND=smtp` è obbligatorio: l'app non parte altrimenti.

Il login guest non usa email: è la via più corta per vedere tutto il resto.

## Ripartire da zero

| Dove | Come |
| ---- | ---- |
| Pagina di anteprima e `prova.html` | il pulsante «Ricomincia da zero» |
| App | disinstallala, o svuota i dati: la chiave sta nel portachiavi |
| Backend | `alembic downgrade base && alembic upgrade head` |

Attenzione a cancellare la chiave di un ospite: senza, quell'account non si
recupera più. È il rovescio di non chiedere un'email.
