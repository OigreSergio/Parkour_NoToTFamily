# 🎓 PkFAMILY Accademia

Sezione tutorial & video di PkFAMILY: tutorial passo-passo, trick database
ricercabile, obiettivi, progressi e badge. Concept ispirato a Ultimate
Parkour App — architettura documentata in
[`docs/ACCADEMIA_TUTORIAL_VIDEO.md`](../docs/ACCADEMIA_TUTORIAL_VIDEO.md).

## Provala subito (dal telefono)

Pagina statica senza build: si apre direttamente dalla branch di sviluppo.

- **Test immediato:**
  https://raw.githack.com/OigreSergio/Parkour_NoToTFamily/claude/ultimate-parkour-architecture-5p7wc8/accademia/index.html
- **Quando verrà copiata su `gh-pages`:**
  https://oigresergio.github.io/Parkour_NoToTFamily/accademia/

I progressi si salvano in `localStorage` del dispositivo: niente account,
niente backend.

## Sviluppo

Tutto vive in `index.html` (HTML + CSS + JS inline, zero dipendenze).
Per aggiungere un trick: nuova voce nell'array `TRICKS`; per collegare un
video ufficiale: valorizzare il campo `video` con l'URL embed.
