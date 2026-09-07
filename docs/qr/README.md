# QR code — web app

Dal 1° settembre 2026 la web app (export Expo) è pubblicata sulla **root** di
`gh-pages` ed è pubblica: il QR da usare è `webapp-qr.png`. Il vecchio
percorso riservato `/t/2fe095ecfaa79a73/` dell'anteprima privata non esiste
più (vedi `docs/WEB_TEST_SPACE.md`).

| File | Punta a | Uso |
| --- | --- | --- |
| `webapp-qr.png` / `.svg` | `https://oigresergio.github.io/Parkour_NoToTFamily/` | **QR ufficiale**: apre la web app pubblica |
| `webapp-test-qr.png` / `.svg` | `…/Parkour_NoToTFamily/t/30dc3113527532d3/` | anteprima Flutter (percorso riservato, non linkato) |

![QR code della web app pubblica](./webapp-qr.png)

## Verifica rapida

Inquadra `webapp-qr.png` con la fotocamera del telefono: deve aprire la mappa
degli spot PkFAMILY (titolo "PkFAMILY — mappa degli spot di parkour"). Se il
telefono mostra "pagina non trovata", il QR è vecchio o il deploy su
`gh-pages` è cambiato: rigenera e ricontrolla con lo script qui sotto.

## Rigenerare / controllare i QR

```sh
pip install "qrcode[pil]" opencv-python-headless
python3 scripts/make_qr.py          # rigenera PNG + SVG e verifica
python3 scripts/make_qr.py --check  # verifica soltanto (decodifica + HTTP 200)
```

Gli URL codificati sono in cima a `scripts/make_qr.py`. I QR sono generati
con correzione d'errore di livello M, modulo da 12 px e bordo di 4 moduli
(1,2 mm per modulo nell'SVG). Lo script rilegge ogni PNG per controllare che
decodifichi esattamente l'URL atteso e che l'URL risponda 200.

I link-invito con QR per i singoli utenti (con codice ordine e ruolo) si
generano invece dalla console `admin-inviti.html` su `gh-pages`, non da qui.
