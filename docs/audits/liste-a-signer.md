# Jeux conçus par l'IA, relus (exigence n° 1)
Pack usine (sha256 5202967e1f66134cd9db3084396948aeabffcfc1aabe45c5b28e46859a228674, copie de travail non commitée du
19/11 09:31, avant la génération de 09:51) · prompt factory.design v3 · modèle qwen2.5:3b · résultats du 19/11/2026
(ai/evals/results/audit-2026-11-19/) · protocole : docs/audits/protocole-jeux-ia.md (version 1).

**État : rien à signer.** Les 10 jeux sont refusés (critère bloquant en échec) : 0 conforme, 0 à corriger, 10 refusés.
Le défaut D1 suffit à refuser chacun d'eux ; il vient du pack (game-designer). Une fois les causes corrigées, chaque
entrée sera rejouée avec `seed + 1000` (protocole § 4), puis relue en entier.

| Id | Titre | Secteur | Niveau | Semaines | Aléas | Verdict | Fiche |
|---|---|---|---|---|---|---|---|
| J01 | Métallerie du Val · Équipement en acier | industrie | expert | 4 | aucun (forcé s2) | refusé | jeux-ia/J01.md |
| J02 | Équipements Véloce · Équipement automobile | automobile | expert | 12 | rares, plan s2/s4/s6 | refusé | jeux-ia/J02.md |
| J03 | Soudures de l'Estuaire · Équipement en acier | industrie | expert | 12 | rares, plan s2/s3/s4 | refusé | jeux-ia/J03.md |
| J04 | Ateliers Métal Loire · Équipement en acier | industrie | expert | 12 | rares, aucun tiré (forcé s2) | refusé | jeux-ia/J04.md |
| J05 | Mécasoud Est · Équipement automobile | automobile | découverte | 5 | rares, plan s2/s3/s4 | refusé | jeux-ia/J05.md |
| J06 | Métallerie du Val · Équipement en acier | industrie | expert | 12 | fréquents, 8 aléas | refusé | jeux-ia/J06.md |
| J07 | Soudures de l'Estuaire · Équipement en acier | industrie | expert | 12 | = J03 | refusé | jeux-ia/J07.md |
| J08 | Équipements Véloce · Équipement automobile | automobile | expert | 12 | = J02 | refusé | jeux-ia/J08.md |
| J09 | Ateliers Métal Loire · Équipement en acier | industrie | expert | 5 | rares, 1 tiré (s3) | refusé | jeux-ia/J09.md |
| J10 | Mécanique du Bocage · Équipement en acier | industrie | expert | 12 | fréquents, 8 aléas | refusé | jeux-ia/J10.md |

## Défauts communs (repris par les fiches)

