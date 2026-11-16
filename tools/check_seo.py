#!/usr/bin/env python3
"""Contrôle les métadonnées des pages construites (dist/).

Le diff pixel surveille le rendu, celui-ci surveille ce que voit Google :
un titre par page, tous différents, de la bonne longueur, et des URLs qui
pointent vraiment vers la page.

Usage :  python3 tools/check_seo.py      (après `npm run build`)
"""
from __future__ import annotations

import glob
import html
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

LONGUEUR_TITRE = 60        # au-delà, Google coupe
DESCRIPTION_MIN = 110
DESCRIPTION_MAX = 165


def pages() -> list[tuple[str, str]]:
    trouvees = [("index", os.path.join(DIST, "index.html"))]
    for f in sorted(glob.glob(os.path.join(DIST, "*", "index.html"))):
        trouvees.append((os.path.basename(os.path.dirname(f)), f))
    return trouvees


def une(motif: str, texte: str) -> list[str]:
    return [html.unescape(m) for m in re.findall(motif, texte, re.S)]


def main() -> int:
    titres: dict[str, str] = {}
    soucis: list[str] = []

    for slug, chemin in pages():
        h = io.open(chemin, encoding="utf-8").read()
        t = une(r"<title>(.*?)</title>", h)
        d = une(r'<meta name="description" content="([^"]*)"', h)
        canon = une(r'<link rel="canonical" href="([^"]*)"', h)
        og = une(r'<meta property="og:url" content="([^"]*)"', h)

        def signale(message: str) -> None:
            soucis.append(f"{slug} : {message}")

        if len(t) != 1:
            signale(f"{len(t)} balises <title>")
        if len(d) != 1:
            signale(f"{len(d)} balises description")
        if len(canon) != 1:
            signale(f"{len(canon)} balises canonical")
        if len(og) != 1:
            signale(f"{len(og)} balises og:url")

        if t:
            if len(t[0]) > LONGUEUR_TITRE:
                signale(f"titre de {len(t[0])} caractères (max {LONGUEUR_TITRE})")
            if t[0] in titres:
                signale(f"titre identique à celui de {titres[t[0]]}")
            titres[t[0]] = slug
        if d and not DESCRIPTION_MIN <= len(d[0]) <= DESCRIPTION_MAX:
            signale(f"description de {len(d[0])} caractères "
                    f"(visez {DESCRIPTION_MIN}-{DESCRIPTION_MAX})")
        if canon and og and canon[0] != og[0]:
            signale(f"canonical et og:url divergent : {canon[0]} / {og[0]}")
        if "delphacrea.crechndo.org" in h:
            signale("renvoie encore vers le site de préproduction")

        marque = "✗" if any(s.startswith(slug + " :") for s in soucis) else "✓"
        print(f"{marque} {slug:36s} {len(t[0]) if t else 0:>3}/{len(d[0]) if d else 0:>3}  "
              f"{t[0][:52] if t else '— sans titre —'}")

    print()
    if soucis:
        for s in soucis:
            print(f"  ✗ {s}")
        print(f"\n{len(soucis)} problème(s) sur {len(pages())} pages.")
        return 1
    print(f"{len(pages())} pages : un titre unique par page, métadonnées cohérentes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
