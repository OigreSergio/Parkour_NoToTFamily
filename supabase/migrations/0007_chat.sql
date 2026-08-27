-- ============================================================================
-- PkFAMILY — chat: limiti, blocco, cancellazione
--
-- BLOCCO 4. Presuppone la 0004, che sblocca le tabelle dalla ricorsione nelle
-- policy (oggi rispondono HTTP 500).
--
-- Colonne reali, confermate sondando la produzione:
--   chats         (id, created_by, created_at, name, is_group)
--   chat_members  (chat_id, user_id, joined_at)
--   messages      (id, chat_id, body, created_at, sender_id)
--   blocked_users (blocker_id, blocked_id, created_at)
--
-- ⚠️ Applicare dopo scripts/dump_schema.sh, e su staging prima.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Il blocco fra utenti
-- ----------------------------------------------------------------------------
alter table public.blocked_users enable row level security;

drop policy if exists "ognuno vede e gestisce i propri blocchi" on public.blocked_users;
create policy "ognuno vede e gestisce i propri blocchi"
  on public.blocked_users for all
  to authenticated
  using (blocker_id = auth.uid())
  with check (blocker_id = auth.uid());

comment on table public.blocked_users is
  'Chi ha bloccato chi. La lista di un utente è visibile solo a lui: sapere di '
  'essere stati bloccati è un''informazione che non spetta a chi blocca dare.';

-- Uno dei due ha bloccato l'altro?
create or replace function public.is_blocked_between(a uuid, b uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.blocked_users
    where (blocker_id = a and blocked_id = b)
       or (blocker_id = b and blocked_id = a)
  );
$$;

revoke all on function public.is_blocked_between(uuid, uuid) from public;
grant execute on function public.is_blocked_between(uuid, uuid) to authenticated;

