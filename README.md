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
| `npm run check:visuel` | **Diff pixel** : 16 pages × 3 largeurs, original contre version générée. |
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
- **Page « Politique de cookies »** : elle affiche le code court
  `[cmplz-document type=…]` au lieu du texte. **Le bug vient du site d'origine**
  (extension Complianz absente) et a été reproduit à l'identique.
- **Analytics** : le site d'origine charge un vieux tag Universal Analytics qui sert
  d'amorce au tag GA4 `G-HZ07V9F2TE`. Ici GA4 est posé directement.
- **Titres et descriptions** : le site d'origine servait deux jeux de balises SEO,
  dont un écrit en dur dans le thème qui écrasait les titres propres à chaque page.
  Le bloc en dur est retiré ; les textes des 16 pages sont dans
  [`tools/seo.py`](tools/seo.py), à modifier là puis `npm run seo`.
- La galerie photos n'ouvre pas de visionneuse : c'est déjà le cas sur le site
  d'origine.
- **Lien dans une liste à icônes** : sur « Notre philosophie », le lien vers Croc La Vie
  passe à la ligne au milieu de la phrase. C'est un comportement d'Elementor, reproduit
  tel quel (`.cnd-liste-icones li a { display: flex }`).
