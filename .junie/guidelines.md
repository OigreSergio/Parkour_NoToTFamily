# Linee guida per Junie

Le istruzioni complete sono in `AGENTS.md` alla radice del repository: leggilo
per intero prima di qualsiasi modifica. In sintesi:

1. Il codice Python vivo è in `remote-service/` (pacchetto `pkremote`). Non
   estendere `backend/`, non toccare `gh-pages`, le migrazioni consegnate e
   i segreti.
2. Identificatori e stati in inglese; commenti, docstring, log e messaggi in
   italiano, con una docstring in testa a ogni modulo.
3. Nessun segreto, nessun contenuto finto, nessuna coordinata nei log.
4. Prima di consegnare: `cd remote-service && ruff check . && pytest` (le
   configurazioni "pkremote: lint" e "pkremote: test" in `.run/` fanno lo
   stesso da PyCharm).
5. Chiudi ogni consegna con la nota `FATTO / VERIFICATO / NON FATTO /
   RISCHI E DECISIONI APERTE / DIVERGENZE TROVATE`.
