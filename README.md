# CRECH'N'DO — site statique (Astro)

Site de la micro-crèche **Crèch'n'do** (Saint-Laurent-Blangy), reconstruit à partir du
site WordPress / Astra / Elementor d'origine en **HTML/CSS/JS statique**, assemblé
avec [Astro](https://astro.build) et hébergé sur GitHub Pages.

Le header et le footer sont **mutualisés** (écrits une seule fois) et injectés dans
chaque page **au moment du build** : le HTML livré est 100 % statique, header et footer
écrits en dur dans chaque page → SEO intact, aucun serveur, aucun JavaScript nécessaire
pour afficher la page.

> C'est du **SSG** (génération statique), pas du SSR : rien ne tourne côté serveur en
> production, on ne sert que des fichiers.

État : **phases 1 et 2 terminées** — le site est reproduit à l'identique et ne dépend
plus d'Astra, d'Elementor, de jQuery ni d'aucune police d'icônes. Tout le rendu tient
dans `public/css/site.css` (44 Ko) et `public/js/site.js` (5 Ko) ; voir
[MIGRATION-PLAN.md](MIGRATION-PLAN.md).

Le rendu est vérifié page par page contre le site d'origine : diff pixel sur
16 pages × 3 largeurs, comparaison du texte visible, contrôle des liens, des requêtes
et des comportements. Les outils sont décrits plus bas.

Le site compte **18 pages** : les 16 reprises de WordPress, plus deux pages de
proximité écrites à la main et sans original —
[`/micro-creche-arras/`](src/fragments/micro-creche-arras-content.html) et
[`/micro-creche-communes-rurales/`](src/fragments/micro-creche-communes-rurales-content.html).
Les outils qui comparent à WordPress n'en tiennent donc pas compte, contrairement à
`npm run check:seo`.

## Structure

```
src/
  layouts/BaseLayout.astro     ← squelette commun (header + footer + <body>)
  lib/
    withBase.js                ← préfixe les URLs quand le site est dans un sous-dossier
    activeMenu.js              ← marque la page courante dans le menu
  fragments/
    header.html                ← EN-TÊTE MUTUALISÉ (à éditer une seule fois)
    footer.html                ← PIED MUTUALISÉ (à éditer une seule fois)
    icons-sprite.html          ← GÉNÉRÉ — les 7 icônes du site, en SVG
    <slug>-head.html           ← GÉNÉRÉ — métadonnées de la page (titre, SEO, GA4)
    <slug>-content.html        ← contenu de la page, écrit à la main
  pages/<slug>.astro           → /<slug>/   (routing automatique)
public/
  css/site.css                 ← TOUT le style du site
  js/site.js                   ← menus, apparitions au défilement, parallaxe
  fonts/Funkids.ttf            ← la police des titres, seule police embarquée
  img/                         ← photos et illustrations
  robots.txt  .nojekyll
tools/                         ← outils de migration et de non-régression
dist/                          ← résultat du build (non versionné)
```

## Développer

```bash
npm install
```

```bash
npm run dev
```

## Construire le site à publier

```bash
npm run build
```

Le contenu de `dist/` est ce qui part en ligne. `npm run preview` le prévisualise.

## Modifier le contenu

- **Header ou footer, sur toutes les pages** : éditer `src/fragments/header.html` ou
  `src/fragments/footer.html`, une seule fois.
- **Une page** : éditer `src/fragments/<slug>-content.html`.
- **Le titre et la description d'une page** : la table `SEO` de
  [`tools/seo.py`](tools/seo.py), puis `npm run seo`. Les règles d'écriture et les
  requêtes qui amènent du trafic sont documentées dans le fichier.
- **Les autres métadonnées** : `src/fragments/<slug>-head.html`.

Les fragments de contenu sont désormais **la source de vérité** : ils sont écrits à la
main et portent en première ligne le marqueur `<!-- réécrit à la main (phase 2) -->`.
`npm run fragments` les reconnaît et les laisse intacts ; il ne régénère plus que les
`<head>` (métadonnées) et les pages `.astro`.

## Outils de migration

| Commande | Rôle |
|---|---|
| `npm run mirror` | Aspire le site d'origine dans `tools/.cache/` (pages + assets). `--force` pour tout retélécharger. |
| `npm run fragments` | Transforme le cache en `public/` + fragments + pages `.astro`. |
| `npm run check:html` | Compare le HTML généré à celui du site d'origine, balise à balise. |
| `npm run check:visuel` | **Diff pixel** : 16 pages × 3 largeurs, original contre version générée. Passer des slugs en arguments pour n'en vérifier que certaines, et `LOCAL=http://localhost:4322` si le serveur n'est pas sur le port par défaut. |
| `npm run check:runtime` | Requêtes en échec, erreurs JS, liens internes morts. |
| `npm run check:interactions` | Menus, burger, galerie, carte, coordonnées : même comportement qu'avant ? |
| `npm run check:textes` | Compare le **texte visible** de chaque page à celui du site d'origine. |
| `npm run seo` | Applique les titres et descriptions de `tools/seo.py` aux `<head>`. |
| `npm run check:seo` | Un titre unique par page, de la bonne longueur, URLs cohérentes. |

Les trois derniers ont besoin que le site soit servi. Exemple complet :

```bash
npm run build && npm run preview
```

```bash
LOCAL=http://localhost:4322 npm run check:visuel
```

Le **diff pixel est le garde-fou de la migration** : tant qu'il affiche 0 %, le rendu
n'a pas bougé. Il tourne aussi sur une seule page :
`npm run check:visuel -- nous-contacter`, et accepte `SEUIL`, `WIDTHS` et `LOCAL`.

Trois écarts résiduels sont attendus et documentés :

- **nous-contacter** : le formulaire est volontairement remplacé par les coordonnées
  cliquables (décision validée) — la moitié basse de la page diffère donc.
- **decouvrir-en-photos** : les photos sont de vraies balises `<img>` là où le site
  d'origine les posait en image de fond ; le rééchantillonnage diffère de 0,1 % de
  pixels, invisible à l'œil.
- **notre-philosophie** : 0,03 % de pixels d'anticrénelage sur les petites icônes.

## Publier sur GitHub Pages

Le déploiement est automatique (`.github/workflows/deploy.yml`) : à chaque push sur
`main`, l'action build et publie.

Mise en route (une seule fois) : le dépôt doit être **public** et
**Settings → Pages → Build and deployment → Source** réglé sur **« GitHub Actions »**.
Sans ça le build réussit mais la publication échoue avec un 404.

Ensuite, chaque push sur `main` publie le site sur
**https://p3cstudio.github.io/crechndo-web/**.

Le workflow build avec deux variables :

| Variable | Rôle |
|---|---|
| `BASE_PATH=/crechndo-web` | préfixe toutes les URLs, le site vivant dans un sous-dossier |
| `SITE_URL=https://p3cstudio.github.io` | domaine annoncé par le sitemap |

### Basculer sur le domaine crechndo.org

1. Créer `public/CNAME` contenant `crechndo.org`.
2. Dans `.github/workflows/deploy.yml`, supprimer le bloc `env:` (`BASE_PATH` et
   `SITE_URL`) : sans eux, le site se construit à la racine et le sitemap annonce
   `https://crechndo.org/…`.
3. Pointer le DNS vers GitHub Pages, puis renseigner le domaine dans
   **Settings → Pages → Custom domain**.

Rien d'autre à changer : la gestion du base path devient automatiquement inactive à la
racine, aussi bien dans le HTML (`src/lib/withBase.js`) que dans les CSS/JS
(`baseInAssets()` dans `astro.config.mjs`).

## Points connus

- **Formulaire de contact** : celui du site d'origine postait vers WordPress et ne
  pouvait pas fonctionner sur un hébergement statique. Il est remplacé par les
  coordonnées cliquables — adresse électronique, téléphone, adresse postale. C'est le
  seul endroit du site qui s'écarte volontairement de l'original.
- **Page « Politique de cookies » réécrite** : elle affichait le code court
  `[cmplz-document type=…]` au lieu du texte — bug hérité du site d'origine
  (extension Complianz désinstallée), d'abord reproduit à l'identique. Le texte
  décrit maintenant ce que le site fait réellement, vérifié dans un navigateur
  après vidage des cookies : aucun cookie de première partie, pas de
  `localStorage` ni de `sessionStorage`, aucun script tiers. **À revérifier si
  l'on réintroduit un traceur, une vidéo intégrée ou un bouton social.**
- **Analytics retiré** : le site d'origine chargeait un vieux tag Universal Analytics
  qui amorçait le tag GA4 `G-HZ07V9F2TE`. Les deux sont supprimés. L'exemption de
  consentement que la CNIL prévoit pour la mesure d'audience ne couvre pas Google
  Analytics, dont l'éditeur réutilise les données pour son propre compte : il aurait
  fallu un bandeau de consentement. Le traceur pesait **178 Ko** sur les 334 Ko de la
  page d'accueil, et les arbitrages SEO se font dans la Search Console, qui ne dépose
  rien sur le site. La purge est dans `ANALYTICS`, au début de
  [`tools/seo.py`](tools/seo.py) ; `tools/build_fragments.py` n'injecte plus rien.
- **reCAPTCHA retiré** : `/nous-contacter/` chargeait encore
  `google.com/recaptcha/api.js` pour un formulaire qui n'existe plus depuis qu'il a été
  remplacé par des coordonnées cliquables. Appel à Google à chaque visite, zéro usage.
- **Un seul tiers subsiste** : la carte Google Maps intégrée sur `/nous-situer/`. C'est
  la seule ressource externe chargée par le site, toutes pages confondues.
- **Réseaux sociaux** : les balises `twitter:` ont été retirées, la crèche n'ayant pas
  de compte X. Facebook, Instagram, WhatsApp et LinkedIn lisent Open Graph, conservé.
  Le compte Instagram est dans `RESEAUX`, au début de
  [`tools/seo.py`](tools/seo.py).
- **Fiche de l'établissement** : adresse, position, téléphone, courriel et communes
  desservies sont déclarés dans les données structurées (`tools/seo.py`). C'est ce que
  Google lit pour relier le site à la fiche Google Business.
- **Titres et descriptions** : le site d'origine servait deux jeux de balises SEO,
  dont un écrit en dur dans le thème qui écrasait les titres propres à chaque page.
  Le bloc en dur est retiré ; les textes des 18 pages sont dans
  [`tools/seo.py`](tools/seo.py), à modifier là puis `npm run seo`.
- **Pages de proximité** : `/micro-creche-arras/` répond à « crèche Arras »,
  la requête la plus demandée du site (1 278 impressions sur 12 mois, position
  moyenne 18) ; `/micro-creche-communes-rurales/` couvre Athies, Feuchy, Fampoux,
  Gavrelle et Roeux **en une seule page**, parce que quatre de ces cinq communes
  totalisent zéro impression sur 12 mois — cinq pages se seraient partagé une
  demande qui n'en nourrit pas une. Les deux sont reliées depuis « Le lieu »,
  « Nous situer », « Présentation », « Offres » et le plan du site, et se citent
  l'une l'autre, mais **pas depuis le menu**, qui reste celui d'origine.
- **Pied de page** : la colonne « Mots clés » listait cinq mots dans des `<span>`
  (bourrage de mots-clés, sans lien). Elle est devenue « Nous trouver » et porte les
  deux pages de proximité, « Nous situer » et « Nous contacter » — mêmes mots, mais
  en liens vers du contenu réel, et présents sur les 18 pages. Cette colonne-là ne
  change pas la hauteur : « Informations », plus haute, dicte la mesure.
  La **politique de cookies** a ensuite été ajoutée à « Informations », qui passe à
  sept entrées. Seul effet : **+25 px à partir de 1025 px de large**. En dessous, les
  colonnes se répartissent sur deux rangées et c'est la colonne du logo (logo +
  adresse sur deux lignes) qui fixe la hauteur, donc rien ne bouge ; sous 768 px la
  bande est masquée.
