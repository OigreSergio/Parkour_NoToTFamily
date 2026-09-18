# Fotografie di riferimento

Sono generate, non fatte a mano:

```sh
cd app && node tools/screenshot.mjs
```

Mostrano l'app di `app/` su un telefono (Pixel 7, 412×915 punti), in italiano,
nel tema chiaro e in quello scuro. Le tessere di mappa non vengono scaricate:
si vede il lino con la sua trama, cioè quello che l'app mostra anche senza
rete.

Servono alla consegna 5 del capitolo grafica del masterplan: guardare l'app
tutta insieme e accorgersi, da un `git diff --stat`, se un ritocco al design
ha spostato qualcosa che non doveva.
