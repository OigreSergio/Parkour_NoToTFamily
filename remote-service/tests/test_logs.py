"""I log: dati personali mascherati, formato JSON, stdout lasciato ai dati."""

import json
import logging

import pytest

from pkremote.logs import bind_request, clear_request, configure_logging, log


@pytest.mark.parametrize("log_format", ["json", "console"])
def test_personal_data_is_masked(capsys: pytest.CaptureFixture[str], log_format: str) -> None:
    configure_logging(log_format=log_format, debug=False)
    log.info(
        "prova",
        lat=41.9028,
        lng=12.4964,
        email="qualcuno@esempio.it",
        authorization="Bearer segreto",
        apikey="chiave",
        elapsed_ms=3,
    )
    captured = capsys.readouterr()
    assert captured.out == ""  # stdout resta ai dati
    assert "41.9028" not in captured.err
    assert "12.4964" not in captured.err
    assert "esempio.it" not in captured.err
    assert "segreto" not in captured.err
    assert "chiave" not in captured.err
    assert "[omesso]" in captured.err
    assert "elapsed_ms" in captured.err


def test_json_format_emits_one_json_object_per_line(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(log_format="json", debug=False)
    log.info("evento_di_prova", numero=1)
    line = capsys.readouterr().err.strip().splitlines()[-1]
    record = json.loads(line)
    assert record["event"] == "evento_di_prova"
    assert record["numero"] == 1
    assert record["level"] == "info"
    assert record["timestamp"].endswith("Z")


def test_bound_request_values_appear_in_every_event(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(log_format="json", debug=False)
    bind_request(request_id="abc123", method="GET", path="/healthz")
    log.info("dentro")
    clear_request()
    log.info("fuori")
    lines = [json.loads(line) for line in capsys.readouterr().err.strip().splitlines()]
    assert lines[-2]["request_id"] == "abc123"
    assert lines[-2]["path"] == "/healthz"
    assert "request_id" not in lines[-1]


def test_standard_logging_goes_through_the_same_formatter(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Le righe di uvicorn (modulo logging) escono in JSON come le nostre."""
    configure_logging(log_format="json", debug=False)
    logging.getLogger("uvicorn.error").info("Started server process [%d]", 42)
    line = capsys.readouterr().err.strip().splitlines()[-1]
    record = json.loads(line)
    assert record["event"] == "Started server process [42]"
    assert record["logger"] == "uvicorn.error"


def test_exceptions_are_rendered_once(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(log_format="json", debug=False)
    try:
        raise ValueError("dettaglio")
    except ValueError:
        log.exception("errore_di_prova")
    err = capsys.readouterr().err
    assert err.count("ValueError: dettaglio") == 1
