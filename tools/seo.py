#!/usr/bin/env python3
"""Titres et descriptions des 16 pages, et application dans les fragments <head>.

POURQUOI CE FICHIER
-------------------
Le site d'origine servait DEUX jeux de balises SEO par page :

  1. un bloc écrit en dur dans l'en-tête du thème, identique sur les 16 pages ;
  2. le bloc de Rank Math, lui propre à chaque page.

Le premier arrivait avant le second : c'est donc le titre générique qui gagnait,
sur les 16 pages. La Search Console le confirme — les pages intérieures
cumulaient 5 786 impressions pour 60 clics, soit 1 % de taux de clic, là où
l'accueil en faisait 2,3 %.

Ce script retire le bloc en dur et réécrit le bloc restant avec les textes
ci-dessous. C'est ici qu'on modifie un titre ou une description : on relance
`python3 tools/seo.py`, qui réécrit les fragments.

RÈGLES D'ÉCRITURE
-----------------
- Titre : 60 caractères au plus, sinon Google le coupe.
- Description : 150 à 160 caractères. Elle ne pèse pas sur le classement, mais
  c'est elle qui décide du clic.
- Le nom de la marque à la fin, sauf sur l'accueil où il porte la requête.
- Un titre par page, qui décrit CETTE page : deux pages qui se ressemblent se
  concurrencent sur la même requête.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAGMENTS = os.path.join(ROOT, "src", "fragments")
MARQUEUR = "<!-- réécrit à la main (phase 2) -->"

# Les requêtes qui amènent déjà du monde, relevées sur 12 mois dans la Search
# Console. Elles guident le choix des mots des titres.
#
#   creche saint laurent blangy      730 impressions   54 clics
#   creche arras (+ variantes)     1 278 impressions   19 clics
#   crech'n'do (+ variantes)       2 102 impressions   58 clics
#   creche saint nicolas              73 impressions    1 clic
#   creche autour de moi             122 impressions    6 clics

SEO: dict[str, tuple[str, str]] = {
    "index": (
        "Micro-crèche à Saint-Laurent-Blangy, près d'Arras",
        "Micro-crèche écologique à 5 min d'Arras : 10 places, repas 100 % bio, "
        "couches lavables, 7h-19h du lundi au vendredi, dès 10 semaines.",
    ),
    "presentation": (
        "Qui sommes-nous ? La micro-crèche Crèch'n'do",
        "Ouverte depuis 2012 à Saint-Laurent-Blangy, Crèch'n'do est née de la "
        "rencontre de parents et de professionnels de la petite enfance.",
    ),
    "notre-philosophie": (
        "Notre philosophie : écologie, bio et respect de l'enfant",
        "Repas 100 % bio, couches lavables, respect des choix éducatifs et fort "
        "taux d'encadrement : la philosophie de notre micro-crèche près d'Arras.",
    ),
    "notre-equipe": (
        "Notre équipe de la petite enfance | Crèch'n'do",
        "Éducatrice de jeunes enfants, auxiliaire de puériculture et "
        "aides-auxiliaires : les professionnelles qui accueillent votre enfant.",
    ),
    "la-micro-creche": (
        "Le lieu : nos espaces d'accueil à Saint-Laurent-Blangy",
        "Une maison de 104 m² refaite à neuf : salle d'activités, espace change, "
        "dortoirs, jardin et potager, au 54 rue Henri Barbusse.",
    ),
    "decouvrir-en-photos": (
        "La micro-crèche en photos | Crèch'n'do",
        "Visite en images de notre micro-crèche de Saint-Laurent-Blangy : hall "
        "d'accueil, salle de jeux, dortoirs et espaces extérieurs.",
    ),
    "nous-situer": (
        "Nous situer : micro-crèche près d'Arras (62)",
        "54 rue Henri Barbusse, 62223 Saint-Laurent-Blangy, à 5 minutes d'Arras. "
        "Plan d'accès et itinéraire vers notre micro-crèche.",
    ),
    "l-accueil-de-votre-enfant-de-a-a-z": (
        "L'accueil de votre enfant de A à Z | Crèch'n'do",
        "Adaptation, change, équipe, jeux, repas, sieste, transmissions, "
        "vacances : tout sur l'accueil de votre enfant, de A à Z.",
    ),
    "la-journee-de-votre-enfant": (
        "La journée type de votre enfant | Crèch'n'do",
        "De l'arrivée à 7h aux premiers départs à 17h : collation, activités, "
        "repas, sieste et goûter. Le déroulé d'une journée, heure par heure.",
    ),
    "offres-et-tarifs": (
        "Offres, tarifs et aides CAF | Micro-crèche Arras",
        "Un tarif horaire tout compris — repas bio, couches et produits d'hygiène —, "
        "une mensualité unique et le complément mode de garde de la CAF.",
    ),
    "nous-contacter": (
        "Nous contacter | Micro-crèche Crèch'n'do, Arras",
        "Téléphone, e-mail et adresse de la micro-crèche Crèch'n'do à "
        "Saint-Laurent-Blangy. Nous répondons à vos questions dans la journée.",
    ),
    "nos-partenaires": (
        "Nos partenaires | Micro-crèche Crèch'n'do",
        "CAF, Département du Pas-de-Calais, Pas-de-Calais Actif, Croc La Vie : "
        "les partenaires qui accompagnent notre micro-crèche.",
    ),
    "on-parle-de-nous": (
        "On parle de nous : la presse et Crèch'n'do",
        "La Voix du Nord, L'Avenir de l'Artois, L'Observateur de l'Arrageois : "
        "les articles consacrés à notre micro-crèche de Saint-Laurent-Blangy.",
    ),
    "plan-du-site": (
        "Plan du site | Crèch'n'do",
        "Toutes les pages du site de la micro-crèche Crèch'n'do à "
        "Saint-Laurent-Blangy : présentation, philosophie, équipe, tarifs, "
        "photos, partenaires et contact.",
    ),
    "politique-de-cookies-ue": (
        "Politique de cookies | Crèch'n'do",
        "Informations sur les cookies déposés par le site de la micro-crèche "
        "Crèch'n'do à Saint-Laurent-Blangy, près d'Arras, et sur la façon de "
        "les refuser.",
    ),
    "mentions-legales": (
        "Mentions légales | Crèch'n'do",
        "Éditeur, hébergeur, confidentialité et droits d'auteur du site de la "
        "micro-crèche Crèch'n'do, 54 rue Henri Barbusse à Saint-Laurent-Blangy.",
    ),
}

# Bloc écrit en dur dans l'en-tête du thème : c'est lui qui écrasait les titres
# de chaque page. On le retire en entier.
BLOC_EN_DUR = re.compile(
    r"<!-- HTML Meta Tags -->.*?"
    r"<!-- Meta Tags Generated via https://www\.opengraph\.xyz -->\s*",
    re.S,
)

# Mots-clés en vrac : Google les ignore depuis 2009, et la liste ressemble à du
# bourrage. La description qui la suit faisait double emploi avec celle de la page.
KEYWORDS = re.compile(r'<meta name="keywords"[^>]*>\s*', re.S)
DESCRIPTION_EN_DUR = re.compile(
    r'<meta name="description" content="Structure d\'accueil[^"]*"\s*/?>\s*', re.S)

# Le site de préproduction, resté dans les métadonnées et les données structurées.
RECETTE = "delphacrea.crechndo.org"


def echappe(texte: str) -> str:
    """Encode ce qui doit l'être dans un attribut HTML."""
    return texte.replace("&", "&amp;").replace('"', "&quot;").replace("'", "&#039;")


