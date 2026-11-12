#!/usr/bin/env python3
"""Aspiration de crechndo.org (WordPress / Astra / Elementor) vers des fichiers statiques.

Ce script NE FAIT QUE TÉLÉCHARGER :
  - les 16 pages HTML brutes      -> tools/.cache/raw/<slug>.html
  - tous les assets référencés    -> tools/.cache/assets/{css,js,fonts,img,vendor}/...

Rien n'est écrit dans public/ : c'est build_fragments.py qui y recopie les assets
en réécrivant leurs URLs, pour que l'opération reste rejouable à volonté.

La transformation (nettoyage du HTML, réécriture des URLs, découpe en fragments)
est faite par build_fragments.py, pour qu'on puisse la rejouer sans re-télécharger.

Usage :  python3 tools/mirror.py [--force]
"""
from __future__ import annotations

import os
import posixpath
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HOST_RE = r"(?:www\.)?crechndo\.org"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", ".cache", "assets")
RAW = os.path.join(ROOT, "tools", ".cache", "raw")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)

# slug -> chemin sur le site d'origine. "index" = la page d'accueil.
PAGES = {
    "index": "/",
    "presentation": "/presentation/",
    "notre-philosophie": "/notre-philosophie/",
    "notre-equipe": "/notre-equipe/",
    "la-micro-creche": "/la-micro-creche/",
    "decouvrir-en-photos": "/decouvrir-en-photos/",
    "nous-situer": "/nous-situer/",
    "l-accueil-de-votre-enfant-de-a-a-z": "/l-accueil-de-votre-enfant-de-a-a-z/",
    "la-journee-de-votre-enfant": "/la-journee-de-votre-enfant/",
    "offres-et-tarifs": "/offres-et-tarifs/",
    "nous-contacter": "/nous-contacter/",
    "nos-partenaires": "/nos-partenaires/",
    "on-parle-de-nous": "/on-parle-de-nous/",
    "plan-du-site": "/plan-du-site/",
    "politique-de-cookies-ue": "/politique-de-cookies-ue/",
    "mentions-legales": "/mentions-legales/",
}

# Toute URL d'asset hébergée sur le site d'origine.
ASSET_RE = re.compile(r"https?://" + HOST_RE + r"/wp-(?:content|includes)/[^\s\"'()<>,\\]+")

# Elementor charge certains modules à la demande, en construisant l'URL à l'exécution :
#   elementorFrontendConfig.urls.assets + "js/chunks/<nom>.min.js"
# Ces fichiers n'apparaissent donc nulle part dans le HTML : on les liste à la main
# (noms extraits des appels loadChunk() des bundles) et on les aspire dans
# public/vendor/elementor/, qui devient la nouvelle valeur de urls.assets.
ELEMENTOR_CHUNKS = [
    "accordion", "alert", "background-slideshow", "background-video",
    "contact-buttons", "container-grid-container", "container-shapes", "counter",
    "floating-bars", "handles-position", "image-carousel", "lightbox-lightbox",
    "nested-accordion", "nested-tabs", "progress", "section-shapes",
    "section-stretched-section", "tabs", "text-editor", "text-path", "toggle",
    "video", "wp-audio",
]
ELEMENTOR_ASSETS_URL = "https://crechndo.org/wp-content/plugins/elementor/assets/"

# Même chose pour les bibliothèques qu'Elementor va chercher à la volée (lightbox,
# boîtes de dialogue, Swiper…). Leur URL est construite à l'exécution à partir de
# urls.assets : l'arborescence doit donc être conservée telle quelle sous vendor/.
ELEMENTOR_RUNTIME_ASSETS = [
    "css/conditionals/dialog.min.css",
    "css/conditionals/lightbox.min.css",
    "lib/dialog/dialog.min.js",
    "lib/share-link/share-link.min.js",
    "lib/swiper/v8/swiper.min.js",
    "lib/swiper/v8/css/swiper.min.css",
]

ASSET_EXT = (
    ".css", ".js",
    ".webp", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".avif",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp4", ".webm",
)
FONT_EXT = (".woff", ".woff2", ".ttf", ".eot", ".otf")

_seen: dict[str, str] = {}      # url nettoyée -> chemin local relatif au cache
_css_queue: list[tuple[str, str]] = []


def clean_url(url: str) -> str:
    """Retire l'ancre, la query et décode les entités HTML d'une URL."""
    url = url.replace("&#038;", "&").replace("&amp;", "&")
    return url.split("#")[0].split("?")[0]


