-- ============================================================================
-- PkFAMILY — moderazione, segnalazioni, obblighi DSA
--
-- BLOCCO 6.
--
-- ⚠️ Applicare dopo scripts/dump_schema.sh, e su staging prima.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Le segnalazioni sono leggibili da chiunque. Va chiuso subito.
-- ----------------------------------------------------------------------------
-- Verificato sulla produzione con la sola publishable key:
--
--   GET  /rest/v1/reports?select=*   → HTTP 200
--   POST /rest/v1/reports            → 42501, RLS rifiuta
--
-- Quindi la RLS è attiva, ma la policy di lettura è permissiva verso tutti. Con
-- la tabella vuota non è successo niente; al primo caso di molestie, però, la
-- segnalazione — chi l'ha fatta e cosa ha scritto — sarebbe leggibile da
-- chiunque abbia la chiave pubblica, **compresa la persona segnalata**.
--
-- Non è un problema teorico: se segnalare espone chi segnala, nessuno segnala,
-- e il meccanismo di notice-and-action che l'art. 16 DSA richiede diventa una
-- casella vuota.
--
-- Il rimedio è una policy RESTRICTIVE: si combina in AND con quelle esistenti,
-- che dall'esterno non si possono leggere e che non ha senso riscrivere alla
-- cieca. Anche se resta in piedi un `using (true)`, questa lo restringe.
drop policy if exists "una segnalazione la vedono solo chi l''ha fatta e i moderatori"
  on public.reports;
create policy "una segnalazione la vedono solo chi l''ha fatta e i moderatori"
  on public.reports as restrictive for select
  to anon, authenticated
  using (reporter_id = auth.uid() or public.is_admin());

comment on table public.reports is
  'Segnalazioni della community. Chi segnala vede le proprie, i moderatori '
  'tutte, nessun altro nessuna. Chi viene segnalato non sa chi l''ha fatto.';

-- ----------------------------------------------------------------------------
-- Stessa lettura aperta su due tabelle che non dovrebbero averla
-- ----------------------------------------------------------------------------
-- `post_saves` (user_id, post_id) dice cosa una persona ha salvato: sono i suoi
-- interessi, e non riguardano nessun altro. `entitlements` (user_id, active)
-- dice se ha un abbonamento — informazione che oggi non serve a niente, visto
-- che il servizio è gratuito, ma che resta esposta.
alter table public.post_saves enable row level security;
drop policy if exists "i salvataggi sono affari propri" on public.post_saves;
create policy "i salvataggi sono affari propri"
  on public.post_saves as restrictive for select
  to anon, authenticated
  using (user_id = auth.uid());

alter table public.entitlements enable row level security;
drop policy if exists "gli entitlement sono affari propri" on public.entitlements;
create policy "gli entitlement sono affari propri"
  on public.entitlements as restrictive for select
  to anon, authenticated
  using (user_id = auth.uid() or public.is_admin());

-- ----------------------------------------------------------------------------
-- Si può segnalare anche uno spot e una persona
-- ----------------------------------------------------------------------------
-- `spot_id` lo aggiunge la 0006. Manca il bersaglio «profilo»: senza, non c'è
-- modo di segnalare un utente molesto se non attraverso un suo messaggio, e su
-- una community con minori è la segnalazione che serve di più.
alter table public.reports
  add column if not exists profile_id uuid references public.profiles (id) on delete cascade;

-- Una segnalazione senza bersaglio non è una segnalazione.
alter table public.reports drop constraint if exists reports_needs_target;
alter table public.reports add constraint reports_needs_target
  check (
    num_nonnulls(spot_id, post_id, comment_id, message_id, profile_id) = 1
  );

-- Nessuno segnala sé stesso, e nessuno segnala a nome di un altro.
drop policy if exists "si segnala come sé stessi" on public.reports;
create policy "si segnala come sé stessi"
  on public.reports for insert
  to authenticated
  with check (reporter_id = auth.uid() and profile_id is distinct from auth.uid());

drop policy if exists "i moderatori trattano le segnalazioni" on public.reports;
create policy "i moderatori trattano le segnalazioni"
  on public.reports for update
  to authenticated
  using (public.is_admin())
  with check (public.is_admin());

