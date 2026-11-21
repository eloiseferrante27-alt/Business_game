# Préventif dans l'usine : diagnostic et proposition de calibrage (19/11/2026)

Auteur : game-designer. Statut : **appliqué** (P1 à P4, 21/11/2026, voir § 5 et § 6) ; §§ 1 à 4 = proposition d'origine. Mise en œuvre et
mesure : `moteur-jeu` (code, mesures), puis `game-designer` (pack `ai/packs/usine.yaml`).
Marques : **[source]** = affirmation reliée à une fiche du corpus (chemin `knowledge/supply-chain/…`, ligne) ou à
une source officielle ; **[calibrage]** = choix de jeu, non sourcé, indicatif ; **[à vérifier]**.

## 1. Diagnostic

### 1.1 Les machines sont déjà en usure ; le préventif évite bien des pannes

- Toutes les machines du pack ont `weibull_shape: 2` (usine.yaml l.691, 704, 717, 730 ; spec J04 l.10084 à
  10316). Forme > 1 = risque de panne croissant avec l'âge **[source]** NIST/SEMATECH e-Handbook, § 8.1.6.2
  « Weibull » (taux de défaillance polynomial d'exposant forme - 1 ; forme 1 = loi exponentielle) :
  https://www.itl.nist.gov/div898/handbook/apr/section1/apr162.htm. Cette page n'est pas encore une fiche du corpus.
- Effet du préventif dans le code (`factory.py`, lecture) : `_prv` remet l'âge à zéro et tire un nouveau seuil
  (`m.age, m.hazard = 0.0, _hazard(m.rng)`), soit une remise à neuf ; la réparation `_rep` fait de même. Une
  intervention par machine ciblée et par semaine, au début de la pause de 20 min la plus tôt (`run`, tri des
  créneaux), durée `preventive_min` = 20 min = la pause : aucune production perdue sur le goulot. Coût : 50 € par
  intervention (`maintenance.cout_preventif`, **[calibrage]** indicatif). Réparation : 75 € x MTTR, sans autre coût.
- Théorie (Monte-Carlo du renouvellement de Weibull, hors moteur, 33 h de marche du goulot par semaine
  **[calibrage]**) : pannes du goulot par semaine et par ligne, sans / avec préventif hebdomadaire.

  | forme | MTBF 36 h | MTBF 60 h | MTBF 90 h |
  |---|---|---|---|
  | 1 (hasard) | 0,92 / 0,92 | 0,55 / 0,55 | 0,37 / 0,37 |
  | 2 (pack) | 0,89 / 0,54 | 0,52 / 0,22 | 0,34 / 0,10 |
  | 3,5 | 0,88 / 0,41 | 0,51 / 0,08 | 0,33 / 0,02 |

- Mesure dans le moteur (spec J04 de l'audit, 3 lignes, 12 semaines, graines 5 à 8, aléas retirés, pilote =
  `played` vide, passif = production et maintenance non jouées). Pilote / passif :

  | cas | pannes des goulots | arrêt des goulots | inactivité des goulots | TRS | OTIF | Δ trésorerie pilote - passif |
  |---|---|---|---|---|---|---|
  | forme 2, MTBF x1 (M3 90 h) | 1-5 / 11-16 | 1-5 h / 11-16 h | 101-120 h / 90-109 h | 81,4-82,2 / 81,2-82,2 | 100 / 100 | -638 à -1 350 € |
  | forme 2, MTBF x0,4 (36 h) | 15-23 / 29-38 | 14-25 h / 31-43 h | 85-103 h / 70-87 h | ±0,4 pt | 100 / 100 | -600 à -938 € |
  | forme 1, MTBF x0,4 | 31-43 / 35-47 | même ordre, signe variable | ~ | ±0,4 pt | 100 / 100 | -900 à -2 138 € |

  Le préventif du goulot supprime 55 à 95 % de ses pannes en forme 2 (conforme à la table théorique), rien en
  forme 1 (conforme à la source). Le moteur est juste sur la fiabilité. (TRS de 82 % ici contre 74,9 % mesuré par
  moteur-jeu : aléas retirés et graines différentes ; l'écart pilote - passif est le même, nul.)

### 1.2 Causes chiffrées de l'« absence d'effet »

1. **L'indicateur ne voit pas les pannes évitées.** Les heures de marche du goulot sont identiques (1 215 / 1 215 h) :
   la production est fixée par la demande (OF tirés). L'arrêt évité (6 à 19 h sur 12 semaines) est repris sur
   l'inactivité du goulot (70 à 120 h), qui baisse d'autant chez le passif. Le TRS mesuré
   (`factory_game._snapshot`, `trs = bons / (cadence x temps planifié)`, l'attente comptée dans le temps
   planifié) reste fixé par la demande ; la `performance` absorbe ce que la `disponibilité` perd. Les notions
   `pannes_par_usure` et `maintenance_preventive` n'ont pour indicateur que `trs` (usine.yaml l.1237, 1242).
   C'est vrai en théorie des contraintes : quand le marché est la contrainte, une heure perdue au goulot se
   rattrape **[source]** wikipedia-fr-theorie-des-contraintes l.32 ; notion `goulot` du pack (l.1245).
2. **La panne évitée ne coûte presque rien.** 36 préventifs x 50 € = 1 800 € ; pannes évitées ≈ 10 x 1 h x 75 € =
   770 € ; aucune vente perdue : le passif gagne 640 à 1 350 €. La notion `maintenance_preventive` dit le
   correctif « souvent plus cher à cause des arrêts et des dégâts en chaîne » **[source]** wikipedia-en-maintenance
   l.50 (« consequential damage »), l.34, l.39 ; le moteur ne modélise ni dégâts ni arrêt coûteux. La note
   `maintenance.cout_preventif` (« une panne du goulot coûte en plus environ 20 produits par heure d'arrêt ») est
   fausse dans J04 : 0 produit perdu, OTIF 100 %.
3. **Aucun contraste hasard / usure.** Toutes les formes valent 2 : la moitié de la leçon RCM (« contre les pannes
   au hasard, le préventif n'aide pas ») n'est jamais observable **[source]** wikipedia-en-reliability-centered-
   maintenance l.28, l.31, l.53 (« does the equipment actually wear out, with use? »).
4. **Le débrief ne dit pas ce que le préventif a fait.** `_lessons` n'ajoute la phrase d'usure que si le TRS est
   sous l'objectif ; `_facts_maintenance` compte les préventifs faits, pas les pannes évitées.
5. Hors sujet pour l'usine : `trs_drift` et `WEAR_TRS` appartiennent à `engine.py` (simulation de chaîne
   logistique) ; dans l'usine `trs_drift` est vide (spec J04 l.2902).

## 2. Proposition

### P1. Dire les pannes évitées (moteur-jeu, débrief et faits) — prioritaire
- Pannes attendues sans préventif sur une période : `X = heures de marche / (MTBF x facteur d'aléa)` **[source]**
  wikipedia-en-mean-time-between-failures l.14 (MTBF = somme des temps de marche / nombre de pannes). Vérifié dans
  le moteur : passif J04, 1 215 h / 90 h = 13,5 attendues, 11 à 16 observées.
- Pannes évitées estimées : `E = X - N` (N observées). Affichées seulement si `E >= 2 x racine(X)` **[calibrage]**
  (seuil de bruit, à la façon d'une loi de Poisson, non sourcé) ; sinon « pas d'écart net avec le hasard ».
- Leçon de débrief, par goulot, toujours émise (pas seulement si le TRS est sous l'objectif), selon la forme :
  - forme > 1, préventif fait, E net : « {goulot} : {N} pannes pour {X} attendues avec son MTBF ; le préventif en a
    évité environ {E} ({H} h d'arrêt). Son risque de panne croît avec l'âge et l'entretien le remet à zéro. »
  - forme > 1, sans préventif : « {goulot} : {N} pannes, autant que prévu par son MTBF ({X}). Son risque croît avec
    l'âge : un entretien régulier en aurait évité une partie. »
  - forme = 1 : « {goulot} : {N} pannes pour {X} attendues{, avec | sans} préventif. Ses pannes arrivent au hasard,
    quel que soit son âge : l'entretien à date fixe ne les évite pas. »
  - toujours, bilan : « Préventif : {C} € ; réparations évitées : environ {R} € ; ventes perdues : {L}. » et, si
    L = 0 et l'inactivité du goulot > H : « le goulot avait {I} h d'inactivité pour rattraper : ici le marché
    limitait l'usine » (wikipedia-fr-theorie-des-contraintes l.32).
- Fait de l'agent maintenance chaque semaine : « {goulot} : {N} panne(s), {X} attendue(s) avec son MTBF. »
- Indicateur : ajouter aux notions `pannes_par_usure`, `maintenance_preventive` et `disponibilite` un indicateur
  « pannes et arrêt des goulots » (à créer dans le contrat des indicateurs ; si `spec.py` change : `architecte`).

### P2. Contraste usure / hasard sur le goulot **[calibrage]**
- Nouvelle clé de profil `bottleneck_shape` (forme du goulot, les autres machines restent à 2) : découverte 3
  (usure marquée, la leçon se voit), équilibré 2, expert 1 (pannes au hasard : le joueur doit reconnaître que le
  préventif du goulot ne sert pas et protéger le goulot autrement, RCM l.19 et l.52). Réglable (`tunables`), valeurs
  prises dans les profils (règle du pack l.296).
- Les machines non goulots gardent la forme 2 : en expert, `toutes` aide encore M1, M2 et M4, pas M3 (contraste
  dans la même ligne).
- Libellé de l'option `aucune` (« l'usure s'accumule ») à rendre conditionnel : faux pour une forme 1.

### P3. Coût d'une panne conforme à la source **[calibrage]**
- `maintenance.cout_degats_panne` : 100 € par panne (pièces et dégâts en chaîne, indicatif, non sourcé ; seul le
  principe est sourcé, wikipedia-en-maintenance l.50). Coût d'une panne du goulot : 75 + 100 = 175 € contre 50 €
  par préventif. Bilan attendu sur J04 (36 préventifs = 1 800 €) :
  - forme 2, MTBF x1 : ≈ 10 pannes évitées x 175 € = 1 750 € : neutre (≈ -50 €) ;
  - forme 2, MTBF x0,4 : ≈ 14,5 x 175 € = 2 540 € : le préventif paie (≈ +740 €) ;
  - forme 1 : 0 évitée : -1 800 €. Gradient vrai : le préventif paie quand l'équipement s'use et casse souvent.
- Corriger la note `maintenance.cout_preventif` (supprimer « 20 produits par heure d'arrêt » ou la conditionner à
  une ligne saturée).

### P4. Mesure plus nette (moteur-jeu, option)
- Tirages séparés pour les seuils de panne et les défauts (`m.rng` sert aux deux, `_mdone` et `_prv`) : le pilote
  et le passif garderaient les mêmes défauts, et la comparaison serait appariée.

## 3. Mesures attendues (critères pour moteur-jeu)

| # | Mesure | Critère |
|---|---|---|
| M1 | J04, forme 2, graines 5-8 : pannes des goulots pilote / passif | pilote <= 50 % du passif (mesuré : 27 %) |
| M2 | même cas : `E` estimé contre (passif - pilote) | écart <= 40 % ; `X` du passif à ±2 racine(X) des pannes observées |
| M3 | forme 1 sur le goulot : leçon émise | jamais « a évité » ; moyenne pilote - passif dans ±2 racine(X) |
| M4 | P3 : Δ trésorerie pilote - passif | ≈ 0 à MTBF x1 ; > 0 à x0,4 ; ≈ -1 800 € en forme 1 (±500 €) |
| M5 | équilibre : `.\scripts\test.ps1 -Fast` | pilote atteint les objectifs en découverte, peine en expert ; passif échoue |
| M6 | tests | une leçon par cas de P1 (forme > 1 avec et sans préventif, forme 1) |

## 4. À vérifier
- Proportions de Nowlan et Heap (1978, AD-A066579, Exhibit 2.13 ; souvent citées 4/2/5/7/14/68 %) : non
  vérifiées sur le rapport, ne pas les afficher.
- Ajouter au corpus la page NIST § 8.1.6.2 (loi de Weibull ; `rag-knowledge`) pour sourcer `weibull_shape`.
- Formes de Weibull typiques par composant (roulements, électronique) : non sourcées ; les valeurs 1, 2, 3
  restent des choix de jeu.
- TRS hors pauses (moteur depuis b6f1cf8) : l'exemple de la fiche wikipedia-en-overall-equipment-effectiveness
  (l.66-71) compte la pause comme perte de disponibilité ; la convention « poste - pauses prévues » n'a pas de fiche
  (à sourcer, NF E60-182 par exemple ; `rag-knowledge`). Note `pilotage.trs` du pack mise à jour en ce sens.

## 5. Mise en œuvre dans le pack et recalibrage (19 et 21/11/2026)

P1 et P4 codés par `moteur-jeu` ; P2 et P3 appliqués dans `ai/packs/usine.yaml`. Toutes les valeurs ci-dessous sont
des **[calibrage]** (non sourcées), sauf mention.

| clé | avant -> après | raison |
|---|---|---|
| `difficulties.*.bottleneck_shape` (+ `tunables`, `fragments`) | 2 partout -> 3 / 2 / 1 | P2 : usure visible en découverte, hasard en expert (RCM l.28, l.53) |
| `maintenance.cout_degats_panne` | absent (0) -> 200 € | P3, mesure M4 ci-dessous |
| `targets.trs`, `pilotage.objectif_trs` | 78 -> 80 % | TRS hors pauses : pilote 79,5-92 % |
| `criteria.trs` | partiel 73-78 -> 75-80 | marge de 5 points gardée |
| `alerts.trs_low`, `warn` des panneaux | 73 gardé | seuil d'une semaine, 7 points sous la cible |
| `stock_mp.stock_securite_jours` | 1 -> 2 jours | expert à 3 lignes : 0-27 -> 0-7 jours-ligne sans matière |
| `difficulties.expert.cash_weeks` | 2,5 -> 3 | J02 à une ligne : le pilote ne pouvait plus recommander en semaine 2 |
| `criteria.stockouts.margin.expert` | 4 -> 5 (pour 2 lignes) | partiel : 2,5 jours-ligne à une ligne, 7,5 à trois |
| `commande_initiale.cover_extra_days` | 1 gardé | 2 retarde la première commande en équilibré |

**M4 (P3)**, J04, 3 lignes, sans aléas, graines 5 à 8, Δ trésorerie pilote (préventif du goulot) - passif (aucun),
moyenne : dégâts 0 € : -1 238 € (forme 2, MTBF du jeu) ; **200 €** : forme 2 +262 € (-425 à +1 225, neutre au bruit
près), forme 2 à MTBF x 0,4 +451 €, forme 3 +265 €, forme 1 -3 038 €. 150 € laissait le préventif perdant même en
forte usure (-137 €). Le gradient usure / hasard est net ; l'écart entre MTBF x 1 et x 0,4 reste faible au regard du
bruit (4 graines).

**Jouabilité** (`autopilot_check`, partie de référence et J01 à J10 régénérés avec le pack, graines 5 à 8 ; passif =
partie avancée sans aucune action) :

| niveau, lignes | parties | pilote jouable | TRS pilote | OTIF min | jours-ligne sans matière | passif en échec |
|---|---|---|---|---|---|---|
| découverte, 1 | 8 | 8 | 89,7-92,0 % | 100 | 0 | 8 |
| découverte, 3 | 8 | 8 | 80,8-82,4 % | 100 | 0 | 8 |
| équilibré, 1 | 4 | 4 | 87,5-89,7 % | 100 | 0-1 (1 partiel) | 4 |
| équilibré, 3 | 4 | 4 | 79,5-80,5 % (2 partiels) | 100 | 0 | 4 |
| expert, 1 | 40 | 40 | 82,7-86,9 % | 100 | 0-2 (14 partiels) | 36 |
| expert, 3 | 40 | 40 | 80,7-84,8 % | 96,7 | 0-7 (12 partiels) | 36 |

Exception : **J04** (modules production et maintenance, sans pilotage) : le passif atteint tout (8 parties sur 8),
déjà avant ce recalibrage. Les OF et la matière y sont pilotés automatiquement ; seul le préventif sépare pilote et
passif, et en expert le goulot tombe au hasard, où ne rien faire est juste. À traiter par la mécanique (voir § 6).

## 6. Pour `moteur-jeu` (textes de `_wear_lessons`, `_lessons`, fait de maintenance)

Remplacer (`{p}` = « panne » si n <= 1, sinon « pannes ») :
1. forme <= 1 : « {goulot} : {n} {p} pour {x} attendues d'après son MTBF, {avec|sans} préventif. Ses pannes arrivent
   au hasard, quel que soit son âge : l'entretien à date fixe ne les évite pas. » (« attendues avec préventif »
   laissait croire à une attente calculée avec le préventif).
2. forme > 1, préventif, écart net : « {goulot} : {n} {p} pour {x} attendues sans entretien d'après son MTBF ; le
   préventif en a évité environ {e} ({h} h d'arrêt). Son risque de panne croît avec l'âge et l'entretien le remet
   à zéro. »
3. forme > 1, préventif, écart sous 2 racine(x) (remplace « pas d'écart net avec le hasard ») : « {goulot} : {n} {p}
   pour {x} attendues sans entretien d'après son MTBF ; l'écart reste dans les variations du hasard : on ne peut pas
   dire combien le préventif en a évité. »
4. forme > 1, sans préventif (remplace « autant que prévu », faux quand n s'écarte de x) : « {goulot} : {n} {p} pour
   {x} attendues d'après son MTBF, sans préventif. Son risque croît avec l'âge : un entretien régulier en aurait
   évité une partie. »
5. bilan (les dégâts sont maintenant comptés) : « Préventif : {C} ; réparations et dégâts évités : environ {R} ;
   ventes perdues : {L} produit(s). »
6. `_lessons`, TRS : « pannes, pauses, ralentissements et rebuts le font baisser » est faux depuis que le TRS exclut
   les pauses -> « pannes, attentes, ralentissements et rebuts le font baisser ». La phrase d'usure se fonde sur
   `any(weibull_shape > 1)` de toutes les machines ; la fonder sur les goulots : tous > 1 -> phrase actuelle ;
   tous = 1 -> « Ici, les pannes du goulot arrivent au hasard : un préventif à date fixe ne les évite pas. » ;
   mixte -> rien.
7. fait de maintenance : « {goulot} : {n} panne(s) depuis le début, {x} attendue(s) sans entretien d'après son
   MTBF. »
8. Phrase d'inactivité (P1, facultative) : ajouter à `_wear` `idle_h` = (attente_matiere + sortie_pleine) / 60 du
   goulot ; si ventes perdues = 0 et `idle_h` > heures d'arrêt évitées : « Aucune vente perdue : le goulot avait
   {i} h d'attente pour rattraper ses arrêts ; ici, le marché limitait l'usine. »
   (wikipedia-fr-theorie-des-contraintes l.32).
9. J04 (à spécifier avec `architecte` si `spec.py` change) : sans module pilotage, le passif ne peut échouer que sur
   un critère propre à la maintenance. Proposition : critère « arrêt des goulots pour panne » (heures, somme de
   `down_h` de `bottleneck_wear`), cible = arrêt du pilote x 1,2, marge 0,3 x cible, appliqué seulement si
   `maintenance` est un module joué et la forme du goulot > 1. Exemple J04 forme 2 : pilote 1-5 h, passif 11-16 h
   -> le passif échoue. Seuil 1,2 : **[calibrage]**.
