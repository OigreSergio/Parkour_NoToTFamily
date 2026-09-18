"""Cache in memoria con scadenza (TTL) e limite di voci.

Serve al proxy dei percorsi: lo stesso tragitto chiesto due volte non deve
costare due chiamate a OSRM. Sta in memoria per una ragione precisa: il
servizio deve poter girare in remoto **senza** provisionare Redis o un
database. Se un giorno gireranno più istanze e servirà una cache condivisa,
questa classe è l'unico punto da sostituire (stessa interfaccia `get`/`set`).

Regole:
- una voce scade dopo `ttl_seconds`;
- oltre `max_entries` viene scartata la voce usata meno di recente
  (politica LRU: `OrderedDict` sposta in fondo ciò che viene letto);
- l'accesso è protetto da un lock asincrono, perché più richieste possono
  arrivare nello stesso momento.
"""

import asyncio
import time
from collections import OrderedDict
from typing import Any


class TTLCache:
    def __init__(self, *, ttl_seconds: int, max_entries: int) -> None:
        if ttl_seconds <= 0 or max_entries <= 0:
            raise ValueError("ttl_seconds e max_entries devono essere positivi")
        self._ttl = ttl_seconds
        self._max = max_entries
        # chiave -> (istante di scadenza, valore)
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Any | None:
        """Il valore, se presente e non scaduto; altrimenti None."""
        async with self._lock:
            item = self._data.get(key)
            if item is None:
                self.misses += 1
                return None
            expires_at, value = item
            if expires_at <= time.monotonic():
                # Scaduto: lo togliamo adesso invece di aspettare la pulizia.
                del self._data[key]
                self.misses += 1
                return None
            self._data.move_to_end(key)  # appena usato = ultimo a essere scartato
            self.hits += 1
            return value

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            if key in self._data:
                del self._data[key]
            while len(self._data) >= self._max:
                self._data.popitem(last=False)  # il meno usato di recente
            self._data[key] = (time.monotonic() + self._ttl, value)

    def stats(self) -> dict[str, int]:
        """Numeri utili in /readyz e nei log: quante voci, quanti hit e miss."""
        return {"entries": len(self._data), "hits": self.hits, "misses": self.misses}
