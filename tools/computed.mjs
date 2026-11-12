/**
 * Relève les styles calculés d'éléments du site, pour pouvoir les reproduire
 * à l'identique sans Elementor.
 *
 * C'est la source de vérité de la phase 2 : plutôt que de lire les feuilles de
 * style d'Elementor (empilées, surchargées, réparties entre le bundle et l'inline),
 * on demande au navigateur ce qu'il affiche réellement.
 *
 * Usage :
 *   node tools/computed.mjs <chemin> "<sélecteur>" [largeur]
 *   node tools/computed.mjs / "header .elementor-widget-nav-menu a.elementor-item" 1440
 *   BASE=http://localhost:4322 node tools/computed.mjs / ".site-footer"
 */
import { chromium } from 'playwright';

const BASE = (process.env.BASE ?? 'https://crechndo.org').replace(/\/$/, '');
const [pagePath = '/', selector = 'body', width = '1440'] = process.argv.slice(2);

const PROPS = [
  'content',
  'display', 'position', 'top', 'left', 'right', 'bottom', 'z-index', 'float', 'clear',
  'width', 'height', 'min-width', 'max-width', 'min-height', 'max-height',
  'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
  'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
  'flex-direction', 'flex-wrap', 'justify-content', 'align-items', 'align-self', 'gap',
  'grid-template-columns', 'order', 'flex-grow', 'flex-shrink', 'flex-basis',
  'font-family', 'font-size', 'font-weight', 'font-style', 'line-height',
  'letter-spacing', 'text-align', 'text-transform', 'text-decoration-line',
  'color', 'background-color', 'background-image', 'background-size',
  'background-position', 'background-repeat',
  'border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width',
  'border-top-color', 'border-style', 'border-radius', 'box-shadow',
  'opacity', 'overflow', 'overflow-x', 'overflow-y', 'visibility',
  'box-sizing', 'transition-property', 'transition-duration', 'transform',
  'list-style-type', 'object-fit', 'vertical-align', 'white-space',
];

// Valeurs qu'on ne montre pas : ce sont les valeurs par défaut du navigateur.
const DEFAULTS = new Map(Object.entries({
  'min-width': '0px', 'min-height': '0px', 'max-width': 'none', 'max-height': 'none',
  'margin-top': '0px', 'margin-right': '0px', 'margin-bottom': '0px', 'margin-left': '0px',
  'padding-top': '0px', 'padding-right': '0px', 'padding-bottom': '0px', 'padding-left': '0px',
  'border-top-width': '0px', 'border-right-width': '0px', 'border-bottom-width': '0px',
  'border-left-width': '0px', 'border-style': 'none', 'border-radius': '0px',
  'box-shadow': 'none', 'opacity': '1', 'overflow': 'visible', 'overflow-x': 'visible',
  'overflow-y': 'visible', 'visibility': 'visible', 'position': 'static', 'z-index': 'auto',
  'top': 'auto', 'left': 'auto', 'right': 'auto', 'bottom': 'auto', 'float': 'none',
  'clear': 'none', 'background-image': 'none', 'background-color': 'rgba(0, 0, 0, 0)',
  'transform': 'none', 'transition-property': 'all', 'transition-duration': '0s',
  'text-transform': 'none', 'text-decoration-line': 'none', 'letter-spacing': 'normal',
  'font-style': 'normal', 'white-space': 'normal', 'order': '0', 'flex-grow': '0',
  'flex-shrink': '1', 'flex-basis': 'auto', 'align-self': 'auto', 'gap': 'normal',
  'grid-template-columns': 'none', 'object-fit': 'fill', 'vertical-align': 'baseline',
  'background-size': 'auto', 'background-position': '0% 0%', 'background-repeat': 'repeat',
  'flex-direction': 'row', 'flex-wrap': 'nowrap', 'justify-content': 'normal',
  'align-items': 'normal', 'height': 'auto', 'width': 'auto', 'list-style-type': 'disc',
}));

const browser = await chromium.launch();
const page = await (await browser.newContext({
  viewport: { width: Number(width), height: 1000 },
})).newPage();
await page.goto(BASE + pagePath, { waitUntil: 'load' });
await page.waitForTimeout(1200);

// Un sélecteur peut viser un pseudo-élément : "… .elementor-item::after".
const pseudoMatch = selector.match(/(.*?)(::?(?:before|after))\s*$/);
const realSelector = pseudoMatch ? pseudoMatch[1].trim() : selector;
const pseudo = pseudoMatch ? pseudoMatch[2].replace(/^:?:/, '::') : null;

const out = await page.evaluate(({ selector, props, pseudo }) => {
  const els = [...document.querySelectorAll(selector)];
  return els.slice(0, 12).map((el, i) => {
    const cs = getComputedStyle(el, pseudo);
    const r = el.getBoundingClientRect();
    const styles = {};
    for (const p of props) styles[p] = cs.getPropertyValue(p);
    if (pseudo) styles.content = cs.getPropertyValue('content');
    return {
      i,
      tag: el.tagName.toLowerCase() + (pseudo ?? ''),
      classes: el.getAttribute('class') ?? '',
      texte: (el.textContent ?? '').trim().replace(/\s+/g, ' ').slice(0, 60),
      boite: `${Math.round(r.width)}×${Math.round(r.height)} @ ${Math.round(r.x)},${Math.round(r.y)}`,
      styles,
    };
  });
}, { selector: realSelector, props: PROPS, pseudo });

await browser.close();

console.log(`# ${BASE}${pagePath}  —  ${selector}  —  ${width}px\n`);
for (const el of out) {
  console.log(`--- [${el.i}] <${el.tag}>  ${el.boite}`);
  if (el.classes) console.log(`    class: ${el.classes}`);
  if (el.texte) console.log(`    texte: ${el.texte}`);
  for (const [k, v] of Object.entries(el.styles)) {
    if (DEFAULTS.get(k) === v) continue;
    console.log(`    ${k}: ${v}`);
  }
  console.log();
}
if (!out.length) console.log('(aucun élément ne correspond)');
