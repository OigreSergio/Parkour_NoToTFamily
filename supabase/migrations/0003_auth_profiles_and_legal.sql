-- ============================================================================
-- Accesso via codice email, profilo del membro, informative sui rischi
--
-- Rispecchia in Supabase quello che il backend FastAPI fa in
-- backend/alembic/versions/2026_09_06_0004_*. Su Supabase il codice via email
-- lo manda Supabase Auth (signInWithOtp, template "Magic Link" impostato su
-- codice OTP e mittente no-reply): qui non serve una tabella di codici, serve
-- tutto quello che viene *dopo* la verifica.
--
-- Due cose non sono cosmetiche e vanno lette prima di modificare il file:
--
--  1. `birth_date` NON sta in public.profiles. Quella tabella è leggibile da
--     chiunque ("profiles are readable by everyone"): metterci la data di
--     nascita la renderebbe pubblica. Sta in member_profiles, con RLS per il
--     solo proprietario e un grant per colonna che la nasconde anche a lui —
--     stesso schema del grant su profiles.display_name in 0001.
--
--  2. Il tetto dei contenuti è applicato dalle policy RLS, non dal client.
--     Un'app vecchia, o una chiamata fatta a mano con la publishable key, non
--     può scavalcarlo.
--
-- Eseguire nel SQL Editor di Supabase dopo 0002_instructor_role.sql.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Tipi
-- ----------------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_type where typname = 'practitioner_type') then
    create type public.practitioner_type as enum ('athlete', 'instructor');
  end if;
  if not exists (select 1 from pg_type where typname = 'experience_band') then
    create type public.experience_band as enum (
      'less_than_month', 'few_months', 'six_months', 'one_year',
      'couple_years', 'over_5_years', 'over_10_years'
    );
  end if;
  if not exists (select 1 from pg_type where typname = 'certification_status') then
    create type public.certification_status as enum ('pending', 'approved', 'rejected');
  end if;
end
$$;

-- ----------------------------------------------------------------------------
-- member_profiles — quello che serve per scegliere gli esercizi giusti
-- ----------------------------------------------------------------------------
create table if not exists public.member_profiles (
  user_id                 uuid primary key references auth.users (id) on delete cascade,
  birth_date              date,
  practitioner_type       public.practitioner_type,
  -- Quello che il membro ha dichiarato: apre subito i livelli corrispondenti.
  experience_band         public.experience_band,
  -- Quello che il gioco degli scavalcamenti sostiene davvero. Ha la precedenza.
  verified_band           public.experience_band,
  quiz_passed_at          timestamptz,
  quiz_attempts           int not null default 0,
  onboarding_completed_at timestamptz,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);

alter table public.member_profiles enable row level security;

create policy "members read their own profile"
  on public.member_profiles for select
  to authenticated
  using (user_id = auth.uid());

create policy "members create their own profile"
  on public.member_profiles for insert
  to authenticated
  with check (user_id = auth.uid());

create policy "members update their own profile"
  on public.member_profiles for update
  to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- La data di nascita si scrive ma non si rilegge: la versione sicura per i
-- minorenni funziona solo se nessun client — nemmeno il proprio — può sapere
-- di essere sotto i 18 anni e disegnare una schermata diversa. Il filtro sta
-- nelle policy qui sotto, non nell'app.
revoke select on public.member_profiles from anon, authenticated;
grant select (
  user_id, practitioner_type, experience_band, verified_band,
  quiz_passed_at, quiz_attempts, onboarding_completed_at, created_at, updated_at
) on public.member_profiles to authenticated;

-- ----------------------------------------------------------------------------
-- Il tetto dei contenuti
--
-- Vale sempre il più basso fra il tetto dell'età e quello dell'esperienza.
-- Nessuna dichiarazione può alzare il primo. Vedi docs/AUTENTICAZIONE.md per
-- le tabelle e il ragionamento.
-- ----------------------------------------------------------------------------
create or replace function public.level_rank(lvl text)
returns int
language sql
immutable
as $$
  select case lvl
    when 'beginner' then 1
    when 'intermediate' then 2
    when 'advanced' then 3
    else 3
  end;