def local_path(url: str) -> str:
    """URL d'origine -> chemin local (css/, js/, fonts/, img/, vendor/)."""
    path = posixpath.normpath(urllib.parse.urlparse(clean_url(url)).path)
    base = posixpath.basename(path)
    ext = posixpath.splitext(base)[1].lower()

    if ext == ".css":
        return "css/" + base
    if ext == ".js":
        return "js/" + base
    if ext in FONT_EXT:
        return "fonts/" + base
    # Un .svg peut être une police d'icônes ou une image : on tranche sur le dossier.
    if ext == ".svg" and re.search(r"/(fonts?|webfonts)/", path):
        return "fonts/" + base
    if path.startswith("/wp-content/uploads/"):
        return "img/" + path[len("/wp-content/uploads/"):]
    # plugins/themes : images de thème, on aplatit
    return "img/_theme/" + base


def fetch(url: str, tries: int = 3) -> bytes:
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"échec du téléchargement de {url} : {last}")


def download_asset(url: str, force: bool = False) -> str | None:
    """Télécharge un asset et renvoie son chemin local (relatif au cache)."""
    key = clean_url(url)
    if key in _seen:
        return _seen[key]

    rel = local_path(key)
    dest = os.path.join(CACHE, rel)

    # Collision : deux URLs différentes qui atterriraient au même endroit.
    for other_url, other_rel in _seen.items():
        if other_rel == rel and other_url != key:
            print(f"  !! COLLISION {rel}\n     {other_url}\n     {key}", file=sys.stderr)

    if force or not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            data = fetch(key)
        except RuntimeError as exc:
            print(f"  ÉCHEC {exc}", file=sys.stderr)
            return None
        with open(dest, "wb") as fh:
            fh.write(data)
        print(f"  + {rel}")

    _seen[key] = rel
    if rel.endswith(".css"):
        _css_queue.append((key, rel))
    return rel


def asset_urls(text: str) -> list[str]:
    """URLs d'assets (avec extension connue) trouvées dans un blob HTML ou CSS."""
    found = {clean_url(m.group(0)) for m in ASSET_RE.finditer(text)}
    return sorted(u for u in found if u.lower().endswith(ASSET_EXT))


CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)")


def css_relative_urls(css: str, css_url: str) -> list[str]:
    """url() relatifs d'une feuille de style, résolus en URLs absolues.

    Font Awesome, par exemple, référence ses polices en ../webfonts/… : sans ça
    les icônes du site tomberaient en 404.
    """
    out = []
    for m in CSS_URL_RE.finditer(css):
        raw = m.group(2).strip()
        if raw.startswith(("data:", "http://", "https://", "//", "#")):
            continue
        out.append(urllib.parse.urljoin(css_url, clean_url(raw)))
    return sorted(set(u for u in out if u.lower().endswith(ASSET_EXT)))


def download_elementor_chunks(force: bool = False) -> None:
    """Aspire les fichiers Elementor chargés dynamiquement vers vendor/elementor/."""
    subpaths = [f"js/chunks/{name}.min.js" for name in ELEMENTOR_CHUNKS]
    subpaths += ELEMENTOR_RUNTIME_ASSETS
    for sub in subpaths:
        rel = f"vendor/elementor/{sub}"
        dest = os.path.join(CACHE, rel)
        if not force and os.path.exists(dest):
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            data = fetch(ELEMENTOR_ASSETS_URL + sub)
        except RuntimeError as exc:
            print(f"  ÉCHEC {exc}", file=sys.stderr)
            continue
        with open(dest, "wb") as fh:
            fh.write(data)
        print(f"  + {rel}")


def main() -> int:
    force = "--force" in sys.argv
    os.makedirs(RAW, exist_ok=True)

    # 1. Les pages HTML
    print("== pages ==")
    html_by_slug: dict[str, str] = {}
    for slug, path in PAGES.items():
        dest = os.path.join(RAW, f"{slug}.html")
        if force or not os.path.exists(dest):
            data = fetch("https://crechndo.org" + path)
            with open(dest, "wb") as fh:
                fh.write(data)
            print(f"  + {slug}.html ({len(data)} o)")
        with open(dest, encoding="utf-8") as fh:
            html_by_slug[slug] = fh.read()

    # 2. Les assets référencés par les pages
    print("== assets des pages ==")
    for slug, html in html_by_slug.items():
        for url in asset_urls(html):
            download_asset(url, force)

    # 3. Les assets référencés par les CSS (polices, images de fond), en cascade
    print("== assets des CSS ==")
    i = 0
    while i < len(_css_queue):
        css_url, rel = _css_queue[i]
        i += 1
        with open(os.path.join(CACHE, rel), encoding="utf-8", errors="replace") as fh:
            css = fh.read()
        for url in asset_urls(css):
            download_asset(url, force)
        for url in css_relative_urls(css, css_url):
            download_asset(url, force)

    # 4. Les modules Elementor chargés à l'exécution (invisibles dans le HTML)
    print("== chunks Elementor ==")
    download_elementor_chunks(force)

    print(f"\n{len(_seen)} assets, {len(html_by_slug)} pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
