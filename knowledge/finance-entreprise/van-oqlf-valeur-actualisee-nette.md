# Valeur actualisée nette (VAN), aussi nommée valeur actuelle nette

> Source : Office québécois de la langue française (OQLF), Grand dictionnaire terminologique, fiche « valeur actualisée nette » (domaine : gestion financière, comptabilité), https://vitrinelinguistique.oqlf.gouv.qc.ca/fiche-gdt/fiche/8438369/valeur-actualisee-nette ; fiche liée « méthode de la valeur actualisée nette » (503682) citée d'après un résultat de recherche, non lue. Fiche datée de 1998 par le site. Consulté le 2026-11-26. Remplace l'ancienne fiche tirée de Wikipédia (source faible). Référence académique (Vernimmen, Finance d'entreprise, Dalloz) : non citée, référence exacte non vérifiée.
> Licence : publication de l'OQLF ; synthèse rédigée en interne, citations courtes ; droits de réutilisation à confirmer.

## Définition (OQLF)

Excédent de la valeur actualisée des rentrées nettes de fonds attendues d'un projet d'investissement sur la valeur actualisée des décaissements requis pour réaliser cet investissement. Terme retenu : « valeur actualisée nette », abréviation VAN ; les variantes « valeur actuelle nette », « valeur nette actualisée » et « bénéfice actualisé » ne sont pas retenues par l'OQLF (rarement employées). Équivalent anglais : net present value (NPV).

## Taux d'actualisation (OQLF)

C'est le taux de rendement minimal fixé par la direction de l'entreprise, en général fondé sur le coût moyen pondéré du capital pour les nouveaux projets. Il est annuel : le paramètre `discount_rate_year` du jeu (0 à 0,3, annexe 0013) est de ce type. La fiche ne dit pas comment convertir un taux annuel en taux hebdomadaire.

## Formule et critère

Formule standard (calcul, pas une citation de l'OQLF) : VAN = somme, pour t de 0 à T, de CFt / (1 + k)^t, avec CFt le flux net de trésorerie de la période t (CF0 = -I, l'investissement initial), k le taux d'actualisation, T l'horizon.

Critère (fiche « méthode de la valeur actualisée nette », OQLF) : un projet d'investissement n'est généralement acceptable que si sa VAN est positive.

## Valeur de contrôle (calcul)

Investissement initial 100 000 EUR, flux de 30 000 EUR par an pendant 5 ans, taux 8 % : VAN = 30 000 x (1 - 1,08^-5) / 0,08 - 100 000 = 119 781,30 - 100 000 = 19 781,30 EUR. VAN positive : projet acceptable.

## Lien avec les fiches du domaine

Les flux d'un investissement industriel (capex, flux annuels, valeur résiduelle) sont à calibrer à part ; les taux de financement de référence sont dans taux-credits-entreprises-bdf-stat-info-2026-09.md.