$$;

create or replace function public.band_ceiling(band public.experience_band)
returns table (max_level text, max_difficulty int)
language sql
immutable
as $$
  select t.lvl, t.diff from (values
    ('less_than_month', 'beginner',     2),
    ('few_months',      'beginner',     3),
    ('six_months',      'intermediate', 5),
    ('one_year',        'intermediate', 6),
    ('couple_years',    'advanced',     8),
    ('over_5_years',    'advanced',    10),
    ('over_10_years',   'advanced',    10)
  ) as t(b, lvl, diff)
  where t.b = coalesce(band::text, 'few_months');
$$;

create or replace function public.age_ceiling(years int)
returns table (max_level text, max_difficulty int)
language sql
immutable
as $$
  select t.lvl, t.diff from (values
    (11, 'beginner',     2),
    (13, 'beginner',     3),
    (15, 'intermediate', 4),
    (17, 'intermediate', 6),
    (200, 'advanced',   10)
  ) as t(max_age, lvl, diff)
  where years <= t.max_age
  order by t.max_age
  limit 1;
$$;

-- SECURITY DEFINER: legge birth_date, che è revocata a tutti i ruoli client.
-- È il solo punto in cui l'età viene toccata, e non esce da qui.
create or replace function public.my_content_ceiling()
returns table (max_level text, max_difficulty int)
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  prof public.member_profiles%rowtype;
  band_lvl text;
  band_diff int;
  age_lvl text;
  age_diff int;
  member_age int;
  qualified boolean;
begin
  select * into prof from public.member_profiles where user_id = auth.uid();

  -- Chi non ha ancora risposto vede il catalogo di sempre: il tetto è la
  -- conseguenza di aver detto all'app chi si è, non una penalità.
  if prof.user_id is null or prof.birth_date is null then
    return query select 'advanced'::text, 10;
    return;
  end if;

  select exists (
    select 1 from public.instructor_certifications c
    where c.user_id = prof.user_id and c.status = 'approved'
  ) into qualified;

  if prof.practitioner_type = 'instructor' and qualified then
    band_lvl := 'advanced';
    band_diff := 10;
  else
    select b.max_level, b.max_difficulty into band_lvl, band_diff
    from public.band_ceiling(coalesce(prof.verified_band, prof.experience_band)) b;
  end if;

  member_age := extract(year from age(current_date, prof.birth_date))::int;
  if member_age >= 18 then
    return query select band_lvl, band_diff;
    return;
  end if;

  select a.max_level, a.max_difficulty into age_lvl, age_diff
  from public.age_ceiling(member_age) a;

  return query select
    case when public.level_rank(age_lvl) < public.level_rank(band_lvl)
         then age_lvl else band_lvl end,
    least(age_diff, band_diff);
end;
$$;

create or replace function public.content_allows(lvl text, diff int)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(
    (
      select public.level_rank(lvl) <= public.level_rank(c.max_level)
         and diff <= c.max_difficulty
      from public.my_content_ceiling() c
    ),
    true
  );
$$;

-- La difficoltà 1-10 che il backend già usa sui tutorial: senza, il tetto
-- potrebbe ragionare solo per livello e sarebbe molto più grossolano.
alter table public.videos
  add column if not exists difficulty int not null default 1
  check (difficulty between 1 and 10);

-- I video oltre il tetto non sono "bloccati": non esistono, per chi guarda.
-- Una riga grigia o un contatore che non torna sarebbero già una differenza
-- visibile, ed è esattamente quello che la versione sicura non deve avere.
drop policy if exists "videos are readable by everyone" on public.videos;
create policy "videos within the viewer's ceiling are readable"
  on public.videos for select
  using (
    auth.uid() is null                       -- visitatori anonimi: catalogo intero
    or public.is_admin()
    or public.content_allows(level, difficulty)
  );

