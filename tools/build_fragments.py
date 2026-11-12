#!/usr/bin/env python3
"""Transforme les pages brutes aspirées par mirror.py en un site Astro statique.

Entrée  : tools/.cache/raw/<slug>.html   +  tools/.cache/assets/**
Sortie  : public/**                      (assets, URLs réécrites)
          src/fragments/<slug>-head|content|scripts.html
          src/fragments/header.html, footer.html   (mutualisés)
          src/pages/<slug>.astro

Le script est idempotent : il repart toujours du cache, jamais de sa propre sortie.

Usage :  python3 tools/build_fragments.py
"""
from __future__ import annotations

import os
import re
import json
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mirror import ASSET_EXT, PAGES, clean_url, local_path  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_RAW = os.path.join(ROOT, "tools", ".cache", "raw")
CACHE_ASSETS = os.path.join(ROOT, "tools", ".cache", "assets")
PUBLIC = os.path.join(ROOT, "public")
FRAGMENTS = os.path.join(ROOT, "src", "fragments")
PAGES_DIR = os.path.join(ROOT, "src", "pages")

SITE = "https://crechndo.org"
GA4_ID = "G-HZ07V9F2TE"

# Bornes de découpe du <body>. Elles sont identiques sur les 16 pages
# (vérifié par le script : toute page qui ne les contient pas fait échouer le build).
CONTENT_START = '<div id="content" class="site-content">'
CONTENT_END = "</div><!-- #content -->"
PAGE_END = "</div><!-- #page -->"

# Le vieux snippet Universal Analytics sert en réalité d'amorce au tag GA4
# (Google charge gtag.js tout seul derrière). On pose donc GA4 directement :
# même propriété, mêmes données, sans dépendre de ce pont hérité.
GA_LEGACY_RE = re.compile(
    r"[ \t]*<script>\s*\(function\(i,s,o,g,r,a,m\).*?</script>\s*", re.S
)
GA4_SNIPPET = f"""<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA4_ID}');
</script>
"""

# Balises WordPress sans objet sur un site statique.
PURGE = [
    r"[ \t]*<link[^>]+rel=[\"']pingback[\"'][^>]*>\s*",
    r"[ \t]*<link[^>]+rel=[\"']https://api\.w\.org/[\"'][^>]*>\s*",
    r"[ \t]*<link[^>]+rel=[\"']EditURI[\"'][^>]*>\s*",
    r"[ \t]*<link[^>]+rel=[\"']wlwmanifest[\"'][^>]*>\s*",
    r"[ \t]*<link[^>]+rel=[\"']shortlink[\"'][^>]*>\s*",
    r"[ \t]*<link[^>]+rel=[\"']dns-prefetch[\"'][^>]*>\s*",
    r"[ \t]*<link[^>]+type=[\"']application/json\+oembed[\"'][^>]*>\s*",
    r"[ \t]*<link[^>]+type=[\"']text/xml\+oembed[\"'][^>]*>\s*",
    r"[ \t]*<link[^>]+type=[\"']application/json[\"'][^>]*>\s*",
    r"[ \t]*<link[^>]+type=[\"']application/rss\+xml[\"'][^>]*>\s*",
    r"[ \t]*<meta[^>]+name=[\"']generator[\"'][^>]*>\s*",
    r"[ \t]*<script type=\"speculationrules\">.*?</script>\s*",
    r"<!-- Cached by WP-Optimize.*?-->\s*",
]

# Préfixes « nus » (sans extension) utilisés par les configs JS d'Elementor.
PREFIX_MAP = [
    ("/wp-content/plugins/elementor/assets/", "/vendor/elementor/"),
    ("/wp-content/plugins/elementor-pro/assets/", "/vendor/elementor-pro/"),
    ("/wp-content/uploads", "/img"),
]


# --------------------------------------------------------------------------- #
#  Réécriture des URLs
# --------------------------------------------------------------------------- #
def _asset_regex(sep: str) -> re.Pattern[str]:
    s = re.escape(sep)
    return re.compile(
        r"https?:" + s + s + r"(?:www\.)?crechndo\.org" + s
        + r"wp-(?:content|includes)" + s + r"[^\s\"'()<>,]+"
    )


