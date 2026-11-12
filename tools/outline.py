#!/usr/bin/env python3
"""Affiche l'arborescence Elementor d'une page : sections, colonnes, widgets.

Sert à préparer la réécriture : on voit d'un coup d'œil de quoi une page est faite,
et quelles règles CSS visent chacun de ses éléments.

Usage :  python3 tools/outline.py <slug> [--css]
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAGMENTS = os.path.join(ROOT, "src", "fragments")

TAG_RE = re.compile(
    r'<(?P<tag>section|div|header|footer)\s+class="(?P<cls>[^"]*elementor-(?:section|column|widget-wrap|element)[^"]*)"'
    r'(?P<rest>[^>]*)>'
)


def outline(slug: str) -> None:
    path = os.path.join(FRAGMENTS, f"{slug}-content.html")
    with open(path, encoding="utf-8") as fh:
        html = fh.read()

    depth = 0
    for m in re.finditer(r"<(/?)(section|div|header|footer)([^>]*)>", html):
        closing, tag, attrs = m.group(1), m.group(2), m.group(3)
        if closing:
            depth = max(0, depth - 1)
            continue
        cls = re.search(r'class="([^"]*)"', attrs)
        cls = cls.group(1) if cls else ""
        eid = re.search(r'data-id="([^"]*)"', attrs)
        wtype = re.search(r'data-widget_type="([^"]*)"', attrs)

        kind = None
        if "elementor-top-section" in cls:
            kind = "SECTION"
        elif "elementor-column" in cls and "elementor-element" in cls:
            col = re.search(r"elementor-col-(\d+)", cls)
            kind = f"colonne {col.group(1)}%" if col else "colonne"
        elif wtype:
            kind = wtype.group(1).replace(".default", "")

        if kind:
            extra = []
            for flag in ("elementor-hidden-mobile", "elementor-hidden-desktop",
                         "elementor-hidden-tablet", "elementor-section-full_width",
                         "elementor-section-boxed"):
                if flag in cls:
                    extra.append(flag.replace("elementor-", ""))
            print(f'{"  " * depth}{kind:<18} {eid.group(1) if eid else "":<10} {" ".join(extra)}')
            depth += 1


def css_for(slug: str) -> None:
    """Règles CSS inlinées visant les éléments de cette page."""
    with open(os.path.join(FRAGMENTS, f"{slug}-head.html"), encoding="utf-8") as fh:
        head = fh.read()
    blocks = re.findall(r'<style class="optimize_css_2"[^>]*>(.*?)</style>', head, re.S)
    for i, block in enumerate(blocks):
        if not block.strip():
            continue
        print(f"\n===== bloc CSS {i} ({len(block)} car.) =====")
        print(re.sub(r"\}", "}\n", block))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    outline(args[0])
    if "--css" in sys.argv:
        css_for(args[0])
