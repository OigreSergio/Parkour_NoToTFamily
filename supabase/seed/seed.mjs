#!/usr/bin/env node
// ============================================================================
// Parkour NoToT Family — Supabase seed
//
// Creates the admin account (admin@pkfamily.app) with a generated password
// (printed ONCE to stdout — store it in a password manager) and inserts the
// five Rome spots as `verified`.
//
// Requires the SQL migration (supabase/migrations/0001_initial.sql) to have
// been run first. Uses the *secret* key, which bypasses RLS — never ship it
// in a client.
//
// Usage:
//   SUPABASE_URL=https://<ref>.supabase.co \
//   SUPABASE_SECRET_KEY=sb_secret_... \
//   node supabase/seed/seed.mjs
//
// Idempotent: re-running skips the admin if it exists and upserts spots by name.
// ============================================================================

import crypto from "node:crypto";

const url = process.env.SUPABASE_URL?.replace(/\/$/, "");
const key = process.env.SUPABASE_SECRET_KEY;
if (!url || !key) {
  console.error("Set SUPABASE_URL and SUPABASE_SECRET_KEY");
  process.exit(1);
}

const headers = {
  apikey: key,
  Authorization: `Bearer ${key}`,
  "Content-Type": "application/json",
};

async function api(path, init = {}) {
  const res = await fetch(`${url}${path}`, {
    ...init,
    headers: { ...headers, ...init.headers },
  });
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) {
    throw new Error(`${init.method ?? "GET"} ${path} → ${res.status}: ${text}`);
  }
  return body;
}

function generatePassword() {
  // 4 groups of 5 from an unambiguous alphabet, e.g. kf7mq-2xhr9-...
  const alphabet = "abcdefghjkmnpqrstuvwxyz23456789";
  const group = () =>
    Array.from(crypto.randomBytes(5), (b) => alphabet[b % alphabet.length]).join("");
  return [group(), group(), group(), group()].join("-");
}

const ADMIN_EMAIL = "admin@pkfamily.app";

async function ensureAdmin() {
  const existing = await api("/auth/v1/admin/users?page=1&per_page=200");
  const match = (existing.users ?? []).find((u) => u.email === ADMIN_EMAIL);
  if (match) {
    console.log(`Admin ${ADMIN_EMAIL} already exists (${match.id}) — password unchanged.`);
    return match.id;
  }

  const password = generatePassword();
  const created = await api("/auth/v1/admin/users", {
    method: "POST",
    body: JSON.stringify({
      email: ADMIN_EMAIL,
      password,
      email_confirm: true,
      user_metadata: { display_name: "PK Family Admin" },
    }),
  });
  console.log(`Created admin ${ADMIN_EMAIL} (${created.id})`);
  console.log(`ADMIN PASSWORD (shown once, save it now): ${password}`);
  return created.id;
}

async function promoteToAdmin(userId) {
  await api(`/rest/v1/profiles?id=eq.${userId}`, {
    method: "PATCH",
    headers: { Prefer: "return=minimal" },
    body: JSON.stringify({ role: "admin", display_name: "PK Family Admin" }),
  });
  console.log("Profile role set to admin.");
}

const SPOTS = [
  {
    name: "Colle Oppio",
    description:
      "Parco sopra la Domus Aurea con muretti, scalinate e ringhiere a due passi dal Colosseo. Ottimo per precision e vault di base.",
    lng: 12.4964,
    lat: 41.8925,
    difficulty: 2,
    water: true,
  },
  {
    name: "EUR Laghetto",
    description:
      "Area del laghetto dell'EUR: muri bassi, panche in pietra e dislivelli regolari. Superfici lisce, ideale per flow e allenamento tecnico.",
    lng: 12.4707,
    lat: 41.8299,
    difficulty: 3,
    water: true,
  },
  {
    name: "Foro Italico",
    description:
      "Marmi, gradinate e muri alti attorno allo Stadio dei Marmi. Grip ottimo sull'asciutto, attenzione col bagnato.",
    lng: 12.4547,
    lat: 41.9339,
    difficulty: 4,
    water: false,
  },
  {
    name: "Parco degli Acquedotti",
    description:
      "Prati e rovine degli acquedotti romani: superfici irregolari, salti tra blocchi antichi. Rispetta le aree recintate.",
    lng: 12.5583,
    lat: 41.8443,
    difficulty: 3,
    water: false,
  },
  {
    name: "Gazometro Ostiense",
    description:
      "Zona industriale del Gazometro: muri in cemento, rail e strutture urbane. Spot serale molto frequentato dalla community.",
    lng: 12.4776,
    lat: 41.8697,
    difficulty: 4,
    water: false,
  },
];

async function seedSpots(adminId) {
  for (const s of SPOTS) {
    const existing = await api(
      `/rest/v1/spots?name=eq.${encodeURIComponent(s.name)}&select=id`
    );
    if (existing.length > 0) {
      console.log(`Spot "${s.name}" already exists — skipped.`);
      continue;
    }
    await api("/rest/v1/spots", {
      method: "POST",
      headers: { Prefer: "return=minimal" },
      body: JSON.stringify({
        name: s.name,
        description: s.description,
        location: `SRID=4326;POINT(${s.lng} ${s.lat})`,
        difficulty: s.difficulty,
        water: s.water,
        status: "verified",
        submitted_by: adminId,
        verified_by: adminId,
        verified_at: new Date().toISOString(),
      }),
    });
    console.log(`Inserted spot "${s.name}" (verified).`);
  }
}

const adminId = await ensureAdmin();
await promoteToAdmin(adminId);
await seedSpots(adminId);
console.log("Seed complete.");
