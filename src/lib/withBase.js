// Préfixe les URLs racine-relatives (/css, /js, /fonts, /img, /vendor et les liens
// internes) par le « base path » du site, pour que tout fonctionne aussi bien à la
// racine d'un domaine (base = "/") que dans un sous-dossier GitHub Pages
// (base = "/crechndo-web/").
//
// - À la racine (base === "/") : NO-OP, la fonction renvoie le HTML tel quel.
//   -> rien à retirer le jour où l'on bascule sur le domaine crechndo.org.
// - En sous-dossier : réécrit /img/... en /crechndo-web/img/..., etc.
//
// Les URLs absolues (https://crechndo.org/...) ne sont jamais touchées : la regex
// n'agit que sur un / précédé d'un délimiteur d'attribut ("=' ( , ou espace).
const PAGES = [
  'presentation', 'notre-philosophie', 'notre-equipe', 'la-micro-creche',
  'decouvrir-en-photos', 'nous-situer', 'l-accueil-de-votre-enfant-de-a-a-z',
  'la-journee-de-votre-enfant', 'offres-et-tarifs', 'nous-contacter',
  'nos-partenaires', 'on-parle-de-nous', 'plan-du-site',
  'politique-de-cookies-ue', 'mentions-legales',
];

export function withBase(html) {
  let base = import.meta.env.BASE_URL; // "/", "/crechndo-web" ou "/crechndo-web/"
  if (base === '/' || base === '') return html;
  if (!base.endsWith('/')) base += '/'; // garantir le slash final

  let out = html
    // assets : href="/css/...", src="/img/...", url(/fonts/...), srcset "…, /img/…"
    .replace(/([="'(,]\s*)\/(css|js|fonts|img|vendor)\//g, (_m, p, dir) => `${p}${base}${dir}/`)
    // accueil
    .replaceAll('href="/"', `href="${base}"`);

  // liens internes vers les autres pages
  for (const slug of PAGES) {
    out = out.replaceAll(`href="/${slug}/`, `href="${base}${slug}/`);
    out = out.replaceAll(`href="/${slug}"`, `href="${base}${slug}"`);
  }
  return out;
}

// Variante pour une URL seule (attribut href/src écrit en Astro, pas dans un
// fragment HTML) : withBase() ne sait traiter que du balisage.
export function basePath(url) {
  let base = import.meta.env.BASE_URL;
  if (base === '/' || base === '') return url;
  if (!base.endsWith('/')) base += '/';
  return base + url.replace(/^\//, '');
}
