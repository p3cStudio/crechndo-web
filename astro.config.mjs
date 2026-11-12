import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// --- base path dans les fichiers CSS/JS ----------------------------------
// src/lib/withBase.js préfixe les URLs du HTML, mais les fichiers de public/
// sont recopiés tels quels : les polices référencées en /fonts/… par le CSS et
// les chemins /vendor/… /img/… que le JS d'Elementor construit à l'exécution
// échapperaient au préfixe et finiraient en 404 dans un sous-dossier.
// On les réécrit donc après le build. À la racine (base "/"), c'est un no-op.
function baseInAssets() {
  return {
    name: 'base-path-dans-les-assets',
    hooks: {
      'astro:build:done': ({ dir, logger }) => {
        const base = (process.env.BASE_PATH || '/').replace(/\/+$/, '');
        if (!base) return;
        const esc = base.replace(/\//g, '\\/'); // forme échappée, pour le JSON des bundles
        let touched = 0;

        const walk = (folder) => {
          for (const entry of fs.readdirSync(folder, { withFileTypes: true })) {
            const file = path.join(folder, entry.name);
            if (entry.isDirectory()) {
              walk(file);
            } else if (/\.(css|js)$/.test(entry.name)) {
              const before = fs.readFileSync(file, 'utf8');
              const after = before
                // chemins normaux : url(/fonts/…), "/css/…"
                .replace(/(["'(=,])\/(css|js|fonts|img|vendor)\//g, `$1${base}/$2/`)
                // chemins échappés du JSON embarqué : "\/vendor\/…"
                .replace(/\\\/(css|js|fonts|img|vendor)\\\//g, `${esc}\\/$1\\/`)
                // dossier nu, sans slash final : "uploadUrl":"\/img"
                .replace(/\\\/(css|js|fonts|img|vendor)(?=")/g, `${esc}\\/$1`);
              if (after !== before) {
                fs.writeFileSync(file, after);
                touched++;
              }
            }
          }
        };
        walk(dir.pathname);
        logger.info(`base "${base}" appliquée à ${touched} fichier(s) CSS/JS`);
      },
    },
  };
}

// Site statique (SSG) : `astro build` génère du HTML pur dans dist/, hébergeable
// tel quel sur GitHub Pages. Header/footer sont mutualisés via des fragments,
// mais écrits « en dur » dans chaque page au build → SEO parfait, aucun serveur.
//
// base : piloté par la variable d'env BASE_PATH.
//   - non définie   -> "/"              (racine : pour le domaine crechndo.org)
//   - "/crechndo-web" -> sous-dossier   (URL de test p3cstudio.github.io/crechndo-web/)
// La GitHub Action passe BASE_PATH=/crechndo-web pour le déploiement de test.

// --- <lastmod> du sitemap ------------------------------------------------
// On donne à Google la vraie date de dernière modification de chaque page, lue
// dans l'historique git des fragments qui la composent. Rien à maintenir à la main.
// Nécessite un clone complet en CI (fetch-depth: 0 dans le workflow).
// Si git est indisponible, on retombe sur la date du build.
const BUILD_DATE = new Date();

function lastModOf(slug) {
  const files = [
    `src/fragments/${slug}-head.html`,
    `src/fragments/${slug}-content.html`,
  ];
  try {
    const out = execFileSync('git', ['log', '-1', '--format=%cI', '--', ...files], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
    return out ? new Date(out) : BUILD_DATE;
  } catch {
    return BUILD_DATE;
  }
}

// "/" -> index ; "/nous-contacter/" -> nous-contacter
function slugFromPath(pathname) {
  const p = pathname.replace(/^\/+|\/+$/g, '');
  return p === '' ? 'index' : p;
}

export default defineConfig({
  site: 'https://crechndo.org',
  base: process.env.BASE_PATH || '/',
  build: {
    format: 'directory', // /nous-contacter/ -> dist/nous-contacter/index.html
  },
  integrations: [
    baseInAssets(),
    sitemap({
      serialize: (item) => ({
        ...item,
        lastmod: lastModOf(slugFromPath(new URL(item.url).pathname)).toISOString(),
      }),
    }),
  ],
});
