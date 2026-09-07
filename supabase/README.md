# Supabase

Schema and seed for the Supabase project backing the app.

## 1. Create the tables

Dashboard → **SQL Editor** → paste the whole content of
[`migrations/0001_initial.sql`](migrations/0001_initial.sql) → **Run**.

This creates `profiles`, `spots`, `spot_likes`, `spot_moderation_events`,
`conversations`, `conversation_members`, `messages`, `videos` — all with Row
Level Security enabled — plus the PostGIS extension, the
`on_auth_user_created` trigger and the `is_admin()` /
`is_conversation_member()` helper functions.

## 1b. Accesso, profili e informative

Dashboard → **SQL Editor** → incolla
[`migrations/0003_auth_profiles_and_legal.sql`](migrations/0003_auth_profiles_and_legal.sql)
→ **Run**.

Aggiunge `member_profiles`, `legal_acceptances`, `instructor_certifications`,
`experience_quiz_attempts`, la colonna `videos.difficulty` e le funzioni che
calcolano il tetto dei contenuti. Il tetto lo applica una policy RLS su
`videos`: un client vecchio, o una chiamata fatta a mano con la publishable
key, non può scavalcarlo. Vedi [docs/AUTENTICAZIONE.md](../docs/AUTENTICAZIONE.md).

Il codice via email lo manda Supabase Auth: Dashboard → **Authentication** →
Providers → Email, con "Confirm email" attivo e il template *Magic Link*
impostato per inviare il codice OTP (`{{ .Token }}`) invece del link. Il
mittente va configurato su un indirizzo **no-reply** in
Project Settings → Auth → SMTP Settings.

`birth_date` sta in `member_profiles` e non in `profiles` di proposito:
`profiles` è leggibile da chiunque. Un `revoke`/`grant` per colonna la nasconde
anche al proprietario — la versione sicura per i minorenni funziona solo se
nessun client può sapere di esserci dentro.

## 1c. Account anonimi

Dashboard → **SQL Editor** → incolla
[`migrations/0004_guest_accounts.sql`](migrations/0004_guest_accounts.sql)
→ **Run**, e attiva Authentication → Providers → **Anonymous sign-ins**.

Su Supabase il guest è un anonymous sign-in: una riga vera in `auth.users` con
la sua sessione persistente, che è la chiave univoca dell'account. Senza questa
migrazione l'iscrizione anonima **fallisce**: `handle_new_user()` costruiva il
nome da `split_part(email, '@', 1)` e per un anonimo l'email è NULL. Da qui in
poi il nome lo genera il database, e una policy RLS impedisce a un anonimo di
dichiararsi istruttore o di aprire una pratica di qualifica.

## 2. Seed (admin + Rome spots)

Requires Node 20+ and the project's **secret** key (Dashboard → Settings →
API Keys). The secret key bypasses RLS — never commit it or ship it in a
client.

```sh
SUPABASE_URL=https://<project-ref>.supabase.co \
SUPABASE_SECRET_KEY=sb_secret_... \
node supabase/seed/seed.mjs
```

Creates `adminpkfamily@gmail.com` (password generated and printed **once** — save
it in a password manager) and inserts five verified Rome spots. Safe to
re-run: it skips whatever already exists.

## Keys used by the apps

- **Publishable key** (`sb_publishable_…`): goes in the mobile app and
  web-admin — safe to expose, RLS applies.
- **Secret key** (`sb_secret_…`): server/seed only, bypasses RLS.
