"""La configurazione: valori di default, normalizzazioni, controlli di produzione."""

import pytest
from pydantic import ValidationError

from pkremote.config import Settings
from tests.production import PRODUCTION


def test_defaults_are_for_local_development() -> None:
    settings = Settings(_env_file=None)
    assert settings.env == "development"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8080
    assert not settings.supabase_configured
    assert not settings.osrm_configured
    assert not settings.jobs_http_enabled


def test_cors_origins_from_comma_separated_string() -> None:
    settings = Settings(_env_file=None, cors_origins="http://a, http://b ,")
    assert settings.cors_origins == ["http://a", "http://b"]


def test_cors_origins_are_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # Passa dalla sorgente "ambiente" di pydantic-settings, non dal kwarg: è il
    # caso in cui `NoDecode` serve davvero.
    monkeypatch.setenv("CORS_ORIGINS", "https://a, https://b ,")
    assert Settings(_env_file=None).cors_origins == ["https://a", "https://b"]


def test_urls_are_normalised() -> None:
    settings = Settings(_env_file=None, supabase_url="https://x.supabase.co/", osrm_base_url="  ")
    assert settings.supabase_url == "https://x.supabase.co"
    assert settings.osrm_base_url is None


def test_empty_secret_counts_as_absent() -> None:
    settings = Settings(_env_file=None, job_token="", supabase_secret_key="  ")
    assert settings.job_token is None
    assert settings.supabase_secret_key is None


def test_port_is_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # I provider impongono la porta con PORT: deve bastare quella.
    monkeypatch.setenv("PORT", "9999")
    assert Settings(_env_file=None).port == 9999


def test_public_router_is_refused_as_proxy_target() -> None:
    with pytest.raises(ValidationError, match=r"routing\.openstreetmap\.de"):
        Settings(_env_file=None, osrm_base_url="https://routing.openstreetmap.de/routed-foot")


@pytest.mark.parametrize(
    "broken",
    [
        {"route_cache_ttl_seconds": 0},
        {"route_cache_max_entries": 0},
        {"http_timeout_seconds": 0},
        {"ready_timeout_seconds": -1},
        {"ready_cache_seconds": -1},
        {"port": 0},
        {"port": 70000},
    ],
)
def test_out_of_range_values_are_rejected_at_configuration(broken: dict[str, object]) -> None:
    # Meglio un errore di configurazione subito che un crash nel lifespan.
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **broken)


def test_secret_key_alone_does_not_configure_supabase() -> None:
    settings = Settings(
        _env_file=None, supabase_url="https://x.supabase.co", supabase_secret_key="segreto-lungo"
    )
    assert settings.supabase_configured is False


def test_production_accepts_a_correct_configuration() -> None:
    settings = Settings(_env_file=None, **PRODUCTION, job_token="t" * 32)
    assert settings.is_production
    assert settings.jobs_http_enabled


def test_production_accepts_ipv6_any_host() -> None:
    settings = Settings(_env_file=None, **{**PRODUCTION, "host": "::"})
    assert settings.host == "::"


@pytest.mark.parametrize(
    "broken",
    [
        {"host": "127.0.0.1"},
        {"debug": True},
        {"cors_origins": []},
        {"cors_origins": ["*"]},
        {"log_format": "console"},
        {"job_token": "change-me"},
        {"job_token": "corto"},
        {"supabase_secret_key": "todo"},
        {"supabase_url": "http://x.supabase.co", "supabase_publishable_key": "sb_publishable_x"},
        {
            "supabase_url": "https://x.supabase.co",
            "supabase_secret_key": "segreto-lungo-abbastanza",
        },
    ],
)
def test_production_rejects_dangerous_configuration(broken: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{**PRODUCTION, **broken})


def test_secrets_never_appear_in_repr_or_dump() -> None:
    settings = Settings(
        _env_file=None,
        supabase_url="https://x.supabase.co",
        supabase_secret_key="segreto-esempio-finto-123",
        job_token="token-finto-lungo-abbastanza-si",
    )
    printed = repr(settings) + str(settings.model_dump())
    assert "esempio-finto" not in printed
    assert "token-finto" not in printed
