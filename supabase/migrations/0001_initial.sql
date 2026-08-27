-- ⚠️ STORICO — MAI APPLICATA IN PRODUZIONE. NON ESEGUIRE.
--
-- Questo file descrive uno schema che in produzione non esiste. Verificato
-- dall'esterno: la tabella `spots` reale ha `lat`/`lng`, `skill_level`,
-- `crowd_level`, `has_fountain`, `author_id` — non `location geography`,
-- `difficulty`, `water`, `submitted_by`, `photo_urls[]`. Le tabelle di chat si
-- chiamano `chats`/`chat_members`, non `conversations`/`conversation_members`.
--
-- Lo schema reale è in 0003_production_baseline.sql (ricostruzione, da
-- sostituire con l'output di scripts/dump_schema.sh).
-- Resta qui come storico del progetto.
--
-- ============================================================================
-- Parkour NoToT Family — initial Supabase schema
-- Run this in the Supabase Dashboard → SQL Editor (paste everything → Run).
--
-- Implements the data model of docs/DATA_MODEL.md adapted to Supabase:
--   * auth (users, sessions, refresh tokens) is handled by Supabase Auth
--     (auth.users) — the app keeps a public.profiles row per user.
--   * every table has Row Level Security enabled with explicit policies.
--   * PostGIS provides geography(Point, 4326) for spot locations.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Extensions
-- ----------------------------------------------------------------------------
create extension if not exists postgis with schema extensions;

-- ----------------------------------------------------------------------------
-- profiles — one row per auth.users row
-- ----------------------------------------------------------------------------
create table public.profiles (
  id           uuid primary key references auth.users (id) on delete cascade,
  display_name text not null default '',
  role         text not null default 'user' check (role in ('user', 'admin')),
  created_at   timestamptz not null default now()
);

-- Helper: is the current user an admin?
-- SECURITY DEFINER so policies can call it without recursive RLS lookups.
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'admin'
  );
$$;

alter table public.profiles enable row level security;

-- Everyone (incl. anonymous map viewers) can read public profile info.
create policy "profiles are readable by everyone"
  on public.profiles for select
  using (true);

-- Users may update only their own profile, and only display_name
-- (column-level grant below prevents role escalation).
create policy "users update own profile"
  on public.profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

revoke update on public.profiles from anon, authenticated;
grant update (display_name) on public.profiles to authenticated;

-- Auto-create a profile whenever a user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, display_name)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1))
  );
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ----------------------------------------------------------------------------
-- spots — moderated: pending → verified | rejected; only verified are public
-- ----------------------------------------------------------------------------
create table public.spots (
  id               uuid primary key default gen_random_uuid(),
  name             text not null,
  description      text not null default '',
  location         extensions.geography(Point, 4326) not null,
  photo_urls       text[] not null default '{}',
  difficulty       int not null default 1 check (difficulty between 1 and 5),
  water            boolean not null default false,
  status           text not null default 'pending'
                     check (status in ('pending', 'verified', 'rejected')),
  submitted_by     uuid not null references public.profiles (id) on delete cascade,
  verified_by      uuid references public.profiles (id) on delete set null,
  verified_at      timestamptz,
  rejection_reason text,
  created_at       timestamptz not null default now()
);

create index spots_location_gist on public.spots using gist (location);
create index spots_status_idx on public.spots (status);

alter table public.spots enable row level security;

-- Verified spots are public (anonymous map/list). Submitters see their own
-- pending/rejected spots; admins see everything.
create policy "verified spots are public, own and admin see all"
  on public.spots for select
  using (
    status = 'verified'
    or submitted_by = auth.uid()
    or public.is_admin()
  );

-- Any signed-in user can submit a spot, but only as themselves and only pending.
create policy "authenticated users submit pending spots"
  on public.spots for insert
  to authenticated
  with check (
    submitted_by = auth.uid()
    and status = 'pending'
    and verified_by is null
    and verified_at is null
  );

-- Submitters can edit their own spot while it is still pending; admins can
-- edit anything (that is how verify/reject happens).
create policy "owners edit pending spots, admins edit all"
  on public.spots for update
  to authenticated
  using (
    public.is_admin()
    or (submitted_by = auth.uid() and status = 'pending')
  )
  with check (
    public.is_admin()
    or (submitted_by = auth.uid() and status = 'pending')
  );

create policy "admins delete spots"
  on public.spots for delete
  to authenticated
  using (public.is_admin());