-- ----------------------------------------------------------------------------
-- Il registro delle azioni di moderazione
-- ----------------------------------------------------------------------------
-- `spot_moderation_events` della migration 0001 **non esiste in produzione**
-- (404 sull'API): il registro non c'è mai stato. Questo lo crea per tutti i
-- tipi di contenuto, non solo per gli spot.
--
-- Serve a due cose diverse: sapere chi ha deciso cosa quando qualcuno contesta,
-- e accorgersi se un moderatore sta esagerando. Conservazione 12 mesi.
create table if not exists public.moderation_events (
  id           uuid primary key default gen_random_uuid(),
  actor_id     uuid not null references public.profiles (id) on delete cascade,
  target_kind  text not null check (target_kind in ('spot', 'message', 'comment', 'post', 'profile', 'contribution')),
  target_id    uuid not null,
  action       text not null check (action in ('verificato', 'rifiutato', 'rimosso', 'sospeso', 'riattivato', 'bannato', 'sbannato', 'ruolo')),
  reason       text,
  report_id    uuid references public.reports (id) on delete set null,
  created_at   timestamptz not null default now()
);

create index if not exists moderation_events_target_idx
  on public.moderation_events (target_kind, target_id, created_at desc);

alter table public.moderation_events enable row level security;

create policy "solo i moderatori leggono il registro"
  on public.moderation_events for select
  to authenticated
  using (public.is_admin());

create policy "il registro si scrive a proprio nome"
  on public.moderation_events for insert
  to authenticated
  with check (public.is_admin() and actor_id = auth.uid());

-- Nessun update, nessun delete: un registro modificabile non è un registro.

create or replace function public.purge_old_moderation_events()
returns integer
language sql
security definer
set search_path = public
as $$
  with gone as (
    delete from public.moderation_events
    where created_at < now() - interval '12 months'
    returning 1
  )
  select count(*)::int from gone;
$$;

revoke all on function public.purge_old_moderation_events() from public;

-- ----------------------------------------------------------------------------
-- La motivazione all'autore — art. 17 DSA
-- ----------------------------------------------------------------------------
-- Quando un contenuto viene rimosso o rifiutato, chi l'ha scritto ha diritto di
-- sapere perché. Non basta scriverlo nel registro interno: deve arrivargli.
--
-- `rejection_reason` su `spots` copriva solo gli spot. Questa tabella copre
-- tutto, e tiene traccia di quando l'autore l'ha letta.
create table if not exists public.moderation_notices (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles (id) on delete cascade,
  target_kind text not null,
  target_id   uuid,
  action      text not null,
  reason      text not null,
  created_at  timestamptz not null default now(),
  read_at     timestamptz
);

create index if not exists moderation_notices_user_idx
  on public.moderation_notices (user_id, created_at desc);

alter table public.moderation_notices enable row level security;

create policy "ognuno legge le motivazioni che lo riguardano"
  on public.moderation_notices for select
  to authenticated
  using (user_id = auth.uid());

create policy "si può segnare come letta la propria"
  on public.moderation_notices for update
  to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

revoke update on public.moderation_notices from authenticated;
grant update (read_at) on public.moderation_notices to authenticated;

create policy "i moderatori scrivono le motivazioni"
  on public.moderation_notices for insert
  to authenticated
  with check (public.is_admin());

-- ----------------------------------------------------------------------------
-- Sospensione, prima del ban
-- ----------------------------------------------------------------------------
-- `banned` esiste già ed è definitivo. Fra «non fare niente» e «fuori per
-- sempre» ci vuole qualcosa: la maggior parte dei casi è una brutta giornata,
-- non un molestatore seriale.
alter table public.profiles
  add column if not exists suspended_until   timestamptz,
  add column if not exists suspension_reason text;

create or replace function public.is_suspended()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(
    (select p.suspended_until > now() from public.profiles p where p.id = auth.uid()),
    false
  );
$$;

revoke all on function public.is_suspended() from public;
grant execute on function public.is_suspended() to authenticated;

-- Un sospeso legge ma non scrive. Vale sul database, non nell'interfaccia.
drop policy if exists "i sospesi non scrivono" on public.messages;
create policy "i sospesi non scrivono"
  on public.messages as restrictive for insert
  to authenticated
  with check (not public.is_suspended());

drop policy if exists "i sospesi non propongono spot" on public.spots;
create policy "i sospesi non propongono spot"
  on public.spots as restrictive for insert
  to authenticated
  with check (not public.is_suspended());

drop policy if exists "i sospesi non contribuiscono" on public.spot_contributions;
create policy "i sospesi non contribuiscono"
  on public.spot_contributions as restrictive for insert
  to authenticated
  with check (not public.is_suspended());

-- ----------------------------------------------------------------------------
-- Una decisione di moderazione, in un colpo solo
-- ----------------------------------------------------------------------------
-- Registro e motivazione all'autore devono andare insieme: una decisione
-- annotata ma non comunicata viola l'art. 17, e una comunicata ma non annotata
-- non è dimostrabile. Farlo in una funzione toglie la possibilità di
-- dimenticarne una.
create or replace function public.record_moderation(
  p_target_kind text,
  p_target_id   uuid,
  p_action      text,
  p_reason      text,
  p_author_id   uuid default null,
  p_report_id   uuid default null
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  event_id uuid;
begin
  if not public.is_admin() then
    raise exception 'Serve un account di moderazione.' using errcode = '42501';
  end if;

  if coalesce(trim(p_reason), '') = '' then
    raise exception 'La motivazione è obbligatoria (art. 17 DSA).'
      using errcode = '23514';
  end if;

  insert into public.moderation_events
    (actor_id, target_kind, target_id, action, reason, report_id)
  values (auth.uid(), p_target_kind, p_target_id, p_action, p_reason, p_report_id)
  returning id into event_id;

  -- Se si sa a chi appartiene il contenuto, la motivazione gli arriva.
  if p_author_id is not null then
    insert into public.moderation_notices
      (user_id, target_kind, target_id, action, reason)
    values (p_author_id, p_target_kind, p_target_id, p_action, p_reason);
  end if;

  if p_report_id is not null then
    update public.reports
    set status = 'accolta', resolution = p_reason,
        resolved_at = now(), resolved_by = auth.uid()
    where id = p_report_id;
  end if;

  return event_id;
end;
$$;

revoke all on function public.record_moderation(text, uuid, text, text, uuid, uuid) from public;
grant execute on function public.record_moderation(text, uuid, text, text, uuid, uuid) to authenticated;

-- ----------------------------------------------------------------------------
-- Verifica dopo l'applicazione
-- ----------------------------------------------------------------------------
--   -- da anonimo: nessuna di queste deve restituire righe altrui
--   GET /rest/v1/reports?select=*
--   GET /rest/v1/post_saves?select=*
--   GET /rest/v1/moderation_events?select=*
--
--   -- una decisione senza motivazione deve fallire
--   select record_moderation('spot', '<uuid>', 'rifiutato', '');
--
--   -- un utente sospeso non deve poter inserire in messages
