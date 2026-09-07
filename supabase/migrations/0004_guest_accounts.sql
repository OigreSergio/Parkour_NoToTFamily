-- ============================================================================
-- Account anonimi (guest)
--
-- Su Supabase il guest è un anonymous sign-in: una riga vera in auth.users,
-- con la sua sessione persistente — quella *è* la chiave univoca che nel
-- backend FastAPI è `users.guest_key_hash`. Non serve replicarla; serve
-- sistemare tre cose che oggi non reggono un utente senza email:
--
--  1. handle_new_user() costruisce il display_name da split_part(email,'@',1).
--     Per un anonimo l'email è NULL, quindi il trigger inserirebbe NULL in una
--     colonna NOT NULL e l'iscrizione fallirebbe. Da qui in poi il nome lo
--     genera il database, come fa app/data/guest_names.py.
--  2. un anonimo non può qualificarsi istruttore: qualificarsi vuol dire
--     mandare certificato e documento d'identità a una persona, che è
--     l'opposto di restare anonimi.
--  3. tutto il resto resta identico: stesse domande, stesso tetto per età e
--     per esperienza, stesse informative.
--
-- Eseguire nel SQL Editor di Supabase dopo 0003_auth_profiles_and_legal.sql.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Nomi generati
--
-- Solo luoghi su cui ci si allena: niente qui può essere letto come
-- un'affermazione su chi c'è dietro l'account. L'alfabeto del suffisso non ha
-- 0/O né 1/I, perché questi nomi si leggono ad alta voce e si riscrivono a
-- mano.
-- ----------------------------------------------------------------------------
create or replace function public.guest_name_candidate()
returns text
language sql
volatile
as $$
  select (array[
    'Muretto', 'Corrimano', 'Cornicione', 'Gradino', 'Ponteggio',
    'Tetto', 'Parapetto', 'Ringhiera', 'Palo', 'Dislivello',
    'Sottopasso', 'Lampione', 'Portico', 'Cordolo', 'Balaustra',
    'Marciapiede', 'Scalone', 'Terrazzo', 'Pilastro', 'Guardrail'
  ])[floor(random() * 20 + 1)]
  || '-'
  || (
    select string_agg(
      substr('23456789ABCDEFGHJKLMNPQRSTUVWXYZ', floor(random() * 32 + 1)::int, 1), ''
    )
    from generate_series(1, 4)
  );
$$;

-- Le collisioni sono estetiche — l'account è identificato dal suo id, non dal
-- nome — ma due `Cornicione-7K4Q` nello stesso thread di commenti sono
-- esattamente il tipo di sovrapposizione che un anonimo non ha modo di
-- risolvere. Cinque tentativi, poi si allarga il suffisso.
create or replace function public.guest_display_name()
returns text
language plpgsql
volatile
security definer
set search_path = public
as $$
declare
  candidate text;
begin
  for _ in 1..5 loop
    candidate := public.guest_name_candidate();
    if not exists (select 1 from public.profiles where display_name = candidate) then
      return candidate;
    end if;
  end loop;
  return candidate || '-' || substr(md5(random()::text), 1, 4);
end;
$$;

-- ----------------------------------------------------------------------------
-- Il trigger di iscrizione regge un utente senza email
-- ----------------------------------------------------------------------------
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
    coalesce(
      nullif(new.raw_user_meta_data ->> 'display_name', ''),
      nullif(split_part(coalesce(new.email, ''), '@', 1), ''),
      public.guest_display_name()
    )
  );
  -- Il profilo del membro nasce insieme all'account: senza, il primo passo
  -- dell'onboarding sarebbe una insert che il client può anche non fare.
  insert into public.member_profiles (user_id)
  values (new.id)
  on conflict (user_id) do nothing;
  return new;
end;
$$;

-- ----------------------------------------------------------------------------
-- Un anonimo è un atleta
-- ----------------------------------------------------------------------------
create or replace function public.is_anonymous()
returns boolean
language sql
stable
as $$
  select coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false);
$$;

drop policy if exists "members create their own profile" on public.member_profiles;
create policy "members create their own profile"
  on public.member_profiles for insert
  to authenticated
  with check (
    user_id = auth.uid()
    and not (public.is_anonymous() and practitioner_type = 'instructor')
  );

drop policy if exists "members update their own profile" on public.member_profiles;
create policy "members update their own profile"
  on public.member_profiles for update
  to authenticated
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and not (public.is_anonymous() and practitioner_type = 'instructor')
  );

-- E non può aprire una pratica di qualifica: la policy lo blocca prima che
-- un documento d'identità parta verso una casella di revisione.
drop policy if exists "members submit their own dossier" on public.instructor_certifications;
create policy "members submit their own dossier"
  on public.instructor_certifications for insert
  to authenticated
  with check (
    user_id = auth.uid()
    and status = 'pending'
    and not public.is_anonymous()
  );
