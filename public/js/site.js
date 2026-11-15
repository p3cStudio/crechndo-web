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

/* --- apparition au défilement --------------------------------------------
   Les blocs marqués `cnd-apparition` restent invisibles jusqu'à ce qu'ils
   entrent dans le champ de vision, puis jouent leur animation une fois.
   C'est ce que faisait Elementor avec ses classes `elementor-invisible`
   et `animated`.                                                           */
(function () {
	var blocs = document.querySelectorAll('.cnd-apparition');
	if (!blocs.length) return;

	function jouer(bloc) {
		bloc.classList.add('cnd-apparition--jouee');
	}

	if (!('IntersectionObserver' in window)) {
		blocs.forEach(jouer);
		return;
	}

	var guetteur = new IntersectionObserver(function (entrees) {
		entrees.forEach(function (e) {
			if (!e.isIntersecting) return;
			jouer(e.target);
			guetteur.unobserve(e.target);
		});
	});
	blocs.forEach(function (b) { guetteur.observe(b); });
})();

/* --- parallaxe au défilement ----------------------------------------------
   Un seul bloc du site glisse verticalement au fil du défilement : le koala
   de la page « Offres et tarifs ». On reprend la formule d'Elementor — le
   décalage va de +50×vitesse quand le bloc entre par le bas de l'écran à
   −50×vitesse quand il sort par le haut. La mesure porte sur le bloc parent,
   qui n'est pas déplacé : mesurer le bloc déplacé le ferait dériver.         */
(function () {
	var blocs = document.querySelectorAll('[data-cnd-parallaxe]');
	if (!blocs.length) return;

	function placer() {
		var hauteurEcran = window.innerHeight;
		blocs.forEach(function (bloc) {
			var cadre = bloc.parentElement.getBoundingClientRect();
			var amplitude = parseFloat(bloc.dataset.cndParallaxe) * 50;
			var avance = (hauteurEcran - cadre.top) / (hauteurEcran + cadre.height);
			avance = Math.min(Math.max(avance, 0), 1);
			bloc.style.transform = 'translateY(' + (amplitude * (1 - 2 * avance)).toFixed(2) + 'px)';
		});
	}

	placer();
	window.addEventListener('scroll', placer, { passive: true });
	window.addEventListener('resize', placer);
})();
