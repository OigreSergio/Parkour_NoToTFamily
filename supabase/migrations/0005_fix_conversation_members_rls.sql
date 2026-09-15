-- ============================================================================
-- Correzione RLS: chi può aggiungere membri a una conversazione
--
-- Falla (referto docs/SECURITY_PENTEST_2026-09.md, sez. 3): la policy di
-- INSERT su conversation_members introdotta in 0001 permetteva a qualsiasi
-- utente autenticato di inserire SE STESSO in QUALSIASI conversazione
-- (clausola `user_id = auth.uid()`), diventandone membro e leggendone i
-- messaggi privati. Bastava conoscere l'UUID della conversazione.
--
-- Correzione: solo il CREATORE della conversazione può aggiungere membri.
-- Verificato che blocca l'auto-aggiunta e non rompe l'aggiunta legittima
-- da parte del creatore. Vale per le chat `direct` attuali (create con
-- entrambi i membri). Per eventuali chat di gruppo con auto-iscrizione
-- servirà un meccanismo di invito esplicito, non il ripristino di questa
-- clausola.
--
-- Eseguire nel SQL Editor di Supabase dopo 0004_guest_accounts.sql.
-- ============================================================================

drop policy if exists "creator adds members, users add themselves"
  on public.conversation_members;

create policy "only the conversation creator adds members"
  on public.conversation_members for insert
  to authenticated
  with check (
    exists (
      select 1 from public.conversations c
      where c.id = conversation_id
        and c.created_by = auth.uid()
    )
  );
