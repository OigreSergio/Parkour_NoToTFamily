#!/usr/bin/env python3
"""Genera l'anteprima navigabile del catalogo tutorial.

Prende la demo della schermata Tutorial (``docs/demo/tutorial-demo.html``, che
replica ``mobile/lib/screens/tutorials_screen.dart``) e ne sostituisce i trick
di esempio con il catalogo reale di ``backend/seeds/videos.json``. Le regole di
accesso restano quelle della demo, cioè quelle di
``app/services/video_service.py``: i video ``beginner`` sono liberi, gli altri
mostrano il paywall con l'URL nascosto.

Serve a provare il catalogo — e in particolare la scelta di tenere gratuiti i
video di sicurezza (flag ``safety`` nel seed) — senza tirare su il backend.

Uso:
    python3 docs/demo/tools/build_tutorial_preview.py
    # default output: docs/demo/tutorial-catalog-preview.html

    python3 docs/demo/tools/build_tutorial_preview.py --fragment out.html
    # in più: la stessa pagina senza <html>/<head>/<body>, per pubblicarla
    # come artifact

    python3 docs/demo/tools/build_tutorial_preview.py out.html --app-url ./ --gate
    # variante per lo spazio di test su gh-pages: i tab Mappa e Lista aprono
    # l'app vera che sta accanto, e la pagina eredita il gate a inviti

Va rilanciato quando cambia il seed: la pagina è un artefatto generato.
"""

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEMO = REPO / "docs" / "demo" / "tutorial-demo.html"
SEED = REPO / "backend" / "seeds" / "videos.json"
DEFAULT_OUT = REPO / "docs" / "demo" / "tutorial-catalog-preview.html"

PR_URL = "https://github.com/OigreSergio/Parkour_NoToTFamily/pull/13"

# Lo stesso gate a inviti dell'app (t/<token>/index.html): senza un pk_pass
# valido la pagina rimanda al placeholder. È riservatezza, non autenticazione
# — vedi docs/WEB_TEST_SPACE.md.
GATE = """<meta name="robots" content="noindex, nofollow">
<script>
(function(){try{var t=localStorage.getItem('pk_pass');
if(!t){location.replace('/Parkour_NoToTFamily/');return}
var p=t.split('.');
crypto.subtle.digest('SHA-256',new TextEncoder().encode('PkFAMILY::pk_4f7934b9aed5ae01b547a0c1::'+p[0])).then(function(b){
var h=Array.prototype.slice.call(new Uint8Array(b),0,8).map(function(x){return x.toString(16).padStart(2,'0')}).join('');
if(h!==p[1]){try{localStorage.removeItem('pk_pass')}catch(e){}location.replace('/Parkour_NoToTFamily/')}});
}catch(e){}})();
</script>
</head>"""


def duration(seconds: int) -> str:
    if seconds >= 3600:
        return f"{seconds // 3600}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
    return f"{seconds // 60}:{seconds % 60:02d}"


def dataset() -> list[dict]:
    """Il catalogo nel formato che si aspetta la demo, ordinato per canale."""
    rows = []
    for video in json.loads(SEED.read_text(encoding="utf-8")):
        # L'id YouTube fa da chiave anche nella demo (landed, apertura scheda).
        video_id = video["url"].rsplit("=", 1)[1]
        # La descrizione del seed è "Canale — argomento. Testo": il canale ha
        # già la sua colonna, qui serve solo il resto.
        _, _, text = video["description"].partition(" — ")
        rows.append(
            {
                "id": video_id,
                "title": video["title"],
                "cat": video["trick_category"],
                "level": video["level"],
                "diff": video["difficulty"],
                "desc": text or video["description"],
                "url": video["url"],
                "ch": video["source_channel"],
                "dur": duration(video["duration_seconds"]),
                "q": video["quality"],
                "safe": bool(video.get("safety")),
            }
        )
    rows.sort(key=lambda row: (row["ch"], row["diff"]))
    return rows


def replace(page: str, old: str, new: str) -> str:
    """Sostituzione che fallisce forte se la demo cambia sotto i piedi."""
    if old not in page:
        raise SystemExit(f"la demo non contiene più questo frammento:\n{old[:120]}…")
    return page.replace(old, new)


