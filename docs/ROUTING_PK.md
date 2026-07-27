# Percorsi PK — distanza e spostamento urbano verso gli spot

Obiettivo: dallo spot selezionato l'utente vede quanto dista e come
raggiungerlo, sia in modo classico (Google Maps) sia con un percorso da
spostamento urbano — scale, vicoli, ponti pedonali, attraversamenti dei
parchi — nello spirito degli street run alla Storror.

## Fase 1 — attiva ora (nessuna infrastruttura)

Implementata in `scripts/web/pk-route.js` + patch del bundle
(`scripts/patch-gh-pages-test-free.py`):

- **Distanza live** dalla posizione GPS (haversine) con ETA a piedi
  (4,5 km/h) e di corsa (9 km/h).
- **🥾 Percorso PK**: routing **pedonale** OSRM sul server pubblico FOSSGIS
  (`routing.openstreetmap.de/routed-foot`), disegnato sulla mappa. Il
  profilo pedonale passa già da scalinate, sentieri, aree pedonali e parchi
  — percorsi che le indicazioni in auto non prenderebbero mai.
- **🗺️ Google Maps**: deep link con navigazione a piedi, per chi vuole il
  percorso classico.

Limiti della fase 1: server pubblico condiviso (fair-use, nessuna garanzia
di uptime) e profilo pedonale *standard*: preferisce il percorso più corto
a piedi, senza pesi parkour.

## Fase 2 — routing PK self-hosted (l'infrastruttura da creare)

Un'istanza OSRM nostra con profilo pedonale modificato in ottica parkour.
Setup in `infra/routing/` (docker compose + istruzioni). In sintesi:

1. Estratto OSM di Roma (Geofabrik, ~400 MB) preprocessato con il profilo.
2. Profilo `pk_foot.lua` = `foot.lua` di OSRM con questi pesi modificati:
   - **bonus** (rate più alto): `steps` (scalinate), `path`, `pedestrian`,
     `footway`, `track`, attraversamento aree `leisure=park`;
   - **malus**: strade con traffico (`primary`, `secondary` senza
     marciapiede), lungo-strada monotoni;
   - opzionale: bonus per vie con `barrier=wall/fence` basse mappate — dove
     l'ambiente urbano offre linee.
3. Il backend FastAPI espone `GET /api/v1/route?from=..&to=..&profile=pk`
   come proxy con cache (Redis) verso OSRM, e `pk-route.js` punta lì.

Costo: ~1 GB RAM per l'istanza OSRM su Roma, rigenerazione dati mensile.

## Fase 3 — idee successive

- Percorsi multi-spot ("line" di allenamento: casa → spot A → spot B).
- Tempi personalizzati sul passo reale dell'utente.
- Segnalazione community di scorciatoie non mappate su OSM (e contributo a
  OSM stesso).
