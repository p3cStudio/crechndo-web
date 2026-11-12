// Marque la page courante dans les menus, AU MOMENT DU BUILD.
// (Astro exécute ce code pendant `astro build` : zéro JavaScript envoyé au
// navigateur, et le marquage est écrit en dur dans le HTML livré.)
//
// On repère les liens par leur href — plus rien à maintenir à la main quand une
// page est ajoutée ou qu'une entrée de menu change de libellé.
//
// Seuls les liens d'une entrée de menu (<li><a …>) sont marqués : le lien du
// logo, qui pointe lui aussi vers l'accueil, est laissé tranquille.
//
// Le lien courant reçoit aria-current="page" ; c'est sur cet attribut que la
// feuille de style s'appuie pour le soulignement du menu bureau et pour le fond
// coloré dans les panneaux déroulants.
export function markActiveMenu(html, path) {
  if (!path) return html;

  // Le même lien figure dans plusieurs menus (bureau déroulé, bureau replié,
  // mobile) : le remplacement est volontairement global.
  const escaped = path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return html.replace(
    new RegExp(`(<li>\\s*<a\\b[^>]*\\shref="${escaped}")`, 'g'),
    '$1 aria-current="page"',
  );
}