def build(app_url: str | None = None, gate: bool = False) -> str:
    page = DEMO.read_text(encoding="utf-8")
    rows = dataset()
    free = sum(1 for row in rows if row["level"] == "beginner")
    safety = sum(1 for row in rows if row["safe"])

    tricks = (
        "const TRICKS = [\n"
        + "\n".join("    " + json.dumps(row, ensure_ascii=False) + "," for row in rows)
        + "\n  ];"
    )
    start = page.index("  // Sample catalog mirroring what the backend serves")
    end = page.index("  const state = {")
    page = (
        page[:start]
        + f"  // Catalogo reale: backend/seeds/videos.json ({len(rows)} video).\n  "
        + tricks
        + "\n\n"
        + page[end:]
    )

    # Testata e checklist: la demo parlava di trick di esempio.
    # Con l'app accanto (gh-pages) i due tab ci portano davvero; da soli restano spenti.
    if app_url:
        link = f'href="{app_url}" target="_blank" rel="noopener"'
        nav_map = f'<a class="nav" {link}><span class="g">\U0001f5fa️</span>Map</a>'
        nav_list = f'<a class="nav" {link}><span class="g">\U0001f4cb</span>List</a>'
        nav_note = (
            f'<p class="navnote">Mappa e Lista aprono <a {link}>l\'app vera</a> in una nuova '
            "scheda — spot, foto e schede sono quelli veri, e questa pagina resta aperta. "
            "Il tab Tutorials dell'app legge da Supabase, dove il catalogo non è ancora "
            "caricato: è questa pagina a mostrarlo.</p>"
        )
    else:
        nav_map = '<button class="nav" disabled><span class="g">\U0001f5fa️</span>Map</button>'
        nav_list = '<button class="nav" disabled><span class="g">\U0001f4cb</span>List</button>'
        nav_note = ""

    banner_start = page.index('  <p class="banner">')
    checklist_end = page.index('</div>\n\n<div class="toast"')
    page = (
        page[:banner_start]
        + f"""  <p class="banner">
    <strong>Anteprima del catalogo tutorial</strong> — i <strong>{len(rows)} video</strong> selezionati
    nella <a href="{PR_URL}">PR #13</a>, dentro la UI della schermata Tutorial. Le regole di accesso
    sono quelle vere di <code>video_service.can_watch</code>. Cambia profilo per vedere cosa sblocca
    il backend:
  </p>

  <div class="roles" role="group" aria-label="Profilo di accesso simulato">
    <button class="role" data-role="anon" aria-pressed="true">Anonimo<small>nessun accesso</small></button>
    <button class="role" data-role="guest" aria-pressed="false">Ospite<small>accesso senza email</small></button>
    <button class="role" data-role="sub" aria-pressed="false">Abbonato<small>premium sbloccati</small></button>
  </div>

  <div class="app">
    <div class="appbar" id="appbar"></div>
    <div class="screen" id="screen"></div>
    <nav class="navbar" aria-label="Navigazione app">
      {nav_map}
      {nav_list}
      <button class="nav" aria-current="true" id="navTutorials"><span class="g">\U0001f4d6</span>Tutorials</button>
    </nav>
  </div>
{nav_note}

  <div class="checklist">
    <h2>Cosa vale la pena provare</h2>
    <ol>
      <li>Da <strong>Anonimo</strong> o <strong>Ospite</strong>: i {free} video <em>beginner</em> si aprono
        e portano al video reale su YouTube; i {len(rows) - free} <em>intermediate/advanced</em> mostrano
        il paywall con l'URL nascosto, esattamente come risponde l'API.</li>
      <li><strong>Sicurezza sempre libera</strong>: apri <em>Ground Tricks</em> da Anonimo. Rolling sul
        cemento, cadere senza farsi male, 10 modi di cadere e l'atterraggio da altezza restano aperti
        pur avendo difficoltà 4-6 — sono i {safety} video marcati
        <span class="safe-chip">⛑ sicurezza</span>.</li>
      <li>La <strong>difficoltà reale</strong> resta nell'indicatore numerico: un video sbloccato con
        gauge 6 è gratuito ma non facile.</li>
      <li>Griglia categorie → lista filtrata; lente \U0001f50d per cercare fra i {len(rows)} titoli;
        omino \U0001f3c3 per segnare un video come "landed".</li>
      <li><strong>Suggestion Generator</strong>: pesca fra i video non ancora landed, con
        − Easier / + Harder / \U0001f500 Switch type.</li>
    </ol>
  </div>
"""
        + page[checklist_end:]
    )

    # Scheda: canale, durata, qualità didattica e link al video vero.
    page = replace(
        page,
        """              <span class="play" id="playBtn" role="button" tabindex="0" aria-label="Riproduci">▶️</span>
              <span style="font-size:0.75rem;opacity:0.85">video: ${esc(t.id)}.mp4</span>""",
        """              <a class="play" href="${t.url}" target="_blank" rel="noopener" aria-label="Guarda su YouTube">▶️</a>
              <span style="font-size:0.75rem;opacity:0.85">${esc(t.ch)} · ${esc(t.dur)}</span>""",
    )
    page = replace(
        page,
        """          <span class="chip">${c.glyph} ${c.label}</span>
          ${runnerBtn(t, '1.5rem')}""",
        """          <span class="chip">${c.glyph} ${c.label}</span>
          <span class="chip">⏱ ${esc(t.dur)}</span>
          <span class="chip">🎓 didattica ${esc(t.q.toLowerCase())}</span>
          ${t.safe ? '<span class="chip safe-chip">⛑ sempre gratuito</span>' : ''}
          ${runnerBtn(t, '1.5rem')}""",
    )
    page = replace(
        page,
        """        <p class="apinote">Risposta del backend per questo profilo:
          <code>{"locked": ${locked}, "is_premium": ${isPremium(t)}, "url": ${locked ? 'null' : '"https://…/' + t.id + '.mp4"'}}</code>
        </p>""",
        """        <p class="apinote">${esc(t.ch)} · risposta del backend per questo profilo:
          <code>{"locked": ${locked}, "is_premium": ${isPremium(t)}, "difficulty": ${t.diff}, "url": ${locked ? 'null' : '"' + t.url + '"'}}</code>
        </p>""",
    )
    page = replace(
        page,
        "<p>Subscribe to unlock intermediate and advanced technique videos.</p>",
        "<p>Serve l'abbonamento per i video intermediate e advanced. "
        "I contenuti di sicurezza restano liberi.</p>",
    )

    # Righe di lista: canale, durata e i due marchi (sicurezza, paywall).
    page = replace(
        page,
        """              ${isLocked(t) ? '<br><span class="sub">🔒 Premium — subscribe to watch</span>' : ''}""",
        """              <br><span class="sub">${esc(t.ch)} · ${esc(t.dur)}"""
        """${t.safe ? ' · <span class="safe-chip">⛑ sicurezza</span>' : ''}"""
        """${isLocked(t) ? ' · 🔒 premium' : ''}</span>""",
    )
    page = replace(
        page,
        """        <span class="sub">${isLocked(t) ? '🔒 Premium — subscribe to watch' : t.level}</span></span>""",
        """        <span class="sub">${esc(t.ch)} · ${isLocked(t) ? '🔒 premium' : t.level}</span></span>""",
    )

    # Etichette: qui sono video del catalogo, non trick generici.
    page = replace(
        page, '<span class="count">${n} tricks</span>', '<span class="count">${n} video</span>'
    )
    page = replace(
        page, 'placeholder="Search tricks…"', f'placeholder="Cerca fra i {len(rows)} video…"'
    )
    page = replace(
        page,
        '<p class="empty">No tutorials here yet.</p>',
        '<p class="empty">Nessun tutorial in questa categoria.</p>',
    )
    page = replace(
        page,
        "<span>Trick</span><span>Difficulty</span><span>Landed</span>",
        "<span>Tutorial</span><span>Difficoltà</span><span>Landed</span>",
    )

    # Stile del marchio sicurezza + fix di dettaglio sulla demo originale.
    page = replace(
        page,
        "  @media (prefers-reduced-motion: reduce) {",
        """  .safe-chip {
    background: color-mix(in srgb, var(--good) 16%, transparent);
    color: var(--good);
    border-radius: 999px;
    padding: 1px 7px;
    font-weight: 600;
    white-space: nowrap;
  }
  .chip.safe-chip { border: 1px solid color-mix(in srgb, var(--good) 45%, transparent); }
  .meta { flex-wrap: wrap; row-gap: 8px; }
  .player .play { text-decoration: none; }
  .banner a, .navnote a { color: var(--accent); font-weight: 600; }
  .navnote { margin: -12px 16px 22px; font-size: 0.82rem; color: var(--ink-soft); line-height: 1.5; }
  a.nav { text-decoration: none; }
  .banner a:focus-visible, .play:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  @media (prefers-reduced-motion: reduce) {""",
    )

    page = replace(
        page,
        "<title>Parkour NoToT · Demo Tutorial</title>",
        "<title>Parkour NoToT · Catalogo Tutorial</title>",
    )
    if gate:
        page = replace(page, "</head>", GATE)
    return page


def fragment(page: str) -> str:
    """La stessa pagina senza involucro, per la pubblicazione come artifact."""
    style = page[page.index("<style>") : page.index("</style>") + len("</style>")]
    body = page[page.index("<body>") + len("<body>") : page.index("</body>")]
    return "<title>Catalogo Tutorial NoToT</title>\n" + style + "\n" + body.strip() + "\n"


def mostra(path: Path) -> str:
    """Percorso relativo al repo quando ci sta dentro, altrimenti assoluto."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--fragment", type=Path, help="scrive anche la versione per l'artifact")
    parser.add_argument("--app-url", help="URL dell'app vera: rende cliccabili i tab Mappa e Lista")
    parser.add_argument(
        "--gate", action="store_true", help="aggiunge il gate a inviti dello spazio di test"
    )
    args = parser.parse_args()

    page = build(app_url=args.app_url, gate=args.gate)
    args.output.write_text(page, encoding="utf-8")
    print(f"scritto {mostra(args.output)}")
    if args.fragment:
        args.fragment.write_text(fragment(page), encoding="utf-8")
        print(f"scritto {mostra(args.fragment)}")


if __name__ == "__main__":
    main()
