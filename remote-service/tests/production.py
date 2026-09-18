"""Una configurazione di produzione corretta, condivisa dai test.

I test tolgono o cambiano un pezzo alla volta per provare i controlli di
`config.py`; le rotte la usano per provare il comportamento in produzione
(HSTS, documentazione spenta).
"""

PRODUCTION = {
    "env": "production",
    "host": "0.0.0.0",  # noqa: S104 - è proprio ciò che un container deve fare
    "cors_origins": ["https://oigresergio.github.io"],
    "log_format": "json",
}
