-- ============================================================================
-- PkFAMILY — rendere utilizzabili gli spot fuori Roma
--
-- BLOCCO 3-bis. Chiude le lacune di schema che impediscono di pubblicare uno
-- spot in modo onesto, tutte verificate sondando la produzione dall'esterno.
--
-- ⚠️ Applicare dopo scripts/dump_schema.sh, e su staging prima.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Quello che non si sa deve poter essere `null`
-- ----------------------------------------------------------------------------
-- Prima della pulizia, tutti e 1.680 gli spot importati portavano
-- `skill_level = 'intermedio'`, `crowd_level = 'medio'`, `has_fountain = false`.
-- Non erano valutazioni: erano lo stesso default ripetuto, mostrato all'utente
-- come se qualcuno ci fosse stato. Perché "non lo sappiamo" sia rappresentabile
-- le colonne devono ammettere null.
alter table public.spots alter column skill_level  drop not null;
alter table public.spots alter column crowd_level  drop not null;
alter table public.spots alter column has_fountain drop not null;

comment on column public.spots.skill_level is
  'principiante | intermedio | avanzato, oppure NULL = nessuno l''ha valutato. '
  'NULL non è un buco da riempire con un default: è l''unica risposta onesta '
  'finché qualcuno non ci va.';

comment on column public.spots.has_fountain is
  'NULL = non lo sappiamo. Diverso da false, che significa "abbiamo guardato e '
  'non c''è". La differenza conta per chi parte con una borraccia mezza vuota.';

-- ----------------------------------------------------------------------------
-- Località e paese, campi veri
-- ----------------------------------------------------------------------------
-- Erano sepolti nella descrizione («Bologna, Italia. Dalla lista community…»),
-- che è anche l'unico posto in cui la si poteva leggere. Estratti da
-- clean_spots.py, servono al cruscotto di copertura e ai filtri.
alter table public.spots
  add column if not exists locality text,
  add column if not exists country  text;

create index if not exists spots_country_idx on public.spots (country);

-- ----------------------------------------------------------------------------
-- Stato di completezza
-- ----------------------------------------------------------------------------
alter table public.spots
  add column if not exists completeness text not null default 'da_completare';

alter table public.spots drop constraint if exists spots_completeness_check;
alter table public.spots add constraint spots_completeness_check
  check (completeness in ('da_completare', 'arricchito', 'verificato'));

comment on column public.spots.completeness is
  'da_completare = solo coordinate e nome; arricchito = toponimo reale, '
  'contesto OSM e almeno una foto con licenza; verificato = una persona c''è '
  'stata e l''ha descritto. Serve a distinguere sulla mappa gli spot raccontati '
  'dai segnaposto, invece di farli sembrare la stessa cosa.';

create index if not exists spots_completeness_idx on public.spots (completeness);

-- ----------------------------------------------------------------------------
-- Provenienza delle foto
-- ----------------------------------------------------------------------------
-- `spot_photos` aveva solo (id, spot_id, url, position). Mancava tutto ciò che
-- serve per pubblicare legalmente una foto: Mapillary è CC-BY-SA 4.0 e
-- Wikimedia Commons richiede l'attribuzione. Senza questi campi le uniche foto
-- pubblicabili sarebbero quelle caricate dagli utenti.
alter table public.spot_photos
  add column if not exists source     text,
  add column if not exists author     text,
  add column if not exists license    text,
  add column if not exists source_url text,
  add column if not exists created_at timestamptz not null default now();

alter table public.spot_photos drop constraint if exists spot_photos_source_check;
alter table public.spot_photos add constraint spot_photos_source_check
  check (source is null or source in ('mapillary', 'wikimedia', 'community'));

-- Una foto di terzi senza licenza nota non va pubblicata. Il vincolo lo rende
-- impossibile invece di lasciarlo alla disciplina di chi scrive il codice.
alter table public.spot_photos drop constraint if exists spot_photos_credit_required;
alter table public.spot_photos add constraint spot_photos_credit_required
  check (source is null or source = 'community' or (author is not null and license is not null));

