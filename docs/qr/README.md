# QR code — web app

| File | Punta a | Uso |
| --- | --- | --- |
| `webapp-qr.png` / `.svg` | `https://oigresergio.github.io/Parkour_NoToTFamily/` | **QR pubblico** della web app |
| `webapp-test-qr.png` / `.svg` | percorso riservato `/t/<token>/` | QR dell'anteprima privata (storico) |

![QR code della web app](./webapp-qr.png)

Finché l'app sta sotto `/t/<token>/` (anteprima privata, vedi
`docs/WEB_TEST_SPACE.md`) il QR pubblico porta al placeholder; diventa valido
appena l'app viene spostata sulla root con `scripts/promote_web_public.sh`.

## Rigenerarli

Servono solo se cambia l'URL (per esempio con un dominio custom):

```sh
pip install "qrcode[pil]"
python3 scripts/make_qr.py                                  # QR pubblico
python3 scripts/make_qr.py --url <URL> --nome webapp-test-qr
```

Correzione d'errore livello M, 12 px (1,2 mm) per modulo, bordo di 4 moduli:
gli stessi parametri dei file già in repo, quindi la rigenerazione è
riproducibile byte per byte.