-- ----------------------------------------------------------------------------
-- legal_acceptances — prova che l'informativa è stata mostrata, a quella versione
-- ----------------------------------------------------------------------------
create table if not exists public.legal_acceptances (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references auth.users (id) on delete cascade,
  document_id      text not null,
  document_version int not null,
  accepted_at      timestamptz not null default now(),
  -- Troncato prima di arrivare qui (/24 IPv4, /48 IPv6).
  ip_address       text,
  user_agent       text,
  unique (user_id, document_id, document_version)
);

create index if not exists legal_acceptances_user_idx
  on public.legal_acceptances (user_id);

alter table public.legal_acceptances enable row level security;

create policy "members read their own acceptances"
  on public.legal_acceptances for select
  to authenticated
  using (user_id = auth.uid() or public.is_admin());

create policy "members record their own acceptances"
  on public.legal_acceptances for insert
  to authenticated
  with check (user_id = auth.uid());

-- Nessuna policy di update o delete, di proposito: un'accettazione è una prova
-- di cosa è stato accettato e quando. Non si modifica e non si cancella.

-- ----------------------------------------------------------------------------
-- instructor_certifications — solo i metadati, mai i file
--
-- Certificato e documento d'identità vengono inoltrati per email alla casella
-- che verifica gli spot e non restano da nessuna parte: qui resta lo SHA-256,
-- che basta a dimostrare poi che il documento revisionato è quello inviato.
-- ----------------------------------------------------------------------------
create table if not exists public.instructor_certifications (
  id                   uuid primary key default gen_random_uuid(),
  user_id              uuid not null references auth.users (id) on delete cascade,
  issuing_body         text not null,
  certificate_filename text not null,
  certificate_sha256   text not null,
  identity_filename    text not null,
  identity_sha256      text not null,
  status               public.certification_status not null default 'pending',
  reviewed_at          timestamptz,
  reviewer_id          uuid references public.profiles (id) on delete set null,
  rejection_reason     text,
  created_at           timestamptz not null default now()
);

create index if not exists instructor_certifications_user_idx
  on public.instructor_certifications (user_id);

alter table public.instructor_certifications enable row level security;

create policy "members read their own dossier"
  on public.instructor_certifications for select
  to authenticated
  using (user_id = auth.uid() or public.is_admin());

create policy "members submit their own dossier"
  on public.instructor_certifications for insert
  to authenticated
  with check (user_id = auth.uid() and status = 'pending');

-- Solo l'admin decide l'esito: approvarsi da soli sarebbe il punto debole
-- dell'intera verifica.
create policy "admins review dossiers"
  on public.instructor_certifications for update
  to authenticated
  using (public.is_admin())
  with check (public.is_admin());

-- ----------------------------------------------------------------------------
-- experience_quiz_attempts — il gioco degli scavalcamenti
-- ----------------------------------------------------------------------------
create table if not exists public.experience_quiz_attempts (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users (id) on delete cascade,
  claimed_band  public.experience_band,
  -- Le risposte giuste. Vedi il grant per colonna più sotto.
  questions     jsonb not null,
  score         int not null default 0,
  total         int not null default 0,
  passed        boolean not null default false,
  granted_band  public.experience_band,
  created_at    timestamptz not null default now(),
  completed_at  timestamptz
);

create index if not exists experience_quiz_attempts_user_idx
  on public.experience_quiz_attempts (user_id);

alter table public.experience_quiz_attempts enable row level security;

create policy "members read their own attempts"
  on public.experience_quiz_attempts for select
  to authenticated
  using (user_id = auth.uid() or public.is_admin());

create policy "members record their own attempts"
  on public.experience_quiz_attempts for insert
  to authenticated
  with check (user_id = auth.uid());

create policy "members complete their own attempts"
  on public.experience_quiz_attempts for update
  to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- `questions` contiene la soluzione: leggibile non renderebbe il gioco un
-- gioco. Su Supabase le domande le prepara un'Edge Function con la secret key
-- (o il backend FastAPI); il client vede solo quello che gli serve.
revoke select on public.experience_quiz_attempts from anon, authenticated;
grant select (
  id, user_id, claimed_band, score, total, passed, granted_band,
  created_at, completed_at
) on public.experience_quiz_attempts to authenticated;
