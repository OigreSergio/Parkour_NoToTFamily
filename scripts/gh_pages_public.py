#!/usr/bin/env python3
"""Trasforma un checkout di `gh-pages` da anteprima privata a sito pubblico.

Lavora *in place* su una copia di lavoro del branch `gh-pages` (non tocca git):

1. sposta l'app da ``/t/<token>/`` alla root e riscrive la base dei percorsi
   ``/Parkour_NoToTFamily/t/<token>`` -> ``/Parkour_NoToTFamily``;
2. toglie il gate a inviti PkPASS (il redirect su ``pk_pass`` manderebbe l'app
   in loop, visto che ora la root *è* l'app) e i meta ``noindex``;
3. scrive ``robots.txt`` permissivo + ``sitemap.xml``, mette in ``404.html``
   una copia di ``index.html`` (deep link della SPA) e aggiunge i meta SEO
   di base a ``index.html``.

La pagina admin degli inviti resta fuori dagli indici (meta noindex + Disallow).

Uso:
  python3 scripts/gh_pages_public.py <dir-gh-pages> [--site-url URL] [--base BASE]

Idempotente: rilanciarlo sullo stesso albero non cambia nulla.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

SITE_URL_DEFAULT = "https://oigresergio.github.io/Parkour_NoToTFamily/"
BASE_DEFAULT = "/Parkour_NoToTFamily"
TESTO_FILE = (".html", ".js", ".json", ".css", ".txt", ".webmanifest")
NOINDEX_SEMPRE = ("admin-inviti.html",)  # pagina interna: resta fuori dagli indici

TITOLO = "PkFAMILY — mappa degli spot di parkour"
DESCRIZIONE = (
    "PkFAMILY: la mappa collaborativa degli spot di parkour. Trova gli spot "
    "vicino a te con foto, livello di difficoltà, distanza e percorso."
)

# blocco del gate a inviti, con lo <script> che lo racchiude
GATE_RE = re.compile(
    r"[ \t]*<script>\s*\(function\(\)\{try\{var t=localStorage\.getItem\('pk_pass'\);"
    r".*?\}catch\(e\)\{\}\}\)\(\);\s*</script>\n?",
    re.DOTALL,
)
NOINDEX_RE = re.compile(r"[ \t]*<meta name=\"robots\" content=\"noindex, nofollow\"\s*/?>\n?")


def file_testo(root: Path):
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in TESTO_FILE]


def sposta_in_root(root: Path) -> str | None:
    """Sposta /t/<token>/* nella root. Ritorna il token trovato (o None)."""
    t = root / "t"
    if not t.is_dir():
        return None
    sotto = [d for d in t.iterdir() if d.is_dir()]
    if len(sotto) != 1:
        sys.exit(f"ERRORE: attesa una sola cartella sotto {t}, trovate {len(sotto)}")
    app = sotto[0]
    token = app.name
    for voce in list(app.iterdir()):
        dest = root / voce.name
        if dest.exists():
            shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
        shutil.move(str(voce), str(dest))
    shutil.rmtree(t)
    print(f"ok: app spostata da /t/{token}/ alla root")
    return token


def riscrivi_base(root: Path, vecchia: str, nuova: str) -> int:
    n = 0
    for p in file_testo(root):
        src = p.read_text(encoding="utf8", errors="surrogateescape")
        if vecchia in src:
            p.write_text(src.replace(vecchia, nuova), encoding="utf8", errors="surrogateescape")
            n += 1
    print(f"ok: base dei percorsi riscritta ({vecchia} -> {nuova}) in {n} file")
    return n


def togli_gate_e_noindex(root: Path) -> None:
    gate = noindex = 0
    for p in root.rglob("*.html"):
        src = orig = p.read_text(encoding="utf8")
        src, k = GATE_RE.subn("", src)
        gate += k
        if p.name not in NOINDEX_SEMPRE:
            src, k = NOINDEX_RE.subn("", src)
            noindex += k
        if src != orig:
            p.write_text(src, encoding="utf8")
    print(f"ok: gate a inviti rimosso da {gate} pagine, meta noindex da {noindex}")


def meta_seo(root: Path, site_url: str) -> None:
    idx = root / "index.html"
    if not idx.is_file():
        sys.exit(f"ERRORE: {idx} non trovato")
    html = idx.read_text(encoding="utf8")
    if 'property="og:title"' in html:
        print("ok: meta SEO già presenti")
        return
    blocco = (
        f'<title>{TITOLO}</title>\n'
        f'    <meta name="description" content="{DESCRIZIONE}" />\n'
        f'    <link rel="canonical" href="{site_url}" />\n'
        f'    <meta name="theme-color" content="#2743E3" />\n'
        f'    <meta property="og:type" content="website" />\n'
        f'    <meta property="og:site_name" content="PkFAMILY" />\n'
        f'    <meta property="og:title" content="{TITOLO}" />\n'
        f'    <meta property="og:description" content="{DESCRIZIONE}" />\n'
        f'    <meta property="og:url" content="{site_url}" />\n'
        f'    <meta property="og:locale" content="it_IT" />\n'
        f'    <meta name="twitter:card" content="summary" />\n'
        f'    <meta name="twitter:title" content="{TITOLO}" />\n'
        f'    <meta name="twitter:description" content="{DESCRIZIONE}" />'
    )
    if "<title>PkFAMILY</title>" not in html:
        sys.exit("ERRORE meta SEO: <title>PkFAMILY</title> non trovato in index.html")
    html = html.replace("<title>PkFAMILY</title>", blocco, 1)
    html = html.replace('<html lang="en">', '<html lang="it">', 1)
    idx.write_text(html, encoding="utf8")
    print("ok: meta SEO aggiunti a index.html")


def robots_e_sitemap(root: Path, site_url: str) -> None:
    (root / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin-inviti.html\n"
        f"\nSitemap: {site_url}sitemap.xml\n",
        encoding="utf8",
    )
    pagine = [""] + [
        rel
        for rel in ("stato/", "tutorial-catalog.html")
        if (root / rel).exists()
    ]
    url = "".join(f"  <url><loc>{site_url}{p}</loc></url>\n" for p in pagine)
    (root / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{url}</urlset>\n",
        encoding="utf8",
    )
    print(f"ok: robots.txt permissivo e sitemap.xml ({len(pagine)} URL)")


def spa_404(root: Path) -> None:
    shutil.copyfile(root / "index.html", root / "404.html")
    print("ok: 404.html = copia di index.html (deep link della SPA)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dir", type=Path, help="copia di lavoro del branch gh-pages")
    ap.add_argument("--site-url", default=SITE_URL_DEFAULT, help="URL pubblico (con / finale)")
    ap.add_argument("--base", default=BASE_DEFAULT, help="base dei percorsi (default /Parkour_NoToTFamily)")
    a = ap.parse_args()

    root = a.dir.resolve()
    site_url = a.site_url if a.site_url.endswith("/") else a.site_url + "/"
    if not root.is_dir():
        sys.exit(f"ERRORE: {root} non è una cartella")

    token = sposta_in_root(root)
    if token:
        riscrivi_base(root, f"{a.base}/t/{token}", a.base)
    togli_gate_e_noindex(root)
    meta_seo(root, site_url)
    robots_e_sitemap(root, site_url)
    spa_404(root)
    (root / ".nojekyll").touch()
    print(f"\nFatto. Sito pubblico pronto in {root}")


if __name__ == "__main__":
    main()
