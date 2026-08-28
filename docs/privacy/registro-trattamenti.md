# Registro dei trattamenti (art. 30 GDPR)

**Documento interno. Non pubblicare.**

Ultimo aggiornamento: 27 agosto 2026

> ⚠️ **L'esenzione per chi ha meno di 250 dipendenti non si applica.** Vale solo
> per trattamenti occasionali, senza categorie particolari e senza rischi per gli
> interessati: qui il trattamento è continuativo, include geolocalizzazione e
> riguarda anche minori dai 16 anni. Il registro va tenuto e aggiornato.

## Titolare

Persona fisica (vedi `mobile/assets/legal/note-legali.md`). Nessun DPO: a questa
scala non è obbligatorio.

## I trattamenti

| # | Trattamento | Interessati | Dati | Base giuridica | Conservazione |
|---|---|---|---|---|---|
| 1 | Sessione anonima | Visitatori | Identificativo casuale in `auth.users` | 6.1.f — dimostrare di aver informato prima di mostrare gli spot | Fino alla cancellazione dei dati del browser |
| 2 | Account | Iscritti | Email, password (hash), nome scelto, data di conferma età | 6.1.b | Fino a cancellazione + 30 gg |
| 3 | Presa d'atto avviso sicurezza | Visitatori e iscritti | `user_id`, versione, hash del testo, timestamp | 6.1.f — prova dell'informazione data | Quanto l'account |
| 4 | Contenuti (spot, contributi, commenti) | Iscritti | Testo, coordinate, foto, autore | 6.1.b + 6.1.f | Spot verificati: indefinita, con attribuzione rimovibile |
| 5 | Chat | Iscritti | Messaggi, partecipanti, timestamp | 6.1.b | Fino a cancellazione; autore azzerato alla chiusura account |
| 6 | Geolocalizzazione | Chi tocca «dove sono» | Posizione precisa, **solo sul dispositivo** | 6.1.a | **Nessuna** |
| 7 | Segnalazioni | Chi segnala e chi è segnalato | Bersaglio, motivo, esito | 6.1.c (artt. 16-17 DSA) + 6.1.f | 12 mesi |
| 8 | Registro di moderazione | Iscritti moderati | Azione, motivazione, chi ha deciso | 6.1.c + 6.1.f | 12 mesi |
| 9 | Accesso genitoriale | Adulto indicato da un minore | Email dell'adulto, token | 6.1.f — dare una strada corretta a chi è sotto soglia | 7 giorni se non completata |
| 10 | Log tecnici e antiabuso | Tutti | IP, user agent, timestamp | 6.1.f (vedi LIA) | ~30 gg, secondo il fornitore |
| 11 | Backup | Tutti | Contenuti della community (no dati personali) | 6.1.f | Rotazione |

## Categorie particolari (art. 9)

**Nessuna, e va tenuto così.** Attenzione a due punti in cui potrebbero entrare
dalla finestra:

- le **foto** caricate dagli utenti possono rivelare dati sulla salute o
  l'appartenenza a un gruppo — i Termini vietano di caricare volti di terzi
  senza consenso;
- i **messaggi in chat** possono contenere di tutto. Non li analizziamo e non li
  indicizziamo: restano contenuti dell'utente.

## Destinatari

Supabase (Francoforte, UE — Supabase Inc. US, DPA + SCC), Cloudflare (rete UE),
GitHub (solo codice e automazioni, nessun dato utente).

## Trasferimenti extra-UE

I dati sono ospitati nel SEE. Il rischio residuo è l'**accesso** del personale
statunitense di Supabase per assistenza, coperto da DPA e clausole contrattuali
standard.

## Misure di sicurezza (art. 32)

Row Level Security su ogni tabella, verificata da `scripts/audit_rls.mjs` in CI.
Publishable key nel client (pubblica per costruzione), secret key mai in un
client. Password con lunghezza minima e controllo contro liste compromesse.
Rate limit sui messaggi imposto dal database. HTTPS obbligatorio, CSP restrittiva.

## Da aggiornare quando

Si aggiunge un fornitore, una finalità, o un tipo di dato. Un registro che
descrive il sistema di sei mesi fa non serve a niente.
