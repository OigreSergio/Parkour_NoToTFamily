#!/usr/bin/env node
// ============================================================================
// Parkour NoToT Family — immagini degli spot verso il database reale
//
// Popola le anteprime/foto di contesto degli spot verificati usando i dati
// generati in docs/demo/spots-streetview.json (miniatura Street View puntata
// sullo spot) più le foto curate a mano (Wikimedia Commons / Flickr, licenza
// verificata). Gli spot sono agganciati per UUID reale, preso dal backup.
//
// Il DB di produzione non ha ancora lo schema esportato nel repo, quindi lo
// script NON dà nulla per scontato: legge l'OpenAPI di PostgREST e decide da
// solo dove scrivere:
//   1. se esiste `spot_photos` con una colonna URL → inserisce lì (idempotente);
//   2. altrimenti, se `spots` ha `photo_urls` (array) → aggiorna quella;
//   3. altrimenti si ferma e spiega cosa manca, senza toccare nulla.
//
// Uso:
//   SUPABASE_URL=https://<ref>.supabase.co \
//   SUPABASE_SECRET_KEY=sb_secret_... \
//   node supabase/seed/seed-spot-images.mjs          # aggiungere --dry-run per provare
// ============================================================================

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const url = process.env.SUPABASE_URL?.replace(/\/$/, "");
const key = process.env.SUPABASE_SECRET_KEY;
const dryRun = process.argv.includes("--dry-run");
if (!url || !key) {
  console.error("Imposta SUPABASE_URL e SUPABASE_SECRET_KEY");
  process.exit(1);
}

const headers = {
  apikey: key,
  Authorization: `Bearer ${key}`,
  "Content-Type": "application/json",
};

async function api(path, init = {}) {
  const res = await fetch(`${url}${path}`, { ...init, headers: { ...headers, ...init.headers } });
  const text = await res.text();
  if (!res.ok) throw new Error(`${init.method ?? "GET"} ${path} → ${res.status}: ${text}`);
  return text ? JSON.parse(text) : null;
}

// --- dati locali -----------------------------------------------------------

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const streetview = JSON.parse(
  readFileSync(join(repoRoot, "docs", "demo", "spots-streetview.json"), "utf8"),
);

// Foto di contesto curate a mano (stesse della pagina demo, licenza verificata).
const CURATED = {
  "Foro Italico — Stadio dei Marmi":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Stadio_dei_marmi_009.jpg/960px-Stadio_dei_marmi_009.jpg",
  "EUR Laghetto":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Roma_EUR_Laghetto_vista_dal_basso.jpg/960px-Roma_EUR_Laghetto_vista_dal_basso.jpg",
  "Colle Oppio Park":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Parco_Del_Colle_Oppio_-_panoramio.jpg/960px-Parco_Del_Colle_Oppio_-_panoramio.jpg",
  "Villa Borghese — Piazza di Siena":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/Plaza_de_Siena%2C_Villa_Borghese%2C_Roma%2C_Italia%2C_2022-09-14%2C_DD_14.jpg/960px-Plaza_de_Siena%2C_Villa_Borghese%2C_Roma%2C_Italia%2C_2022-09-14%2C_DD_14.jpg",
  "Spot Colonne Colosseo":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Colonne_Tempio_Venere_Colosseo_Roma_09feb08.jpg/960px-Colonne_Tempio_Venere_Colosseo_Roma_09feb08.jpg",
  "Garbatella — Scalinate": "https://live.staticflickr.com/34/72998499_c2311608eb_b.jpg",
  "Spot Metro Colosseo":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Colosseo_-_panoramio_%2810%29.jpg/960px-Colosseo_-_panoramio_%2810%29.jpg",
  "Spot EUR":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bd/2024-05-06-Palazzo-dello-Sport-2.jpg/960px-2024-05-06-Palazzo-dello-Sport-2.jpg",
  "Spot Corviale 1":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Corviale_%285582072620%29.jpg/960px-Corviale_%285582072620%29.jpg",
  "Spot Corviale 2":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Municipio_XI_%28Roma%29_in_2020.03.jpg/960px-Municipio_XI_%28Roma%29_in_2020.03.jpg",
  "Spot Corviale 3":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Municipio_XI_%28Roma%29_in_2020.02.jpg/960px-Municipio_XI_%28Roma%29_in_2020.02.jpg",
  "Spot Primavalle":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Largo_borromeo_primavalle_roma.jpg/960px-Largo_borromeo_primavalle_roma.jpg",
  "Spot Villa Carpegna":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Roma_-_Villa_Carpegna_innevata_-_panoramio.jpg/960px-Roma_-_Villa_Carpegna_innevata_-_panoramio.jpg",
  "Spot Colosseo — Monte Oppio":
    "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Parc_Colle_Oppio_-_Rome_%28IT62%29_-_2021-08-29_-_1.jpg/960px-Parc_Colle_Oppio_-_Rome_%28IT62%29_-_2021-08-29_-_1.jpg",
};

