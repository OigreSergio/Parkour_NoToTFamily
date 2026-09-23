"""Client minimo per PostgREST, l'API REST che Supabase mette davanti a Postgres.

Perché un client scritto a mano e non la libreria `supabase-py`: qui servono
due sole operazioni (verificare che il progetto risponda e leggere righe con
filtri) e un client di poche righe si legge, si prova con un trasporto finto e
non porta dipendenze. Quando serviranno RPC o scritture, si estende questo.

Le regole del masterplan che questo file rispetta:
- la chiave pubblicabile va bene ovunque: le policy RLS restano attive, quindi
  con essa il servizio vede solo ciò che vedrebbe un visitatore anonimo;
- la chiave segreta scavalca le RLS: oggi nessun job la usa, e `from_settings`
  non costruisce mai il client con lei. Quando servirà, il job che la richiede
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

from pkremote.config import Settings
from pkremote.errors import UpstreamError
from pkremote.integrations.http import fetch
from pkremote.logs import log


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

    @classmethod
    def from_settings(cls, settings: Settings, http: httpx.AsyncClient) -> SupabaseClient | None:
        """Il client di lettura, o None se la configurazione non lo permette.

        Nasce solo dalla chiave pubblicabile: con le RLS attive vede solo dati
        pubblici, che per le letture è esattamente ciò che vogliamo. La chiave
        segreta non è mai un ripiego: se è l'unica presente, il servizio lo
        dice nel log e resta senza Supabase.
        """
        if not settings.supabase_configured:
            if settings.supabase_url is not None and settings.supabase_secret_key is not None:
                log.warning(
                    "supabase_lettura_disattivata",
                    motivo="manca SUPABASE_PUBLISHABLE_KEY: la segreta non serve a leggere",
                )
            return None
        assert settings.supabase_url is not None  # garantiti da supabase_configured
        assert settings.supabase_publishable_key is not None
        return cls(
            url=settings.supabase_url,
            key=settings.supabase_publishable_key,
            role="publishable",
            http=http,
        )

    def __repr__(self) -> str:
        # Mai la chiave: questo repr può finire in un log.
        return f"SupabaseClient(url={self._url!r}, role={self.role!r})"

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> httpx.Response:
        return await fetch(
            self._http,
            f"{self._url}{path}",
            service="Supabase",
            params=params,
            headers={**self._headers, **(extra_headers or {})},
            timeout_seconds=timeout_seconds,
        )

    @staticmethod
    def _rows(response: httpx.Response, table: str) -> list[dict[str, Any]]:
        """Il corpo di una risposta a una lettura, o `UpstreamError` se non è quello atteso."""
        if response.status_code // 100 != 2:
            raise UpstreamError(f"Supabase risponde {response.status_code} su {table}")
        try:
            body = response.json()
        except ValueError as exc:  # un proxy davanti a Supabase che risponde HTML
            raise UpstreamError(f"Supabase: risposta non JSON su {table}") from exc
        if not isinstance(body, list):
            raise UpstreamError(f"Supabase: risposta inattesa su {table} (non è una lista)")
        return body

    async def ping(self, *, timeout_seconds: float | None = None) -> None:
        """Una lettura minima (`spots`, una riga, solo `id`): se risponde 200 il
        progetto esiste, la chiave è accettata e le RLS lasciano leggere. È più
        leggera dello schema OpenAPI di `/rest/v1/`, che pesa centinaia di kB."""
        response = await self._get(
            "/rest/v1/spots", params={"select": "id", "limit": "1"}, timeout_seconds=timeout_seconds
        )
        if response.status_code != 200:
            raise UpstreamError(f"Supabase risponde {response.status_code}")

    async def select(
        self, table: str, *, params: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        """Legge righe da `table` con i filtri PostgREST passati in `params`.

        Esempi di `params`: `{"select": "id,name", "status": "eq.verified",
        "order": "name.asc", "limit": "100"}`. Restituisce al massimo una
        pagina (il limite lo decide il progetto, di solito 1000 righe): per
        tutto usare `select_all`.
        """
        return self._rows(await self._get(f"/rest/v1/{table}", params=params), table)

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
            response = await self._get(
                f"/rest/v1/{table}",
                params=params,
                extra_headers={"Range": f"{start}-{start + page_size - 1}"},
            )
            if response.status_code == 416:  # oltre l'ultima riga: finito
                break
            chunk = self._rows(response, table)
            if not chunk:
                break
            if chunk == previous:
                raise UpstreamError(f"Supabase ignora l'intestazione Range su {table}")
            rows.extend(chunk)
            start += len(chunk)
            previous = chunk
        return rows