-- ----------------------------------------------------------------------------
-- spot_likes — per-user like tracking (likes count = count(*) per spot)
-- ----------------------------------------------------------------------------
create table public.spot_likes (
  spot_id    uuid not null references public.spots (id) on delete cascade,
  user_id    uuid not null references public.profiles (id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (spot_id, user_id)
);

alter table public.spot_likes enable row level security;

create policy "likes are readable by everyone"
  on public.spot_likes for select
  using (true);

create policy "users like as themselves"
  on public.spot_likes for insert
  to authenticated
  with check (user_id = auth.uid());

create policy "users remove their own likes"
  on public.spot_likes for delete
  to authenticated
  using (user_id = auth.uid());

-- ----------------------------------------------------------------------------
-- spot_moderation_events — audit log of every admin action on a spot
-- ----------------------------------------------------------------------------
create table public.spot_moderation_events (
  id         uuid primary key default gen_random_uuid(),
  spot_id    uuid not null references public.spots (id) on delete cascade,
  actor_id   uuid not null references public.profiles (id) on delete cascade,
  action     text not null check (action in ('verified', 'rejected', 'edited')),
  reason     text,
  created_at timestamptz not null default now()
);

create index spot_moderation_events_spot_idx on public.spot_moderation_events (spot_id);

alter table public.spot_moderation_events enable row level security;

create policy "admins read moderation log"
  on public.spot_moderation_events for select
  to authenticated
  using (public.is_admin());

create policy "admins write moderation log as themselves"
  on public.spot_moderation_events for insert
  to authenticated
  with check (public.is_admin() and actor_id = auth.uid());

-- ----------------------------------------------------------------------------
-- chat — conversations, members, messages (text only for v1)
-- ----------------------------------------------------------------------------
create table public.conversations (
  id         uuid primary key default gen_random_uuid(),
  kind       text not null default 'direct' check (kind in ('direct', 'group')),
  created_by uuid not null references public.profiles (id) on delete cascade,
  created_at timestamptz not null default now()
);

create table public.conversation_members (
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  user_id         uuid not null references public.profiles (id) on delete cascade,
  joined_at       timestamptz not null default now(),
  primary key (conversation_id, user_id)
);

create table public.messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  author_id       uuid not null references public.profiles (id) on delete cascade,
  body            text not null check (length(body) between 1 and 4000),
  created_at      timestamptz not null default now()
);

create index messages_conversation_idx on public.messages (conversation_id, created_at);

-- SECURITY DEFINER membership check avoids recursive RLS between
-- conversations / conversation_members / messages.
create or replace function public.is_conversation_member(conv_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.conversation_members
    where conversation_id = conv_id and user_id = auth.uid()
  );
$$;

alter table public.conversations enable row level security;
alter table public.conversation_members enable row level security;
alter table public.messages enable row level security;

create policy "members read their conversations"
  on public.conversations for select
  to authenticated
  using (public.is_conversation_member(id) or created_by = auth.uid());

create policy "users create conversations as themselves"
  on public.conversations for insert
  to authenticated
  with check (created_by = auth.uid());

create policy "members see membership of their conversations"
  on public.conversation_members for select
  to authenticated
  using (public.is_conversation_member(conversation_id));

create policy "creator adds members, users add themselves"
  on public.conversation_members for insert
  to authenticated
  with check (
    user_id = auth.uid()
    or exists (
      select 1 from public.conversations c
      where c.id = conversation_id and c.created_by = auth.uid()
    )
  );

create policy "users leave conversations"
  on public.conversation_members for delete
  to authenticated
  using (user_id = auth.uid());

create policy "members read messages"
  on public.messages for select
  to authenticated
  using (public.is_conversation_member(conversation_id));

create policy "members write messages as themselves"
  on public.messages for insert
  to authenticated
  with check (
    author_id = auth.uid()
    and public.is_conversation_member(conversation_id)
  );

-- ----------------------------------------------------------------------------
-- videos — curated training/recovery videos (public read, admin write)
-- ----------------------------------------------------------------------------
create table public.videos (
  id         uuid primary key default gen_random_uuid(),
  title      text not null,
  url        text not null,
  category   text not null check (category in ('recovery', 'practice', 'conditioning')),
  level      text not null check (level in ('beginner', 'intermediate', 'advanced')),
  created_at timestamptz not null default now()
);

alter table public.videos enable row level security;

create policy "videos are readable by everyone"
  on public.videos for select
  using (true);

create policy "admins insert videos"
  on public.videos for insert
  to authenticated
  with check (public.is_admin());

create policy "admins update videos"
  on public.videos for update
  to authenticated
  using (public.is_admin())
  with check (public.is_admin());

create policy "admins delete videos"
  on public.videos for delete
  to authenticated
  using (public.is_admin());
