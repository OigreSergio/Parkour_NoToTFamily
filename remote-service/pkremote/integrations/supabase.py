"""Client minimo per PostgREST, l'API REST che Supabase mette davanti a Postgres.

Perché un client scritto a mano e non la libreria `supabase-py`: qui servono
due sole operazioni (verificare che il progetto risponda e leggere righe con
filtri) e un client di poche righe si legge, si prova con un trasporto finto e
non porta dipendenze. Quando serviranno RPC o scritture, si estende questo.

Le regole del masterplan che questo file rispetta:
- la chiave pubblicabile va bene ovunque: le policy RLS restano attive, quindi
  con essa il servizio vede solo ciò che vedrebbe un visitatore anonimo;
- la chiave segreta scavalca le RLS: oggi nessun job la usa, e `app.py` non
  costruisce mai questo client con lei. Quando servirà, il job che la richiede
  lo farà in modo esplicito e documentato.

Non ancora possibile, ed è il prossimo passo (analisi, cap. 9): agire per
conto di una persona. Servirebbe `apikey: <pubblicabile>` più
`Authorization: Bearer <JWT dell'utente>`, così PostgREST applica le RLS come
quell'utente (e il tetto dei contenuti della migrazione 0003 scatta).

Attenzione a `select=*`: la migrazione 0003 revoca alcune colonne per
`member_profiles` ed `experience_quiz_attempts`; su quelle tabelle va chiesto
un elenco di colonne, altrimenti PostgREST rifiuta l'intera richiesta.
"""

from typing import Any

import httpx
from pydantic import SecretStr

from pkremote.errors import UpstreamError


class SupabaseClient:
    def __init__(self, *, url: str, key: SecretStr, role: str, http: httpx.AsyncClient) -> None:
        """`role` è solo un'etichetta ("publishable" o "secret") per log e diagnostica."""
        self._url = url.rstrip("/")
        self.role = role
        self._http = http
        # PostgREST vuole la chiave in due intestazioni. Il valore viene letto
        # una volta qui e non conservato altrove.
        secret = key.get_secret_value()
        self._headers = {"apikey": secret, "Authorization": f"Bearer {secret}"}

    def __repr__(self) -> str:
        # Mai la chiave: questo repr può finire in un log.
        return f"SupabaseClient(url={self._url!r}, role={self.role!r})"

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, str] | None,
        headers: dict[str, str],
        timeout_seconds: float | None,
    ) -> httpx.Response:
        options: dict[str, Any] = (
            {"timeout": timeout_seconds} if timeout_seconds is not None else {}
        )
        try:
            return await self._http.get(
                f"{self._url}{path}", params=params or {}, headers=headers, **options
            )
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Supabase non raggiungibile: {exc.__class__.__name__}") from exc

    async def ping(self, *, timeout_seconds: float | None = None) -> None:
        """Una lettura minima (`spots`, una riga, solo `id`): se risponde 200 il
        progetto esiste, la chiave è accettata e le RLS lasciano leggere. È più
        leggera dello schema OpenAPI di `/rest/v1/`, che pesa centinaia di kB."""
        response = await self._get(
            "/rest/v1/spots",
            params={"select": "id", "limit": "1"},
            headers=self._headers,
            timeout_seconds=timeout_seconds,
        )
        if response.status_code != 200:
            raise UpstreamError(f"Supabase risponde {response.status_code}")

    async def select(self, table: str, *, params: dict[str, str] | None = None) -> Any:
        """Legge righe da `table` con i filtri PostgREST passati in `params`.

        Esempi di `params`: `{"select": "id,name", "status": "eq.verified",
        "order": "name.asc", "limit": "100"}`. Restituisce al massimo una
        pagina (il limite lo decide il progetto, di solito 1000 righe): per
        tutto usare `select_all`.
        """
        response = await self._get(
            f"/rest/v1/{table}", params=params, headers=self._headers, timeout_seconds=None
        )
        if response.status_code // 100 != 2:
            raise UpstreamError(f"Supabase risponde {response.status_code} su {table}")
        return response.json()

    async def select_all(
        self, table: str, *, params: dict[str, str] | None = None, page_size: int = 1000
    ) -> list[dict[str, Any]]:
        """Come `select`, ma legge tutte le righe a pagine.

        La paginazione usa l'intestazione `Range: inizio-fine`, la stessa
        tecnica di `📲/backup.mjs`. Il passo successivo parte da quante righe
        sono arrivate davvero, non da `page_size`: se il progetto ha un limite
        più basso (per esempio 100 righe per richiesta), le pagine sono più
        corte ma nessuna riga viene saltata. Si smette quando arriva una
        pagina vuota o un 416 ("oltre l'ultima riga"). Un server che ignora
        `Range` restituirebbe la stessa pagina per sempre: viene riconosciuto
        e segnalato come errore invece di girare all'infinito.

        Chi chiama deve passare un `order` su una colonna univoca (o che
        finisca con `id.asc`): senza ordine stabile due pagine possono
        sovrapporsi o lasciare buchi.
        """
        rows: list[dict[str, Any]] = []
        start = 0
        previous: list[dict[str, Any]] | None = None
        while True:
            headers = {**self._headers, "Range": f"{start}-{start + page_size - 1}"}
            response = await self._get(
                f"/rest/v1/{table}", params=params, headers=headers, timeout_seconds=None
            )
            if response.status_code == 416:  # oltre l'ultima riga: finito
                break
            if response.status_code // 100 != 2:
                raise UpstreamError(f"Supabase risponde {response.status_code} su {table}")
            chunk = response.json()
            if not isinstance(chunk, list):
                raise UpstreamError(f"Supabase: risposta inattesa su {table} (non è una lista)")
            if not chunk:
                break
            if chunk == previous:
                raise UpstreamError(f"Supabase ignora l'intestazione Range su {table}")
            rows.extend(chunk)
            start += len(chunk)
            previous = chunk
        return rows