def applique(slug: str, head: str, titre: str, description: str) -> str:
    head = BLOC_EN_DUR.sub("", head)
    head = KEYWORDS.sub("", head)
    head = DESCRIPTION_EN_DUR.sub("", head)
    head = head.replace(RECETTE, "crechndo.org")

    # Le titre et la description de la page, dans les trois familles de balises.
    # Deux pages n'avaient aucune description : on la pose alors après le titre.
    head = re.sub(r"<title>.*?</title>", f"<title>{echappe(titre)}</title>", head, flags=re.S)
    for attribut, nom, valeur in (
        ("name", "description", description),
        ("property", "og:description", description),
        ("name", "twitter:description", description),
        ("property", "og:title", titre),
        ("name", "twitter:title", titre),
    ):
        balise = f'<meta {attribut}="{nom}" content="{echappe(valeur)}" />'
        motif = rf'<meta {attribut}="{re.escape(nom)}" content="[^"]*"\s*/?>'
        if re.search(motif, head):
            head = re.sub(motif, balise, head)
        else:
            head = head.replace("</title>", "</title>\n" + balise, 1)

    # Une page n'avait pas de balise canonique : on la pose à partir du slug.
    if 'rel="canonical"' not in head:
        chemin = "/" if slug == "index" else f"/{slug}/"
        head = head.replace(
            "</title>",
            f'</title>\n<link rel="canonical" href="https://crechndo.org{chemin}" />', 1)

    # Horaires réels, repris du contenu du site : lundi-vendredi, 7h-19h.
    head = head.replace(
        '"openingHours":["Mo,Tu,We,Th,Fr,Sa,Su 09:00-17:00"]',
        '"openingHours":["Mo,Tu,We,Th,Fr 07:00-19:00"]')
    # Dans le JSON des données structurées, l'apostrophe du nom était échappée
    # deux fois : Google lisait le nom antislash compris. On retire l'antislash
    # surnuméraire (deux antislashs suivis d'une apostrophe).
    head = head.replace(chr(92) * 2 + "'", "'")

    # Les données structurées portaient elles aussi le titre générique du site,
    # sur les nœuds WebPage et Article. On les relit en JSON plutôt qu'à coups
    # d'expressions régulières : le bloc est trop imbriqué pour ça.
    def recale(bloc: re.Match) -> str:
        try:
            donnees = json.loads(bloc.group(1))
        except ValueError:
            return bloc.group(0)
        for noeud in donnees.get("@graph", []):
            if noeud.get("@type") in ("WebPage", "Article"):
                for champ in ("name", "headline"):
                    if champ in noeud:
                        noeud[champ] = titre
                if "description" in noeud:
                    noeud["description"] = description
        return bloc.group(0).replace(
            bloc.group(1), json.dumps(donnees, ensure_ascii=False, separators=(",", ":")))

    head = re.sub(
        r'(?<=<script type="application/ld\+json" class="rank-math-schema">)(.*?)(?=</script>)',
        recale, head, flags=re.S)

    return head


def main() -> int:
    trop_long = []
    for slug, (titre, description) in SEO.items():
        chemin = os.path.join(FRAGMENTS, f"{slug}-head.html")
        head = io.open(chemin, encoding="utf-8").read()
        corps = head.split("\n", 1)[1] if head.startswith(MARQUEUR) else head
        corps = applique(slug, corps, titre, description)
        io.open(chemin, "w", encoding="utf-8").write(MARQUEUR + "\n" + corps.lstrip("\n"))

        drapeau = ""
        if len(titre) > 60:
            drapeau = "  ← titre trop long"
            trop_long.append(slug)
        if not 120 <= len(description) <= 160:
            drapeau += "  ← description hors de 120-160"
        print(f"{slug:36s} {len(titre):>3}/{len(description):>3}  {titre}{drapeau}")

    print(f"\n{len(SEO)} pages réécrites.")
    return 1 if trop_long else 0


if __name__ == "__main__":
    raise SystemExit(main())
