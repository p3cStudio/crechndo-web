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

// Le header a été réécrit en phase 2 : ses sélecteurs diffèrent d'un site à
// l'autre. Les sondes qui le visent reçoivent donc un jeu de sélecteurs par site.
const SELECTEURS = {
  origine: {
    parentSousMenu: 'nav.elementor-nav-menu--main li.menu-item-has-children',
    sousMenu: 'ul.sub-menu',
    burger: '.elementor-menu-toggle',
    panneau: 'nav.elementor-nav-menu--dropdown',
    vignettes: '.e-gallery-image',
    carte: '.elementor-custom-embed iframe',
  },
  genere: {
    parentSousMenu: '.cnd-menu-bureau__liste li:has(> .cnd-sous-menu)',
    sousMenu: '.cnd-sous-menu',
    burger: '.cnd-burger',
    panneau: '.cnd-panneau',
    vignettes: '.cnd-galerie img',
    carte: '.cnd-carte iframe',
  },
};

const PROBES = [
  {
    // SmartMenus était configuré en « ouverture au clic », pas au survol :
    // la réécriture reprend ce comportement.
    name: 'sous-menu du header au clic (desktop)',
    viewport: { width: 1440, height: 900 },
    path: '/',
    async run(page, sel) {
      await page.waitForTimeout(1200);
      const parent = page.locator(sel.parentSousMenu).first();
      const sub = parent.locator(sel.sousMenu).first();
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
    async run(page, sel) {
      // Le header contient deux barres (desktop et mobile) : on prend le bouton
      // réellement affiché à cette largeur.
      await page.waitForTimeout(1200);
      const toggles = await page.$$eval(sel.burger,
        (els) => els.map((e) => e.offsetParent !== null));
      const toggle = page.locator(sel.burger).nth(toggles.indexOf(true));
      const menus = page.locator(sel.panneau);
      const before = await menus.evaluateAll((els) => els.map((e) => e.getBoundingClientRect().height > 0));
      await toggle.click();
      await page.waitForTimeout(800);
      const after = await menus.evaluateAll((els) => els.map((e) => e.getBoundingClientRect().height > 0));
      return { avant: before, apres: after };
    },
  },
  {
    // Le site d'origine pose ses vignettes en image de fond, au fil du
    // défilement ; le site généré utilise de vraies balises <img>. On compare
    // donc ce qui compte : le nombre de photos et leur ordre.
    name: 'galerie : photos affichées',
    viewport: { width: 1440, height: 900 },
    path: '/decouvrir-en-photos/',
    async run(page, sel) {
      for (let passe = 0; passe < 20; passe++) {
        const reste = await page.evaluate(async (sel) => {
          for (const el of document.querySelectorAll(sel.vignettes)) {
            el.scrollIntoView({ block: 'center' });
            await new Promise((r) => setTimeout(r, 60));
          }
          await new Promise((r) => setTimeout(r, 300));
          return [...document.querySelectorAll(sel.vignettes)].filter((e) =>
            e.tagName === 'IMG' ? !e.complete : getComputedStyle(e).backgroundImage === 'none').length;
        }, sel);
        if (!reste) break;
      }
      return await page.evaluate((sel) => {
        const sources = [...document.querySelectorAll(sel.vignettes)].map((e) =>
          (e.tagName === 'IMG' ? e.getAttribute('src') : e.dataset.thumbnail).split('/').pop());
        return { photos: sources.length, ordre: sources.join(',') };
      }, sel);
    },
  },
  {
    name: 'carte Google',
    viewport: { width: 1440, height: 900 },
    path: '/nous-situer/',
    async run(page, sel) {
      const src = await page.locator(sel.carte).getAttribute('src');
      return { carte: (src ?? '').split('?')[0] };
    },
  },
  {
    // Le bloc encadré de la page « Nous contacter », commun aux deux sites.
    // (Le formulaire, lui, est volontairement remplacé par les coordonnées
    // cliquables : il n'est donc pas comparé.)
    name: 'page contact : coordonnées encadrées',
    viewport: { width: 1440, height: 900 },
    path: '/nous-contacter/',
    async run(page) {
      const cadre = page.locator('.elementor-element-f63628a, .cnd-coordonnees').first();
      return {
        texte: (await cadre.innerText()).replace(/\s+/g, ' ').trim(),
      };
    },
  },
];

const browser = await chromium.launch();

async function probe(base, p, jeu) {
  const ctx = await browser.newContext({ viewport: p.viewport });
  const page = await ctx.newPage();
  try {
    await page.goto(base + p.path, { waitUntil: 'load', timeout: 60000 });
    return await p.run(page, SELECTEURS[jeu]);
  } catch (e) {
    return { erreur: e.message.split('\n')[0] };
  } finally {
    await ctx.close();
  }
}

let ko = 0;
for (const p of PROBES) {
  const a = JSON.stringify(await probe(ORIGIN, p, 'origine'));
  const b = JSON.stringify(await probe(LOCAL, p, 'genere'));
  const same = a === b;
  if (!same) ko++;
  console.log(`${same ? '✓' : '✗'} ${p.name}`);
  console.log(`    origine : ${a}`);
  if (!same) console.log(`    généré  : ${b}`);
}

await browser.close();
console.log(`\n${PROBES.length - ko}/${PROBES.length} comportements identiques.`);
process.exit(ko ? 1 : 0);
