# PkFAMILY — Masterplan web app, community e sicurezza

> Documento di raccordo. Tiene insieme **grafica**, **struttura**, **community
> sempre attiva (4 turni su 24 h)** e **sicurezza dei dati** della web app
> PkFAMILY (Parkour NoToT Family). È scritto per essere letto da persone e da
> agenti AI che lavoreranno sul repository: frasi corte, una regola per riga,
> tabelle dove servono, nessuna conoscenza implicita.
>
> Versione 1.0 · 15 settembre 2026 · branch `claude/sharp-johnson-1qrer5`.
> Il prompt operativo per Opus 5 Max che usa questo documento è in
> [`PROMPT_OPUS5_MAX.md`](PROMPT_OPUS5_MAX.md).


## Indice

| Capitolo | Per chi | In una riga |
| --- | --- | --- |
| [0. Come usare questo documento](#0-come-usare-questo-documento) | tutti | Regole di lettura, glossario (Dot, fake report, turno), fonti di verità, assunzioni |
| [1. Fotografia dello stato attuale](#1-fotografia-dello-stato-attuale-settembre-2026) | tutti | Cosa esiste davvero nel repo e online, dati reali, problemi trovati in ordine di urgenza |
| [2. Visione e principi](#2-visione-e-principi-non-negoziabili) | tutti | Le dieci regole, a partire da "niente attività finta" |
| [3. Elevazione grafica](#3-elevazione-grafica--il-design-system-pkfamily) | agenti UI/design | Identità "ricamo su lino", token, tipografia, componenti, layout responsive, PWA, lingue |
| [4. Elevazione strutturale](#4-elevazione-strutturale--architettura-dati-pipeline) | agenti backend/infra | Architettura obiettivo, un solo backend, rotte, modello dati, Edge Functions, CI/CD, osservabilità |
| [5. Community sempre viva](#5-community-sempre-viva--workflow-4-turni-zero-contenuti-finti) | lead community, moderatori, agenti console | I 4 turni UTC, SLA, cosa fa Dot, playbook di attività reali, metriche, anti fake report, regole |
| [6. Sicurezza dei dati](#6-sicurezza-dei-dati--misure-massime-in-ordine-di-priorità) | agenti sicurezza, admin | Minacce, priorità 0, identità e RLS, privacy by design, infrastruttura, backup e incidenti, verifiche |
| [7. Roadmap a fasi](#7-roadmap-a-fasi-con-criteri-di-accettazione) | admin, agenti | Sei fasi con criteri di accettazione e definizione di "fatto" |
| [8. Protocollo tra agenti](#8-protocollo-di-collaborazione-tra-agenti) | agenti | Formato dell'incarico, nota di consegna, regole di lavoro, passaggio tra agenti |
| [Appendici](#appendici) | operativi | Turni settimana tipo, SQL di moderazione, stati di una segnalazione, handoff, codice di condotta, checklist rilascio, decisioni aperte |

---

## 0. Come usare questo documento

### 0.1 Se sei un agente AI

1. Leggi **tutto** il capitolo 0 e il capitolo 2 (principi). Sono le regole.
2. Leggi il capitolo che riguarda il tuo compito (3 grafica, 4 struttura,
   5 community, 6 sicurezza). Gli altri capitoli li consulti solo se servono.
3. Prima di scrivere codice, leggi il capitolo 1: dice **cosa esiste davvero**
   e dove. Non ricostruire ciò che c'è già.
4. Segui il protocollo di consegna del capitolo 8. Ogni consegna dice cosa è
   fatto, cosa è verificato, cosa manca e quali rischi restano.
5. Regola di precedenza: per lo **stato attuale** vince il codice nel repo;
   per la **direzione** vince questo documento. Se i due divergono, scrivilo
   nella consegna, non risolverlo in silenzio.

### 0.2 Glossario (termini usati in tutto il documento)

| Termine | Significato in questo documento |
| --- | --- |
| **PkFAMILY** | Il prodotto: mappa collaborativa degli spot di parkour, tutorial, community, chat. Nome tecnico del repo: Parkour NoToT Family. |
| **Web app** | La build Flutter web pubblicata su GitHub Pages (branch `gh-pages`) più le pagine statiche che le stanno intorno (`/stato/`, catalogo tutorial, landing). |
| **Family / membri** | Le persone reali con un account. |
| **Dot** | Qualsiasi assistente automatico o bot del prodotto (assistente in-app, automazioni, script). Dot **non pubblica mai** commenti, post, voti o segnalazioni. Può solo aiutare le persone (vedi 5.4). |
| **Fake report** | Una segnalazione non fatta da una persona reale su un contenuto reale: generata, simulata, duplicata artificialmente o inventata per "far vedere attività". Vietata sempre. |
| **Turno** | Finestra di 6 ore in UTC in cui almeno un moderatore umano è responsabile della community (vedi 5.2). |
| **Moderatore** | Membro con ruolo `moderator`: gestisce segnalazioni e contenuti. Non ha accesso ai dati personali oltre lo stretto necessario. |
| **Admin** | L'unico ruolo che governa ruoli, chiavi, backup e configurazione. |
| **Fonte di verità** | Il posto dove un dato "vale": vedi 0.3. |

### 0.3 Fonti di verità

| Cosa | Dove vale | Note |
| --- | --- | --- |
| Dati di produzione (spot, profili, post, segnalazioni…) | Progetto Supabase `PkFAMILY` (Postgres + RLS) | Schema di riferimento in `supabase/migrations/`. Le tabelle reali sono più di quelle nelle migrazioni (vedi 1.3): vanno esportate. |
| Codice dell'app | Branch `main` di questo repo | Oggi la build pubblicata a settembre 2026 **non** ha i sorgenti su `main` (vedi 1.4). Va sanato per primo. |
| Build pubblicata | Branch `gh-pages` | Deve essere sempre generata da `main` via CI, mai a mano. |
| Regole di prodotto e direzione | Questo documento + `docs/PROJECT_RULES_AND_ROADMAP.md` | In caso di conflitto tra i due, vale questo documento; il vecchio va aggiornato. |
| Segreti | GitHub Environments / Secrets e il gestore password dell'admin | Mai nel repo, mai in pagine pubblicate, mai nelle chat. |

### 0.4 Assunzioni dichiarate

- "Dot" non compare nel codice attuale. Lo trattiamo come nome dell'assistente
  automatico del prodotto. Se Dot fosse un'altra cosa, la regola non cambia:
  **nessun contenuto sintetico spacciato per attività della community**.
- La web app di riferimento è la build Flutter web (settembre 2026). Il vecchio
  bundle Expo ancora servito alla root di `gh-pages` è considerato legacy.
- Lingue iniziali: italiano ed inglese, poi spagnolo e portoghese brasiliano,
  poi giapponese e altre lingue asiatiche. L'app deve nascere già traducibile.
- Orari: tutti gli orari di servizio sono espressi in **UTC**; le interfacce
  mostrano l'ora locale dell'utente.

---

## 1. Fotografia dello stato attuale (settembre 2026)

Questa sezione descrive ciò che esiste. Non è un giudizio: serve a non
rifare il lavoro e a partire dai problemi veri.

### 1.1 Cosa c'è nel monorepo (`main`, ultimo commit 11 agosto 2026)

| Cartella | Contenuto | Stato reale |
| --- | --- | --- |
| `backend/` | API FastAPI + PostGIS + Redis: auth JWT, spot, moderazione, commenti, video, chat WebSocket. Test con pytest. | Completo come scaffold, **non è il backend di produzione** (l'app parla direttamente con Supabase). |
| `mobile/` | App Flutter (Riverpod, flutter_map): mappa, lista, dettaglio spot, tutorial, suggeritore di trick. | Sorgenti fermi a luglio/agosto. La build web pubblicata a settembre ha più funzioni (account, email, fontanelle, segnalazioni) i cui sorgenti **non sono qui**. |
| `web-admin/` | Next.js: login + coda spot in attesa. | Prototipo, poco usato. |
| `admin-desktop/` | Console admin in un singolo `index.html`: moderazione, utenti, segnalazioni, backup. | Usa la **secret key** Supabase dentro il browser. Da sostituire (vedi 6.2). |
| `supabase/` | `0001_initial.sql` (profili, spot, like, audit, chat, video, tutto con RLS), `0002_instructor_role.sql`, seed. | Buona base. Lo schema reale di produzione ha tabelle in più (posts, comments, ratings, reports, entitlements, blocked_users, fountains, spot_photos, video_progress, chats). |
| `docs/` | Architettura, modello dati, regole, verifica spot, spazio web di test, routing PK, demo HTML, foto spot con manifest e licenze, QR. | Ottima documentazione di base; alcune parti descrivono il bundle Expo ormai legacy. |
| `scripts/` | Pipeline dati: lista Google Maps (1.710 spot), foto, patch del bundle, deploy anteprima. | Funzionanti; alcune legate al bundle Expo. |
| `infra/` | Mappa locale (tile) e routing OSRM self-hosted. | Pronti come compose, non in produzione. |
| `📲/` | Backup pubblico quotidiano (branch `backup` rigenerata ogni notte) + piano di recovery. | Attivo. Il backup pubblico include `profiles` (username, ruolo). |
| `.github/workflows/` | `backup-quotidiano.yml`, `sync-map.yml`. | Nessuna CI di test/lint, nessun deploy automatico della web app. |

### 1.2 Cosa c'è online (branch `gh-pages`)

| Percorso | Cosa è | Note |
| --- | --- | --- |
| `/` | Vecchio bundle Expo (React Native web) + `pk-route.js` + `pk-scheda.js`, con meta SEO e `robots.txt` aperto | Legacy: da sostituire con la landing e l'app Flutter. |
| `/t/30dc…/` | **Build Flutter web attuale**: mappa "ricamo", 1.706 spot, 124 tutorial, satellite, fontanelle (OSM), distanza, Street View, voti, form segnalazione, accesso via email, menù account, font Quicksand | È l'app vera. Percorso "riservato" ma solo per riservatezza, non per sicurezza. `manifest.json` e `index.html` ancora con i default Flutter ("A new Flutter project"). |
| `/t/prova-accesso/` | Pagina di prova del flusso di accesso (codice via email, palette "lino/filo", font Fraunces + Karla) | Contiene la publishable key (va bene) e l'URL del progetto. |
| `/stato/` | Pagina pubblica di stato del progetto | Aggiornata a luglio. |
| `/tutorial-catalog.html` | Catalogo tutorial statico | Palette diversa dall'app. |
| `/admin-inviti.html` | Console inviti a pagamento (5 €), genera link firmati con un segreto **scritto in chiaro nella pagina** | Problema di sicurezza P0 (vedi 6.2). Non linkata e in `robots.txt`, ma pubblica. |

### 1.3 Dati reali (dal backup pubblico del 20 luglio 2026)

Tabelle in produzione: `spots`, `spot_photos`, `fountains`, `profiles`
(`username`, `avatar_url`, `role`, `banned`), `posts`, `comments`,
`post_likes`, `post_saves`, `ratings`, `videos`, `video_progress`, `reports`
(`reason`, `post_id | comment_id | message_id`), `chats`, `chat_members`,
`messages`, `entitlements`, `blocked_users`. A luglio: 24 spot verificati,
2 profili, community vuota. L'app di settembre incorpora 1.706 spot e 124
tutorial come dati di anteprima.

### 1.4 Problemi trovati, in ordine di urgenza

| # | Problema | Perché conta | Dove si risolve |
| --- | --- | --- | --- |
| P0-1 | Segreto di firma inviti in chiaro in `admin-inviti.html` | Chiunque può generare inviti "pagati" e ruoli admin | 6.2, fase 0 |
| P0-2 | Console admin che usa la secret key nel browser | Una chiave che bypassa tutte le RLS vive in localStorage di un PC | 6.2, fase 0 |
| P0-3 | Sorgenti della build pubblicata non su `main` | Nessuno può ricostruire l'app; impossibile fare CI, review, sicurezza | 4.6, fase 0 |
| P1-1 | Schema di produzione non esportato nelle migrazioni | Recovery (scenario B del piano backup) non eseguibile | 4.4, fase 0 |
| P1-2 | Nessuna CI (test, lint, scansione segreti, build) | Ogni push è un rischio | 4.6, fase 0 |
| P1-3 | Due backend (FastAPI e Supabase) senza una decisione | Lavoro duplicato, regole diverse | 4.2 |
| P2-1 | Tre palette e tre famiglie di font in giro (lino/filo, console blu, demo teal; Quicksand, Fraunces+Karla, system) | L'app non sembra un unico prodotto | 3 |
| P2-2 | Web app con `index.html`/manifest di default, senza landing, senza pagine spot indicizzabili | Non si condivide, non si trova, non si installa bene | 3.8, 4.3 |
| P2-3 | Segnalazioni senza stato, senza assegnazione, senza SLA, senza audit | Impossibile moderare 24 h con turni | 5, 4.4 |
| P2-4 | Backup pubblico con `profiles` | Username e ruolo sono pubblici nell'app, ma un dump quotidiano su GitHub è un'esposizione in più | 6.6 |

---

## 2. Visione e principi non negoziabili

**Visione.** PkFAMILY è la casa digitale dei traceur: si apre in un secondo
sul telefono, mostra gli spot veri intorno a te con foto vere, ti dice come
arrivarci e chi ci si allena, e ti fa trovare persone reali con cui muoverti.
È una web app installabile (PWA) che sembra e si comporta come un'app nativa,
identica in Asia, Europa e Sud America nello stesso istante.

**Principi.** Sono regole, non consigli. Ogni agente le rispetta senza chiedere.

1. **Regola zero: niente attività finta.** Ogni commento, post, voto, like,
   segnalazione e messaggio è scritto da una persona reale con un account
   reale. Dot (o qualsiasi bot) non pubblica mai nulla a nome della community.
   Nessun account seme, nessun "riempimento", nessun contatore gonfiato.
2. **Solo verificato è pubblico.** Uno spot è `pending → verified | rejected`;
   sulla mappa vanno solo i `verified` (la lista Google Maps importata resta
   etichettata `community` finché una persona non la verifica).
3. **Minimo dato necessario.** Raccogliamo e mostriamo solo i dati che servono
   alla funzione. La posizione dell'utente resta sul dispositivo.
4. **Nessun segreto nel client.** Publishable key sì, secret key mai. Le
   operazioni privilegiate passano da funzioni server con ruolo verificato.
5. **Una sola fonte per il codice.** Tutto ciò che è online nasce da `main`
   tramite CI. Niente build a mano, niente patch sul bundle pubblicato.
6. **Un solo prodotto, un solo linguaggio visivo.** Un design system, dei
   token, dei componenti. Ogni pagina nuova li usa.
7. **Le persone moderano, le macchine aiutano.** Dot può riassumere,
   tradurre, classificare, proporre. Decide e pubblica sempre una persona.
8. **Trasparenza.** Le regole della community, i tempi di risposta e le
   statistiche di moderazione sono pubblici.
9. **Accessibile e veloce ovunque.** WCAG 2.2 AA, funziona su rete 3G in
   Giacarta come su fibra a Roma.
10. **Ogni cambiamento è tracciato.** Migrazioni solo in avanti, audit log
    immutabile per le azioni di moderazione, commit convenzionali.

---

## 3. Elevazione grafica — il design system PkFAMILY

Obiettivo: far sembrare la web app un prodotto unico, curato e riconoscibile,
partendo da ciò che già funziona (la mappa "ricamo su lino", gli spilli da
cucito, la scheda spot con Street View) e unificando il resto.

### 3.1 Identità visiva: "ricamo su lino"

La metafora già scelta per la mappa diventa l'identità di tutto il prodotto:
il lino è lo sfondo, i fili colorati sono gli accenti, gli spilli sono i
marker, le cuciture sono i bordi. Calda, artigianale, diversa da qualsiasi app
di mappe. Le pagine admin usano la stessa base con contrasto più alto.

### 3.2 Token (una sola lista, usata da Flutter, pagine statiche e console)

| Token | Chiaro | Scuro | Uso |
| --- | --- | --- | --- |
| `lino` (sfondo) | `#F4ECE0` | `#16130E` | Sfondo pagina |
| `carta` (superficie) | `#FBF7EF` | `#201B14` | Card, fogli, pannelli |
| `carta-alt` | `#EFE4D2` | `#2A241B` | Superficie secondaria, chip |
| `inchiostro` (testo) | `#1F1B16` | `#F0E7D7` | Testo principale |
| `tenue` (testo secondario) | `#6F6456` | `#A2947F` | Etichette, didascalie |
| `filo` (accento) | `#C26A52` | `#D98A70` | Azioni primarie, link, spillo selezionato |
| `filo-scuro` | `#A8543E` | `#E6A894` | Hover/pressed dell'accento |
| `verde` (ok) | `#63864A` | `#8FB072` | Verificato, successo, fontanella |
| `ambra` (attesa) | `#B97A0E` | `#E0A94E` | In attesa, avvisi |
| `rosso` (errore) | `#B4463A` | `#E06C5F` | Errori, rifiutato, azioni distruttive |
| `blu-community` | `#6F9CB8` | `#8FB4CC` | Spot `community` non ancora verificati, info |
| `cucitura` (bordo) | `#E0D4BD` | `#362E23` | Bordi, divisori |
| `ombra` | `0 1px 0 rgba(31,27,22,.05)` | nessuna | Elevazione minima |

Regole: contrasto testo/sfondo ≥ 4,5:1 (verificato per ogni coppia sopra);
i colori di stato non sono mai l'unico segnale (sempre icona o testo accanto).
Il tema segue il sistema, con interruttore manuale salvato sul dispositivo.

### 3.3 Tipografia

| Ruolo | Famiglia | Pesi | Note |
| --- | --- | --- | --- |
| Display (titoli, numeri grandi) | **Fraunces** | 600, 700 | Già usata nella pagina di accesso. Ottica variabile, carattere caldo. |
| Testo e UI | **Karla** | 400, 500, 700 | Leggibile a 14–16 px, ottima resa su schermi economici. |
| Mono (coordinate, codici) | `ui-monospace` | 400 | Coordinate, ID, codici invito. |

Scala: 12 · 14 · 16 (base) · 18 · 22 · 28 · 36 · 44. Interlinea 1,45 per il
testo, 1,05 per i titoli. La build Flutter passa da Quicksand a Karla/Fraunces
(font incorporati con subset latino esteso; giapponese/cinese usano il font di
sistema con fallback dichiarato).

### 3.4 Spaziatura, forma, movimento

- Griglia a 4 px: 4 · 8 · 12 · 16 · 24 · 32 · 48.
- Raggi: 10 px (input, chip), 14 px (card), 20 px (fogli in basso), pieno per
  avatar e badge.
- Bordi da 1 px color `cucitura`; ombre quasi assenti (l'identità è piatta e
  materica, non "glassy").
- Movimento: 150 ms per stati, 250 ms per transizioni di pagina, curva
  standard; `prefers-reduced-motion` disattiva tutto tranne le dissolvenze.
- Area tocco minima 44×44 px; focus visibile sempre (anello 2 px `filo`).

### 3.5 Iconografia e mappa

- Icone: Material Symbols Rounded, peso 400, riempite quando attive.
- Spilli: SVG "spillo da cucito" già esistente. Testa colorata per stato:
  `verde` verificato, `blu-community` community, `ambra` in attesa (visibile
  solo all'autore e ai moderatori), `filo` selezionato. Punta esatta sul
  punto. A zoom bassi: cluster a "gomitolo" con numero.
- Stile mappa: `embroidery_style.json` è la fonte; la vista satellite resta
  come alternativa con un solo interruttore.
- Posizione utente: punto `blu-community` con alone, mai memorizzata.
- Fontanelle: goccia `verde` piccola, con distanza in metri.

### 3.6 Componenti (nomi condivisi tra codice e documento)

| Componente | Cosa fa | Stati obbligatori |
| --- | --- | --- |
| `PkAppBar` | Titolo, azione di ritorno, azioni contestuali | default, con ricerca aperta |
| `PkBottomNav` / `PkNavRail` | Mappa · Lista · Tutorial · Community · Io | attivo, badge notifiche |
| `PkSpotCard` | Anteprima spot: foto, nome, difficoltà, distanza, fontanella, voto | caricamento (scheletro), senza foto (Street View come copertina), errore |
| `PkSpotSheet` | Scheda completa: galleria, contesto visivo, "portami lì", voti, commenti, segnala | ospite (solo lettura), membro, moderatore |
| `PkTutorialCard` | Miniatura, titolo, livello, durata, "atterrato" | libero, premium bloccato, atterrato |
| `PkPostCard` | Post community: autore, spot collegato, media, reazioni, segnala | normale, in revisione (solo autore/mod), rimosso |
| `PkChip` | Filtri (livello, fontanella, verificati, distanza) | selezionato, disabilitato |
| `PkButton` | primario (`filo`), secondario (bordo), distruttivo (`rosso`), fantasma | caricamento, disabilitato |
| `PkEmptyState` | Illustrazione a "punto croce" + testo + azione | prima visita, nessun risultato, offline |
| `PkToast` / `PkDialog` | Conferme, errori, azioni irreversibili | — |
| `PkReportForm` | Segnala contenuto: motivo, dettagli, anteprima di cosa si segnala | inviato, duplicato già aperto |
| `PkModQueueItem` | Voce della coda di moderazione con timer SLA | aperto, preso in carico, scaduto |

Ogni componente vive in `mobile/lib/ui/` (Flutter) e, per le pagine statiche,
in un foglio `docs/site/pk.css` con le stesse variabili CSS dei token.

### 3.7 Layout responsive

| Larghezza | Navigazione | Mappa e scheda |
| --- | --- | --- |
| < 600 px (telefono) | `PkBottomNav` a 5 voci | Mappa a tutto schermo, scheda come foglio dal basso (3 altezze: anteprima, metà, piena) |
| 600–1024 px (tablet) | `PkNavRail` a sinistra | Mappa + scheda in colonna destra da 360 px |
| > 1024 px (desktop) | Rail + intestazione | Mappa + pannello laterale 420 px, lista e scheda affiancate; scorciatoie da tastiera (`/` cerca, `Esc` chiude) |

La web app è utilizzabile con sola tastiera e con lettore di schermo: la mappa
ha una lista equivalente sempre raggiungibile.

### 3.8 Da "sito Flutter" a web app installabile

- `index.html` e `manifest.json` di marca: nome "PkFAMILY", descrizione,
  `theme-color` `#C26A52`, icone 192/512 e maskable, splash su lino con lo
  spillo, `lang` corretto, Open Graph e Twitter card.
- Schermata di avvio in HTML/CSS puro (non attende il motore Flutter):
  logo, barra di progresso, testo "Sto cucendo la mappa…".
- Service worker: cache dell'app shell, delle tile già viste e dei dati di
  anteprima; modalità offline dichiarata (`PkEmptyState` offline).
- Prestazioni obiettivo su 4G medio: primo contenuto < 1,8 s (schermata di
  avvio), app interattiva < 4 s, pagine statiche < 100 kB, immagini in
  WebP/AVIF con dimensioni esplicite. Build Flutter con WebAssembly quando
  supportato, CanvasKit in fallback, caricamento differito delle sezioni
  pesanti (chat, community).
- Pagine statiche indicizzabili accanto all'app (vedi 4.3): landing, pagina
  di ogni spot verificato, catalogo tutorial, stato, regole, privacy.

### 3.9 Lingue, orari, unità

- Tutte le stringhe in file ARB (Flutter) e JSON (pagine statiche). Nessuna
  stringa scritta a mano nel codice.
- Ordine di rilascio: it, en → es, pt-BR → ja, zh-Hans, ko.
- Date e ore mostrate nel fuso dell'utente con l'indicazione "(ora locale)";
  gli orari dei turni e degli eventi sono salvati in UTC.
- Unità: metri/chilometri ovunque (il parkour è metrico anche in America).
- Testi brevi, tono "family": diretto, caldo, mai infantile. Le stesse parole
  in tutte le lingue per gli stati (`verificato`, `in attesa`, `community`).

### 3.10 Consegne del capitolo grafica

1. `docs/design/tokens.json` + `docs/site/pk.css` + `mobile/lib/ui/theme.dart`
   generati dalla stessa lista di token.
2. Libreria componenti Flutter con una pagina "vetrina" (`/app/vetrina`,
   visibile solo in sviluppo) che mostra ogni componente in ogni stato.
3. `index.html`, `manifest.json`, icone, splash, service worker di marca.
4. Verifica accessibilità automatica (contrasto, etichette) nella CI.
5. Screenshot di riferimento (telefono, tablet, desktop, chiaro e scuro) in
   `docs/design/screens/`.

---

## 4. Elevazione strutturale — architettura, dati, pipeline

### 4.1 Architettura obiettivo (vista d'insieme)

```
                ┌──────────────────────────────────────────────┐
                │  Pagine statiche (landing, /spot/<slug>/,     │
                │  tutorial, stato, regole, privacy)  ← SEO     │
   Browser ───► │  Web app Flutter (PWA)  /app/…                │
   (tel./PC)    │  Console moderazione + admin  /console/…      │
                └───────────────┬──────────────────────────────┘
                                │ HTTPS, publishable key, sessione utente
                ┌───────────────▼──────────────────────────────┐
                │  Supabase (regione EU)                        │
                │  Auth (email OTP/magic link, passkey, MFA)    │
                │  Postgres + PostGIS + RLS  (fonte di verità)  │
                │  Storage privato (foto) con URL firmati       │
                │  Realtime (chat, coda moderazione)            │
                │  Edge Functions (azioni privilegiate, inviti, │
                │  email, Dot-copilota, digest)                 │
                └───────────────┬──────────────────────────────┘
                                │ solo da funzioni server
                ┌───────────────▼──────────────────────────────┐
                │  Servizi esterni: tile mappa (OpenFreeMap /   │
                │  server locale), OSRM routing, email          │
                │  transazionale, Sentry, Cloudflare (WAF/CDN)  │
                └──────────────────────────────────────────────┘
```

### 4.2 Decisione: un solo backend in produzione

- **Supabase è il backend di produzione**: Auth, Postgres con RLS, Storage,
  Realtime, Edge Functions. È già dove vivono i dati e l'app di settembre.
- **FastAPI resta come servizio di supporto**, non come API dell'app: proxy
  con cache per il routing PK (OSRM self-hosted, `docs/ROUTING_PK.md`) e job
  pesanti (pipeline foto, import spot). Se entro la fase 2 non serve, si
  archivia in `legacy/` con una nota. Nessuna nuova funzione di prodotto va
  in FastAPI.
- **Le regole di business stanno nel database** (vincoli, trigger, policy RLS,
  funzioni SQL) e nelle Edge Functions per ciò che richiede privilegi. I
  client mirrorano, non inventano (regola già in vigore).
- **Dove vive il servizio di supporto (settembre 2026):** in `remote-service/`
  (pacchetto Python `pkremote`), scritto per girare in remoto senza database
  proprio: stato, proxy dei percorsi con cache e coordinate arrotondate, job
  sui dati. `backend/` resta com'è finché la decisione G non lo archivia. Le
  ragioni e lo stato sono in `docs/ANALISI_STRUTTURA_PYTHON.md`.

### 4.3 Mappa delle rotte (information architecture)

| Rotta | Cosa mostra | Chi può | Tipo |
| --- | --- | --- | --- |
| `/` | Landing: cos'è, mappa anteprima, "Apri l'app", QR | tutti | statica |
| `/spot/<slug>/` | Pagina di uno spot verificato: foto, descrizione, mappa, fontanelle, link all'app | tutti | statica, generata dai dati a ogni build |
| `/tutorial/` | Catalogo tutorial (già esistente, da riallineare ai token) | tutti | statica |
| `/stato/` | Stato del progetto e registro modifiche | tutti | statica |
| `/regole/`, `/privacy/`, `/termini/`, `/trasparenza/` | Regole community, informativa, condizioni, report di moderazione | tutti | statiche |
| `/app/` | Shell PWA; reindirizza a `/app/mappa` | tutti (ospite) | Flutter |
| `/app/mappa`, `/app/lista` | Mappa e lista spot con filtri | tutti | Flutter |
| `/app/spot/<id>` | `PkSpotSheet` | tutti; commenti e voti solo membri | Flutter |
| `/app/spot/nuovo` | Proponi uno spot (`pending`) | membri | Flutter |
| `/app/tutorial`, `/app/tutorial/<id>` | Tutorial con livelli e "atterrato" | tutti; premium per abbonati | Flutter |
| `/app/community` | Feed di post reali (per spot, per zona, per lingua) | lettura tutti; scrittura membri | Flutter |
| `/app/chat` | Conversazioni 1:1 e gruppi | membri | Flutter |
| `/app/io` | Profilo, lingua, tema, privacy, esporta/elimina dati | membri | Flutter |
| `/app/segnala/<tipo>/<id>` | `PkReportForm` | membri | Flutter |
| `/console/` | Coda moderazione, turni, passaggi di consegne, statistiche | `moderator`, `admin` | Flutter (stesso codice, sezione protetta) |
| `/console/admin` | Ruoli, inviti, backup, configurazione | `admin` con MFA | Flutter |

I percorsi `/t/<token>/` e `admin-inviti.html` spariscono al termine della
fase 0. Il vecchio bundle Expo viene rimosso da `gh-pages`.

### 4.4 Modello dati (estensione dello schema reale)

Lo schema di produzione va prima **esportato** in `supabase/migrations/0003_stato_produzione.sql`
(dump dello schema, senza dati). Poi, in migrazioni separate e solo in avanti:

| Tabella / modifica | Scopo |
| --- | --- |
| `profiles.role` ammette `moderator` (oltre a `user`, `instructor`, `admin`) | Ruolo di moderazione senza poteri admin |
| `profiles` + `locale`, `timezone`, `region` (`EU`, `AS`, `SA`, `NA`, `AF`, `OC`) | Lingua, ora locale, appartenenza ai turni; `region` scelta dall'utente, mai dedotta dalla posizione |
| `reports` + `status`, `severity`, `category`, `assigned_to`, `taken_at`, `resolved_at`, `resolution`, `resolution_note`, `duplicate_of`, `sla_due_at`, `reporter_hash` | Segnalazione con ciclo di vita completo (appendice C) |
| `moderation_actions` (nuova, append-only) | Ogni azione di moderazione: chi, cosa, su cosa, perché, quando, turno. Nessun `UPDATE`/`DELETE` (trigger che li vieta) |
| `moderation_shifts` (nuova) | Le 4 finestre UTC (appendice A) |
| `shift_assignments` (nuova) | Chi copre quale turno in quale settimana; primario e riserva |
| `shift_handoffs` (nuova) | Nota di passaggio di consegne a fine turno (appendice D) |
| `user_strikes` (nuova) | Richiami, silenziamenti, ban con scadenza e motivo |
| `appeals` (nuova) | Ricorso dell'autore contro un'azione; deciso da un moderatore diverso |
| `community_events` (nuova) | Jam, sessioni, sfide: reali, con organizzatore umano |
| `content_versions` (nuova) | Versioni di post/commenti modificati, per la moderazione |
| `spots.slug`, `spots.region`, `spots.language_hint` | Pagine statiche, filtri per area e lingua |
| `notification_preferences` (nuova) | Consenso esplicito per ogni tipo di notifica |
| Viste: `moderation_queue`, `community_health_daily` | Coda con timer SLA; metriche reali (5.6) |

Ogni tabella ha RLS attiva e politiche esplicite. Ogni politica ha un test
(vedi 6.3). Le viste per i moderatori espongono solo i campi necessari.

### 4.5 Contratti delle funzioni privilegiate (Edge Functions)

| Funzione | Chi la chiama | Cosa fa | Controlli |
| --- | --- | --- | --- |
| `mod-take` / `mod-resolve` | moderatore | Prende in carico e chiude una segnalazione, scrive in `moderation_actions` | Ruolo, turno attivo o lead, motivo obbligatorio |
| `mod-strike` | moderatore | Richiamo, silenzio 24 h / 7 gg, ban (il ban lo conferma un secondo moderatore o l'admin) | Doppia firma per il ban |
| `invite-create` / `invite-redeem` | admin / utente | Inviti firmati **lato server** con scadenza e uso singolo | Sostituisce `admin-inviti.html` |
| `account-export` / `account-delete` | utente | Esporta i propri dati (JSON) e cancella l'account (GDPR) | Conferma via email, cancellazione differita 7 gg |
| `digest-build` | pianificata | Costruisce il riepilogo settimanale **solo da contenuti reali** | Nessuna generazione di contenuti |
| `dot-assist` | moderatore | Riassume, traduce, classifica un contenuto per il moderatore | Output visibile solo al moderatore; non scrive mai nel DB dei contenuti |
| `photo-ingest` | utente | Riceve foto, elimina EXIF/geotag, ridimensiona, sposta nel bucket privato | Limite dimensione, tipi ammessi, scansione |

### 4.6 Pipeline: da `main` a online, sempre e solo via CI

| Workflow | Quando | Cosa fa |
| --- | --- | --- |
| `ci.yml` | ogni PR e push su `main` | `flutter analyze` + `flutter test`; `ruff` + `pytest`; lint pagine statiche; test RLS su Postgres effimero; scansione segreti (gitleaks); controllo licenze foto (manifest presenti) |
| `deploy-web.yml` | push su `main` | Build Flutter web → genera pagine statiche dai dati → pubblica `gh-pages`. Nessun altro modo di aggiornare `gh-pages` |
| `preview.yml` | PR con etichetta `preview` | Pubblica sotto `/preview/<pr>/` con `noindex`; cancellata alla chiusura |
| `db-migrate.yml` | manuale, con approvazione | Applica le migrazioni via Supabase CLI; blocca se lo schema reale diverge |
| `backup-quotidiano.yml` | ogni notte | Come oggi, con le modifiche di 6.6 |
| `sync-map.yml` | manuale | Come oggi, ma produce dati per la build, non patch sul bundle |
| `budget.yml` | ogni PR | Lighthouse su landing e `/app/`: fallisce se sfora i budget di 3.8 |
| `remote-service.yml` (esiste) | PR e push su `main` che toccano `remote-service/` | `ruff` + `pytest` del servizio remoto; sui push su `main` costruisce l'immagine, la prova su `/healthz` e la pubblica su GitHub Container Registry |
| `gitleaks.yml` (esiste) | ogni push e PR; settimanale su tutta la storia | Scansione segreti (S0-4). La chiave pubblicabile è esclusa in `.gitleaks.toml` |

Ambienti GitHub: `production` (segreti di deploy e Supabase, richiede
approvazione dell'admin), `preview`. I segreti stanno lì e in nessun altro posto.

### 4.7 Osservabilità

- Sentry per Flutter web ed Edge Functions (senza PII: niente email, niente
  posizione, niente corpo dei messaggi).
- Controllo di disponibilità esterno su `/` e `/app/` ogni 5 minuti con
  avviso all'admin e al moderatore di turno.
- Cruscotto in `/console/`: segnalazioni aperte per turno, SLA rispettati,
  errori delle ultime 24 h, utenti attivi reali.

### 4.8 Consegne del capitolo struttura

1. Sorgenti della build di settembre recuperati e uniti in `main`
   (`mobile/`), con `flutter build web` riproducibile.
2. `supabase/migrations/0003_stato_produzione.sql` + migrazioni 0004… per le
   tabelle di 4.4, con test RLS.
3. Edge Functions di 4.5 in `supabase/functions/`, con test.
4. Workflow di 4.6 in `.github/workflows/`.
5. `docs/ARCHITECTURE.md` e `docs/DATA_MODEL.md` aggiornati per riflettere
   Supabase come backend di produzione.

---

## 5. Community sempre viva — workflow, 4 turni, zero contenuti finti

### 5.1 Cosa significa "sempre attiva"

Non significa "sempre piena di commenti". Significa che in qualsiasi momento,
in qualsiasi fuso, una persona che apre l'app trova: contenuti reali recenti,
una risposta umana alle segnalazioni entro tempi dichiarati, e occasioni
concrete per allenarsi con altri. L'attività la fanno i membri; il team crea
le condizioni e garantisce la presenza umana 24 ore su 24.

### 5.2 I 4 turni (6 ore ciascuno, in UTC, con 15 minuti di sovrapposizione)

| Turno | Finestra UTC | Roma (CEST / CET) | Tokyo | Giacarta | São Paulo | Chi lo copre di norma |
| --- | --- | --- | --- | --- | --- | --- |
| **A · Alba** | 00:00–06:00 | 02–08 / 01–07 | 09–15 | 07–13 | 21–03 | Moderatori in Asia e Oceania |
| **B · Ponte** | 06:00–12:00 | 08–14 / 07–13 | 15–21 | 13–19 | 03–09 | Moderatori in Europa, Medio Oriente, India |
| **C · Meridiano** | 12:00–18:00 | 14–20 / 13–19 | 21–03 | 19–01 | 09–15 | Moderatori in Europa, Africa, Sud America |
| **D · Sera** | 18:00–24:00 | 20–02 / 19–01 | 03–09 | 01–07 | 15–21 | Moderatori nelle Americhe |

Regole dei turni:

- Le finestre sono fisse in UTC: l'ora legale non le sposta; cambia solo la
  colonna locale (l'app la calcola).
- Ogni turno ha un **primario** e una **riserva**. La riserva risponde se il
  primario non prende in carico una segnalazione P0 entro 15 minuti.
- Un **lead di moderazione** (a rotazione settimanale) è reperibile per le
  escalation in qualsiasi turno. Il ban richiede la sua conferma o quella
  dell'admin.
- Passaggio di consegne: negli ultimi 15 minuti il moderatore uscente scrive
  la nota di handoff (appendice D); l'entrante la conferma. Nessun turno
  inizia senza nota confermata.
- Copertura minima: 4 moderatori primari + 4 riserve + 1 lead = 9 persone
  reali. Finché la squadra è più piccola, si copre con turni doppi dichiarati
  in `/trasparenza/` (mai con un bot).
- Calendario delle assegnazioni in `shift_assignments`, visibile in
  `/console/turni`, con esportazione ICS per ogni moderatore.

### 5.3 Livelli di priorità e tempi di risposta (SLA)

| Livello | Esempi | Presa in carico | Decisione |
| --- | --- | --- | --- |
| **P0** | Minaccia, dati personali esposti, minori, contenuti illegali, spot su proprietà privata con rischio | 15 min | 1 h |
| **P1** | Molestie, spam, impersonazione, foto senza licenza, segnalazione ripetuta sullo stesso contenuto | 1 h | 6 h |
| **P2** | Off-topic, duplicati, errori nei dati dello spot, descrizioni non chiare | 6 h | 24 h |
| **P3** | Suggerimenti, richieste di modifica, ricorsi non urgenti | 24 h | 72 h |

I timer partono alla creazione della segnalazione e sono visibili nella coda.
Un P0 non preso in carico entro 15 minuti avvisa riserva e lead; a 30 minuti
avvisa l'admin.

### 5.4 Cosa fa Dot (e cosa non farà mai)

| Dot **può** (solo verso persone del team) | Dot **non può** |
| --- | --- |
| Riassumere una discussione lunga per il moderatore | Scrivere commenti, post, risposte, recensioni |
| Tradurre una segnalazione o un post nella lingua del moderatore | Mettere like, voti, "atterrato", salvataggi |
| Proporre categoria e priorità di una segnalazione (il moderatore conferma) | Creare o inviare segnalazioni |
| Preparare una bozza di risposta all'autore, che il moderatore modifica e firma | Pubblicare nulla in autonomia, nemmeno "a nome del team" |
| Costruire il digest settimanale **da contenuti reali** con link e autori | Inventare eventi, spot, statistiche, testimonianze |
| Segnalare pattern sospetti (stesso IP, raffiche di report) al lead | Avere un account con profilo pubblico |

Ogni output di Dot è marcato `origine: dot` nei log e non entra nelle tabelle
dei contenuti. Un test automatico verifica che nessun `INSERT` in `posts`,
`comments`, `ratings`, `reports`, `messages` provenga da un ruolo di servizio.

### 5.5 Playbook: attività reali che tengono viva la community

Il moderatore di turno non è solo "guardia": è **ospite di casa**. Ogni
attività qui sotto è fatta da una persona con il proprio nome, mai da un bot.

| Ritmo | Attività | Chi | Come si evita il finto |
| --- | --- | --- | --- |
| Ogni turno | Rispondere ai nuovi post senza risposte da più di 12 h, dare il benvenuto ai nuovi membri (messaggio personale, non template automatico) | moderatore di turno | Risposte scritte a mano, firmate |
| Ogni turno | Controllare la coda, chiudere P2/P3 vecchi, aggiornare la nota di handoff | moderatore di turno | — |
| Ogni giorno | "Domanda del giorno" in bacheca, scritta dal moderatore del turno B o C, taggata come **team** | moderatore | Etichetta visibile "dal team PkFAMILY" |
| Ogni settimana | **Spot della settimana**: scelto tra gli spot con attività reale (voti, foto, commenti), presentato con le foto e i commenti dei membri (citati con consenso) | lead + editor | Nessun dato inventato; link ai contenuti originali |
| Ogni settimana | Digest email/notifica: nuovi spot verificati, post più utili, eventi in arrivo per regione | `digest-build` + revisione umana | Solo contenuti esistenti, con autore |
| Ogni settimana | **Jam regionali**: almeno un allenamento reale a settimana per regione, creato da un membro o istruttore in `community_events` | membri, istruttori, ambasciatori | Un evento ha sempre un organizzatore umano e un luogo verificato |
| Ogni mese | Sfida del mese (es. "10 spot nuovi verificati in Asia"), con classifica **di azioni reali** (spot proposti e verificati, foto con licenza, ricorsi accolti) | lead | Contatori calcolati dal DB, non modificabili a mano |
| Ogni mese | Domande & risposte con un istruttore (live o asincrono) | istruttore | Persona reale, ruolo `instructor` |
| Ogni mese | Report di trasparenza in `/trasparenza/`: segnalazioni ricevute, tempi, azioni, ricorsi | lead | Numeri presi dalle viste del DB |
| Continuo | Programma ambasciatori: un referente per città/regione che apre la strada ai nuovi (badge visibile) | admin | Badge assegnato da un admin a una persona identificata |
| Continuo | Riconoscimenti per azioni reali: "primo spot verificato", "5 foto con licenza", "risposta utile" (votata dai membri) | automatico ma basato su fatti | Nessun riconoscimento per attività simulata |

Il primo mese, con pochi membri, va bene che la bacheca sia poco affollata:
è preferibile a una bacheca piena di contenuti finti. La landing lo dice
chiaramente: "Community nuova, tutte le persone qui sono vere".

### 5.6 Metriche di salute (tutte calcolate da dati reali)

| Metrica | Definizione | Obiettivo iniziale |
| --- | --- | --- |
| Membri attivi settimanali | Account con almeno un'azione (post, commento, voto, spot, evento) negli ultimi 7 gg | crescita costante, nessuna soglia finta |
| Tempo alla prima risposta | Mediana tra un post e la prima risposta di **un altro membro** | < 12 h |
| SLA rispettati | % di segnalazioni prese in carico e decise nei tempi di 5.3, per turno | ≥ 95 % |
| Ricorsi accolti | % di azioni ribaltate in appello | < 10 % (se più alto, i moderatori sbagliano; se 0 %, i ricorsi non funzionano) |
| Spot verificati a settimana | Nuovi `verified` per regione | ≥ 5 per regione attiva |
| Eventi svolti | `community_events` con almeno 2 partecipanti confermati | ≥ 1 per regione a settimana |
| Ritenzione D7 / D30 | Nuovi membri ancora attivi dopo 7 / 30 gg | misurare, poi migliorare |

Vietato: contatori di "membri online" gonfiati, "visualizzazioni" stimate,
qualsiasi metrica non ricostruibile da una query.

### 5.7 Integrità delle segnalazioni (anti fake report)

- Una segnalazione richiede un account con email verificata e almeno 24 h di
  anzianità (gli ospiti possono solo "nascondere per me").
- Limite: 5 segnalazioni per utente per ora, 20 al giorno; oltre, la
  segnalazione entra in coda "da verificare" con priorità bassa.
- Deduplica: stesso contenuto segnalato da più persone → un solo fascicolo
  con contatore; raffiche dallo stesso dispositivo/IP → un solo fascicolo con
  flag `possibile_abuso`.
- Peso del segnalante: chi ha segnalazioni accolte pesa di più; chi ha molte
  segnalazioni respinte pesa meno. Il peso ordina la coda, **non decide**.
- Ogni segnalazione chiusa ha esito e nota; il segnalante riceve un riscontro
  (accolta / respinta / duplicata) senza dettagli sull'altro utente.
- Nessuna segnalazione viene creata da script, test in produzione, o dal team
  "per provare il flusso": si usa l'ambiente di anteprima.

### 5.8 Regole della community (bozza da pubblicare in `/regole/`)

1. Persone vere, nomi scelti liberamente, un account a testa.
2. Gli spot sono luoghi pubblici o con permesso; niente indirizzi privati,
   niente foto di persone riconoscibili senza consenso.
3. Rispetto: niente insulti, niente discriminazioni, niente umiliazione dei
   principianti.
4. Sicurezza prima dello spettacolo: niente incitamento a rischi
   sproporzionati; si può descrivere un trick difficile, non sfidare qualcuno
   a farlo.
5. Foto e video: solo propri o con licenza indicata.
6. Le segnalazioni sono uno strumento, non un'arma: segnalare in malafede ha
   le stesse conseguenze di infrangere le regole.
7. Le decisioni dei moderatori si possono contestare con un ricorso; decide
   un moderatore diverso.

### 5.9 Consegne del capitolo community

1. Tabelle e viste di 4.4 con RLS, test e viste per la coda.
2. Sezione `/console/` con coda, timer SLA, presa in carico, azioni, handoff,
   calendario turni, statistiche.
3. Edge Functions `mod-*`, `dot-assist`, `digest-build`.
4. Pagine `/regole/` e `/trasparenza/` generate dai dati.
5. Documento operativo per i moderatori (`docs/MODERAZIONE.md`) con le
   procedure di 5.2–5.7 in forma di checklist.

---

## 6. Sicurezza dei dati — misure massime, in ordine di priorità

Principio: i dati dei membri sono l'asset del progetto e una responsabilità
legale (GDPR in Europa, LGPD in Brasile, APPI in Giappone). Ogni misura qui
sotto ha un proprietario (agente o persona) e un criterio di verifica.

### 6.1 Modello delle minacce (cosa proteggiamo, da chi)

| Asset | Minaccia principale | Conseguenza |
| --- | --- | --- |
| Email, nome scelto, lingua, regione dei membri | Furto del database, chiave esposta, RLS sbagliata | Violazione dati, obbligo di notifica entro 72 h |
| Messaggi privati della chat | Accesso non autorizzato, moderatore curioso, log verbosi | Danno alle persone, perdita di fiducia |
| Posizione dell'utente | Memorizzazione o invio non necessario | Profilazione, stalking |
| Foto caricate (EXIF con GPS, volti) | Metadati non rimossi, bucket pubblico | Esposizione di abitazioni e persone |
| Ruoli e chiavi (admin, secret key) | Segreto nel client, sessione rubata, nessuna MFA | Controllo totale del sistema |
| Integrità della community | Account finti, raffiche di segnalazioni, script | Moderazione inutilizzabile |
| Disponibilità | Abuso di API pubbliche, dipendenze compromesse | App giù in una regione mentre le altre sono attive |

### 6.2 Priorità 0 — da fare prima di ogni altra cosa

| # | Misura | Come si verifica |
| --- | --- | --- |
| S0-1 | Rimuovere `admin-inviti.html` da `gh-pages`; **ruotare** il segreto `PK_SECRET` e la secret key Supabase; invalidare gli inviti già emessi e riemetterli con `invite-create` | La pagina restituisce 404; la vecchia chiave non autentica più |
| S0-2 | Ritirare `admin-desktop/index.html` come strumento operativo (resta solo in `legacy/` con avviso). Sostituirlo con `/console/admin`: Supabase Auth, ruolo `admin`, MFA obbligatoria, azioni via Edge Functions | Nessun file nel repo o online contiene `sb_secret_` |
| S0-3 | Portare su `main` i sorgenti della build pubblicata; da lì in poi `gh-pages` scritto solo da CI | `deploy-web.yml` verde; `gh-pages` ha come autore solo il bot di CI |
| S0-4 | Scansione segreti in CI (gitleaks) e pre-commit; verifica della storia git (se emerge un segreto: rotazione, non riscrittura silenziosa) | CI fallisce su un segreto di prova |
| S0-5 | MFA (TOTP o passkey) obbligatoria per `admin` e `moderator`; sessioni admin da 12 h massimo | Login admin senza MFA rifiutato |
| S0-6 | Esportare lo schema di produzione e allineare le RLS: ogni tabella con RLS **attiva** e almeno una policy; nessuna tabella "aperta" | Query `select … from pg_tables where not rowsecurity` vuota per lo schema `public` |

### 6.3 Identità, accesso e autorizzazioni

- **Accesso membri**: email + codice usa e getta (OTP) o magic link, con
  passkey (WebAuthn) come opzione consigliata. Password solo se l'utente la
  vuole, con minimo 12 caratteri e controllo contro liste di password
  compromesse. Argon2id resta lo standard dove si gestiscono hash.
- **Ospiti**: possono leggere; non possono scrivere, votare, segnalare. Nessun
  identificativo del dispositivo salvato lato server.
- **Ruoli**: `user` → `instructor` (qualifica), `moderator` (funzione),
  `admin` (governo). Un ruolo si assegna solo da `/console/admin` con MFA, e
  ogni cambio finisce in `moderation_actions`.
- **RLS come unica barriera**: ogni policy è scritta come "chi, cosa, con quale
  condizione" e ha un test SQL (pgTAP o script in CI) che prova il caso
  permesso **e** il caso negato. Le funzioni `security definer` hanno
  `search_path` fisso e sono elencate in `docs/SECURITY_RLS.md`.
- **Principio del minimo privilegio per i moderatori**: vedono username,
  contenuto segnalato, cronologia di moderazione. **Non** vedono email,
  IP, posizione, messaggi privati non segnalati. Le email le vede solo
  l'admin, e solo in `/console/admin`.
- **Sessioni**: token di accesso brevi (≤ 1 h), refresh con rotazione e
  revoca; "esci da tutti i dispositivi" nel profilo; revoca automatica al
  cambio ruolo o al ban.

### 6.4 Protezione dei dati personali (privacy by design)

| Dato | Regola |
| --- | --- |
| Posizione utente | Usata solo sul dispositivo per distanza e percorso. Mai inviata al server, mai loggata. Le richieste di routing inviano solo coordinate arrotondate a 100 m verso il proxy, senza identità |
| Coordinate degli spot | Pubbliche per natura (luoghi pubblici). Uno spot in area privata viene rifiutato |
| Foto | Bucket **privato**; URL firmati a scadenza breve; EXIF e GPS rimossi da `photo-ingest`; opzione di sfocare volti; limite 10 MB, solo JPEG/PNG/WebP/HEIC convertiti |
| Chat | Cifrata in transito e a riposo; conservata 180 giorni poi cancellata; segnalabile con estratto; blocco utente immediato; niente anteprime dei messaggi nei log o nelle notifiche push |
| Email | Solo per accesso, notifiche scelte, comunicazioni obbligatorie. Mai in export pubblici, mai nei backup pubblici |
| Nome scelto / avatar | Pubblici, modificabili, con filtro anti-impersonazione dei ruoli ("admin", "PkFAMILY", "team" riservati) |
| Età | Accesso dai 14 anni (età del consenso digitale in Italia; 16 dove la legge locale lo richiede: l'app chiede la data di nascita solo come anno e non la conserva, salva solo la fascia) |
| Diritti | `/app/io` → esporta i miei dati (JSON entro 24 h), cancella account (7 gg di ripensamento, poi cancellazione con anonimizzazione dei contenuti pubblici: i post restano attribuiti a "membro cancellato") |
| Conservazione | Log applicativi 30 gg; audit di moderazione 2 anni; backup completi cifrati 90 gg; segnalazioni chiuse 1 anno |
| Base giuridica e documenti | Informativa in `/privacy/` (it/en/es/pt-BR), DPA con Supabase e con i fornitori (email, Sentry), registro dei trattamenti in `docs/legal/` |
| Residenza | Progetto Supabase in regione UE; trasferimenti extra-UE coperti da clausole standard dei fornitori |

### 6.5 Sicurezza dell'applicazione e dell'infrastruttura

- **Intestazioni**: GitHub Pages non permette intestazioni personalizzate.
  Soluzione: dominio proprio dietro **Cloudflare** (proxy) che imposta
  `Content-Security-Policy` (senza `unsafe-inline` nelle pagine statiche;
  `wasm-unsafe-eval` solo per l'app Flutter), `Strict-Transport-Security`,
  `X-Content-Type-Options`, `Referrer-Policy: strict-origin-when-cross-origin`,
  `Permissions-Policy` (geolocalizzazione solo per la propria origine). In
  alternativa: hosting su Cloudflare Pages. Fino ad allora: meta CSP nelle
  pagine statiche.
- **WAF e limiti**: regole Cloudflare contro bot e raffiche; limiti in
  Supabase (rate limit auth) e nelle Edge Functions (per utente e per IP);
  Turnstile sui form pubblici (accesso, segnalazione).
- **Accesso alla console**: `/console/*` protetta anche a livello di rete
  (Cloudflare Access con allowlist di email dei moderatori) oltre che da
  ruolo e MFA.
- **Dipendenze**: lockfile committati, Dependabot attivo, CodeQL attivo,
  audit settimanale (`flutter pub outdated`, `npm audit`, `pip-audit`), SBOM
  generato in CI, niente CDN esterne nelle pagine statiche (font e script
  serviti dal sito).
- **Input**: ogni scrittura passa da vincoli DB (lunghezze, enum, check) e da
  validazione nelle Edge Functions; testi sanificati alla visualizzazione;
  link esterni con `rel="noopener nofollow"`; nessun HTML utente.
- **Segreti**: solo in GitHub Environments e nel gestore password dell'admin;
  rotazione ogni 90 giorni (calendario in `docs/SECURITY_RUNBOOK.md`) e
  immediata a ogni sospetto; chiavi Supabase separate per anteprima e
  produzione.
- **Ambienti**: progetto Supabase di anteprima con dati sintetici (qui sì) per
  test e demo; produzione mai usata per prove.

### 6.6 Backup, continuità, incidenti

- Backup completo **cifrato** (age/GPG con chiave dell'admin) ogni notte in
  uno storage privato, non nel repo; conservazione 90 gg; prova di ripristino
  ogni trimestre su un progetto vuoto (esito registrato in `/stato/`).
- Backup pubblico quotidiano: **esclude `profiles`** e qualsiasi tabella con
  dati riferibili a persone; resta utile per spot, video e statistiche.
  Alternativa: renderlo privato del tutto (decisione dell'admin, appendice G).
- Point-in-time recovery (piano Supabase Pro) appena la community supera i
  500 membri.
- **Runbook incidenti** (`docs/SECURITY_RUNBOOK.md`): chi avvisare, come
  ruotare le chiavi, come mettere l'app in sola lettura (interruttore in
  `/console/admin`), modello di comunicazione ai membri, valutazione se
  notificare l'autorità entro 72 h, post-mortem senza colpe entro 7 gg.
- Contatto sicurezza pubblico (`SECURITY.md` esiste): `security.txt` su
  `/.well-known/`, tempi di risposta dichiarati, riconoscimento ai ricercatori.

### 6.7 Verifiche continue

| Verifica | Frequenza | Dove |
| --- | --- | --- |
| Test RLS (permesso + negato) | ogni PR | `ci.yml` |
| Scansione segreti | ogni PR + settimanale su tutta la storia | `ci.yml` |
| Dipendenze vulnerabili | ogni PR + settimanale | Dependabot, CodeQL |
| Intestazioni e TLS (Mozilla Observatory, ssllabs) | mensile | manuale, esito in `/stato/` |
| Revisione accessi (chi è admin/moderator, sessioni attive) | mensile | `/console/admin` |
| Prova di ripristino backup | trimestrale | runbook |
| Test di penetrazione esterno | prima del lancio pubblico, poi annuale | fornitore esterno |
| Programma di bug bounty | dopo il lancio | `SECURITY.md` |

### 6.8 Consegne del capitolo sicurezza

1. Tutte le misure S0 chiuse e verificate (tabella 6.2).
2. `docs/SECURITY_RLS.md` (ogni policy, ogni funzione privilegiata, ogni test).
3. `docs/SECURITY_RUNBOOK.md` (rotazioni, incidenti, sola lettura, contatti).
4. `docs/legal/` (informativa, registro trattamenti, elenco fornitori e DPA).
5. `SECURITY.md` aggiornato con la checklist di 6.7 e `security.txt` online.

---

## 7. Roadmap a fasi con criteri di accettazione

Ogni fase si chiude solo quando **tutti** i criteri sono verificati. Le durate
sono indicative per un agente che lavora a tempo pieno con revisione umana.

| Fase | Durata | Contenuto | Criteri di accettazione |
| --- | --- | --- | --- |
| **0 · Igiene e urgenze** | 1–2 settimane | S0-1…S0-6; sorgenti su `main`; CI base; schema esportato; rimozione bundle Expo e percorsi `/t/` | Nessun segreto online o nel repo; `flutter build web` da `main` riproduce l'app; `ci.yml` verde; migrazione `0003` presente |
| **1 · Design system e shell web** | 2–4 settimane | Token, componenti, tipografia, `index.html`/manifest/splash/service worker, layout responsive, landing e pagine statiche, i18n it/en | Vetrina componenti completa; Lighthouse ≥ 90 su prestazioni/accessibilità/PWA; screenshot di riferimento approvati dall'admin |
| **2 · Struttura dati e console** | 3–5 settimane | Tabelle 4.4, RLS + test, Edge Functions 4.5, `/console/` con coda, turni, handoff, ricorsi | Test RLS verdi; una segnalazione percorre tutto il ciclo (appendice C) in anteprima; audit immutabile verificato |
| **3 · Programma community e turni** | 2–3 settimane | Regole, trasparenza, playbook 5.5, calendario turni, formazione moderatori, digest, eventi | 4 turni coperti per 2 settimane di prova con SLA ≥ 95 %; primo report di trasparenza pubblicato; zero contenuti sintetici (test 5.4) |
| **4 · Hardening completo** | 2–3 settimane | Cloudflare (intestazioni, WAF, Access), Turnstile, backup cifrato, runbook, documenti legali, prova di ripristino, pentest | Observatory A+; pentest senza alti aperti; runbook provato con un'esercitazione |
| **5 · Lancio pubblico** | 1 settimana | Dominio, SEO delle pagine spot, es/pt-BR, comunicazione, QR pubblico | Landing indicizzata; app installabile; `/stato/` e `/trasparenza/` aggiornati |
| **6 · Espansione** | continua | ja/zh/ko, routing PK self-hosted, eventi regionali, istruttori | Metriche 5.6 in crescita reale |

### 7.1 Definizione di "fatto" (vale per ogni consegna)

- [ ] Codice su `main` tramite PR con CI verde e una revisione.
- [ ] Test: unità per le regole, integrazione per le funzioni, RLS per le
      policy, widget per le UI con logica.
- [ ] Documentazione aggiornata (questo documento, `DATA_MODEL.md`,
      `ARCHITECTURE.md`, `SECURITY_*.md`).
- [ ] Nessun dato inventato, nessun segreto, nessuna stringa fuori dai file
      di traduzione.
- [ ] Accessibilità verificata (contrasto, etichette, tastiera).
- [ ] Nota di consegna nel formato del capitolo 8.

---

## 8. Protocollo di collaborazione tra agenti

Serve per far lavorare più agenti (o più sessioni) senza passi falsi.

### 8.1 Ogni incarico arriva in questo formato

```
Incarico: <titolo breve>
Capitoli da leggere: <es. 0, 2, 4.4, 4.5, 6.3>
Obiettivo: <una frase>
File che puoi toccare: <elenco o cartelle>
File che NON devi toccare: <elenco>
Criteri di accettazione: <elenco verificabile>
Vincoli: niente contenuti finti; niente segreti; migrazioni solo in avanti; …
Consegna attesa: PR su <branch> + nota di consegna
```

### 8.2 Ogni consegna finisce con questa nota

```
FATTO: <cosa è stato fatto, in frasi complete>
VERIFICATO: <cosa è stato eseguito e con quale esito: comandi, test, URL>
NON FATTO: <cosa manca e perché>
RISCHI / DECISIONI APERTE: <cosa deve decidere una persona>
DIVERGENZE TROVATE: <dove codice e documento non coincidono>
```

### 8.3 Regole di lavoro

1. Prima leggi, poi scrivi. Non riscrivere ciò che esiste: estendi.
2. Un incarico = un branch = una PR piccola. Commit convenzionali
   (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`).
3. Non inventare dati, nomi, statistiche, testimonianze, eventi. Se serve un
   esempio, usa l'ambiente di anteprima ed etichettalo come tale.
4. Non chiedere conferme per scelte di routine; chiedi solo quando due
   interpretazioni portano a lavori diversi. Nel dubbio, scegli la più
   prudente per la privacy.
5. Se trovi un segreto, non copiarlo mai nella consegna: indica dove sta.
6. Se trovi un problema fuori dal tuo incarico, segnalalo nella nota, non
   correggerlo di nascosto.
7. Aggiorna questo documento quando una decisione cambia; la modifica va nella
   stessa PR.

### 8.4 Come si passano il lavoro due agenti

L'agente uscente scrive la nota di consegna (8.2) e apre la PR; l'agente
entrante legge la nota, la PR e i capitoli indicati, ed elenca nella sua prima
risposta cosa ha capito e cosa farà. Nessun agente parte da zero.

---

## Appendici

### A · Schema dei turni (settimana tipo)

| UTC | Lun | Mar | Mer | Gio | Ven | Sab | Dom |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 00–06 (A) | A1 / rA | A1 / rA | A2 / rA | A2 / rA | A1 / rA | A2 / rA | A1 / rA |
| 06–12 (B) | B1 / rB | B1 / rB | B2 / rB | B2 / rB | B1 / rB | B2 / rB | B1 / rB |
| 12–18 (C) | C1 / rC | C1 / rC | C2 / rC | C2 / rC | C1 / rC | C2 / rC | C1 / rC |
| 18–24 (D) | D1 / rD | D1 / rD | D2 / rD | D2 / rD | D1 / rD | D2 / rD | D1 / rD |

`X1`/`X2` = primari alternati, `rX` = riserva. Il lead cambia ogni lunedì
alle 06:00 UTC. Nessuna persona copre più di 2 turni in 24 h né più di 5
turni a settimana. Le sovrapposizioni (05:45–06:00, 11:45–12:00, 17:45–18:00,
23:45–00:00) servono al passaggio di consegne.

### B · Bozza SQL delle tabelle di moderazione (da rifinire in migrazione)

```sql
-- Ruolo moderator
alter table public.profiles drop constraint if exists profiles_role_check;
alter table public.profiles add constraint profiles_role_check
  check (role in ('user', 'instructor', 'moderator', 'admin'));

-- Ciclo di vita delle segnalazioni
alter table public.reports
  add column status text not null default 'open'
    check (status in ('open','triaged','in_review','resolved','appealed','closed')),
  add column severity text not null default 'P2' check (severity in ('P0','P1','P2','P3')),
  add column category text,
  add column assigned_to uuid references public.profiles(id),
  add column taken_at timestamptz,
  add column resolved_at timestamptz,
  add column resolution text check (resolution in ('actioned','dismissed','duplicate')),
  add column resolution_note text,
  add column duplicate_of uuid references public.reports(id),
  add column sla_due_at timestamptz;

-- Audit immutabile
create table public.moderation_actions (
  id          uuid primary key default gen_random_uuid(),
  actor_id    uuid not null references public.profiles(id),
  action      text not null,          -- take, resolve, strike, ban, unban, role_change, appeal_decide
  target_type text not null,          -- report, post, comment, message, spot, profile
  target_id   uuid not null,
  reason      text not null,
  shift_code  text,                   -- A, B, C, D
  created_at  timestamptz not null default now()
);
create or replace function public.forbid_change() returns trigger
language plpgsql as $$ begin raise exception 'audit log is append-only'; end $$;
create trigger moderation_actions_immutable
  before update or delete on public.moderation_actions
  for each row execute function public.forbid_change();

-- Turni e assegnazioni
create table public.moderation_shifts (
  code text primary key,              -- 'A','B','C','D'
  starts_utc time not null, ends_utc time not null, label text not null
);
insert into public.moderation_shifts values
  ('A','00:00','06:00','Alba'), ('B','06:00','12:00','Ponte'),
  ('C','12:00','18:00','Meridiano'), ('D','18:00','24:00','Sera');

create table public.shift_assignments (
  id uuid primary key default gen_random_uuid(),
  shift_code text not null references public.moderation_shifts(code),
  day date not null,
  moderator_id uuid not null references public.profiles(id),
  kind text not null check (kind in ('primary','backup','lead')),
  unique (shift_code, day, kind, moderator_id)
);

create table public.shift_handoffs (
  id uuid primary key default gen_random_uuid(),
  shift_code text not null references public.moderation_shifts(code),
  day date not null,
  outgoing_id uuid not null references public.profiles(id),
  incoming_id uuid references public.profiles(id),
  note text not null,
  confirmed_at timestamptz,
  created_at timestamptz not null default now()
);
```

Le policy RLS per queste tabelle: lettura e scrittura solo per `moderator` e
`admin` (`public.is_moderator()`), con `actor_id = auth.uid()` in inserimento.
Guardia contro i contenuti sintetici: un trigger su `posts`, `comments`,
`ratings`, `reports`, `messages` rifiuta inserimenti quando
`auth.uid()` è nullo o `auth.role() = 'service_role'`.

### C · Macchina a stati di una segnalazione

```
open ──(Dot propone categoria/priorità; il moderatore conferma)──► triaged
triaged ──(presa in carico: assigned_to, taken_at)──► in_review
in_review ──► resolved{actioned | dismissed | duplicate}  (nota obbligatoria)
resolved ──(l'autore fa ricorso entro 14 gg)──► appealed
appealed ──(moderatore diverso decide)──► closed
resolved ──(14 gg senza ricorso)──► closed
```

Ogni transizione scrive una riga in `moderation_actions`. Il timer SLA parte
in `open` e si ferma in `resolved`.

### D · Nota di passaggio di consegne (template)

```
Turno: <A|B|C|D> · Data UTC: <aaaa-mm-gg> · Uscente: <nome> · Entrante: <nome>
Aperte: <n> (P0: <n>, P1: <n>) — le più vecchie: <id, motivo, da quanto>
In corso: <id → cosa manca per chiudere>
Da tenere d'occhio: <utente/discussione/spot e perché>
Eventi in arrivo nelle prossime 12 h: <evento, regione, organizzatore>
Note per il lead: <sì/no + testo>
Confermato dall'entrante alle <hh:mm UTC>
```

### E · Codice di condotta dei moderatori

1. Moderi con il tuo nome, non con un account condiviso.
2. Non scrivi mai contenuti a nome di membri o di account inesistenti.
3. Non usi i dati che vedi per scopi diversi dalla moderazione; non li copi
   fuori dalla console.
4. Ogni azione ha un motivo scritto che il membro potrebbe leggere.
5. Se un caso ti riguarda personalmente, lo passi a un altro moderatore.
6. Non prometti esiti; non discuti i casi in pubblico.
7. Rispetti i tempi del turno; se non puoi coprirlo, avvisi la riserva e il
   lead con almeno 4 ore di anticipo.

### F · Checklist di sicurezza per ogni rilascio

- [ ] Nessun segreto nel diff (gitleaks verde).
- [ ] Nuove tabelle: RLS attiva + policy + test permesso/negato.
- [ ] Nuove Edge Functions: controllo ruolo, limiti, validazione input, log
      senza PII.
- [ ] Nuovi campi personali: aggiunti a export/cancellazione account e alla
      tabella di conservazione (6.4).
- [ ] Nuove dipendenze: licenza compatibile, nessuna vulnerabilità nota.
- [ ] Intestazioni e CSP invariate o aggiornate di proposito.
- [ ] `docs/SECURITY_RLS.md` e `docs/SECURITY_RUNBOOK.md` aggiornati se serve.

### G · Decisioni aperte per l'admin (non bloccano la fase 0)

| Decisione | Opzioni | Raccomandazione |
| --- | --- | --- |
| Hosting con intestazioni di sicurezza | Cloudflare davanti a GitHub Pages con dominio proprio · Cloudflare Pages · restare su GitHub Pages con meta CSP | Cloudflare davanti a GitHub Pages (poco lavoro, WAF e Access inclusi) |
| Backup pubblico | Tenerlo senza `profiles` · renderlo privato | Tenerlo senza `profiles` (utile e trasparente) |
| Destino di FastAPI | Proxy routing e job · archiviare | Tenerlo solo se il routing PK self-hosted parte entro la fase 2 |
| Font dell'app Flutter | Passare a Karla/Fraunces · restare su Quicksand | Karla/Fraunces (un solo linguaggio con il sito) |
| Inviti a pagamento (5 €) | Mantenere con `invite-create` · sospendere fino al lancio | Mantenere, ma con firma lato server e registro nel DB |
| Età minima | 14 (Italia) · 16 (uniforme) | 14 con soglia locale dove richiesta |
