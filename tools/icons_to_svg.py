#!/usr/bin/env python3
"""Convertit en SVG les quelques glyphes d'icônes utilisés par le site.

Le site n'emploie que sept icônes, réparties dans quatre polices (Font Awesome
solid et brands, eicons, et la police maison « creche ») pesant ensemble ~1,2 Mo.
On extrait les tracés de ces sept glyphes, et les polices peuvent disparaître.

Le SVG produit respecte la convention des polices d'icônes : le glyphe est dessiné
dans une boîte carrée haute de 1 em, et l'axe Y est inversé (les polices montent,
le SVG descend). Le viewBox est donc centré sur cette boîte, pas sur l'encre du
glyphe : une icône posée à 16px occupe exactement 16px, comme avec la police.

Sortie : src/fragments/icons.json  (id -> {viewBox, path, width})

Usage :  tools/.cache/venv/bin/python tools/icons_to_svg.py
"""
from __future__ import annotations

import json
import os
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "public", "fonts")
OUT = os.path.join(ROOT, "src", "fragments", "icons.json")
SPRITE = os.path.join(ROOT, "src", "fragments", "icons-sprite.html")

# id souhaité -> (fichier de police, point de code)
ICONS = {
    "caret-down": ("fa-solid-900.ttf", 0xF0D7),
    "phone": ("fa-solid-900.ttf", 0xF879),
    "map-marker": ("fa-solid-900.ttf", 0xF3C5),
    "facebook": ("fa-brands-400.ttf", 0xF39E),
    "menu-bar": ("eicons.ttf", 0xE816),
    "close": ("eicons.ttf", 0xE87F),
    "creche-puce": ("creche.ttf", 0xE800),
}


def extract(font_file: str, codepoint: int) -> dict:
    font = TTFont(os.path.join(FONTS, font_file))
    upm = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    name = cmap.get(codepoint)
    if name is None:
        raise SystemExit(f"{font_file}: aucun glyphe pour U+{codepoint:04X}")

    glyph_set = font.getGlyphSet()
    svg_pen = SVGPathPen(glyph_set)
    # Dans une police, l'axe Y monte ; en SVG, il descend. On retourne le tracé
    # à l'extraction, pour que le chemin produit soit directement utilisable.
    glyph_set[name].draw(TransformPen(svg_pen, (1, 0, 0, -1, 0, 0)))
    path = svg_pen.getCommands()

    # Largeur d'avance du glyphe, en em : c'est elle qui donne le rapport
    # largeur/hauteur de l'icône, comme dans le texte.
    advance = font["hmtx"][name][0]

    # Repère des polices : origine sur la ligne de base, Y vers le haut (le tracé
    # a déjà été retourné plus haut). Reste à placer la boîte de l'icône.
    #
    # Avec `line-height: 1`, une icône de police occupe une boîte haute d'un em.
    # Le glyphe y est posé par le navigateur à partir des montantes de la police :
    # le demi-interligne (souvent négatif) écarte la ligne de base du haut de la
    # boîte. On reproduit exactement ce calcul, sans quoi l'icône se retrouve
    # décalée de un ou deux pixels — ce qui se voit au diff.
    ascent = font["hhea"].ascent
    descent = font["hhea"].descent  # négatif
    demi_interligne = (upm - (ascent - descent)) / 2
    haut = ascent + demi_interligne  # distance ligne de base -> haut de la boîte

    font.close()
    # Dimensions exprimées en em, pour que l'icône occupe exactement la place
    # qu'occupait le glyphe : même hauteur de boîte, même avance, et la ligne de
    # base au même endroit (d'où le décalage vertical négatif).
    return {
        "viewBox": f"0 {-haut:g} {advance} {upm}",
        "path": path,
        "largeur": round(advance / upm, 4),
        # La boîte fait un em de haut, comme celle du glyphe.
        "hauteur": 1,
        # Décalage pour que la ligne de base du SVG tombe sur celle du texte.
        "ligneDeBase": round(-(upm - haut) / upm, 4),
    }


def main() -> int:
    icons = {}
    for name, (font_file, codepoint) in ICONS.items():
        if not os.path.exists(os.path.join(FONTS, font_file)):
            print(f"  police absente : {font_file}", file=sys.stderr)
            continue
        icons[name] = extract(font_file, codepoint)
        print(f"  {name:14s} {font_file:20s} U+{codepoint:04X}  "
              f"viewBox={icons[name]['viewBox']}  {len(icons[name]['path'])} car.")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(icons, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # Planche d'icônes insérée une fois par page : le balisage se contente
    # ensuite d'un <use href="#cnd-i-…">, lisible et sans tracé dupliqué.
    parts = [
        "<!-- GÉNÉRÉ par tools/icons_to_svg.py — ne pas éditer à la main.",
        "     Tracés extraits des polices d'icônes d'origine (Font Awesome,",
        "     eicons, police maison « creche »), qui ne sont plus chargées. -->",
        '<svg xmlns="http://www.w3.org/2000/svg" class="cnd-planche-icones" aria-hidden="true" focusable="false">',
    ]
    for name, data in icons.items():
        parts.append(
            f'  <symbol id="cnd-i-{name}" viewBox="{data["viewBox"]}">'
            f'<path d="{data["path"]}"/></symbol>'
        )
    parts.append("</svg>")
    parts.append("<style>")
    parts.append("/* Taille de chaque icône, reprise de l'avance et des montantes du glyphe. */")
    for name, data in icons.items():
        parts.append(
            f".cnd-icone--{name}{{width:{data['largeur']}em;height:{data['hauteur']}em;"
            f"vertical-align:{data['ligneDeBase']}em}}"
        )
    parts.append("</style>")
    with open(SPRITE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts) + "\n")

    print(f"\n{len(icons)} icônes écrites dans {os.path.relpath(OUT, ROOT)}")
    print(f"planche : {os.path.relpath(SPRITE, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
