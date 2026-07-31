-- ============================================================================
-- Livelli di appartenenza — ruolo `instructor`
--
-- Tutti gli account nascono uguali (`user`). L'unica progressione è una
-- qualifica: `instructor`, concessa (e revocabile) da un admin al membro che
-- si qualifica per insegnare. `admin` resta riservato: è l'unico ruolo che
-- opera la console web (moderazione, qualifiche) e non esiste alcun percorso
-- self-service per ottenerlo — si assegna solo a mano, a livello di database.
--
-- Eseguire nel SQL Editor di Supabase dopo 0001_initial.sql.
-- ============================================================================

alter table public.profiles
  drop constraint if exists profiles_role_check;

alter table public.profiles
  add constraint profiles_role_check
  check (role in ('user', 'instructor', 'admin'));

-- Nessuna policy RLS cambia: `instructor` è una qualifica riconosciuta, non
-- un privilegio di scrittura aggiuntivo. is_admin() resta l'unico gate admin.