function streetviewThumb(sv) {
  return (
    "https://streetviewpixels-pa.googleapis.com/v1/thumbnail" +
    `?panoid=${encodeURIComponent(sv.pano_id)}&cb_client=maps_sv.tactile.gps` +
    `&w=640&h=360&yaw=${sv.yaw}&pitch=0&thumbfov=100`
  );
}

/** Per ogni spot: [preview Street View, eventuale foto di contesto]. */
function imagesFor(spot) {
  const imgs = [];
  if (spot.streetview) imgs.push(streetviewThumb(spot.streetview));
  if (CURATED[spot.name]) imgs.push(CURATED[spot.name]);
  return imgs;
}

// --- introspezione schema --------------------------------------------------

async function loadSchema() {
  const openapi = await api("/rest/v1/");
  const defs = openapi.definitions ?? {};
  return {
    columnsOf: (table) => Object.keys(defs[table]?.properties ?? {}),
    has: (table) => Boolean(defs[table]),
  };
}

const URL_COLUMNS = ["url", "photo_url", "image_url", "src"];

async function main() {
  const schema = await loadSchema();

  if (schema.has("spot_photos")) {
    const cols = schema.columnsOf("spot_photos");
    const urlCol = URL_COLUMNS.find((c) => cols.includes(c));
    if (urlCol && cols.includes("spot_id")) {
      return seedSpotPhotos(urlCol, cols.includes("position"));
    }
    console.error(
      `spot_photos esiste ma non ho riconosciuto le colonne (${cols.join(", ")}); mi fermo.`,
    );
    process.exit(1);
  }

  if (schema.columnsOf("spots").includes("photo_urls")) {
    return seedPhotoUrlsArray();
  }

  console.error(
    "Né spot_photos né spots.photo_urls trovati nello schema esposto: niente da fare.\n" +
      "Esporta lo schema di produzione (TODO in 📲/README.md) e riprova.",
  );
  process.exit(1);
}

async function seedSpotPhotos(urlCol, hasPosition) {
  for (const spot of streetview.spots) {
    const imgs = imagesFor(spot);
    if (!imgs.length) continue;
    const existing = await api(
      `/rest/v1/spot_photos?spot_id=eq.${spot.id}&select=${urlCol}`,
    );
    const have = new Set(existing.map((r) => r[urlCol]));
    // la scheda dell'app ordina per position: le seed partono dopo le esistenti
    let position = existing.length;
    for (const img of imgs) {
      if (have.has(img)) {
        console.log(`= ${spot.name}: già presente (${img.slice(0, 60)}…)`);
        continue;
      }
      if (dryRun) {
        console.log(`~ ${spot.name}: inserirei ${img.slice(0, 80)}`);
        continue;
      }
      const row = { spot_id: spot.id, [urlCol]: img };
      if (hasPosition) row.position = position++;
      await api("/rest/v1/spot_photos", {
        method: "POST",
        headers: { Prefer: "return=minimal" },
        body: JSON.stringify(row),
      });
      console.log(`+ ${spot.name}: foto aggiunta (${img.slice(0, 60)}…)`);
    }
  }
  console.log("Seed spot_photos completato.");
}

async function seedPhotoUrlsArray() {
  for (const spot of streetview.spots) {
    const imgs = imagesFor(spot);
    if (!imgs.length) continue;
    const rows = await api(`/rest/v1/spots?id=eq.${spot.id}&select=photo_urls`);
    if (!rows.length) {
      console.log(`? ${spot.name}: id non trovato nel DB — salto.`);
      continue;
    }
    const current = rows[0].photo_urls ?? [];
    const merged = [...current, ...imgs.filter((i) => !current.includes(i))];
    if (merged.length === current.length) {
      console.log(`= ${spot.name}: già completo.`);
      continue;
    }
    if (dryRun) {
      console.log(`~ ${spot.name}: photo_urls ${current.length} → ${merged.length}`);
      continue;
    }
    await api(`/rest/v1/spots?id=eq.${spot.id}`, {
      method: "PATCH",
      headers: { Prefer: "return=minimal" },
      body: JSON.stringify({ photo_urls: merged }),
    });
    console.log(`+ ${spot.name}: photo_urls ${current.length} → ${merged.length}`);
  }
  console.log("Seed spots.photo_urls completato.");
}

await main();