| N° | Critère | Défaut, citation exacte et preuve | Jeux | Propriétaire | Bloquant |
|---|---|---|---|---|---|
| D1 | C2 | Règle `camion_six_palettes` citée « Cahier §2 : camion de 4 à 6 palettes (values.fournisseur.camion_palettes, exemple). » (textes.md l. 15 ; ai/packs/usine.yaml l. 331-333) : le cahier n'est pas une fiche de knowledge/supply-chain. | 10 | game-designer | oui |
| D2 | C2 (lu) | Notion `delai_et_fiabilite` : « le prix n'est qu'un critère de choix parmi d'autres » (textes.md l. 98 dans J01). La fiche citée, wikipedia-fr-stock-de-securite (l. 6), parle de demande imprévisible et de délais aléatoires ; ni « prix », ni « fournisseur », ni « critère » n'y figurent, ni ailleurs dans le corpus. | 10 | game-designer | oui |
| D3 | C4 (g) | Module Pilotage : « MP au point de commande (consommation pendant le délai + 1 jour) » (textes.md l. 24 ; pack l. 1040). Le moteur compte délai + 1 + `mp_safety_days` (factory_game.py l. 143). Exemple J01 : 2 000 u./sem. ÷ 5 j ÷ 120 u./palette = 3,33 palettes/j ; (3 + 1 + 1) j donnent 16,7, soit 17 palettes, valeur de la leçon (« le place à 17 palettes ») ; délai + 1 donnerait 14. La note `stock_mp.stock_securite_jours` (pack l. 449, vue formateur) dit encore « Le moteur code encore délai + 1 jour ». | 9 (sauf J04) | game-designer | oui |
| D4 | C4 (b) | Pitch « Niveau expert : pannes plus fréquentes, plus de défauts, stocks bas, usine chargée à 92 %, livraison à J+1. » alors que `tunings` remet `mtbf_factor` (et `mp_stock_days`, `pf_stock_days`) au profil découverte : factory_generation.py l. 28-30 change les valeurs, l. 94 garde `detail` du niveau. | J01, J03, J04, J06, J07, J10 | game-designer (fragments) + moteur-jeu (composition) | oui |
| D5 | C4 | Fait du magasinier MP : « Une ligne s'est arrêtée 1406 minutes faute de matière. » La valeur est la somme des lignes (factory_game.py l. 657-659) : alertes du même écran 445 + 445 + 517 min (J01, briefings-alea.json l. 29 et 107-125). Faux dès deux lignes. | J01, J06, J09 (vus) ; tout jeu à 2 ou 3 lignes | moteur-jeu | oui |
| D6 | C4 (f), C3 (lu) | `unmet` faux, hors sujet ou dégénéré : il déclare absent ce que le jeu simule (aléas, fournisseurs, soudure, automobile), ou il oublie la vraie demande non couverte (marketing en J09, cibles chiffrées en J10). J10 : « usine chargée à  ubs  ough  ough … » passe le filtre C3. | 9 (sauf J04) | ia-runtime | oui |
| D7 | C1 (écriture) | Nombres non mis en forme : « TRS de Ligne 1 à 68.268 % », « 13.7 bons par heure mesurés pour 16.0 attendus », « trésorerie finale d'au moins 95400 € », « OTIF moyen >= 95.0 (partiel 90.0) », « TRS moyen de 74.0 % ». Origine juste (voir C1 tranché). | 10 | moteur-jeu (correction en cours) | non |
| D8 | C1 (outil) | L'outil C1 ne cherche pas le rapport de semaine (`state.snap.report`), d'où les 25 « non trouvés ». Il accepte aussi des coïncidences comme « trouvés » : « 4 » semaines → `pack.placement_rules[1].note` ; « 0 » jour-ligne → `pack.world.spawn[0]` ; « 6 » palettes → `pack.limits.weeks[2]` (J01 controles.json l. 34-76). Un « trouvé » ne prouve donc pas l'origine. | 10 | ia-runtime (outil d'eval) | non |
| D9 | C9 | Ruptures du pilote en expert. (a) Stock MP de départ de 2,5 j (`difficulties.expert.mp_stock_days`), plus court que les 3 j du fournisseur standard : rupture certaine en semaine 1 (J01 1 406 min, J02 572, J06 1 304, J09 1 544), absente quand le réglage `mp_stock_days` vaut découverte (J03, J04, J10). (b) La marge partielle de 4 jours-ligne, calibrée à 2 lignes (note `criteria.stockouts`), ne tient pas à 3 lignes (J10 : 6 ; J01 : 18 ; J06 : 14). | J01, J06, J09, J10 ; J02 et J08 partiels | game-designer (calibrage) + moteur-jeu (mécanique) | oui |
| D10 | C9 | Découverte : TRS du pilote à 74,2 % pour une cible de 78 % (J05, 3 lignes). En découverte, tout doit être atteint. À vérifier, voir plus bas. | J05 | game-designer + moteur-jeu (mesure) | oui |
| D11 | C5 (lu) | Sigles non expliqués à leur première apparition : « OTIF moyen d'au moins 95 %, TRS moyen … » (règle `objectifs`, l. 7, avant les notions) ; « stock PF + encours », « MP au point de commande » (module Pilotage, l. 24). | 10 | game-designer | non |
| D12 | C5 (latent) | Personnalité `bienveillant` : « style: tutoie, rassure, glisse parfois un conseil » (pack l. 1107), contraire au vouvoiement exigé. Le défaut ne se voit dans aucun des 10 jeux, puisqu'aucun n'a pris ce ton, mais il apparaîtra dès qu'un jeu le prendra (J07 aurait dû). | 0 vu | game-designer | non |
| D13 | C5 (registre) | Pitch « votre équipe pilote pilotage, production et maintenance » (J05 : « votre équipe pilote pilotage pour livrer »). Le texte vient de factory_generation.py l. 92 ; la copie de travail dit déjà « votre équipe assure les modules », à confirmer au prochain tirage. | 10 | moteur-jeu | non |
| D14 | C10 / C8 | Le modèle ignore les consignes. Il choisit expert sur les 9 jeux où le niveau n'est pas imposé ou est « à revoir » (dont J01 « découverte, lycéens », J03 « niveau moyen ») ; il prend `agent_tone: exigeant` sur 10 jeux sur 10 (dont J05 « en douceur » et J07 « plus bienveillants ») ; 6 jeux expert reçoivent des `tunings` découverte qui défont le niveau. La régénération ne change rien : la spec de J07 est identique à celle de J03, celle de J08 à celle de J02 (même sha256). | 10 | ia-runtime | C8 oui (J07, J08) |
| D15 | C6 | Prix des offres arrondis à l'euro : en J05, l'offre rapide (8,4 €/u.) et la standard (7,5 €/u.) s'affichent toutes deux « 8 €/u. » (spec.json l. 115-128), si bien que l'écart de coût disparaît de l'écran. | J05 (vu) ; tout libellé | moteur-jeu | non |

