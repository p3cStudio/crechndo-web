# Migration crechndo.org — WordPress ➜ HTML/JS pur (Astro + GitHub Pages)

> Analyse réalisée le 11/11/2026 sur https://crechndo.org
> Site de référence pour la méthode : `../nidenvol-html`

---

## 1. Analyse du site existant

### 1.1 Stack technique

| Élément | crechndo.org | nidenvol.fr (déjà migré) |
|---|---|---|
| Thème WP | **Astra 4.14.2** + Astra Pro (astra-addon 4.13.12) + `astra-child` | Hello Elementor |
| Page builder | **Elementor 4.3.6** + **Elementor Pro** | Elementor 3.35 + Pro |
| SEO | Rank Math | Rank Math |
| Optimisation | **WP-Optimize Minify** (bundles CSS/JS concaténés) | aucune (fichiers séparés) |
| Polices | « fun-kids » (Funkids.ttf, plugin Custom Fonts), Font Awesome 5.15.3, eicons, icônes custom « creche » | Poppins/Roboto locales |
| Analytics | `analytics.js` avec `UA-24729931-1`, qui **amorce automatiquement le tag GA4 `G-HZ07V9F2TE`** (pont hérité Google, `is_legacy_loaded:true`) — la collecte GA4 fonctionne bel et bien | — |

Différence structurelle importante avec nidenvol : ici le CSS/JS est **pré-bundlé** par WP-Optimize.
Un seul CSS de header (≈ 377 Ko) + 5 bundles JS (≈ 755 Ko) + 12 petits CSS Elementor par widget.
Le CSS Elementor spécifique à chaque page est **inliné** dans le `<head>` (blocs `optimize_css_2`).

### 1.2 Pages (16)

| # | URL | Sections | Widgets | Particularité |
|---|---|---:|---:|---|
| 1 | `/` | 14 | 44 | accueil |
| 2 | `/presentation/` | 12 | 38 | |
| 3 | `/notre-philosophie/` | 15 | 55 | page la plus riche |
| 4 | `/notre-equipe/` | 10 | 31 | portraits équipe |
| 5 | `/la-micro-creche/` | 9 | 30 | |
| 6 | `/decouvrir-en-photos/` | 8 | 26 | **galerie masonry + lightbox** |
| 7 | `/nous-situer/` | 8 | 26 | **iframe Google Maps** |
| 8 | `/l-accueil-de-votre-enfant-de-a-a-z/` | 15 | 53 | |
| 9 | `/la-journee-de-votre-enfant/` | 17 | 56 | |
| 10 | `/offres-et-tarifs/` | 10 | 34 | 2× `<h1>` |
| 11 | `/nous-contacter/` | 9 | 26 | **formulaire Elementor Pro + reCAPTCHA v3** |
| 12 | `/nos-partenaires/` | 10 | 32 | logos partenaires |
| 13 | `/on-parle-de-nous/` | 13 | 38 | revue de presse |
| 14 | `/plan-du-site/` | 8 | 22 | widget sitemap (HTML statique) |
| 15 | `/politique-de-cookies-ue/` | 7 | 21 | |
| 16 | `/mentions-legales/` | 8 | 22 | **absente du sitemap.xml** mais liée depuis le footer |

### 1.3 Composants Elementor utilisés

`heading`, `text-editor`, `image`, `image-box`, `icon-list`, `icon`, `button`, `spacer`,
`theme-site-logo`, `nav-menu` (header), `gallery` (1×), `google_maps` (1×), `form` (1×), `sitemap` (1×).

Header = template Elementor **#31** (identique sur les 16 pages).
Footer = template Elementor **#88** (identique sur les 16 pages, 5 colonnes + variante mobile).

### 1.4 Navigation

```
Accueil
Présentation ▾   Présentation Générale · Notre philosophie · Notre équipe
La micro crèche ▾  Le lieu · Découvrir en photos · Nous situer
Parents ▾        L'accueil de votre enfant de A à Z · La journée de votre enfant
Offres
Nous contacter
Pré-Inscription        ➜ externe  http://inscription.crechndo.org/preinscription
Postuler ▾       Pour un poste (Airtable) · Pour un apprentissage (Airtable)
```

