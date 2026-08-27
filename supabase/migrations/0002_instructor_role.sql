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
