-- ============================================================================
-- PkFAMILY — account, gate di sicurezza, accesso tramite genitore
--
-- BLOCCO 2 del piano di lancio (docs/LAUNCH_PROMPT.md).
--
-- ⚠️ PRIMA DI APPLICARLA: esegui scripts/dump_schema.sh e prova su staging.
-- Le policy attuali di `spots` non sono ispezionabili dall'esterno, e qui se
-- ne aggiunge una. È il motivo per cui la policy nuova è **RESTRICTIVE**: si
-- combina in AND con quelle esistenti senza doverle conoscere né riscrivere.
-- Una permissive avrebbe potuto allargare l'accesso invece di restringerlo.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- profiles — età, supervisione, chat, cancellazione
-- ----------------------------------------------------------------------------
alter table public.profiles
  add column if not exists age_confirmed_at        timestamptz,
  add column if not exists supervised              boolean not null default false,
  add column if not exists supervisor_confirmed_at timestamptz,
  add column if not exists chat_enabled            boolean not null default true,
  add column if not exists deletion_requested_at   timestamptz;

comment on column public.profiles.supervised is
  'Account aperto da un adulto per un minore sotto i 16 anni che lo usa sotto '
  'la sua supervisione. Il titolare dell''account è l''adulto: non esiste un '
  'account del minore, quindi non si tratta nessuna email di minore e non '
  'scatta l''art. 8 GDPR.';

comment on column public.profiles.chat_enabled is
  'Sugli account supervisionati nasce false: il rischio più serio in una '
  'community aperta è il contatto adulto-minore. Il genitore può attivarla. '
  'Il vincolo è applicato nelle policy di messages/chat_members, non solo in UI.';

comment on column public.profiles.deletion_requested_at is
  'Inizio dei 30 giorni di grazia prima della cancellazione definitiva '
  '(art. 17 GDPR). Alla scadenza i messaggi vengono pseudonimizzati, non '
  'rimossi dalle conversazioni altrui.';

-- Un account supervisionato deve avere una conferma dell'adulto: senza, è solo
-- un flag messo a caso.
alter table public.profiles
  drop constraint if exists profiles_supervised_needs_confirmation;
alter table public.profiles
  add constraint profiles_supervised_needs_confirmation
  check (not supervised or supervisor_confirmed_at is not null);

-- L'utente può cambiare solo ciò che è suo, e mai il proprio ruolo.
grant update (username, avatar_url, chat_enabled, deletion_requested_at)
  on public.profiles to authenticated;

-- ----------------------------------------------------------------------------
-- Il testo del gate di sicurezza, versionato
-- ----------------------------------------------------------------------------
-- La versione corrente vive qui, in una sola funzione. Quando il testo cambia:
-- nuova migration che la ridefinisce, e il gate ricompare a tutti.
--
-- Deve restare allineata a `mobile/assets/legal/safety_notice_<versione>.md` e
-- alla costante nel client. Il test `safety_notice_test.dart` verifica che
-- l'hash del file corrisponda a quello che il client dichiara.
create or replace function public.current_safety_notice_version()
returns text
language sql
immutable
as $$ select 'v1'::text $$;

-- ----------------------------------------------------------------------------
-- safety_acknowledgements — la presa d'atto, registrata
-- ----------------------------------------------------------------------------
-- Senza registrazione il gate in giudizio vale zero: serve poter dimostrare
-- *quale testo esatto* è stato mostrato e *quando*. Da qui version + hash.
create table if not exists public.safety_acknowledgements (
  user_id     uuid not null references auth.users (id) on delete cascade,
  version     text not null,
  text_sha256 text not null,
  accepted_at timestamptz not null default now(),
  revoked_at  timestamptz,
  primary key (user_id, version)
);

comment on table public.safety_acknowledgements is
  'Presa d''atto del carattere informativo della mappa e assunzione del '
  'rischio. NON è un esonero di responsabilità: verso un consumatore una '
  'clausola che limita la responsabilità per danni alla persona è nulla '
  '(artt. 33 e 36 Cod. Consumo; art. 1229 c.c. per dolo e colpa grave).';

comment on column public.safety_acknowledgements.revoked_at is
  'Revoca. La riga resta: cancellarla distruggerebbe la prova che a suo tempo '
  'il testo era stato accettato.';

alter table public.safety_acknowledgements enable row level security;

create policy "ognuno legge le proprie prese d''atto"
  on public.safety_acknowledgements for select
  to authenticated
  using (user_id = auth.uid());

create policy "ognuno registra la propria presa d''atto"
  on public.safety_acknowledgements for insert
  to authenticated
  with check (user_id = auth.uid());

-- L'update serve solo per revocare o riaccettare. Il testo e l'hash non si
-- toccano: sono il contenuto della prova.
create policy "ognuno revoca o riaccetta la propria"
  on public.safety_acknowledgements for update
  to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

