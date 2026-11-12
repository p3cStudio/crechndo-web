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
  // Déclenche le lazy-loading des images et des fonds, puis remonte en haut.
  await page.evaluate(async () => {
    const step = window.innerHeight;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 60));
    }
    window.scrollTo(0, 0);
  });
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
      const flag = pct > 0.1 || Math.abs(dh) > 4 ? '✗' : '✓';
      rows.push(
        `${flag} ${slug.padEnd(36)} ${String(width).padStart(5)}px  ` +
          `${pct.toFixed(3).padStart(7)}%  hauteur ${a.height}/${b.height}` +
          (dh ? ` (Δ${dh})` : ''),
      );
      console.log(rows.at(-1));

      if (pct > 0.1 || Math.abs(dh) > 4) {
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
