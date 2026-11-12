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

État : **phase 1 terminée** — le site est reproduit à l'identique, librairies WordPress
comprises. La phase 2 (suppression d'Astra, Elementor, jQuery et Font Awesome) reste à
faire ; voir [MIGRATION-PLAN.md](MIGRATION-PLAN.md).

## Structure

```
src/
  layouts/BaseLayout.astro     ← squelette commun (header + footer + <body>)
  lib/
    withBase.js                ← préfixe les URLs quand le site est dans un sous-dossier
    activeMenu.js              ← remet les marqueurs « page courante » dans le menu
    menuState.js               ← GÉNÉRÉ — quel item de menu est actif, page par page
  fragments/
    header.html                ← HEADER MUTUALISÉ (à éditer une seule fois)
    footer.html                ← FOOTER MUTUALISÉ (à éditer une seule fois)
    <slug>-head.html           ← <head> propre à la page
    <slug>-content.html        ← contenu propre à la page
    <slug>-scripts.html        ← scripts de fin de page
  pages/<slug>.astro           → /<slug>/   (routing automatique)
public/
  css/ js/ fonts/ img/         ← assets du site d'origine, URLs racine-relatives
  vendor/elementor/            ← modules Elementor chargés à l'exécution
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
- **Le titre, la description, les métadonnées d'une page** :
  `src/fragments/<slug>-head.html`.

⚠️ Tant que la phase 1 n'est pas close, relancer `npm run fragments` **écrase** les
fragments et les pages `.astro` à partir du cache d'aspiration. À partir de la phase 2,
les fragments deviennent la source de vérité et cette commande ne doit plus être lancée.

## Outils de migration

| Commande | Rôle |
|---|---|
| `npm run mirror` | Aspire le site d'origine dans `tools/.cache/` (pages + assets). `--force` pour tout retélécharger. |
| `npm run fragments` | Transforme le cache en `public/` + fragments + pages `.astro`. |
| `npm run check:html` | Compare le HTML généré à celui du site d'origine, balise à balise. |
| `npm run check:visuel` | **Diff pixel** : 16 pages × 3 largeurs, original contre version générée. |
| `npm run check:runtime` | Requêtes en échec, erreurs JS, liens internes morts. |
| `npm run check:interactions` | Menus, burger, galerie, carte, formulaire : même comportement qu'avant ? |

Les trois derniers ont besoin que le site soit servi. Exemple complet :

```bash
npm run build && npm run preview
```

```bash
LOCAL=http://localhost:4322 npm run check:visuel
```

Le **diff pixel est le garde-fou de la phase 2** : tant qu'il affiche 0 %, le rendu n'a
pas bougé. Il tourne aussi sur une seule page : `npm run check:visuel -- nous-contacter`.

## Publier sur GitHub Pages

Le déploiement est automatique (`.github/workflows/deploy.yml`) : à chaque push sur
`main`, l'action build et publie.

Mise en route (une seule fois) :

1. Le dépôt GitHub doit être **public**.
2. **Settings → Pages → Build and deployment → Source = « GitHub Actions »**.
3. Pousser sur `main` → le site sort sur **https://p3cstudio.github.io/crechndo-web/**

Le workflow build avec `BASE_PATH=/crechndo-web` (sous-dossier de l'URL github.io).

### Basculer sur le domaine crechndo.org

1. Créer `public/CNAME` contenant `crechndo.org`.
2. Dans `.github/workflows/deploy.yml`, supprimer les deux lignes `env:` / `BASE_PATH`.
3. Pointer le DNS vers GitHub Pages, puis renseigner le domaine dans
   **Settings → Pages → Custom domain**.

Rien d'autre à changer : la gestion du base path devient automatiquement inactive à la
racine, aussi bien dans le HTML (`src/lib/withBase.js`) que dans les CSS/JS
(`baseInAssets()` dans `astro.config.mjs`).

## Points connus

- **Formulaire de contact** : celui du site d'origine poste vers WordPress et ne peut
  pas fonctionner sur un hébergement statique. Il est pour l'instant reproduit tel quel,
  donc inopérant ; il sera remplacé en phase 2 par les coordonnées cliquables.
- **Page « Politique de cookies »** : elle affiche le code court
  `[cmplz-document type=…]` au lieu du texte. **Le bug vient du site d'origine**
  (extension Complianz absente) et a été reproduit à l'identique.
- **Analytics** : le site d'origine charge un vieux tag Universal Analytics qui sert
  d'amorce au tag GA4 `G-HZ07V9F2TE`. Ici GA4 est posé directement.
- **Métadonnées SEO** : les 16 pages partagent le même `<title>` et la même
  `meta description` — fidèle à l'original, mais à corriger un jour.
- La galerie photos n'ouvre pas de lightbox : c'est déjà le cas sur le site d'origine.
