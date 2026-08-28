-- ============================================================================
-- PkFAMILY — un video, una riga
--
-- Serve a caricare il catalogo di `docs/TUTORIAL_CATALOG.md` (124 video) senza
-- che rilanciare lo script produca 124 righe in più.
-- ============================================================================

-- Prima di mettere il vincolo, togliamo eventuali doppioni già presenti,
-- tenendo la riga più vecchia: è quella a cui possono essere già collegati i
-- progressi di qualcuno (`video_progress`).
delete from public.videos a
using public.videos b
where a.url is not null
  and a.url = b.url
  and a.created_at > b.created_at;

-- `url` diventa la chiave naturale: è l'unica cosa che identifica davvero un
-- video, molto più del titolo (che l'autore può cambiare) o del nostro id.
-- Parziale, perché una tappa del percorso senza video ha `url` a null e più
-- tappe possono trovarsi in quello stato insieme.
create unique index if not exists videos_url_idx
  on public.videos (url)
  where url is not null;

comment on index public.videos_url_idx is
  'Chiave naturale per il caricamento del catalogo: scripts/seed_videos.mjs '
  'fa upsert su questa, così rilanciarlo aggiorna invece di duplicare.';

-- ----------------------------------------------------------------------------
-- Nota su `thumbnail_url`
-- ----------------------------------------------------------------------------
-- Resta vuota di proposito per i video di YouTube, e vale la pena scriverlo
-- qui perché è il genere di campo che qualcuno riempirà «per completezza».
--
-- Le anteprime stanno su `i.ytimg.com`. Riempire quella colonna significa che
-- l'app le scarica appena si apre la lista: una richiesta a Google prima che
-- l'utente tocchi qualcosa, mentre l'informativa dichiara che non ne parte
-- nessuna. La CSP la bloccherebbe comunque (`img-src` non include ytimg), e il
-- risultato sarebbe un riquadro rotto invece del segnaposto disegnato in
-- locale.
--
-- Se un giorno servissero delle anteprime: si scaricano una volta e si mettono
-- in Supabase Storage, servite dal nostro dominio.
