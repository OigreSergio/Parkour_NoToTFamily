# 📲 Backup & Recovery — PkFAMILY

Il progetto è un'idea di business oltre che una passione: i dati (spot, utenti,
community) sono l'asset. Questa cartella contiene il piano per non perderli mai.

## Collegamento diretto al backup

- **Ultimo backup (visualizza):**
  https://github.com/OigreSergio/Parkour_NoToTFamily/blob/backup/%F0%9F%93%B2/backup-quotidiano.json
- **Ultimo backup (download diretto):**
  https://raw.githubusercontent.com/OigreSergio/Parkour_NoToTFamily/backup/%F0%9F%93%B2/backup-quotidiano.json

Il file vive sulla branch `backup`, che **ogni 24 ore si distrugge e si
rigenera** (workflow `backup-quotidiano.yml`, ore 03:17 UTC): la branch viene
ricreata da zero a ogni giro, quindi contiene sempre e solo il backup più
recente. I link sopra non cambiano mai.

## Cosa viene salvato

| Copia | Contenuto | Dove | Frequenza |
| ----- | --------- | ---- | --------- |
| 1. Database primario | tutto | Supabase (progetto PkFAMILY) | live |
| 2. Backup pubblico | **solo contenuti della community**: spot, foto, fontanelle, video. Nessuna tabella con dati personali. | branch `backup` di questo repo (pubblico) | ogni 24 h, automatico |
| 3. Backup completo | tutto, inclusi utenti auth (email) | **solo sul PC dell'admin** — mai nel repo | manuale, consigliato 1×/settimana |

Comandi:

```sh
node "📲/backup.mjs"                                   # backup pubblico
SUPABASE_SECRET_KEY=sb_secret_... node "📲/backup.mjs"  # backup completo (resta locale)
```

Il backup completo (`backup-completo.json`) è nel `.gitignore`: **non
committarlo e non condividerlo** — contiene dati personali degli utenti
(GDPR). La console admin (`admin-desktop/`) ha un pulsante che scarica lo
stesso backup completo con un click.

## Piano di recovery

Obiettivi: **RPO 24 h** (al massimo si perde l'ultimo giorno), **RTO ~1 h**
(tempo per tornare online).

### Scenario A — righe cancellate o modificate per errore
1. Apri il backup più recente (link diretto sopra, o il completo locale).
2. Reinserisci le righe con la console admin oppure via REST:
   `curl -X POST "$SUPABASE_URL/rest/v1/<tabella>" -H "apikey: $SECRET" -H "Authorization: Bearer $SECRET" -H "Prefer: resolution=merge-duplicates" -d @righe.json`
3. Verifica nell'app che i dati siano tornati.

### Scenario B — progetto Supabase perso o compromesso
1. Crea un nuovo progetto su supabase.com.
2. Ricrea lo schema (SQL Editor). Lo schema di produzione va esportato oggi
   stesso in `supabase/migrations/` (vedi TODO sotto).
3. Reimporta le tabelle dal backup completo locale (ordine: profiles → spots →
   il resto), poi ricrea gli utenti auth con l'Admin API (le password non sono
   nei backup: gli utenti faranno "password dimenticata").
4. Aggiorna URL e publishable key nell'app e nella console admin.

### Scenario C — app web rotta dopo un aggiornamento
La branch `gh-pages` è versionata: `git revert` (o reset alla build precedente)
e push → il sito torna com'era in pochi minuti. I dati non sono toccati.

## Regole di sicurezza

- La **secret key** non entra mai nel repo, nelle chat pubbliche o nell'app:
  vive solo sul PC dell'admin (console) e nei secret di GitHub se serviranno.
- Se una chiave viene esposta: Dashboard Supabase → Settings → API → rigenera.
- Il backup pubblico finisce su un branch pubblico di un repo pubblico, con
  storia git permanente: **ciò che entra lì è diffuso a destinatari
  indeterminati, per sempre.** La leggibilità via RLS non è il criterio giusto —
  `profiles` è leggibile da chiunque nell'app, ma pubblicarla in un file su
  GitHub è un'altra cosa. L'elenco delle tabelle ammesse è esplicito in
  `backup.mjs` (`TABLES_PUBBLICHE`), con un controllo che fa fallire lo script se
  ci finisce una tabella con dati personali.

## TODO
- [ ] Esportare lo schema di produzione in `supabase/migrations/` (serve per lo scenario B).
- [ ] Quando gli utenti crescono: valutare il piano Supabase Pro (backup PITR gestiti).
