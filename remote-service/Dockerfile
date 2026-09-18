# Immagine del servizio remoto. Due stadi: nel primo si installa il pacchetto,
# nel secondo si copia solo il risultato, così l'immagine finale non contiene
# pip, cache o sorgenti superflui.
#
# Costruire e provare in locale:
#   docker build -t pkremote remote-service
#   docker run --rm -p 8080:8080 -e CORS_ORIGINS=http://localhost:8080 pkremote
#   curl http://localhost:8080/healthz
#
# In remoto la stessa immagine viene costruita dal workflow
# .github/workflows/remote-service.yml e pubblicata su GitHub Container Registry.

FROM python:3.14-slim AS build
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /src
COPY pyproject.toml ./
COPY pkremote ./pkremote
# `--prefix` installa in una cartella separata che il secondo stadio copia in blocco.
RUN pip install --prefix=/install .

FROM python:3.14-slim
# HOST=0.0.0.0 è obbligatorio in un container (vedi config.py); PORT resta
# sovrascrivibile dal provider; i log in JSON sono quelli che i provider indicizzano.
ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    LOG_FORMAT=json
# Il processo non gira come root: se qualcosa va storto, il danno resta contenuto.
RUN useradd --create-home --uid 10001 pkremote
COPY --from=build /install /usr/local
USER pkremote
WORKDIR /home/pkremote
EXPOSE 8080
# Il provider (o Docker stesso) chiama /healthz per sapere se il processo è vivo.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os, sys, urllib.request; r = urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT', '8080'), timeout=3); sys.exit(0 if r.status == 200 else 1)"
CMD ["pkremote", "serve"]
