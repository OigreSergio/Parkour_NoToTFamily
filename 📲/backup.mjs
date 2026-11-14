#!/usr/bin/env node
// ============================================================================
// PkFAMILY — backup del database Supabase
//
// Due modalità:
//   * PUBBLICA (default): usa la publishable key → salva solo i dati che le
//     policy RLS rendono pubblici (spot verificati, profili, video, ecc.).
//     Output: 📲/backup-quotidiano.json (committabile, nessun dato privato).
//   * COMPLETA: se è impostata SUPABASE_SECRET_KEY salva TUTTO, inclusi gli
//     utenti auth (email). Output: 📲/backup-completo.json — è nel .gitignore,
//     NON va mai committato né condiviso: contiene dati personali.
//
// Uso:
//   node 📲/backup.mjs                        # backup pubblico
//   SUPABASE_SECRET_KEY=sb_secret_... node 📲/backup.mjs   # backup completo
// ============================================================================

import { writeFileSync } from "node:fs";

const SUPABASE_URL = process.env.SUPABASE_URL ?? "https://gkdzdtxqkftebrxhgway.supabase.co";
const PUBLISHABLE_KEY =
  process.env.SUPABASE_PUBLISHABLE_KEY ?? "sb_publishable_Xi0aGU8lnV182kEKpsmU3w__uAkFVXg";
const SECRET_KEY = process.env.SUPABASE_SECRET_KEY;

const key = SECRET_KEY ?? PUBLISHABLE_KEY;
const mode = SECRET_KEY ? "completo" : "pubblico";
const outFile = SECRET_KEY ? "📲/backup-completo.json" : "📲/backup-quotidiano.json";

const TABLES = [
  "spots", "spot_photos", "fountains", "profiles", "posts", "comments",
  "post_likes", "post_saves", "ratings", "videos", "video_progress",
  "reports", "chats", "chat_members", "messages", "entitlements", "blocked_users",
];

const headers = { apikey: key, Authorization: `Bearer ${key}` };
const PAGE = 1000;

async function dumpTable(name) {
  const rows = [];
  for (let from = 0; ; from += PAGE) {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/${name}?select=*`, {
      headers: { ...headers, Range: `${from}-${from + PAGE - 1}` },
    });
    if (!res.ok) {
      // tabella non leggibile in questa modalità (RLS): salta
      return { skipped: true, status: res.status };
    }
    const chunk = await res.json();
    rows.push(...chunk);
    if (chunk.length < PAGE) break;
  }
  return rows;
}

async function dumpAuthUsers() {
  const users = [];
  for (let page = 1; ; page++) {
    const res = await fetch(
      `${SUPABASE_URL}/auth/v1/admin/users?page=${page}&per_page=200`,
      { headers }
    );
    if (!res.ok) throw new Error(`auth admin → ${res.status}`);
    const body = await res.json();
    users.push(...(body.users ?? []));
    if ((body.users ?? []).length < 200) break;
  }
  // niente hash delle password nel file: bastano email/id/metadata per il ripristino
  return users.map(({ id, email, phone, created_at, last_sign_in_at, user_metadata, email_confirmed_at }) =>
    ({ id, email, phone, created_at, last_sign_in_at, user_metadata, email_confirmed_at }));
}

const backup = {
  progetto: SUPABASE_URL,
  modalita: mode,
  generato_il: new Date().toISOString(),
  tabelle: {},
};

for (const t of TABLES) {
  const rows = await dumpTable(t);
  if (rows.skipped) {
    console.log(`~ ${t}: saltata (HTTP ${rows.status})`);
  } else {
    backup.tabelle[t] = rows;
    console.log(`✓ ${t}: ${rows.length} righe`);
  }
}

if (SECRET_KEY) {
  backup.utenti_auth = await dumpAuthUsers();
  console.log(`✓ utenti auth: ${backup.utenti_auth.length}`);
}

writeFileSync(outFile, JSON.stringify(backup, null, 1));
console.log(`\nBackup ${mode} salvato in ${outFile}`);
if (SECRET_KEY) console.log("ATTENZIONE: contiene dati personali — non committarlo, non condividerlo.");
