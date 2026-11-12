/**
 * Vérifie que les comportements dynamiques se comportent PAREIL sur le site
 * d'origine et sur le site généré : sous-menus du header, menu burger mobile,
 * galerie + lightbox, carte.
 *
 * On ne teste pas « est-ce que ça marche » dans l'absolu, mais « est-ce que ça fait
 * la même chose qu'avant » : chaque sonde tourne des deux côtés et on compare.
 *
 * Prérequis : le site généré doit être servi (npm run preview).
 * Usage :  LOCAL=http://localhost:4322 node tools/check_interactions.mjs
 */
import { chromium } from 'playwright';

const ORIGIN = (process.env.ORIGIN ?? 'https://crechndo.org').replace(/\/$/, '');
const LOCAL = (process.env.LOCAL ?? 'http://localhost:4321').replace(/\/$/, '');

const PROBES = [
  {
    // SmartMenus est configuré ici en « ouverture au clic », pas au survol.
    name: 'sous-menu du header au clic (desktop)',
    viewport: { width: 1440, height: 900 },
    path: '/',
    async run(page) {
      await page.waitForTimeout(1200);
      const parent = page.locator('nav.elementor-nav-menu--main li.menu-item-has-children').first();
      const sub = parent.locator('ul.sub-menu').first();
      const before = await sub.isVisible();
      await parent.locator('> a').click();
      await page.waitForTimeout(800);
      return { avant: before, apres: await sub.isVisible() };
    },
  },
  {
    name: 'menu burger (mobile)',
    viewport: { width: 375, height: 812 },
    path: '/',
    async run(page) {
      // Le header contient deux barres (desktop et mobile) : on prend le bouton
      // réellement affiché à cette largeur.
      await page.waitForTimeout(1200);
      const toggles = await page.$$eval('.elementor-menu-toggle',
        (els) => els.map((e) => e.offsetParent !== null));
      const toggle = page.locator('.elementor-menu-toggle').nth(toggles.indexOf(true));
      const menus = page.locator('nav.elementor-nav-menu--dropdown');
      const before = await menus.evaluateAll((els) => els.map((e) => e.offsetParent !== null));
      await toggle.click();
      await page.waitForTimeout(800);
      const after = await menus.evaluateAll((els) => els.map((e) => e.offsetParent !== null));
      return { avant: before, apres: after };
    },
  },
  {
    name: 'galerie : vignettes affichées',
    viewport: { width: 1440, height: 900 },
    path: '/decouvrir-en-photos/',
    async run(page) {
      // Les vignettes sont des images de fond posées en JS quand l'élément entre
      // dans le champ de vision. On amène donc chaque élément à l'écran, puis on
      // attend que TOUTES soient peintes : comparer des comptes partiels
      // reviendrait à comparer la vitesse du réseau, pas le rendu.
      const items = await page.evaluate(() => document.querySelectorAll('.e-gallery-item').length);
      let peintes = 0;
      for (let pass = 0; pass < 20 && peintes < items; pass++) {
        await page.evaluate(async () => {
          for (const el of document.querySelectorAll('.e-gallery-item')) {
            el.scrollIntoView({ block: 'center' });
            await new Promise((r) => setTimeout(r, 80));
          }
        });
        await page.waitForTimeout(500);
        peintes = await page.evaluate(() => [...document.querySelectorAll('.e-gallery-image')]
          .filter((e) => getComputedStyle(e).backgroundImage !== 'none').length);
      }
      return { items, toutesPeintes: peintes === items };
    },
  },
  {
    name: 'carte Google',
    viewport: { width: 1440, height: 900 },
    path: '/nous-situer/',
    async run(page) {
      const src = await page.locator('.elementor-custom-embed iframe').getAttribute('src');
      return { carte: (src ?? '').split('?')[0] };
    },
  },
  {
    name: 'formulaire de contact : champs',
    viewport: { width: 1440, height: 900 },
    path: '/nous-contacter/',
    async run(page) {
      return {
        champs: await page.$$eval('form.elementor-form [name^="form_fields"]',
          (els) => els.map((e) => e.getAttribute('name')).join(',')),
      };
    },
  },
];

const browser = await chromium.launch();

async function probe(base, p) {
  const ctx = await browser.newContext({ viewport: p.viewport });
  const page = await ctx.newPage();
  try {
    await page.goto(base + p.path, { waitUntil: 'load', timeout: 60000 });
    return await p.run(page);
  } catch (e) {
    return { erreur: e.message.split('\n')[0] };
  } finally {
    await ctx.close();
  }
}

let ko = 0;
for (const p of PROBES) {
  const a = JSON.stringify(await probe(ORIGIN, p));
  const b = JSON.stringify(await probe(LOCAL, p));
  const same = a === b;
  if (!same) ko++;
  console.log(`${same ? '✓' : '✗'} ${p.name}`);
  console.log(`    origine : ${a}`);
  if (!same) console.log(`    généré  : ${b}`);
}

await browser.close();
console.log(`\n${PROBES.length - ko}/${PROBES.length} comportements identiques.`);
process.exit(ko ? 1 : 0);
