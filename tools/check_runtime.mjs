/**
 * Contrôle fonctionnel du site généré : requêtes en échec, erreurs JS, liens morts.
 *
 * Prérequis : le site généré doit être servi (npm run preview).
 * Usage :  LOCAL=http://localhost:4322 node tools/check_runtime.mjs
 */
import { chromium } from 'playwright';

const LOCAL = (process.env.LOCAL ?? 'http://localhost:4321').replace(/\/$/, '');

const PATHS = [
  '/', '/presentation/', '/notre-philosophie/', '/notre-equipe/', '/la-micro-creche/',
  '/decouvrir-en-photos/', '/nous-situer/', '/l-accueil-de-votre-enfant-de-a-a-z/',
  '/la-journee-de-votre-enfant/', '/offres-et-tarifs/', '/nous-contacter/',
  '/nos-partenaires/', '/on-parle-de-nous/', '/plan-du-site/',
  '/politique-de-cookies-ue/', '/mentions-legales/',
];

// Domaines tiers dont on ne contrôle pas la disponibilité depuis ici.
const THIRD_PARTY = /google\.com\/maps|googletagmanager|google-analytics|maps\.google|gstatic|doubleclick/;

const browser = await chromium.launch();
const ctx = await browser.newContext();
const page = await ctx.newPage();

const failures = [];
const errors = [];
const internalLinks = new Set();

page.on('requestfailed', (r) => {
  if (!THIRD_PARTY.test(r.url())) failures.push(`${page.url()} → ÉCHEC ${r.url()}`);
});
page.on('response', (r) => {
  if (r.status() >= 400 && !THIRD_PARTY.test(r.url())) {
    failures.push(`${page.url()} → HTTP ${r.status()} ${r.url()}`);
  }
});
page.on('pageerror', (e) => errors.push(`${page.url()} → ${e.message}`));
page.on('console', (m) => {
  if (m.type() === 'error' && !THIRD_PARTY.test(m.text())) {
    errors.push(`${page.url()} → console: ${m.text().slice(0, 160)}`);
  }
});

for (const p of PATHS) {
  await page.goto(LOCAL + p, { waitUntil: 'load' });
  await page.evaluate(async () => {
    const step = window.innerHeight;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 50));
    }
  });
  await page.waitForTimeout(500);
  // On résout chaque lien par rapport à la page : indispensable quand le site est
  // servi dans un sous-dossier, sinon on recollerait le préfixe deux fois.
  const base = page.url();
  for (const href of await page.$$eval('a[href]', (as) => as.map((a) => a.getAttribute('href')))) {
    if (href && !/^(#|mailto:|tel:|https?:)/.test(href)) {
      internalLinks.add(new URL(href, base).toString());
    }
  }
  process.stdout.write('.');
}
console.log();

// Les liens internes pointent-ils tous vers une page qui existe ?
const dead = [];
for (const href of [...internalLinks].sort()) {
  const r = await page.request.get(href, { maxRedirects: 5 });
  if (!r.ok()) dead.push(`${href} → HTTP ${r.status()}`);
}

await browser.close();

const section = (title, list) => {
  console.log(`\n== ${title} : ${list.length} ==`);
  [...new Set(list)].slice(0, 30).forEach((l) => console.log('  ' + l));
};
section('requêtes en échec', failures);
section('erreurs JavaScript', errors);
section('liens internes morts', dead);
console.log(`\n${internalLinks.size} liens internes distincts vérifiés.`);
process.exit(failures.length + errors.length + dead.length ? 1 : 0);
