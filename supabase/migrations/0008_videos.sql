-- ============================================================================
-- PkFAMILY — video: gratuiti per tutti, e il percorso "Inizia da qui"
--
-- BLOCCO 5. `is_starter` e `order_index` li ha già aggiunti la 0006.
--
-- ⚠️ Applicare dopo scripts/dump_schema.sh, e su staging prima.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Il gating premium sparisce, non si nasconde
-- ----------------------------------------------------------------------------
-- Il vecchio bundle forzava `hasVideo = true` nel JavaScript, ma le policy del
-- database continuavano a rifiutare: l'utente vedeva un'interfaccia sbloccata e
-- riceveva errori silenziosi. Con il servizio gratuito il paywall va tolto dove
-- è davvero applicato, cioè qui.
--
-- I nomi elencati sotto sono quelli plausibili di policy che l'esterno non
-- permette di leggere: `drop policy if exists` è innocuo su quelle inesistenti.
-- Dopo il dump dello schema, verifica che non ne resti qualcuna con un altro
-- nome — è il tipo di residuo che si scopre solo quando un utente si lamenta.
drop policy if exists "premium videos require a subscription" on public.videos;
drop policy if exists "subscribers watch premium videos"      on public.videos;
drop policy if exists "entitlements gate videos"              on public.videos;

drop policy if exists "i video sono di tutti" on public.videos;
create policy "i video sono di tutti"
  on public.videos for select
  using (true);

comment on table public.videos is
  'Catalogo dei video. Leggibile da chiunque, anche senza account e senza aver '
  'accettato il gate di sicurezza: per chi inizia è la porta d''ingresso, e '
  'guardare un video non comporta nessun rischio da segnalare.';

-- ----------------------------------------------------------------------------
-- Quello che serve al percorso per chi inizia
-- ----------------------------------------------------------------------------
alter table public.videos
  add column if not exists description  text,
  add column if not exists safety_note  text,
  add column if not exists author       text,
  add column if not exists source       text not null default 'youtube',
  add column if not exists stage        text;

comment on column public.videos.safety_note is
  'La riga di sicurezza specifica di questa tappa. Non è la stessa per tutti: '
  'quello che serve sapere prima di una rullata non è quello che serve prima '
  'di un salto di precisione.';

comment on column public.videos.author is
  'Chi ha fatto il video. Verificato via oEmbed al momento del seed, non '
  'trascritto a mano: attribuire un video alla persona sbagliata è peggio che '
  'non attribuirlo.';

comment on column public.videos.stage is
  'La tappa del percorso "Inizia da qui" (riscaldamento, atterraggio, …). '
  'NULL per i video che non ne fanno parte.';

-- Una tappa del percorso deve avere una posizione: senza, l'ordine dipende
-- dall'ordine di inserimento, che non è un ordine didattico.
alter table public.videos drop constraint if exists videos_starter_needs_order;
alter table public.videos add constraint videos_starter_needs_order
  check (not is_starter or order_index is not null);

create unique index if not exists videos_starter_stage_idx
  on public.videos (stage) where is_starter;

-- ----------------------------------------------------------------------------
-- La scrittura resta agli admin
-- ----------------------------------------------------------------------------
drop policy if exists "solo gli admin curano il catalogo" on public.videos;
create policy "solo gli admin curano il catalogo"
  on public.videos for all
  to authenticated
  using (public.is_admin())
  with check (public.is_admin());

-- ----------------------------------------------------------------------------
-- Verifica dopo l'applicazione
-- ----------------------------------------------------------------------------
--   -- da anonimo, senza presa d'atto del gate: i video si devono vedere
--   select count(*) from videos;
--   -- nessun video "starter" senza posizione
--   select count(*) from videos where is_starter and order_index is null;  -- 0