def rewrite_assets(text: str, sep: str = "/", prefix: str = "") -> str:
    """Remplace les URLs d'assets du site d'origine par leur chemin local.

    `sep` vaut "/" dans le HTML et le CSS, et "\\/" dans le JSON embarqué dans les JS.
    `prefix` permet de produire une URL absolue (og:image, JSON-LD) au lieu d'un
    chemin racine-relatif.
    """
    def repl(m: re.Match[str]) -> str:
        url = m.group(0).replace(sep, "/") if sep != "/" else m.group(0)
        if not clean_url(url).lower().endswith(ASSET_EXT):
            return m.group(0)  # pas un fichier : traité par PREFIX_MAP
        out = prefix + "/" + local_path(url)
        return out.replace("/", sep) if sep != "/" else out

    text = _asset_regex(sep).sub(repl, text)

    for src, dst in PREFIX_MAP:
        a = (SITE + src).replace("/", sep) if sep != "/" else SITE + src
        b = (prefix + dst).replace("/", sep) if sep != "/" else prefix + dst
        text = text.replace(a, b)
    return text


def rewrite_internal_links(text: str) -> str:
    """Liens vers d'autres pages du site -> chemins racine-relatifs.

    On laisse de côté tout ce qui commence par /wp- (admin-ajax, wp-json) : ces
    URLs ne doivent surtout pas ressembler à des chemins valides du site statique.
    """
    text = re.sub(r"https?://(?:www\.)?crechndo\.org/(?!wp-)", "/", text)
    text = re.sub(r"https?://(?:www\.)?crechndo\.org(?=[\"'\s>])", "/", text)
    return text


def rewrite_js(text: str) -> str:
    return rewrite_assets(rewrite_assets(text, sep="\\/"), sep="/")


