/* ==========================================================================
   Crèch'n'do — comportements du site, en JavaScript natif.
   Remplace jQuery + SmartMenus + le frontend d'Elementor pour la navigation.
   ========================================================================== */
(function () {
  'use strict';

  /* --- burgers (menu bureau replié, et menu mobile) ----------------------- */
  var burgers = document.querySelectorAll('.cnd-burger');

  function fermerPanneau(burger) {
    var panneau = document.getElementById(burger.getAttribute('aria-controls'));
    burger.setAttribute('aria-expanded', 'false');
    if (panneau) {
      panneau.classList.remove('cnd-ouvert');
      // on referme aussi les sous-menus laissés ouverts
      panneau.querySelectorAll('.cnd-ouvert').forEach(function (li) {
        li.classList.remove('cnd-ouvert');
        var lien = li.querySelector('a[aria-expanded]');
        if (lien) lien.setAttribute('aria-expanded', 'false');
      });
    }
  }

  burgers.forEach(function (burger) {
    burger.addEventListener('click', function () {
      var ouvert = burger.getAttribute('aria-expanded') === 'true';
      var panneau = document.getElementById(burger.getAttribute('aria-controls'));
      if (ouvert) {
        fermerPanneau(burger);
      } else {
        burger.setAttribute('aria-expanded', 'true');
        if (panneau) panneau.classList.add('cnd-ouvert');
      }
    });
  });

  /* --- sous-menus --------------------------------------------------------- */
  /* Comme sur le site d'origine, un sous-menu s'ouvre au CLIC, pas au survol. */
  var parents = document.querySelectorAll('.cnd-entete a[aria-expanded]');

  function fermerSousMenus(saufCeLien) {
    parents.forEach(function (lien) {
      if (lien === saufCeLien) return;
      lien.setAttribute('aria-expanded', 'false');
      if (lien.parentElement) lien.parentElement.classList.remove('cnd-ouvert');
    });
  }

  parents.forEach(function (lien) {
    lien.addEventListener('click', function (evenement) {
      var sousMenu = lien.parentElement && lien.parentElement.querySelector('.cnd-sous-menu');
      if (!sousMenu) return; // lien normal : on laisse faire
      evenement.preventDefault();
      var ouvert = lien.getAttribute('aria-expanded') === 'true';
      fermerSousMenus(lien);
      lien.setAttribute('aria-expanded', ouvert ? 'false' : 'true');
      lien.parentElement.classList.toggle('cnd-ouvert', !ouvert);
    });
  });

  /* --- fermeture au clic en dehors, et à la touche Échap ------------------ */
  document.addEventListener('click', function (evenement) {
    if (evenement.target.closest && evenement.target.closest('.cnd-entete')) return;
    fermerSousMenus(null);
  });

  document.addEventListener('keydown', function (evenement) {
    if (evenement.key !== 'Escape') return;
    fermerSousMenus(null);
    burgers.forEach(fermerPanneau);
  });
})();
