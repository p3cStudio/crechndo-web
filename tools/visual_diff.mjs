/**
 * Comparaison pixel entre le site d'origine (crechndo.org) et le site généré.
 *
 * Pour chaque page et chaque largeur, on capture la page entière des deux côtés,
 * puis on compte les pixels qui diffèrent. C'est le garde-fou de toute la migration :
 * tant qu'il est vert, on sait que le rendu n'a pas bougé.
 *
 * Prérequis : le site généré doit être servi (npm run preview).
 *
 * Usage :
 *   node tools/visual_diff.mjs                       # 16 pages × 3 largeurs
 *   node tools/visual_diff.mjs nous-contacter        # une page
 *   LOCAL=http://localhost:4321 node tools/visual_diff.mjs
 */
import { chromium } from 'playwright';
import pixelmatch from 'pixelmatch';
import { PNG } from 'pngjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const OUT = path.join(ROOT, 'tools', '.cache', 'visual');

const ORIGIN = process.env.ORIGIN ?? 'https://crechndo.org';
const LOCAL = process.env.LOCAL ?? 'http://localhost:4321';
const WIDTHS = (process.env.WIDTHS ?? '375,768,1440').split(',').map(Number);
// Écart toléré, en pourcentage de pixels. SEUIL=0 pour tout faire remonter.
const SEUIL = Number(process.env.SEUIL ?? 0.1);

const PAGES = {
  index: '/',
  presentation: '/presentation/',
  'notre-philosophie': '/notre-philosophie/',
  'notre-equipe': '/notre-equipe/',
  'la-micro-creche': '/la-micro-creche/',
  'decouvrir-en-photos': '/decouvrir-en-photos/',
  'nous-situer': '/nous-situer/',
  'l-accueil-de-votre-enfant-de-a-a-z': '/l-accueil-de-votre-enfant-de-a-a-z/',
  'la-journee-de-votre-enfant': '/la-journee-de-votre-enfant/',
  'offres-et-tarifs': '/offres-et-tarifs/',
  'nous-contacter': '/nous-contacter/',
  'nos-partenaires': '/nos-partenaires/',
  'on-parle-de-nous': '/on-parle-de-nous/',
  'plan-du-site': '/plan-du-site/',
  'politique-de-cookies-ue': '/politique-de-cookies-ue/',
  'mentions-legales': '/mentions-legales/',
};

// Ce qui ne peut pas être identique d'une capture à l'autre : carte Google (tuiles
// chargées dynamiquement) et reCAPTCHA. On les masque des deux côtés.
const MASK_SELECTORS = ['iframe', '.elementor-g-recaptcha', '.grecaptcha-badge'];