-- ----------------------------------------------------------------------------
-- Il blocco vale davvero, non solo nell'interfaccia
-- ----------------------------------------------------------------------------
-- In una conversazione a due, se uno dei due ha bloccato l'altro nessuno dei
-- due scrive più. Nasconderlo solo lato client lascerebbe passare i messaggi
-- via API: un blocco aggirabile con curl non è un blocco.
create or replace function public.can_write_to_chat(target_chat uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select not exists (
    select 1
    from public.chat_members other
    join public.chats c on c.id = other.chat_id
    where other.chat_id = target_chat
      and c.is_group = false
      and other.user_id <> auth.uid()
      and public.is_blocked_between(auth.uid(), other.user_id)
  );
$$;

revoke all on function public.can_write_to_chat(uuid) from public;
grant execute on function public.can_write_to_chat(uuid) to authenticated;

drop policy if exists "niente messaggi fra utenti che si sono bloccati" on public.messages;
create policy "niente messaggi fra utenti che si sono bloccati"
  on public.messages as restrictive for insert
  to authenticated
  with check (public.can_write_to_chat(chat_id));

-- ----------------------------------------------------------------------------
-- Limite di frequenza, applicato dal database
-- ----------------------------------------------------------------------------
-- Un limite scritto nel client non è un limite: chi vuole inondare una chat non
-- passa dal client. Questo trigger è la versione che conta.
--
-- 20 messaggi al minuto: una conversazione concitata ne fa una decina, uno
-- script ne farebbe migliaia.
create or replace function public.enforce_message_rate_limit()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  recent integer;
begin
  select count(*) into recent
  from public.messages
  where sender_id = new.sender_id
    and created_at > now() - interval '1 minute';

  if recent >= 20 then
    raise exception 'Troppi messaggi: aspetta qualche secondo.'
      using errcode = '53400';
  end if;

  return new;
end;
$$;

drop trigger if exists messages_rate_limit on public.messages;
create trigger messages_rate_limit
  before insert on public.messages
  for each row execute function public.enforce_message_rate_limit();

-- Senza questo indice il conteggio scandisce l'intera tabella a ogni messaggio.
create index if not exists messages_sender_recent_idx
  on public.messages (sender_id, created_at desc);

-- ----------------------------------------------------------------------------
-- Solo con email confermata
-- ----------------------------------------------------------------------------
-- Una chat aperta a indirizzi non verificati è una chat aperta a chiunque, e
-- rende inutile il ban: basta rifarsi un account con un'email inventata.
create or replace function public.has_confirmed_email()
returns boolean
language sql
stable
security definer
set search_path = auth, public
as $$
  select coalesce(
    (select u.email_confirmed_at is not null
       from auth.users u where u.id = auth.uid()),
    false
  );
$$;

revoke all on function public.has_confirmed_email() from public;
grant execute on function public.has_confirmed_email() to authenticated;

drop policy if exists "serve un'email confermata per scrivere" on public.messages;
create policy "serve un'email confermata per scrivere"
  on public.messages as restrictive for insert
  to authenticated
  with check (public.has_confirmed_email());

-- ----------------------------------------------------------------------------
-- Cancellare i propri messaggi
-- ----------------------------------------------------------------------------
-- Solo i propri, e solo cancellarli: un messaggio già letto non si riscrive.
drop policy if exists "ognuno cancella i propri messaggi" on public.messages;
create policy "ognuno cancella i propri messaggi"
  on public.messages for delete
  to authenticated
  using (sender_id = auth.uid());

-- ----------------------------------------------------------------------------
-- Cancellazione dell'account: pseudonimizzare, non cancellare
-- ----------------------------------------------------------------------------
-- Alla scadenza dei 30 giorni di grazia, i messaggi già inviati **restano**
-- nelle conversazioni, senza più un autore identificabile.
--
-- Non è una scorciatoia: cancellarli toglierebbe agli altri partecipanti metà
-- della loro conversazione, e loro non hanno chiesto niente. È il bilanciamento
-- standard fra l'art. 17 GDPR e l'interesse legittimo degli altri interessati,
-- e va scritto nell'informativa perché l'utente lo sappia prima di cancellarsi.
create or replace function public.pseudonymise_deleted_accounts()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  affected integer := 0;
  victim   uuid;
begin
  for victim in
    select id from public.profiles
    where deletion_requested_at is not null
      and deletion_requested_at < now() - interval '30 days'
  loop
    -- L'autore diventa nullo: il messaggio resta leggibile, la persona no.
    update public.messages set sender_id = null where sender_id = victim;

    delete from public.spot_contributions where author_id = victim;
    delete from public.chat_members         where user_id  = victim;
    delete from public.blocked_users        where blocker_id = victim or blocked_id = victim;
    delete from public.profiles             where id = victim;

    -- La riga in auth.users va rimossa a parte, con l'Admin API: da SQL non è
    -- raggiungibile. Vedi docs/OPS_TODO.md.
    affected := affected + 1;
  end loop;

  return affected;
end;
$$;

revoke all on function public.pseudonymise_deleted_accounts() from public;

comment on function public.pseudonymise_deleted_accounts() is
  'Da schedulare (pg_cron, giornaliero). Chiude le richieste di cancellazione '
  'scadute. Se non gira, il pulsante "elimina account" segna soltanto una data '
  'e non cancella niente — cioè il diritto dell''art. 17 resta sulla carta.';

-- `sender_id` deve poter essere nullo perché la pseudonimizzazione funzioni.
alter table public.messages alter column sender_id drop not null;

comment on column public.messages.sender_id is
  'NULL = account eliminato. Il messaggio resta nella conversazione degli '
  'altri partecipanti, senza autore.';

-- ----------------------------------------------------------------------------
-- Verifica dopo l'applicazione
-- ----------------------------------------------------------------------------
--   select * from chats limit 1;      -- 200 e lista vuota, non più 500
--   -- 21 insert di fila nello stesso minuto → il 21° deve fallire con 53400
--   -- bloccato A→B, poi B scrive nella chat diretta → deve fallire
--   -- utente con email non confermata che scrive → deve fallire
