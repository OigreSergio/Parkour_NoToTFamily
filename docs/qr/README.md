# QR code — web app

La web app è in **anteprima privata** (vedi `docs/WEB_TEST_SPACE.md`): l'URL
base mostra solo un placeholder e l'app vera è su un percorso riservato,
raggiungibile con il QR di test.

| File | Punta a | Uso |
| --- | --- | --- |
| `webapp-test-qr.png` / `.svg` | percorso riservato `/t/<token>/` | **QR attuale di accesso** all'anteprima |
| `webapp-qr.png` / `.svg` | URL base (oggi placeholder) | da rigenerare al lancio pubblico |
| `tutorial-catalog-qr.png` / `.svg` | `/t/<token>/tutorial-catalog.html` | anteprima del **catalogo tutorial** (vedi `docs/TUTORIAL_CATALOG.md`) |

![QR code di accesso all'anteprima](./webapp-test-qr.png)

I QR sono generati con correzione d'errore di livello M; la build web (export
Expo) è servita dal branch `gh-pages`.

Tutti puntano dentro l'area riservata, quindi funzionano solo su un dispositivo
già registrato con un invito valido: da un dispositivo nuovo si finisce sul
placeholder.
