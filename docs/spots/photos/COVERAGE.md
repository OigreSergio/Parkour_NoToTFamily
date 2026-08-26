# Copertura degli spot

Rigenerato con `python scripts/spot_coverage.py` — non modificare a mano.

**26 spot** · 11 con almeno una foto · 17 con gli
ostacoli rilevati sul posto · **4 completi** (foto degli ostacoli +
descrizione + rilievo).

Legenda foto: `✅ spot` = si vedono gli ostacoli · `🟡 zona` = si vede solo il
luogo intorno, non gli ostacoli · `❌` = nessuna foto.

| Spot | Foto | Descrizione | Rilievo |
| --- | --- | --- | --- |
| Colle Oppio Park | 🟡 2 zona | ✅ | ✅ |
| EUR Laghetto | 🟡 1 zona | ✅ | ✅ |
| Foro Italico — Stadio dei Marmi | ✅ 1 spot + 1 zona | ✅ | ✅ |
| Garbatella — Scalinate | ✅ 1 spot | ✅ | ✅ |
| MA Spot — Largo Emanuele Ruspoli | ❌ nessuna | ✅ | ❌ da rilevare |
| Parkour Park Municipio Roma III | ❌ nessuna | ✅ | ✅ |
| Spot Colonne Colosseo | ❌ nessuna | ✅ | ✅ |
| Spot Colosseo — Monte Oppio | 🟡 1 zona | ✅ | ✅ |
| Spot Corviale 1 | 🟡 1 zona | ✅ | ✅ |
| Spot Corviale 2 | ❌ nessuna | ✅ | ✅ |
| Spot Corviale 3 | ❌ nessuna | ✅ | ✅ |
| Spot EUR | ❌ nessuna | ✅ | ✅ |
| Spot Massimina Parco Nord | ❌ nessuna | ✅ | ❌ da rilevare |
| Spot Massimina Parco Sud | ❌ nessuna | ✅ | ❌ da rilevare |
| Spot Metro Colosseo | ✅ 1 spot | ✅ | ✅ |
| Spot NoToT Game | ❌ nessuna | ✅ | ❌ da rilevare |
| Spot Pizzeria Massimina | ❌ nessuna | ✅ | ❌ da rilevare |
| Spot Primavalle | 🟡 1 zona | ✅ | ✅ |
| Spot Rooftop Casal Lumbroso | ❌ nessuna | ✅ | ❌ da rilevare |
| Spot Scuola Massimina | ❌ nessuna | ✅ | ❌ da rilevare |
| Spot Tufello | 🟡 1 zona | ✅ | ❌ da rilevare |
| Spot Via Giovanni Prati | ❌ nessuna | ✅ | ❌ da rilevare |
| Spot Villa Carpegna | 🟡 1 zona | ✅ | ✅ |
| Spot con fontanella - Trastevere/Gianicolo | ❌ nessuna | ✅ | ✅ |
| Spot verso la metro Cipro | ❌ nessuna | ✅ | ✅ |
| Villa Borghese — Piazza di Siena | ✅ 1 spot + 1 zona | ✅ | ✅ |

## Cosa serve per chiudere una scheda

1. **Una foto degli ostacoli** — scattata sul posto, non della zona:
   `python scripts/add_spot_photos.py "<nome spot>" foto.jpg`
2. **Il rilievo** — cosa c'è davvero (altezze, distanze, fondo, orari buoni),
   scritto nella descrizione; poi `"surveyed": true` nel seed.

Vedi [`README.md`](README.md) per il flusso completo.