### C1 tranché : ce sont des faux positifs sur l'origine
Les 25 « non trouvés » (J01 5, J02 3, J04 1, J06 6, J08 3, J09 6, J10 1) sont tous calculés par le moteur à partir
du rapport de la semaine passée : minutes d'arrêt faute de matière (factory_game.py l. 657-659 ; alertes
`starved`), TRS par ligne (alerte `trs_low`, gabarit du pack l. 385), produits contrôlés et rebuts (l. 698), cartons
et palettes (l. 712). Aucun chiffre n'est inventé : C1 n'est bloquant pour aucun jeu. Restent trois écarts : leur
écriture (D7), une phrase fausse sur 1 406 min (D5, qui relève de C4) et l'outil lui-même (D8).

## Corrections du pack à faire par game-designer (après les relances d'ia-runtime, par priorité)
1. D1 : retirer `citation` de `game_rules.camion_six_palettes` (pack l. 333). C'est une règle du jeu, comme
   `matiere_payee_reception` ; sa valeur figure déjà dans « Non sourcé » (`fournisseur.camion_palettes`, exemple).
2. D2 : réécrire `notions.delai_et_fiabilite`, par exemple « Plus les délais de réapprovisionnement sont aléatoires,
   plus le stock de sécurité doit être important. » (wikipedia-fr-stock-de-securite, l. 6). Supprimer la clause sur le
   prix, faute de fiche.
3. D3 : `modules.pilotage.autopilot` (l. 1040) → « MP au point de commande (consommation pendant le délai + 1 jour de
   révision + 1 jour de sécurité) » ; mettre à jour la note `stock_mp.stock_securite_jours` (l. 449).
4. D4 : découper `difficulties.<niveau>.detail` en fragments par clé (`mtbf_factor` : « machines fiables » /
   « pannes plus fréquentes » ; `defect_factor` ; `mp_stock_days` et `pf_stock_days` : « stocks confortables » /
   « stocks bas » ; `load` : « usine chargée à {load} % » ; `promised_days` : « livraison à J+{n} »). Mécanique pour
   moteur-jeu : `_meta` assemble les fragments du profil réellement appliqué à chaque clé. Exemple J03 : « Niveau
   expert : machines fiables, plus de défauts, stocks confortables, usine chargée à 92 %, livraison à J+1. »
