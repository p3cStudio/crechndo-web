#!/usr/bin/env python3
"""Affiche l'ossature d'une page et les réglages que l'éditeur d'origine a posés
élément par élément. C'est la fiche de route pour réécrire la page à la main.

Usage :  python3 tools/reglages.py <slug>
"""
from __future__ import annotations

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAGMENTS = os.path.join(ROOT, "src", "fragments")

# Sélecteurs qui ne décrivent rien de visible : calques d'effets de mouvement,
# surcouches, béquilles de compatibilité d'Elementor.
SELECTEURS_INUTILES = re.compile(
    r"motion-effects-container|background-overlay|elementor-bc-flex-widget"
    r"|drop-cap|widget-image-caption"
)

# Déclarations sans effet visible : transitions et variables globales reprises
# telles quelles du thème.
DECLARATIONS_INUTILES = re.compile(r"^(transition|--e-transform|.*var\(--e-global)")


def reglages(slug: str) -> dict[str, list[str]]:
    """Pour chaque identifiant d'élément, les déclarations qui le concernent."""
    head = io.open(os.path.join(FRAGMENTS, f"{slug}-head.html"), encoding="utf-8").read()
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", head, re.S))
    par_id: dict[str, list[str]] = {}
    media = ""
    for m in re.finditer(r"(@media[^{]*\{)|([^{}@]+)\{([^{}]*)\}|(\})", css):
        if m.group(1):
            media = m.group(1).strip()[:40]
            continue
        if m.group(4):
            media = ""
            continue
        sel, corps = m.group(2).strip(), m.group(3).strip()
        # On écarte les parties de sélecteur inutiles une à une : une même
        # règle mélange souvent un sélecteur utile et un calque d'effet.
        sel = ",".join(p for p in sel.split(",") if not SELECTEURS_INUTILES.search(p))
        if not sel:
            continue
        corps = ";".join(d for d in corps.split(";")
                         if d.strip() and not DECLARATIONS_INUTILES.match(d.strip()))
        if not corps:
            continue
        for eid in set(re.findall(r"elementor-element-([0-9a-f]{6,9})", sel)):
            sel = re.sub(r":not\([^)]*\)", "", sel)
            sel = ",".join(p for p in sel.split(",") if eid in p)
            reste = re.sub(r"\.elementor-\d+ \.elementor-element\.elementor-element-[0-9a-f]+", "", sel)
            reste = re.sub(r"\.elementor-element-[0-9a-f]+", "", reste).strip(" >,")
            par_id.setdefault(eid, []).append(
                f"{media + ' ' if media else ''}{reste + ' ' if reste else ''}{corps}")
    return par_id


def main() -> int:
    slug = sys.argv[1]
    par_id = reglages(slug)
    html = io.open(os.path.join(FRAGMENTS, f"{slug}-content.html"), encoding="utf-8").read()
    if html.startswith("<!-- réécrit"):
        print(f"{slug} est déjà réécrite.")
        return 0

    for m in re.finditer(r"<(?:section|div)\s+([^>]*data-id=[^>]*)>", html):
        attrs = m.group(1)
        cls = (re.search(r'class="([^"]*)"', attrs) or [None, ""])[1]
        eid = (re.search(r'data-id="([^"]*)"', attrs) or [None, ""])[1]
        wtype = (re.search(r'data-widget_type="([^"]*)"', attrs) or [None, None])[1]
        if "elementor-top-section" in cls:
            genre, decal = "SECTION", ""
        elif "elementor-column" in cls:
            col = re.search(r"elementor-col-(\d+)", cls)
            genre, decal = f"colonne {col.group(1) if col else '?'}%", "  "
        elif wtype:
            genre, decal = wtype.replace(".default", ""), "    "
        else:
            continue
        drapeaux = [d.replace("elementor-", "") for d in
                    ("elementor-hidden-mobile", "elementor-hidden-tablet", "elementor-hidden-desktop",
                     "elementor-section-full_width", "elementor-align-center", "elementor-align-right",
                     "elementor-invisible", "e-transform") if d in cls]
        print(f"{decal}{genre:<16} {eid:<10} {' '.join(drapeaux)}")
        for d in par_id.get(eid, []):
            print(f"{decal}    · {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
