"""Client verso i sistemi esterni. Uno per sistema, nessuna logica di prodotto.

- `supabase.py`: PostgREST del progetto Supabase (letture con la chiave
  pubblicabile, scritture solo con la chiave segreta e solo lato server);
- `osrm.py`: il motore dei percorsi (self-hosted in infra/routing o pubblico);
- `geo.py`: decodifica delle geometrie che PostGIS restituisce via REST.

Tutti ricevono un `httpx.AsyncClient` già creato dall'app (un solo pool di
connessioni per processo) e nei test un client con trasporto finto.
"""