5. D9 : calibrage des ruptures en expert. (a) Mécanique à spécifier pour moteur-jeu : au départ, une commande standard
   déjà en route, de min(camion, ⌈conso × (délai + 1) − stock initial⌉) palettes, qui arrive le jour
   ⌊mp_stock_days⌋. Exemple J01 : ⌈3,33 × 4 − 8⌉ = 6 palettes, arrivée à J+2. Le stock reste bas, mais la rupture
   n'est plus garantie. (b) `criteria.stockouts.margin` par ligne : partiel = marge × lignes ÷ 2, soit 6 jours-ligne en
   expert à 3 lignes (règle `apply_rules`, moteur-jeu). (a) et (b) seront mesurés (graines 5 à 8, 1 et 3 lignes)
   avant d'être adoptés.
6. D10 : après mesure du TRS du pilote par niveau et par nombre de lignes (moteur-jeu), choisir entre une cible par
   niveau et le retrait du temps sans commande dans le temps planifié (voir « À vérifier »).
7. D12 : `personalities.bienveillant.style` → « vouvoie, rassure, glisse parfois un conseil ».
8. D11 : expliquer OTIF et TRS dans la règle `objectifs` (200 caractères au plus après substitution), et écrire
   « produits finis » et « matière » en clair dans `modules.pilotage.autopilot`.
9. Nuance de C2 : dans `notions.pannes_par_usure`, remplacer « la plupart des pannes ne sont pas liées à l'âge » par
   « … ne sont pas forcément liées à l'âge ». La fiche wikipedia-en-reliability-centered-maintenance écrit « the vast
   majority of failures are not necessarily linked to the age of the asset ».

## Hors pack (propriétaires)
- ia-runtime : D6, D8, D14, le secteur de J10 et la régénération sans effet. La conception doit être refusée (ou
  relancée) quand une clé de la section régénérée reste identique malgré une `note`, quand `unmet` répète un mot ou
  contient des mots hors dictionnaire, ou quand `unmet` nie une fonction simulée (aléas, fournisseurs).
- moteur-jeu : D4 (composition), D5, D7, D9 (mécanique), D13, D15, et la vérification du joueur passif de J04 (fiche
  J04).

## À vérifier (rien n'est tranché par supposition)
- D10 : le moteur compte-t-il dans le temps planifié du TRS les heures où la ligne attend faute de commande ? La fiche
  wikipedia-en-overall-equipment-effectiveness (l. 164-170) range « lack of orders » dans l'OOE, pas dans l'OEE.
  Si c'est le cas, une charge plus faible (0,80 en découverte) fait baisser le TRS atteignable. Indice : le TRS du
  pilote vaut 74,2 % en J05 (découverte), contre 76,6 % en J06 et 76,8 % en J10 (expert, 3 lignes).
- J04 : le joueur passif obtient les mêmes verdicts que le pilote (TRS 74,9 % partiel, 3 jours-ligne partiel) et plus
  de trésorerie (387 931 € contre 386 468 €). Un rôle tenu sans action garde-t-il le préventif par défaut ?
- Écarts d'exécution par rapport au protocole : le dossier s'appelle `audit-2026-11-19` (au lieu de
  `jeux-ia-<date>`), il n'y a pas d'`index.md` (un `resume.md` à la place) et aucune réplique d'agent n'a été produite.

Défauts trouvés et corrigés : aucun à ce jour (corrections listées ci-dessus, aucun commit).
Limites connues : la relecture ne couvre ni les répliques libres des agents (`npc.dialogue`, non produites), ni le
rendu Godot, ni d'autres graines.

Je certifie avoir pris connaissance de ces 10 jeux et de leurs fiches.
Nom : ____________  Date : ____________  Signature : ____________

Relu par game-designer le 19/11/2026, sur les résultats du 19/11/2026.
