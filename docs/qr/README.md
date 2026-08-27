# QR code — web app

La web app è in **anteprima privata** (vedi `docs/DEPLOY.md`): l'URL
base mostra solo un placeholder e l'app vera è su un percorso riservato,
raggiungibile con il QR di test.

| File | Punta a | Uso |
| --- | --- | --- |
| `webapp-test-qr.png` / `.svg` | percorso riservato `/t/<token>/` | **QR attuale di accesso** all'anteprima |
| `webapp-qr.png` / `.svg` | URL base (oggi placeholder) | da rigenerare al lancio pubblico |

![QR code di accesso all'anteprima](./webapp-test-qr.png)

I QR sono generati con correzione d'errore di livello M; la build web (export
Expo) è servita dal branch `gh-pages`.
