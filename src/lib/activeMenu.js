// Réapplique les marqueurs « page courante » au header mutualisé, AU MOMENT DU BUILD.
// (Astro exécute ce code pendant `astro build` : zéro JavaScript envoyé au navigateur.)
//
// Le header est stocké une seule fois, neutre. Chaque page lui réinjecte ici
// exactement ce que WordPress produisait :
//   <li>  … current-menu-item page_item page-item-<ID> current_page_item menu-item-<N>
//   <a>   … aria-current="page"  class="elementor-(sub-)item elementor-item-active …
//   <li>  … current-menu-ancestor current-menu-parent menu-item-has-children menu-item-<N>
//
// Le menu figurant quatre fois dans le header (desktop/mobile × principal/déroulant),
// les remplacements sont volontairement globaux.
//
// tools/build_fragments.py vérifie à chaque génération que le header ainsi reconstruit
// est identique, à l'octet près, à celui du site d'origine.
export function markActiveMenu(html, state) {
  if (!state || !state.activeIds || state.activeIds.length === 0) return html;

  const { pageId, activeIds, ancestorIds = [] } = state;

  // Le header contient deux menus WordPress distincts (barre desktop et barre mobile),
  // chacun rendu deux fois : un même lien porte donc plusieurs identifiants d'item.
  for (const activeId of activeIds) {
    html = html.replace(
      new RegExp(
        `(<li class="[^"]*?)(menu-item-${activeId}">)(<a [^>]*?)(class="elementor-(?:sub-)?item )`,
        'g',
      ),
      (_m, liPrefix, liEnd, aOpen, cls) =>
        `${liPrefix}current-menu-item page_item page-item-${pageId} current_page_item ` +
        `${liEnd}${aOpen}aria-current="page" ${cls}elementor-item-active `,
    );
  }

  for (const ancestorId of ancestorIds) {
    html = html.replace(
      new RegExp(`(<li class="[^"]*?)(menu-item-has-children menu-item-${ancestorId}")`, 'g'),
      (_m, liPrefix, rest) => `${liPrefix}current-menu-ancestor current-menu-parent ${rest}`,
    );
  }
  return html;
}