Rendu : 2 `<nav>` (desktop + dropdown mobile) pilotés par **SmartMenus/jQuery**.
Point de rupture mobile Astra : **921 px**. Breakpoints Elementor : 767 / 1024 px.

### 1.5 Assets

- **136 fichiers uniques**, **5,5 Mo** au total — très confortable pour GitHub Pages.
- 90 `.webp` + 8 `.png` + 1 `.jpg` + 1 `.svg` (dont les variantes `srcset`).
- Polices : `Funkids.ttf`, famille d'icônes custom `creche.{eot,ttf,woff,woff2}`, `eicons.*`, Font Awesome `solid`/`brands`.
- ⚠️ Open Sans et Montserrat sont déclarées en CSS mais **jamais chargées** : le rendu actuel repose
  sur les polices système. Il faudra conserver exactement la même pile de polices pour rester à l'identique.

### 1.6 Points bloquants pour un hébergement statique

| Point | Impact | Traitement |
|---|---|---|
| **Formulaire de contact** Elementor Pro (POST `admin-ajax.php` + reCAPTCHA v3) | ne fonctionnera pas sur GitHub Pages | ➜ décision à prendre (voir section 4) |
| Google Analytics chargé via le pont hérité UA ➜ GA4 | fonctionne, mais dépend d'un mécanisme de transition que Google peut couper | ➜ poser le tag GA4 `G-HZ07V9F2TE` en direct |
| `wp-json`, oEmbed, RSS, pingback, speculationrules, emoji | inutiles | supprimés |
| Avatar Gravatar dans le JSON-LD | appel externe inutile | supprimé |

### 1.7 Observations annexes (hors périmètre « à l'identique »)

- **SEO** : les 16 pages partagent *exactement* le même `<title>`, la même `meta description` et le même
  `og:title`. C'est une faiblesse réelle — corrigeable en phase 3 si tu le souhaites.
- Léger **débordement horizontal en mobile** sur l'accueil (visible sur le site actuel).
- L'événement GA4 `pré_inscription` n'est **pas** déclaré dans le code du site : c'est une règle
  configurée côté GA4 (à partir des clics sortants). Elle survivra à la migration tant que le lien
  vers `inscription.crechndo.org` reste un lien externe — à revérifier après mise en ligne.
- Le lien footer « Accueil » pointe vers `https://www.crechndo.org/` (avec `www`) alors que le site
  canonique est sans `www`.

---

## 2. Architecture cible

Identique à `nidenvol-html` : **Astro 7 en SSG pur**, header/footer mutualisés et injectés *au build*
(`set:html`), donc écrits en dur dans chaque page livrée → SEO parfait, zéro serveur.

```
crechndo-html/
├── astro.config.mjs          site: https://crechndo.org · base: BASE_PATH||'/' · sitemap + lastmod git
├── package.json              astro ^7 + @astrojs/sitemap
├── .github/workflows/deploy.yml
├── public/
│   ├── css/  js/  fonts/  img/        (assets aspirés, URLs racine-relatives)
│   ├── CNAME  robots.txt  .nojekyll  404.html
├── src/
│   ├── layouts/BaseLayout.astro
│   ├── lib/withBase.js                (préfixe base path, no-op à la racine)
│   ├── fragments/
│   │   ├── header.html  footer.html   (mutualisés, édités 1 seule fois)
│   │   └── <slug>-head.html / -content.html / -scripts.html   × 16
│   └── pages/<slug>.astro             × 16  (routing automatique)
└── tools/
    ├── mirror.py    aspiration du site d'origine
    ├── split.py     découpe head/content/scripts + réécriture des URLs
    └── visual_diff.py  captures original vs local + diff pixel
```

---

## 3. Plan de migration

### Phase A — Aspiration & squelette Astro  *(phase 1 : on garde Elementor)* — ✅ FAIT

