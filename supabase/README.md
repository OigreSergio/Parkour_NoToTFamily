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
