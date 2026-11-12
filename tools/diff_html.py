#!/usr/bin/env python3
"""Compare le HTML généré (dist/) au HTML du site d'origine (cache).

On applique à la page d'origine exactement les mêmes réécritures d'URL que lors de
la génération, puis on compare balise à balise. Tout ce qui reste comme différence
est soit voulu (balises WordPress purgées, bascule GA4), soit une régression.

Depuis la phase 2, le header et le footer sont réécrits à la main : les comparer au
balisage d'origine n'aurait plus de sens. La comparaison porte donc sur le <head> et
sur le contenu de la page — c'est-à-dire sur ce qui n'a pas encore été réécrit.
Le garde-fou du balisage réécrit, c'est le diff pixel (tools/visual_diff.mjs).

Usage :  python3 tools/diff_html.py [slug…]      (sans argument : les 16 pages)
"""
from __future__ import annotations

import difflib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_fragments import (  # noqa: E402
    CACHE_RAW,
    CONTENT_END,
    CONTENT_START,
    GA_LEGACY_RE,
    purge,
    rewrite_assets,
    rewrite_head,
    rewrite_internal_links,
)
from mirror import PAGES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")


def tags(html: str) -> list[str]:
    """Découpe le HTML en une ligne par balise / bloc de texte, pour un diff lisible."""
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    parts = re.split(r"(<[^>]+>)", html)
    return [p.strip() for p in parts if p.strip()]


def contenu_de_page(body: str) -> str:
    """Ne garde que le contenu de la page, sans le header ni le footer."""
    debut = body.index(CONTENT_START)
    fin = body.index(CONTENT_END) + len(CONTENT_END)
    return body[debut:fin]


def expected(slug: str) -> str:
    with open(os.path.join(CACHE_RAW, f"{slug}.html"), encoding="utf-8") as fh:
        html = purge(fh.read())
    head_start = html.index(">", html.index("<head")) + 1
    head = html[head_start:html.index("</head>")]
    head = rewrite_head(GA_LEGACY_RE.sub("", head))
    body = html[html.index(">", html.index("<body")) + 1:html.index("</body>")]
    body = rewrite_internal_links(rewrite_assets(body))
    return head + contenu_de_page(body)


def actual(slug: str) -> str:
    path = os.path.join(DIST, "index.html" if slug == "index" else f"{slug}/index.html")
    with open(path, encoding="utf-8") as fh:
        html = fh.read()
    head_start = html.index(">", html.index("<head")) + 1
    head = html[head_start:html.index("</head>")]
    # On retire ce que la migration ajoute volontairement : le tag GA4, qui
    # remplace l'ancien snippet UA, et notre feuille de style.
    head = re.sub(r"<!-- Google Analytics 4 -->.*?gtag\('config'[^<]*</script>", "", head, flags=re.S)
    head = re.sub(r"<!-- Notre feuille de style.*?-->", "", head, flags=re.S)
    head = re.sub(r'<link rel="stylesheet" href="[^"]*/css/site\.css"\s*/?>', "", head)
    body = html[html.index(">", html.index("<body")) + 1:html.index("</body>")]
    return head + contenu_de_page(body)


def main() -> int:
    slugs = sys.argv[1:] or list(PAGES)
    total = 0
    for slug in slugs:
        a, b = tags(expected(slug)), tags(actual(slug))
        diff = [
            line for line in difflib.unified_diff(a, b, "origine", "généré", n=1, lineterm="")
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
        ]
        status = "✓ identique" if not diff else f"✗ {len(diff)} différences"
        print(f"{slug:40s} {status}")
        for line in diff[:40]:
            print("    " + line[:200])
        total += len(diff)
    print(f"\nTotal : {total} différences sur {len(slugs)} page(s).")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