-- ----------------------------------------------------------------------------
-- Il percorso "Inizia da qui"
-- ----------------------------------------------------------------------------
alter table public.videos
  add column if not exists is_starter  boolean not null default false,
  add column if not exists order_index integer;

create index if not exists videos_starter_idx on public.videos (is_starter, order_index);

-- ----------------------------------------------------------------------------
-- Segnalazioni: due lacune che bloccano gli obblighi DSA
-- ----------------------------------------------------------------------------
-- `reports` aveva (id, reporter_id, post_id, comment_id, message_id, reason,
-- created_at). Mancava `spot_id`, quindi **uno spot pericoloso non era
-- segnalabile** — su una mappa di luoghi fisici è la segnalazione che conta di
-- più. E mancava qualunque stato, quindi non c'era modo di sapere se una
-- segnalazione fosse stata trattata, né di documentarlo.
alter table public.reports
  add column if not exists spot_id     uuid references public.spots (id) on delete cascade,
  add column if not exists status      text not null default 'aperta',
  add column if not exists resolution  text,
  add column if not exists resolved_at timestamptz,
  add column if not exists resolved_by uuid references public.profiles (id) on delete set null;

alter table public.reports drop constraint if exists reports_status_check;
alter table public.reports add constraint reports_status_check
  check (status in ('aperta', 'in_esame', 'accolta', 'respinta'));

create index if not exists reports_status_idx on public.reports (status, created_at);

comment on column public.reports.resolution is
  'Motivazione della decisione, da comunicare a chi ha segnalato e all''autore '
  'del contenuto: art. 17 DSA (statement of reasons).';

-- ----------------------------------------------------------------------------
-- Contributi della community su uno spot
-- ----------------------------------------------------------------------------
-- Livello, affollamento e "cosa ci si allena" non esistono in nessuna API:
-- l'unica fonte è chi c'è stato. Questa tabella raccoglie le proposte, che
-- passano dalla moderazione come una proposta di spot.
create table if not exists public.spot_contributions (
  id           uuid primary key default gen_random_uuid(),
  spot_id      uuid not null references public.spots (id) on delete cascade,
  author_id    uuid not null references public.profiles (id) on delete cascade,
  description  text,
  skill_level  text,
  crowd_level  text,
  has_fountain boolean,
  status       text not null default 'pending'
                 check (status in ('pending', 'accepted', 'rejected')),
  review_note  text,
  created_at   timestamptz not null default now(),
  reviewed_at  timestamptz,
  reviewed_by  uuid references public.profiles (id) on delete set null
);

create index if not exists spot_contributions_spot_idx
  on public.spot_contributions (spot_id, status);

alter table public.spot_contributions enable row level security;

create policy "ognuno vede i propri contributi, gli admin tutti"
  on public.spot_contributions for select
  to authenticated
  using (author_id = auth.uid() or public.is_admin());

create policy "gli utenti contribuiscono come sé stessi"
  on public.spot_contributions for insert
  to authenticated
  with check (author_id = auth.uid() and status = 'pending');

create policy "gli admin moderano i contributi"
  on public.spot_contributions for update
  to authenticated
  using (public.is_admin())
  with check (public.is_admin());

-- ----------------------------------------------------------------------------
-- Verifica dopo l'applicazione
-- ----------------------------------------------------------------------------
--   select completeness, count(*) from spots group by 1;
--     → nessuno spot 'arricchito' o 'verificato' senza qualcosa da mostrare
--   select count(*) from spots where skill_level is null;
--     → deve essere alto: è il numero di spot che nessuno ha ancora valutato
--   insert into spot_photos(spot_id, url, source) values (…, …, 'mapillary');
--     → deve FALLIRE: manca il credito
