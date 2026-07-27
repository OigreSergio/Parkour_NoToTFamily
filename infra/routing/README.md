# OSRM self-hosted per i percorsi PK (fase 2)

Istanza OSRM con profilo pedonale in ottica parkour (vedi
`docs/ROUTING_PK.md`). Primo avvio con il profilo `foot` standard:

```sh
cd infra/routing
# 1. dati OSM del Lazio (contengono Roma)
curl -LO https://download.geofabrik.de/europe/italy/centro-latest.osm.pbf

# 2. profilo: estrai foot.lua dall'immagine (base per pk_foot.lua)
docker run --rm --entrypoint cat ghcr.io/project-osrm/osrm-backend:latest \
  /opt/foot.lua > pk_foot.lua
#    ...poi applica i pesi PK descritti in docs/ROUTING_PK.md §2

# 3. preprocessing (una tantum, ~10 min)
docker compose -f docker-compose.osrm.yml run --rm osrm-prepare

# 4. avvio del router su :5000
docker compose -f docker-compose.osrm.yml up -d osrm-pk
curl 'http://localhost:5000/route/v1/foot/12.45,41.907;12.4966,41.8925?overview=false'
```

Quando il router è in produzione, cambiare `ROUTER` in
`scripts/web/pk-route.js` (o nel futuro proxy `/api/v1/route`).