# --------------------------------------------------------------------------- #
#  Assets : cache -> public
# --------------------------------------------------------------------------- #
def copy_assets() -> int:
    count = 0
    for dirpath, _dirnames, filenames in os.walk(CACHE_ASSETS):
        for name in filenames:
            src = os.path.join(dirpath, name)
            rel = os.path.relpath(src, CACHE_ASSETS)
            dst = os.path.join(PUBLIC, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            ext = os.path.splitext(name)[1].lower()
            if ext == ".css":
                with open(src, encoding="utf-8", errors="replace") as fh:
                    css = fh.read()
                css = rewrite_assets(css)
                # Font Awesome référence ses polices en ../webfonts/… : on remappe.
                css = re.sub(
                    r"url\(\s*(['\"]?)\.\./webfonts/([^)'\"?#]+)([^)]*)\1\s*\)",
                    lambda m: f"url({m.group(1)}/fonts/{m.group(2)}{m.group(3)}{m.group(1)})",
                    css,
                )
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(css)
            elif ext == ".js":
                with open(src, encoding="utf-8", errors="replace") as fh:
                    js = fh.read()
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(rewrite_js(js))
            else:
                shutil.copy2(src, dst)
            count += 1
    return count


# --------------------------------------------------------------------------- #
#  Pages : découpe en fragments
# --------------------------------------------------------------------------- #
def purge(text: str) -> str:
    for pattern in PURGE:
        text = re.sub(pattern, "", text, flags=re.S)
    return text


def rewrite_head(head: str) -> str:
    """Réécrit le <head>.

    Les URLs de partage social (og:image, twitter:image, JSON-LD) doivent rester
    ABSOLUES : les robots des réseaux sociaux ne savent pas résoudre un chemin
    relatif. Les liens de pages (canonical, og:url) restent inchangés, eux aussi
    absolus et pointant déjà vers le bon domaine.
    """
    stash: list[str] = []

    def keep(m: re.Match[str]) -> str:
        stash.append(m.group(0))
        return f"@@KEEP{len(stash) - 1}@@"

    head = re.sub(r'<script type="application/ld\+json".*?</script>', keep, head, flags=re.S)
    head = re.sub(r"<meta[^>]*(?:og:image|twitter:image)[^>]*>", keep, head)

    head = rewrite_assets(head)

    for i, block in enumerate(stash):
        head = head.replace(f"@@KEEP{i}@@", rewrite_assets(block, prefix=SITE))
    return head


def split_page(slug: str, html: str) -> dict[str, str]:
    html = purge(html)

    # --- head -------------------------------------------------------------
    head_open = html.index("<head")
    head_start = html.index(">", head_open) + 1
    head_end = html.index("</head>")
    head = html[head_start:head_end]
    head = GA_LEGACY_RE.sub(GA4_SNIPPET, head)
    head = rewrite_head(head)

    # --- body -------------------------------------------------------------
    body_open = html.index("<body")
    body_tag_end = html.index(">", body_open) + 1
    body_tag = html[body_open:body_tag_end]
    body = html[body_tag_end:html.index("</body>")]

    for marker in (CONTENT_START, CONTENT_END, PAGE_END):
        if marker not in body:
            raise SystemExit(f"{slug}: borne de découpe introuvable -> {marker!r}")

    i_cs = body.index(CONTENT_START)
    i_ce = body.index(CONTENT_END) + len(CONTENT_END)
    i_pe = body.index(PAGE_END, i_ce) + len(PAGE_END)

    header = body[:i_cs]
    content = body[i_cs:i_ce]
    footer = body[i_ce:i_pe]
    scripts = body[i_pe:]

    prep = lambda s: rewrite_internal_links(rewrite_assets(s))  # noqa: E731

    cls = re.search(r'class="([^"]*)"', body_tag)
    return {
        "body_class": cls.group(1) if cls else "",
        "body_tag": body_tag,
        "head": head,
        "header": prep(header),
        "content": prep(content),
        "footer": prep(footer),
        "scripts": prep(scripts),
    }


# --------------------------------------------------------------------------- #
#  Menu : header neutre + état « page courante »
# --------------------------------------------------------------------------- #
# Le menu apparaît quatre fois dans le header (barre desktop + barre mobile, chacune
# avec sa version déroulante). WordPress marque la page courante avec :
#   <li>  … current-menu-item page_item page-item-<ID> current_page_item menu-item-<N>
#   <a>   … aria-current="page"  class="elementor-(sub-)item elementor-item-active …
# et son éventuel parent avec :
#   <li>  … current-menu-ancestor current-menu-parent menu-item-has-children menu-item-<N>
ACTIVE_LI_RE = re.compile(
    r'<li class="[^"]*current-menu-item[^"]*page-item-(\d+)[^"]*menu-item-(\d+)"'
)
ANCESTOR_LI_RE = re.compile(
    r'<li class="[^"]*current-menu-ancestor[^"]*menu-item-has-children menu-item-(\d+)"'
)


def neutralize_menu(html: str) -> str:
    """Retire tous les marqueurs « page courante » du menu."""
    html = re.sub(r"current-menu-item page_item page-item-\d+ current_page_item ", "", html)
    html = html.replace("current-menu-ancestor current-menu-parent ", "")
    html = html.replace(' aria-current="page"', "")
    html = html.replace("elementor-item elementor-item-active", "elementor-item")
    html = html.replace("elementor-sub-item elementor-item-active", "elementor-sub-item")
    return html


def menu_state_of(html: str) -> dict:
    """Décrit l'état du menu d'une page : quels items sont actifs, quels parents le sont.

    Le header contient DEUX menus WordPress distincts (barre desktop et barre mobile),
    chacun rendu deux fois (version principale + version déroulante) : le même lien
    porte donc plusieurs identifiants d'item. On les collecte tous.
    """
    found = ACTIVE_LI_RE.findall(html)
    page_ids = {int(pid) for pid, _ in found}
    if len(page_ids) > 1:
        raise SystemExit(f"plusieurs page-item différents dans un même menu : {page_ids}")
    return {
        "pageId": page_ids.pop() if page_ids else None,
        "activeIds": sorted({int(iid) for _, iid in found}),
        "ancestorIds": sorted({int(m) for m in ANCESTOR_LI_RE.findall(html)}),
    }


def apply_menu_state(html: str, state: dict) -> str:
    """Inverse de neutralize_menu() — doit reproduire le header d'origine à l'octet près.

    Cette fonction n'existe que pour le contrôle de non-régression ci-dessous ;
    c'est src/lib/activeMenu.js qui fait le vrai travail au build.
    """
    if not state["activeIds"]:
        return html
    page_id = state["pageId"]
    for item_id in state["activeIds"]:
        html = re.sub(
            rf'(<li class="[^"]*?)(menu-item-{item_id}">)(<a [^>]*?)(class="elementor-(?:sub-)?item )',
            lambda m: (
                f"{m.group(1)}current-menu-item page_item page-item-{page_id} current_page_item "
                f'{m.group(2)}{m.group(3)}aria-current="page" {m.group(4)}elementor-item-active '
            ),
            html,
        )
    for anc in state["ancestorIds"]:
        html = re.sub(
            rf'(<li class="[^"]*?)(menu-item-has-children menu-item-{anc}")',
            lambda m: f"{m.group(1)}current-menu-ancestor current-menu-parent {m.group(2)}",
            html,
        )
    return html


def main() -> int:
    for d in (PUBLIC, FRAGMENTS, PAGES_DIR):
        os.makedirs(d, exist_ok=True)

    print("== assets -> public/ ==")
    print(f"  {copy_assets()} fichiers")

    print("== pages ==")
    parts: dict[str, dict[str, str]] = {}
    for slug in PAGES:
        path = os.path.join(CACHE_RAW, f"{slug}.html")
        with open(path, encoding="utf-8") as fh:
            parts[slug] = split_page(slug, fh.read())

    # --- footer mutualisé -------------------------------------------------
    # On ne mutualise que si les 16 pages produisent EXACTEMENT le même HTML :
    # sinon on masquerait une différence réelle entre les pages.
    variants = {p["footer"] for p in parts.values()}
    if len(variants) != 1:
        raise SystemExit(f"footer : {len(variants)} variantes, mutualisation impossible")
    with open(os.path.join(FRAGMENTS, "footer.html"), "w", encoding="utf-8") as fh:
        fh.write(variants.pop())
    print(f"  footer.html mutualisé sur les {len(parts)} pages")

    # --- header mutualisé + état du menu ----------------------------------
    # Les 16 headers ne diffèrent que par les marqueurs « page courante » du menu.
    # On stocke donc UN header neutre, plus un petit descripteur par page, et c'est
    # le layout qui réapplique les marqueurs au build (voir src/lib/activeMenu.js).
    neutrals = {slug: neutralize_menu(p["header"]) for slug, p in parts.items()}
    distinct = set(neutrals.values())
    if len(distinct) != 1:
        for slug, n in neutrals.items():
            with open(os.path.join(FRAGMENTS, f"{slug}-header.html"), "w", encoding="utf-8") as fh:
                fh.write(n)
        raise SystemExit(f"header : {len(distinct)} variantes une fois le menu neutralisé")
    with open(os.path.join(FRAGMENTS, "header.html"), "w", encoding="utf-8") as fh:
        fh.write(distinct.pop())
    print(f"  header.html mutualisé sur les {len(parts)} pages (menu neutralisé)")

    menu_state = {slug: menu_state_of(p["header"]) for slug, p in parts.items()}
    with open(os.path.join(ROOT, "src", "lib", "menuState.js"), "w", encoding="utf-8") as fh:
        fh.write(
            "// GÉNÉRÉ par tools/build_fragments.py — ne pas éditer à la main.\n"
            "// Marqueurs « page courante » du menu, réappliqués au header mutualisé\n"
            "// au moment du build par src/lib/activeMenu.js.\n"
            "export const MENU_STATE = "
            + json.dumps(menu_state, ensure_ascii=False, indent=2)
            + ";\n"
        )
    print(f"  menuState.js ({sum(1 for v in menu_state.values() if v['activeIds'])} pages avec un item actif)")

    # Contrôle fort : réappliquer l'état doit redonner le header d'origine, à l'octet près.
    for slug, p in parts.items():
        rebuilt = apply_menu_state(neutrals[slug], menu_state[slug])
        if rebuilt != p["header"]:
            raise SystemExit(
                f"{slug}: le header reconstruit depuis le header mutualisé diffère de l'original"
            )
    print("  header reconstruit à l'identique sur les 16 pages ✓")

    # --- fragments par page ----------------------------------------------
    for slug, p in parts.items():
        for part in ("head", "content", "scripts"):
            with open(os.path.join(FRAGMENTS, f"{slug}-{part}.html"), "w", encoding="utf-8") as fh:
                fh.write(p[part])

    # --- pages .astro -----------------------------------------------------
    for slug, p in parts.items():
        astro = f"""---
// Page générée depuis {PAGES[slug]} — ne pas éditer à la main tant que la phase 1
// n'est pas terminée : relancer tools/build_fragments.py écrase ce fichier.
import BaseLayout from '../layouts/BaseLayout.astro';
import head from '../fragments/{slug}-head.html?raw';
import content from '../fragments/{slug}-content.html?raw';
import scripts from '../fragments/{slug}-scripts.html?raw';
import {{ withBase }} from '../lib/withBase.js';

const bodyClass = {json.dumps(p["body_class"], ensure_ascii=False)};
---
<BaseLayout bodyClass={{bodyClass}} slug={json.dumps(slug)}>
  <Fragment slot="head" set:html={{withBase(head)}} />
  <Fragment set:html={{withBase(content)}} />
  <Fragment slot="scripts" set:html={{withBase(scripts)}} />
</BaseLayout>
"""
        with open(os.path.join(PAGES_DIR, f"{slug}.astro"), "w", encoding="utf-8") as fh:
            fh.write(astro)
    print(f"  {len(parts)} pages .astro")

    # --- contrôle : attributs du <body> identiques ? ----------------------
    tags = {re.sub(r'class="[^"]*"', 'class="…"', p["body_tag"]) for p in parts.values()}
    if len(tags) != 1:
        print(f"  !! le <body> n'a pas les mêmes attributs partout : {tags}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