revoke update on public.safety_acknowledgements from authenticated;
grant update (revoked_at) on public.safety_acknowledgements to authenticated;

-- ----------------------------------------------------------------------------
-- Il controllo, isolato dalla RLS
-- ----------------------------------------------------------------------------
create or replace function public.has_accepted_safety_notice()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.safety_acknowledgements a
    where a.user_id = auth.uid()
      and a.version = public.current_safety_notice_version()
      and a.revoked_at is null
  );
$$;

revoke all on function public.has_accepted_safety_notice() from public;
grant execute on function public.has_accepted_safety_notice() to authenticated;

-- ----------------------------------------------------------------------------
-- Niente spot senza presa d'atto
-- ----------------------------------------------------------------------------
-- RESTRICTIVE: si combina in AND con le policy esistenti su `spots`, che
-- restano intatte. Chi rifiuta il gate vede la mappa vuota **anche
-- interrogando l'API a mano** — un rifiuto aggirabile disattivando JavaScript
-- non sarebbe un rifiuto.
--
-- L'autore vede sempre i propri spot (deve poter seguire una proposta in
-- attesa) e l'admin sempre tutto (altrimenti la moderazione si autobloccherebbe).
--
-- Nota: perché questo valga anche per chi non ha un account, il client apre una
-- sessione anonima (Supabase Auth → Anonymous sign-ins, da abilitare nella
-- dashboard). Senza quella, un visitatore non autenticato non ha `auth.uid()`
-- e questa policy gli nega gli spot in blocco.
drop policy if exists "spot solo dopo la presa d'atto" on public.spots;
create policy "spot solo dopo la presa d'atto"
  on public.spots as restrictive for select
  to authenticated
  using (
    public.has_accepted_safety_notice()
    or author_id = auth.uid()
    or public.is_admin()
  );

-- ----------------------------------------------------------------------------
-- La chat non è per gli account supervisionati, salvo scelta del genitore
-- ----------------------------------------------------------------------------
create or replace function public.can_use_chat()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(
    (select p.chat_enabled and not coalesce(p.banned, false)
       from public.profiles p where p.id = auth.uid()),
    false
  );
$$;

revoke all on function public.can_use_chat() from public;
grant execute on function public.can_use_chat() to authenticated;

drop policy if exists "chat disattivabile per account supervisionati" on public.messages;
create policy "chat disattivabile per account supervisionati"
  on public.messages as restrictive for insert
  to authenticated
  with check (public.can_use_chat());

drop policy if exists "chat disattivabile per account supervisionati" on public.chat_members;
create policy "chat disattivabile per account supervisionati"
  on public.chat_members as restrictive for insert
  to authenticated
  with check (public.can_use_chat());

-- ----------------------------------------------------------------------------
-- parent_access_requests — la richiesta del minore a un adulto
-- ----------------------------------------------------------------------------
-- Contiene l'email di un terzo, fornita da un minore. Perciò: nessuna policy,
-- quindi **nessun accesso dal client**. Si scrive e si legge solo da una Edge
-- Function con la secret key, che invia una sola email e applica il rate limit.
-- Le richieste non completate si cancellano dopo 7 giorni: non si tiene a bagno
-- un archivio di contatti di terzi.
create table if not exists public.parent_access_requests (
  id           uuid primary key default gen_random_uuid(),
  parent_email text not null,
  token_hash   text not null unique,
  created_at   timestamptz not null default now(),
  expires_at   timestamptz not null default now() + interval '7 days',
  completed_at timestamptz
);

create index if not exists parent_access_requests_expires_idx
  on public.parent_access_requests (expires_at);

alter table public.parent_access_requests enable row level security;
-- Nessuna policy: RLS attiva senza policy nega tutto ai ruoli anon e
-- authenticated. È voluto.

create or replace function public.purge_expired_parent_requests()
returns integer
language sql
security definer
set search_path = public
as $$
  with gone as (
    delete from public.parent_access_requests
    where completed_at is null and expires_at < now()
    returning 1
  )
  select count(*)::int from gone;
$$;

revoke all on function public.purge_expired_parent_requests() from public;

comment on function public.purge_expired_parent_requests() is
  'Da schedulare (pg_cron, giornaliero). Se non gira, le email dei genitori '
  'restano in tabella oltre i 7 giorni dichiarati nell''informativa.';

-- ----------------------------------------------------------------------------
-- Verifica dopo l'applicazione
-- ----------------------------------------------------------------------------
-- Automatizzata in scripts/audit_rls.mjs. A mano, da client autenticato:
--
--   select public.has_accepted_safety_notice();   -- false prima di accettare
--   select * from spots limit 1;                   -- 0 righe finché è false
--   insert into safety_acknowledgements(user_id, version, text_sha256)
--     values (auth.uid(), 'v1', '<hash>');
--   select * from spots limit 1;                   -- ora si vedono
--
--   select * from parent_access_requests;          -- deve tornare 0 righe sempre