- **Images redimensionnées** : dix images étaient servies bien plus grandes que
  leur emplacement. Deux causes distinctes.
  Les cinq photos de la galerie n'avaient **aucun `srcset`** : 2560 px pour un
  emplacement de 553 px. Trois variantes 1024 px ont été produites au besoin
  (`cwebp -q 90 -resize 1024 0`), les deux autres existaient déjà.
  Les cinq autres (logos partenaires, portrait de l'équipe, bandeau de presse)
  avaient un `srcset`
  complet mais un **`sizes` mensonger** hérité de WordPress — `(max-width: 1024px)
  100vw, 1024px` — alors qu'Elementor les affiche dans des colonnes de 165 à
  325 px. Seul le `sizes` a été corrigé, aucun fichier ajouté.
  Résultat à densité 1 : **1062 Ko → 342 Ko, soit −719 Ko (68 %)**. Les largeurs
  des `sizes` sont **mesurées dans le navigateur** à 375, 768 et 1440 px : les
  réécrire au jugé ramène le problème.
- **Coordonnées actionnables** : dans le pied de page, l'adresse mène à l'itinéraire
  Google Maps, le téléphone est un lien `tel:`, le courriel un `mailto:`, et un lien
  pointe vers les avis Google de la fiche (`maps?cid=1781165689255930395`, soit le
  CID `0x18b7f8c1e236aa1b` relevé sur la fiche). Le numéro de la barre haute est
  lui aussi devenu cliquable. Un soulignement discret a été ajouté
  (`.cnd-pied .cnd-pied-coord a`) : sans lui, rien ne distinguait ces liens du texte.
  Coût mesuré : **+38 px à partir de 1025 px, +7 px entre 768 et 1024**.
- **Pied de page affiché sur mobile** : le site d'origine le masquait entièrement
  sous 768 px (`.cnd-pied-haut { display: none }`). La barre haute l'étant aussi,
  ni l'adresse, ni le numéro, ni le courriel n'apparaissaient nulle part sur un
  téléphone — c'est-à-dire là où un lien `tel:` sert le plus. Les colonnes
  s'empilent désormais : la marque sur toute la largeur, les quatre colonnes de
  liens deux par deux. Empilées une par une, la bande atteignait 946 px ; sur
  deux rangs elle fait **775 px à 375 px**, sans débordement horizontal. C'est le
  même parti que nidenvol, qui passe de 4 à 2 puis 1 colonne et ne masque jamais
  son pied de page.
  Les liens de contact passent à 14 px et reçoivent du rembourrage sur mobile :
  la zone tactile passe de **14 px à 37 px de haut**. Sans `inline-block`, le
  rembourrage vertical d'un élément en ligne n'agrandirait pas la zone cliquable.
- **Distances** : celles de `/micro-creche-communes-rurales/` sont calculées à vol
  d'oiseau entre les coordonnées de la crèche et celles relevées sur OpenStreetMap,
  pas estimées. Les recalculer avant de les modifier.
- **Pictogrammes** : les noms de fichiers hérités de WordPress ne décrivent pas
  leur contenu (`…CRECHE-ARRAS.webp` est un symbole €, `…ECO-RESPONSABLE.webp`
  une calculatrice, `…ATHIES-FEUCHY.webp` un calendrier). Les ouvrir avant de
  les réutiliser.
- La galerie photos n'ouvre pas de visionneuse : c'est déjà le cas sur le site
  d'origine.
- **Lien dans une liste à icônes** : sur « Notre philosophie », le lien vers Croc La Vie
  passe à la ligne au milieu de la phrase. C'est un comportement d'Elementor, reproduit
  tel quel (`.cnd-liste-icones li a { display: flex }`).