async function shoot(page, url, width) {
  await page.setViewportSize({ width, height: 1000 });
  await page.goto(url, { waitUntil: 'load', timeout: 60000 });
  // Déclenche le chargement différé des images et des fonds, puis remonte en
  // haut. On avance par tiers d'écran : la galerie du site d'origine ne charge
  // ses vignettes que si elles passent vraiment près du champ de vision, et un
  // défilement par bonds d'un écran entier en saute une partie.
  // On repasse jusqu'à ce que tout soit chargé : la galerie du site d'origine
  // ne pose ses vignettes qu'au fil du défilement, et un seul passage n'y
  // suffit pas toujours.
  // Une seule passe suffit s'il n'y a pas de galerie à réveiller.
  const galerie = await page.evaluate(() => document.querySelectorAll('.e-gallery-image').length > 0);
  let restantes = 0;
  for (let essai = 0; essai < (galerie ? 20 : 1); essai++) {
    const reste = await page.evaluate(async () => {
      const pas = window.innerHeight / 3;
      for (let y = 0; y < document.body.scrollHeight; y += pas) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 70));
      }
      window.scrollTo(0, 0);
      await new Promise((r) => setTimeout(r, 400));
      return [...document.querySelectorAll('.e-gallery-image')]
        .filter((e) => getComputedStyle(e).backgroundImage === 'none').length;
    });
    restantes = reste;
    if (!reste) break;
  }
  // Il reste parfois une vignette que le chargement différé d'Elementor ne
  // déclenche jamais, tout en bas de la page. On la pose nous-mêmes à partir de
  // l'attribut que le widget lui a laissé : sinon on comparerait un trou blanc
  // du site d'origine à une photo bien chargée du site généré.
  if (restantes) {
    await page.evaluate(() => {
      document.querySelectorAll('.e-gallery-image').forEach((e) => {
        if (getComputedStyle(e).backgroundImage !== 'none') return;
        const url = e.dataset.thumbnail;
        if (!url) return;
        e.style.backgroundImage = `url("${url}")`;
        e.classList.add('e-gallery-image-loaded');
      });
    });
  }
  // Attend que toutes les images soient réellement peintes. Sans ça, on
  // comparerait la vitesse du réseau plutôt que le rendu : sur les pages à
  // vignettes, le site d'origine n'a pas toujours fini de charger quand le
  // site local, servi en local, a déjà tout affiché.
  await page
    .evaluate(async () => {
      // Chaque attente est bornée : une image en chargement différé restée
      // hors du champ de vision ne se charge jamais, et sans garde-fou on
      // attendrait indéfiniment.
      const borne = (p) => Promise.race([p, new Promise((r) => setTimeout(r, 15000))]);
      const charge = (url) => borne(new Promise((r) => {
        const i = new Image();
        i.onload = i.onerror = r;
        i.src = url;
      }));
      // Les vignettes de la galerie d'origine sont des images de fond posées
      // en JavaScript : on les précharge pour être sûr qu'elles sont peintes.
      const fonds = [...document.querySelectorAll('*')]
        .map((e) => getComputedStyle(e).backgroundImage.match(/url\("(.+?)"\)/))
        .filter(Boolean)
        .map((m) => m[1]);
      await Promise.all([...new Set(fonds)].map(charge));
      // Les images en chargement différé qui n'ont jamais croisé le champ de
      // vision ne se chargeraient jamais : on les force avant d'attendre.
      document.images.forEach ||= Array.prototype.forEach;
      for (const i of document.images) {
        if (!i.complete) i.loading = 'eager';
      }
      await Promise.all([...document.images].map((i) =>
        i.complete ? null : borne(new Promise((r) => { i.onload = i.onerror = r; }))));
      await borne(document.fonts.ready);
    })
    .catch(() => console.warn('    (images encore en cours de chargement)'));
  await page.waitForTimeout(600);
  // Neutralise les animations en cours pour que la capture soit déterministe.
  await page.addStyleTag({
    content: `*,*::before,*::after{animation:none!important;transition:none!important}`,
  });
  for (const sel of MASK_SELECTORS) {
    await page.evaluate((s) => {
      document.querySelectorAll(s).forEach((el) => {
        el.style.visibility = 'hidden';
      });
    }, sel);
  }
  await page.waitForTimeout(200);
  return PNG.sync.read(await page.screenshot({ fullPage: true }));
}

async function main() {
  const slugs = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(PAGES);
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await chromium.launch();
  const ctx = await browser.newContext({ deviceScaleFactor: 1 });
  const page = await ctx.newPage();

  let worst = 0;
  const rows = [];

  for (const slug of slugs) {
    for (const width of WIDTHS) {
      const a = await shoot(page, ORIGIN + PAGES[slug], width);
      const b = await shoot(page, LOCAL + PAGES[slug], width);

      const h = Math.min(a.height, b.height);
      const diff = new PNG({ width, height: h });
      const crop = (img) => {
        const out = new PNG({ width, height: h });
        PNG.bitblt(img, out, 0, 0, width, h, 0, 0);
        return out;
      };
      const n = pixelmatch(crop(a).data, crop(b).data, diff.data, width, h, {
        threshold: 0.12,
        includeAA: false,
      });
      const pct = (100 * n) / (width * h);
      worst = Math.max(worst, pct);

      const dh = a.height - b.height;
      const flag = pct > SEUIL || Math.abs(dh) > 4 ? '✗' : '✓';
      rows.push(
        `${flag} ${slug.padEnd(36)} ${String(width).padStart(5)}px  ` +
          `${pct.toFixed(3).padStart(7)}%  hauteur ${a.height}/${b.height}` +
          (dh ? ` (Δ${dh})` : ''),
      );
      console.log(rows.at(-1));

      if (pct > SEUIL || Math.abs(dh) > 4) {
        fs.writeFileSync(path.join(OUT, `${slug}-${width}-diff.png`), PNG.sync.write(diff));
        fs.writeFileSync(path.join(OUT, `${slug}-${width}-origine.png`), PNG.sync.write(a));
        fs.writeFileSync(path.join(OUT, `${slug}-${width}-genere.png`), PNG.sync.write(b));
      }
    }
  }

  await browser.close();
  const bad = rows.filter((r) => r.startsWith('✗'));
  console.log(`\n${rows.length - bad.length}/${rows.length} captures conformes. ` +
    `Pire écart : ${worst.toFixed(3)} %.`);
  if (bad.length) console.log(`Captures en écart dans ${OUT}`);
  process.exit(bad.length ? 1 : 0);
}

main();