| # | Tâche | Livrable |
|---|---|---|
| A1 | Initialiser le projet Astro (mêmes versions que nidenvol) + config + workflow GitHub Pages | build qui tourne |
| A2 | `tools/mirror.py` : aspirer les 16 pages + les 136 assets (y compris `srcset`, `url()` CSS, polices FA/eicons/creche/Funkids) | `public/` rempli |
| A3 | Réécrire toutes les URLs absolues en racine-relatives (`/css`, `/js`, `/fonts`, `/img`) ; purger le bruit WP (wp-json, oEmbed, RSS, emoji, pingback, generator, speculationrules, gravatar) | HTML propre |
| A4 | `tools/split.py` : découper chaque page en `head` / `content` / `scripts` ; extraire header (#31) et footer (#88) et **vérifier leur identité octet-pour-octet** sur les 16 pages avant de les mutualiser | 50 fragments |
| A5 | Conserver tel quel le CSS Elementor inliné par page (`optimize_css_2`) → rendu strictement identique | — |
| A6 | Créer les 16 `.astro` avec les `class` du `<body>` exactes (`elementor-page-N`, `ast-*`…) | routing OK |
| A7 | `CNAME`, `robots.txt`, `sitemap` (ajouter `/mentions-legales/`, oubliée dans le sitemap WP), `404.html` | — |

### Phase B — Vérification de la phase 1 — ✅ FAIT (sauf B4, déploiement)

| # | Tâche |
|---|---|
| B1 | `npm run build` + `npm run preview` |
| B2 | `tools/visual_diff.py` : capture **16 pages × 3 largeurs (375 / 768 / 1440)**, original vs local, diff pixel — seuil d'acceptation à ~0 % |
| B3 | Tests fonctionnels : menus déroulants, burger mobile, header sticky, galerie + lightbox, iframe Maps, tous les liens internes/externes, ancres |
| B4 | Déploiement GitHub Pages (sous-dossier de test `BASE_PATH`) puis re-vérification en ligne — **reste à faire** |

**Résultats des vérifications (11/11/2026)**, à la racine comme en sous-dossier :

| Contrôle | Résultat |
|---|---|
| HTML comparé balise à balise au site d'origine | **0 différence** sur les 16 pages |
| Diff pixel, 16 pages × 375/768/1440 px | **48/48 captures identiques**, écart max 0,000 % |
| Requêtes en échec / erreurs JS / liens morts | **0 / 0 / 0** |
| Menus, burger, galerie, carte, formulaire | **5/5 comportements identiques** |

Deux constats hérités du site d'origine, reproduits tels quels :
la page « Politique de cookies » affiche le code court `[cmplz-document …]` au lieu du
texte (extension Complianz absente), et la galerie photos n'ouvre pas de lightbox.

**➜ À ce stade le site est en ligne, statique, visuellement identique, encore habillé d'Elementor.**

### Phase C — Suppression d'Elementor / WordPress  *(phase 2 : HTML + CSS + JS purs)*

Méthode : **une page à la fois**, chaque page repassant par le diff pixel de B2 avant d'être validée.
On commence par header/footer (gain sur les 16 pages), puis les pages de la plus simple à la plus complexe.

| # | Tâche |
|---|---|
| C1 | Extraire les vrais tokens de design (couleurs pastel, typo fun-kids / pile système, espacements, breakpoints 767 / 921 / 1024) dans `src/styles/tokens.css` + `base.css` |
| C2 | Remplacer les primitives de mise en page Elementor (`section` / `container` / `column`) par une micro-grille CSS maison reproduisant la largeur « boxed » (1140 px), les gouttières et les règles d'empilement responsive |
| C3 | Réécrire les widgets en HTML sémantique + CSS composant : `heading`, `text-editor`, `image`, `image-box`, `icon-list`, `icon`, `button`, `spacer` |
| C4 | **Header** : nav pure HTML/CSS, sous-menus en CSS au survol (desktop) + ~20 lignes de JS vanilla (mobile), sticky en CSS ➜ supprime `nav-menu`, SmartMenus, jQuery |
| C5 | **Footer** : grille 5 colonnes + variante mobile, en CSS |
| C6 | **Icônes** : Font Awesome + eicons + police custom `creche` ➜ **SVG inline** (supprime 4 fichiers de police + 2 CSS) |
| C7 | **Galerie** : masonry en CSS (`columns`) + lightbox vanilla (~40 lignes) ➜ supprime e-gallery, Swiper, la lightbox Elementor |
| C8 | **Formulaire de contact** : solution compatible statique (voir section 4) |
| C9 | Suppression des bundles : jQuery, jQuery-UI, Astra JS, Elementor frontend + Pro, le CSS de 377 Ko. **~1,1 Mo de CSS/JS ➜ ~40 Ko attendus** |
| C10 | Analytics : retrait de l'UA mort (ou remplacement GA4 — voir questions) |

### Phase D — Finitions

| # | Tâche |
|---|---|
| D1 | Lighthouse (perf / a11y / SEO) + correction des régressions |
| D2 | Images : ne garder que les tailles réellement utilisées, `width`/`height` + `loading="lazy"` systématiques |
| D3 | *(optionnel)* `title` / `meta description` / `og:` propres par page |
| D4 | Bascule DNS vers GitHub Pages + `CNAME` crechndo.org, redirections éventuelles |
| D5 | `README.md` : comment éditer une page, ajouter une page, publier |

---

## 4. Décisions validées (11/11/2026)

| Sujet | Décision | Détail |
|---|---|---|
| **Formulaire de contact** | Remplacé par les **coordonnées cliquables** | `mailto:contact@crechndo.org` + `tel:0695176338` + adresse postale. Plus aucune dépendance serveur ni reCAPTCHA |
| **Analytics** | **Tag GA4 posé en direct** : `G-HZ07V9F2TE` | Même propriété que celle qui collecte aujourd'hui. On remplace le vieux `analytics.js` (UA) par `gtag.js`, ce qui supprime la dépendance au pont hérité Google et une requête réseau |
| **Dépôt GitHub** | `p3cStudio/crechndo-web` | URL de test : `https://p3cstudio.github.io/crechndo-web/` (`BASE_PATH=/crechndo-web`) |
| **Hébergement** | Test sur `github.io`, puis bascule **crechndo.org** via `CNAME` | Le site canonique est **sans** `www` |
| **Phase 2** | **Suppression complète** d'Astra, Elementor, jQuery, Font Awesome et des polices d'icônes, page par page, avec diff pixel à chaque étape | ~1,1 Mo de CSS/JS ➜ ~40 Ko ; classes CSS maison |

### Précision sur l'analytics

Contrairement à ce que j'ai écrit dans la première version de ce document, la mesure **fonctionne**.
Le site charge le vieux snippet Universal Analytics, et celui-ci déclenche automatiquement le chargement
de `googletagmanager.com/gtag/js?id=G-HZ07V9F2TE` (`config` envoyé avec `is_legacy_loaded: true`).
Les `page_view` partent bien vers la propriété GA4 — d'où le trafic visible dans l'interface,
et le cookie `_ga_HZ07V9F2TE` présent sur le site.

Ce pont hérité reste cependant un mécanisme de transition. En migrant on pose directement :

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-HZ07V9F2TE"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-HZ07V9F2TE');
</script>
```

Même propriété, mêmes données, une dépendance en moins.

## 5. Risques identifiés

| Risque | Mitigation |
|---|---|
| Le CSS Elementor est très spécifique : c'est en phase C que les régressions se cachent | Diff pixel obligatoire page par page, jamais de « gros bang » |
| Police d'icônes custom `creche` : il faut retrouver les glyphes/codepoints | Extraction depuis le `.woff` + conversion en SVG, vérification visuelle |
| Open Sans / Montserrat déclarées mais non chargées | Reproduire la pile de polices **à l'identique**, ne surtout pas « corriger » |
| Événement GA4 `pré_inscription` configuré côté Google | Vérifier qu'il se déclenche toujours après la mise en ligne |
