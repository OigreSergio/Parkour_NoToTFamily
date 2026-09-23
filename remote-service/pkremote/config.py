"""Configurazione del servizio: tutto arriva dalle variabili d'ambiente.

Perché dalle variabili d'ambiente e non da un file nel repository:

- in remoto (container su un cloud, macchina virtuale, GitHub Actions) è il
  modo standard di passare configurazione e segreti senza scriverli nel codice;
- lo stesso pacchetto gira identico in locale e in remoto: cambia solo ciò che
  l'ambiente gli passa (è il principio "12-factor");
- i segreti (chiave segreta Supabase, token dei job) non finiscono mai nel
  repository, come chiede il masterplan (cap. 2 regola 4, cap. 6.5).

In locale si può usare un file `.env` (copiato da `.env.example`): viene letto
solo se esiste, ed è escluso da git.

I nomi delle variabili sono quelli dei campi in maiuscolo: il campo `host` si
imposta con `HOST`, `supabase_url` con `SUPABASE_URL`, e così via.
"""

from functools import cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Valori che non devono mai arrivare in produzione: se un segreto è uno di
# questi, il servizio rifiuta di partire invece di girare "quasi" configurato.
PLACEHOLDER_SECRETS = {"", "change-me", "cambiami", "xxx", "todo"}

#: Il router pedonale pubblico di FOSSGIS: a uso equo per i client, non per un proxy.
PUBLIC_ROUTER_HOST = "routing.openstreetmap.de"


