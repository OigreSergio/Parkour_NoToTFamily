-- ============================================================================
-- PkFAMILY — la chat non risponde: ricorsione infinita nelle policy RLS
--
-- Sintomo, riproducibile oggi in produzione con la sola publishable key:
--
--   GET /rest/v1/chats?select=*&limit=1
--   → HTTP 500
--     {"code":"42P17",
--      "message":"infinite recursion detected in policy for relation \"chat_members\""}
--
-- Stessa risposta su `chat_members` e `messages`. Non è «la chat non ha ancora
-- un client»: è che a livello di database **non può funzionare**.
--
-- Causa: la policy su `chats` interroga `chat_members` per sapere se chi legge
-- è membro, e la policy su `chat_members` interroga `chats` per sapere se la
-- conversazione è sua. Postgres valuta le due policy una dentro l'altra e si
-- ferma con 42P17.
--
-- Rimedio: una funzione SECURITY DEFINER, che gira con i privilegi di chi l'ha
-- creata e quindi **non riattiva la RLS** sulle tabelle che legge. Le policy
-- interrogano lei, e il ciclo si spezza. È lo stesso pattern già presente in
-- 0001_initial.sql:226 (`is_conversation_member`), che però era scritto per
-- tabelle — `conversations`/`conversation_members` — che in produzione non
-- esistono: qui è applicato ai nomi reali.
--
-- ⚠️ PRIMA DI APPLICARLA: questa migration ricrea le policy delle tabelle di
-- chat, e le policy attuali non sono ispezionabili dall'esterno. Esegui prima
-- scripts/dump_schema.sh per avere lo stato reale, e verifica che i nomi delle
-- policy droppate corrispondano. In caso di dubbio applicala su un progetto di
-- staging, non direttamente in produzione.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Il test di appartenenza, isolato dalla RLS
-- ----------------------------------------------------------------------------
create or replace function public.is_chat_member(chat_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.chat_members
    where chat_members.chat_id = is_chat_member.chat_id
      and chat_members.user_id = auth.uid()
  );
$$;

revoke all on function public.is_chat_member(uuid) from public;
grant execute on function public.is_chat_member(uuid) to authenticated;

comment on function public.is_chat_member(uuid) is
  'Chi chiama è membro della chat? SECURITY DEFINER apposta: le policy di '
  'chats/chat_members/messages la usano per non interrogarsi a vicenda (42P17).';

-- ----------------------------------------------------------------------------
-- chats
-- ----------------------------------------------------------------------------
alter table public.chats enable row level security;

drop policy if exists "members read their chats" on public.chats;
drop policy if exists "users create chats as themselves" on public.chats;

create policy "members read their chats"
  on public.chats for select
  to authenticated
  using (public.is_chat_member(id) or created_by = auth.uid());

create policy "users create chats as themselves"
  on public.chats for insert
  to authenticated
  with check (created_by = auth.uid());

-- ----------------------------------------------------------------------------
-- chat_members — la tabella su cui la ricorsione si chiudeva
-- ----------------------------------------------------------------------------
alter table public.chat_members enable row level security;

drop policy if exists "members see membership of their chats" on public.chat_members;
drop policy if exists "creator adds members, users add themselves" on public.chat_members;
drop policy if exists "users leave chats" on public.chat_members;

-- Nessun riferimento a `chats` qui dentro: si guarda solo la propria riga o si
-- passa dalla funzione. È questo che rompe il ciclo.
create policy "members see membership of their chats"
  on public.chat_members for select
  to authenticated
  using (user_id = auth.uid() or public.is_chat_member(chat_id));

create policy "creator adds members, users add themselves"
  on public.chat_members for insert
  to authenticated
  with check (
    user_id = auth.uid()
    or exists (
      select 1 from public.chats c
      where c.id = chat_id and c.created_by = auth.uid()
    )
  );

create policy "users leave chats"
  on public.chat_members for delete
  to authenticated
  using (user_id = auth.uid());

-- ----------------------------------------------------------------------------
-- messages
-- ----------------------------------------------------------------------------
alter table public.messages enable row level security;

drop policy if exists "members read messages" on public.messages;
drop policy if exists "members write messages as themselves" on public.messages;

create policy "members read messages"
  on public.messages for select
  to authenticated
  using (public.is_chat_member(chat_id));

create policy "members write messages as themselves"
  on public.messages for insert
  to authenticated
  with check (
    author_id = auth.uid()
    and public.is_chat_member(chat_id)
  );

-- ----------------------------------------------------------------------------
-- Verifica dopo l'applicazione
-- ----------------------------------------------------------------------------
-- Da non autenticato, con la sola publishable key, tutte e tre devono
-- rispondere 200 con lista vuota — mai più 500:
--
--   curl -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
--        "$SUPABASE_URL/rest/v1/chats?select=id&limit=1"
--   curl ... "$SUPABASE_URL/rest/v1/chat_members?select=chat_id&limit=1"
--   curl ... "$SUPABASE_URL/rest/v1/messages?select=id&limit=1"
--
-- Il controllo è automatizzato in scripts/audit_rls.mjs (BLOCCO 9).
