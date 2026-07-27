# PkFAMILY — Console Admin (PC)

Applicazione desktop per l'uso logistico dell'admin: moderazione spot,
gestione utenti, segnalazioni e backup, con pieno controllo sul database.

## Come si usa

1. Scarica [`index.html`](index.html) sul PC (tasto destro → Salva).
2. Aprilo con il browser (doppio click).
3. Al primo avvio inserisci la **secret key** di Supabase
   (Dashboard → Settings → API). Resta salvata solo in quel browser.

Nessuna installazione, nessun server: un solo file.

## Cosa può fare

- **Panoramica** — numeri live: spot per stato, utenti, post, segnalazioni, video.
- **Spot** — cerca/filtra; verifica, rifiuta (con motivo), modifica, elimina.
- **Utenti** — email + username; banna/sbanna, promuovi/rimuovi admin,
  reset password (generata e mostrata una sola volta).
- **Segnalazioni** — coda dei report della community.
- **Backup** — scarica il backup completo in JSON con un click
  (vedi [📲/README.md](../📲/README.md) per il piano completo).

## Sicurezza

La console usa la **secret key**, che bypassa ogni protezione RLS: è lo
strumento dell'amministratore, non va distribuita né pubblicata online.
Solo il PC dell'admin. Se la chiave finisce in mani sbagliate: Dashboard
Supabase → Settings → API → rigenera la secret key.