class Settings(BaseSettings):
    """Tutti i parametri del servizio, con i valori per lo sviluppo locale."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Identità dell'ambiente -------------------------------------------------
    #: Decide i controlli di sicurezza: in `production` scattano quelli sotto.
    #: Si chiama APP_ENV e non ENV perché `ENV` è una variabile che la shell
    #: POSIX riserva al proprio file di avvio: su alcune immagini è già
    #: impostata e il servizio si rifiuterebbe di partire senza motivo.
    app_env: Literal["development", "test", "production"] = "development"
    #: Con `debug` le risposte d'errore sono più parlanti e i log più verbosi.
    debug: bool = False
    #: Nome libero dell'istanza (es. "fly-ams", "render-eu"): compare nei log e in /healthz.
    instance_name: str = "locale"

    # --- Rete: dove ascolta il server HTTP ------------------------------------------
    #: In remoto DEVE essere "0.0.0.0" (o "::" per IPv6): tutte le interfacce, perché
    #: il traffico arriva dal bilanciatore del provider, non da localhost. Con
    #: 127.0.0.1 il container parte ma nessuna richiesta lo raggiunge, ed è
    #: l'errore più difficile da vedere.
    host: str = "127.0.0.1"
    #: Molti provider (Render, Fly, Heroku, Railway) impongono la porta con `PORT`:
    #: il nome del campo è scelto apposta per leggerla senza altre configurazioni.
    port: int = Field(default=8080, ge=1, le=65535)
    #: Origini del browser autorizzate a chiamare l'API (CORS). Stringa separata da
    #: virgola nell'ambiente, lista qui dentro. `NoDecode` evita che pydantic provi
    #: a interpretarla come JSON prima del nostro validatore.
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    #: Il provider termina il TLS e inoltra al servizio in HTTP aggiungendo le
    #: intestazioni X-Forwarded-*: con `True` uvicorn le usa per ricostruire lo
    #: schema (https) e l'indirizzo del chiamante.
    proxy_headers: bool = True
    #: Da quali indirizzi accettare quelle intestazioni. In locale solo il proxy
    #: sulla stessa macchina; su un PaaS in cui il container è raggiungibile solo
    #: dal proxy della piattaforma si mette "*". Fidarsi di chiunque quando la
    #: porta è esposta direttamente permetterebbe a un client di falsificare
    #: schema e indirizzo.
    forwarded_allow_ips: str = "127.0.0.1"

    # --- Supabase (backend di produzione, masterplan 4.2) --------------------------
    #: URL del progetto, es. https://<ref>.supabase.co (senza barra finale).
    supabase_url: str | None = None
    #: Chiave pubblicabile: fatta per i client, le policy RLS restano attive. È
    #: l'unica chiave con cui il servizio legge. `SecretStr` la maschera in log,
    #: repr e dump: si legge solo con `.get_secret_value()`, e solo dove serve.
    supabase_publishable_key: SecretStr | None = None
    #: Chiave segreta: scavalca le RLS. Nessun job la usa oggi: viene letta e
    #: mascherata perché, quando un job privilegiato esisterà, la chiederà in modo
    #: esplicito. Non è mai il ripiego per le letture: senza chiave pubblicabile
    #: il servizio non legge Supabase affatto.
    supabase_secret_key: SecretStr | None = None
    #: Tempo massimo per ogni chiamata HTTP in uscita (Supabase, OSRM).
    http_timeout_seconds: float = Field(default=10.0, gt=0)
    #: Tempo massimo per ciascun controllo di /readyz: un bilanciatore che aspetta
    #: dieci secondi per sapere se l'istanza è pronta la considera già morta.
    ready_timeout_seconds: float = Field(default=3.0, gt=0)
    #: Per quanti secondi /readyz riusa l'ultimo esito invece di interrogare di
    #: nuovo Supabase e OSRM: un bilanciatore che sonda ogni 10 s non deve costare
    #: una chiamata a Supabase ogni 10 s. 0 = nessuna cache.
    ready_cache_seconds: int = Field(default=10, ge=0)

    # --- Percorsi: proxy con cache verso OSRM (docs/ROUTING_PK.md, fase 2) --------
    #: URL del motore OSRM (es. http://osrm:5000). Vuoto = proxy disattivato:
    #: la rotta risponde 503 e i client usano il loro fallback in linea d'aria.
    osrm_base_url: str | None = None
    #: Profilo OSRM da usare: "foot" standard, "pk_foot" quando esisterà (fase 2).
    osrm_profile: str = "foot"
    #: Durata di una risposta in cache e numero massimo di voci in memoria.
    route_cache_ttl_seconds: int = Field(default=3600, ge=1)
    route_cache_max_entries: int = Field(default=5000, ge=1)
    #: Cifre decimali tenute nelle coordinate ricevute: 3 decimali sono circa
    #: 111 metri. È la misura di privacy del masterplan (cap. 6.4): il servizio
    #: riceve la posizione precisa nella query string, la arrotonda subito e da
    #: quel momento non la usa, non la mette in cache e non la scrive nei log.
    coordinate_decimals: int = Field(default=3, ge=0, le=6)

    # --- Job ---------------------------------------------------------------------------
    #: Token per lanciare i job via HTTP. Vuoto = i job si lanciano solo da CLI.
    job_token: SecretStr | None = None
    #: Cartella in cui i job scrivono i risultati (creata se manca).
    jobs_output_dir: Path = Path("./output")

    # --- Log ---------------------------------------------------------------------------
    #: "json" in remoto (i provider lo indicizzano), "console" per leggere a occhio.
    log_format: Literal["json", "console"] = "json"

    # --- Normalizzazioni ---------------------------------------------------------------

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """`CORS_ORIGINS=http://a,http://b` diventa `["http://a", "http://b"]`."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("supabase_url", "osrm_base_url", mode="before")
    @classmethod
    def _clean_url(cls, value: object) -> object:
        """Stringa vuota = non configurato; la barra finale viene tolta per
        poter concatenare i percorsi senza doppie barre."""
        if isinstance(value, str):
            value = value.strip().rstrip("/")
            return value or None
        return value

    @field_validator("osrm_base_url")
    @classmethod
    def _never_the_public_router(cls, value: str | None) -> str | None:
        """Il server pubblico FOSSGIS è a uso equo per i client, non per un proxy:
        metterlo qui trasformerebbe il servizio in un relay anonimo a spese di
        altri (docs/ROUTING_PK.md, fase 1). Il proxy esiste per l'OSRM proprio."""
        if value is not None and PUBLIC_ROUTER_HOST in value:
            raise ValueError(
                f"OSRM_BASE_URL non può puntare al server pubblico {PUBLIC_ROUTER_HOST}: "
                "il proxy serve per un OSRM proprio (infra/routing)"
            )
        return value

    @field_validator("supabase_publishable_key", "supabase_secret_key", "job_token", mode="before")
    @classmethod
    def _empty_secret_is_none(cls, value: object) -> object:
        """Una variabile presente ma vuota (`JOB_TOKEN=`) vale come assente."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    # --- Controlli che valgono solo in produzione -----------------------------------

    @model_validator(mode="after")
    def _production_guardrails(self) -> Settings:
        """In produzione il servizio si rifiuta di partire con una configurazione
        che "sembra" funzionare ma espone dati o non riceve traffico.

        Ogni controllo corrisponde a un errore visto davvero in progetti simili;
        il messaggio dice cosa correggere, mai il valore ricevuto.
        """
        if self.app_env != "production":
            return self
        problems: list[str] = []
        if self.debug:
            problems.append("DEBUG deve essere false in produzione")
        if self.host not in {"0.0.0.0", "::"}:  # noqa: S104 - in un container è la scelta corretta
            problems.append(
                "HOST deve essere 0.0.0.0 (o ::) in produzione, altrimenti il traffico non arriva"
            )
        if not self.cors_origins:
            problems.append("CORS_ORIGINS non può essere vuoto in produzione")
        if "*" in self.cors_origins:
            problems.append('CORS_ORIGINS non può contenere "*" in produzione')
        if self.log_format != "json":
            problems.append("LOG_FORMAT deve essere json in produzione")
        if self.supabase_url is not None and not self.supabase_url.startswith("https://"):
            problems.append(
                "SUPABASE_URL deve essere https:// in produzione "
                "(la chiave viaggia nell'intestazione)"
            )
        if self.supabase_secret_key is not None and self.supabase_publishable_key is None:
            problems.append(
                "SUPABASE_SECRET_KEY senza SUPABASE_PUBLISHABLE_KEY: la segreta non serve a leggere"
            )
        for name, secret in (
            ("SUPABASE_SECRET_KEY", self.supabase_secret_key),
            ("SUPABASE_PUBLISHABLE_KEY", self.supabase_publishable_key),
            ("JOB_TOKEN", self.job_token),
        ):
            value = secret.get_secret_value().strip().lower() if secret is not None else None
            if value is not None and value in PLACEHOLDER_SECRETS:
                problems.append(f"{name} ha un valore segnaposto")
        if self.job_token is not None and len(self.job_token.get_secret_value()) < 24:
            problems.append("JOB_TOKEN è troppo corto (minimo 24 caratteri)")
        if problems:
            raise ValueError("configurazione non valida per la produzione: " + "; ".join(problems))
        return self

    # --- Comodità di lettura ---------------------------------------------------------------

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def supabase_configured(self) -> bool:
        """Letture possibili: servono l'URL e la chiave pubblicabile (non la segreta)."""
        return self.supabase_url is not None and self.supabase_publishable_key is not None

    @property
    def osrm_configured(self) -> bool:
        return self.osrm_base_url is not None

    @property
    def jobs_http_enabled(self) -> bool:
        return self.job_token is not None


@cache
def get_settings() -> Settings:
    """Legge la configurazione una volta sola per processo.

    Nei test non si usa: si costruisce `Settings(_env_file=None, ...)` a mano e
    la si passa a `create_app`, così ogni test ha la configurazione che vuole.
    """
    return Settings()
