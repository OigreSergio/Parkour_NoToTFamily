# Accademia — architettura tutorial & video

Modulo di apprendimento di PkFAMILY, ispirato al concept di **Ultimate Parkour
App** (App Store, id1018993970): un hub centrale che collega tutorial scritti +
video, un trick database ricercabile, obiettivi personali con scadenza,
tracking dei progressi e badge collezionabili.

## Mappa del concept

| Ultimate Parkour App | PkFAMILY Accademia | Stato |
| -------------------- | ------------------ | ----- |
| 60+ tutorial scritti e video | 26 trick con tutorial passo-passo in italiano; slot video per i contenuti PkFAMILY | ✅ v1 (`accademia/index.html`) |
| Trick database ricercabile, aggiornato automaticamente | Ricerca per nome/descrizione + filtri categoria/livello | ✅ v1 (dati inline) → v2 da Supabase |
| Goal setting + promemoria | Obiettivo per trick con scadenza e countdown | ✅ v1 (senza notifiche push) |
| Progress tracking per trick | Stati: da imparare → in allenamento → landed, con barre per livello | ✅ v1 |
| 30+ achievement | 12 badge con sblocco automatico e toast | ✅ v1 |
| Suggestions generator | "Suggeriscimi un trick": propone solo trick con prerequisiti landati | ✅ v1 |
| News feed social | Già coperto dal resto di PkFAMILY (post/commenti su Supabase) | — |

Aggiunta nostra, assente nell'app originale: ogni trick dichiara i suoi
**prerequisiti** e la scheda avvisa se non sono ancora landati — la
progressione è il messaggio di sicurezza del progetto ("Landa sicuro").

## v1 — com'è fatta

- **Un solo file**: `accademia/index.html`, zero dipendenze, mobile-first,
  tema chiaro/scuro automatico, palette coerente con la pagina `/stato/`.
- **Navigazione**: hub + tab bar (Home · Tutorial · Trick · Obiettivi ·
  Badge), routing via hash così il tasto "indietro" del telefono funziona.
- **Persistenza**: `localStorage` (chiave `pkfamily_accademia_v1`) — i
  progressi restano sul dispositivo, nessun account richiesto.
- **Video**: campo `video` per ogni trick (URL embed). Finché è `null` la
  scheda mostra un placeholder con ricerca YouTube; quando i video PkFAMILY
  saranno pronti basta valorizzare il campo.

## v2 — collegamento a Supabase

Le tabelle esistono già nel progetto PkFAMILY (vedi backup `📲/`):

- `videos` → sorgente del campo `video` dei trick e dei tutorial extra
  caricati dalla community (moderati come gli spot: pending → verified).
- `video_progress` → sostituisce `localStorage` per gli utenti loggati
  (merge al primo login: il locale vince se più avanzato).
- Da creare: `trick_goals` (user_id, trick_id, due_date) e
  `user_badges` (user_id, badge_id, unlocked_at), con RLS per-utente come
  le tabelle esistenti.

I trick stessi possono migrare in una tabella `tricks` (id, nome, categoria,
livello, prerequisiti, steps jsonb, video_url) così il database "si aggiorna
da solo" come nell'app originale, senza rideploy.

## Deploy

La v1 è statica: si pubblica copiando `accademia/` nella branch `gh-pages`
(diventa `…/Parkour_NoToTFamily/accademia/`). Per il test immediato da
telefono si può servire direttamente dalla branch di sviluppo via
raw.githack (vedi `accademia/README.md`).
