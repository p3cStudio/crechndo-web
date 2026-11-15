/**
 * Compare le texte visible du contenu de chaque page, entre le site d'origine
 * et le site généré.
 *
 * Le diff pixel attrape les écarts de mise en forme ; celui-ci attrape les
 * écarts de contenu — un titre mal recopié, un paragraphe oublié, une liste
 * tronquée. C'est le garde-fou de la réécriture à la main.
 *
 * Prérequis : le site généré doit être servi (npm run preview ou npm run dev).
 * Usage :  LOCAL=http://localhost:4322 node tools/check_textes.mjs [slug…]
 */
import { chromium } from 'playwright';

const ORIGIN = (process.env.ORIGIN ?? 'https://crechndo.org').replace(/\/$/, '');
const LOCAL = (process.env.LOCAL ?? 'http://localhost:4321').replace(/\/$/, '');

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

async function textes(page, url) {
  await page.goto(url, { waitUntil: 'load', timeout: 60000 });
  await page.waitForTimeout(500);
  return page.evaluate(() => {
    const racine = document.querySelector('#content');
    const sortie = [];
    const parcourir = (n) => {
      if (n.nodeType === 3) {
        const t = n.textContent.replace(/\s+/g, ' ').trim();
        if (t) sortie.push(t);
        return;
      }
      if (n.nodeType !== 1) return;
      if (getComputedStyle(n).display === 'none') return;
      if (n.tagName === 'SCRIPT' || n.tagName === 'STYLE') return;
      // Les champs de formulaire et les images portent aussi du texte visible.
      if (n.tagName === 'IMG' && n.alt) sortie.push(`[image ${n.alt}]`);
      // Le site d'origine pose certaines images en fond, avec un rôle et un
      // libellé plutôt qu'une balise <img> : on les compte de la même façon.
      if (n.getAttribute('role') === 'img' && n.getAttribute('aria-label')) {
        sortie.push(`[image ${n.getAttribute('aria-label')}]`);
      }
      if (n.tagName === 'INPUT' || n.tagName === 'TEXTAREA') {
        sortie.push(`[champ ${n.getAttribute('placeholder') ?? n.type}]`);
      }
      for (const e of n.childNodes) parcourir(e);
    };
    parcourir(racine);
    return sortie;
  });
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await ctx.newPage();

const slugs = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(PAGES);
let ko = 0;
for (const slug of slugs) {
  const a = await textes(page, ORIGIN + PAGES[slug]);
  const b = await textes(page, LOCAL + PAGES[slug]);
  const ecarts = [];
  const n = Math.max(a.length, b.length);
  for (let i = 0; i < n; i++) {
    if (a[i] !== b[i]) ecarts.push(`      ligne ${i}\n        origine : ${a[i] ?? '(rien)'}\n        généré  : ${b[i] ?? '(rien)'}`);
    if (ecarts.length >= 5) break;
  }
  if (ecarts.length) ko++;
  console.log(`${ecarts.length ? '✗' : '✓'} ${slug.padEnd(36)} ${a.length} fragments de texte`);
  ecarts.forEach((e) => console.log(e));
}

await browser.close();
console.log(`\n${slugs.length - ko}/${slugs.length} pages au texte identique.`);
process.exit(ko ? 1 : 0);
