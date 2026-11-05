# G-MIX - Rapport d’écart (T01, livrable 1)

Audit du 2026-11-01, code de départ `91c6709` sur `contribution_amine`.
Périmètre : lecture du moteur, des modèles, des API, des interfaces web, des
assets procéduraux, des scènes/scripts Godot et des tests. T01 ne modifie pas
le comportement du jeu. Les sources fournies à la racine ont été copiées dans
`docs/` sans déplacer les originaux.

## 1. Références et méthode

- [Mon monde v3](<Mon monde v3 - blocs, agents et assets.md>) : seule référence du monde,
  huit blocs, méthodes intégrées à la production ; v1/v2 exclues de l’audit normatif.
- [Cahier des charges](<Cahier des charges - configurations et interface.md>) :
  extraction documentaire des 42 pages du [PDF fourni](<Cahier des charges configurations et interface.pdf>).
  Les références § ci-dessous désignent ce cahier. Le PDF garde les maquettes et
  l’indentation originale de l’annexe A ; l’extraction ne constitue pas un YAML valide.
- [AGENTS.md](../AGENTS.md) : périmètre des tâches, extension additive et décisions T00.
- Sources **absentes** : « module fournisseurs et acheminement », son réseau mondial,
  annexe A détaillée et bibliothèque de crises sourcées ; ancien catalogue usine
  AL-01…AL-13. Demandées à Amine. Aucun intitulé ou effet absent n’est déduit.

Statuts : **présent conforme** = exigence limitée vérifiée ; **à compléter** = base
réutilisable mais conformité incomplète ; **absent** = aucune réalisation trouvée ;
**source manquante** = impossible de conclure sans le document désigné.
Un tableau affiché ou un asset 3D ne prouve pas une règle moteur.

## 2. Constat général et correction de l’inventaire initial

Le jeu actuel est une simulation hebdomadaire fonctionnelle, avec tablette et
scénario JSON. Il n’est pas encore le moteur journalisé configurable du cahier.
Les indications initiales d’AGENTS.md doivent être nuancées :

| Sujet | Constat dans le code courant | Statut / suite |
|---|---|---|
| Catalogues | `SUPPLIER_CATALOG`, `PRODUCT_CATALOG`, `LINE_NAMES` ne sont plus présents. `scenario.py` charge `scenarios/default.json`. | À compléter par T02, conserver ce point d’entrée. |
| Configuration | Un fichier JSON décrit produits, fournisseurs, stocks, gamme, demande, flotte, agents et blocs. Pas de `config/world.yaml` ni de validation Annexe A. | À compléter, pas « aucun fichier de configuration ». |
| Tablette | `tablet.js` comporte Fournisseurs, Comparateur, Achats MP, Commandes clients, OF, Stocks & alertes. | À compléter : aucune des dix pages avec les trois onglets communs. |
| Stock | `StockItem` unifie MP/SF/PF/PDR ; `MaterialStock` et `Stock` ne sont pas des classes du code audité. | Garder les champs/identifiants actuels, ne pas reconstruire à partir d’un inventaire périmé. |
| Clients | `CustomerAgent` génère les commandes ; pas de classe `GMSClientAgent` dans cette révision. | Réutiliser `CustomerAgent` dans T16. |
| Monde | Neuf blocs, dont `bureau_etude`, et responsable de production affecté à ce bureau. | Écart avec les huit blocs v3. Intégrer les méthodes à la production sans supprimer les anciens identifiants. |
| Production | Quatre lignes sur quatre produits ; gamme commune de quatre machines. | Ajouter le choix `lignes_identiques` ; préserver les références existantes (§25). |
| Temps | `current_week`, `work_minutes_per_week`, délais et décisions à la semaine. | T00/T03 : choix humain requis avant migration. |
| Aléas | Deux événements de marché, plus retards et pannes dans les règles métier. Aucun identifiant AL-NN. | T30 : ne pas confondre ces mécanismes avec un catalogue pilotable. |

## 3. Socle commun (§1–§9, §23)

| Exigence | État observé et preuve | Écart / tâche |
|---|---|---|
| API et simulation existantes conservées | **Présent conforme** pour la compatibilité actuelle : `/`, `/health`, `/api/state`, `/api/new-game`, `/api/decisions`, `/api/next-turn`, plus `/api/scenarios` et trois routes `/api/tablet/*` dans `main.py`. | Les extensions `/api/v2` doivent s’ajouter (T05). |
| Identifiants historiques | **Présent conforme** sur ce point : `LINE-01…04`, `Ln-Mk`, `SKU-*`, `MAT-*`, `SUP-*`. | Conserver aussi `SF-*`, `MAT-CART`, `MAT-PDR`, les blocs/agents et les préfixes de commandes/camions existants. Ajouter les IDs ZONE-TYPE-NN sans remplacement destructif. |
| Monde depuis configuration, sans constantes métier | **À compléter** : JSON et modèles Pydantic présents. `SEED = 42`, seuils/probabilités de `MarketAgent`, bornes de difficulté, valeurs par défaut et formules simplifiées restent dans Python ; implantation et nombres de machines visibles restent dans JS. | T02, puis tâches moteur/UI correspondantes. Ne pas externaliser aveuglément les constantes purement graphiques comme paramètres métier. |
| Paramètres `fixe/a_generer/desactive`, noyau obligatoire, monde figé | **Absent** : `load_scenario` lit et met en cache un dictionnaire mutable ; pas de phase génération/validation ni de verrouillage. | T02 ; génération §23 à attribuer explicitement, non couverte par une tâche dédiée du board. |
| Vérifications §4 | **À compléter** : types/bornes Pydantic, scénario inconnu et références de décisions vérifiés. Pas de validation croisée MTTR/MTBF, point de commande, capacités, offres, distance/transport ou écart volontaire. | T02. Le scénario courant a ≥2 vendeurs pour chaque MP/PDR, mais le chargeur ne l’impose pas. |
| Horloge 8 h, ×1…×60, pause, saut | **Absent** : `next_turn` avance directement une semaine. L’horloge Three.js sert à l’animation. | T00/T03. Équivalence des résultats DOIT (§24), même journal DEVRAIT (§9). |
| Tirages depuis la graine du scénario | **À compléter** : tous les tirages métier Python utilisent `self.rng`/le `rng` transmis, pas de tirage global trouvé. Graine 42 en dur, sans champ scénario ni état RNG dans SQLite. | T02/T03. Le test existant compare seulement les KPIs de deux nouvelles parties ; la reprise diverge, voir §9. |
| Journal append-only de tous les changements | **Absent** : `events: list[str]` réinitialisé chaque semaine, `last_week` écrasé ; pas d’heure/élément/avant/après/cause. | T03. Le journal de transactions SQLite n’est pas le journal métier. |
| KPIs depuis journal uniquement | **Absent** : calculs directs depuis état et compteurs dans `next_turn`, `_refresh_kpis`, `quotes` ; KPIs initiaux issus du profil de difficulté. | T05 et chaque moteur. Aucune formule de KPI ne doit migrer vers le navigateur. |
| Droits serveur et tentatives refusées | **Absent** : validation des références métier présente, mais aucun droit `verrouille/initial/libre`, compteur de changements, délai d’effet ou journal de refus. | T04. Les actions existantes ne sont pas des contrôles de droits. |
| Agents et ressources partagées | **À compléter** : cinq états définis dans `AgentState`, seuls disponible/occupé assignés par ensemble de rôles en fin de semaine. Pas de file de tâches ni d’exclusion mutuelle temporelle. | T03 et T10–T16 ; un même réceptionnaire sert quai et réception. |
| Alertes ouverture/fermeture/gravité | **À compléter** : `_refresh_alerts` reconstruit des chaînes d’alertes stock. Pannes et retards existent dans état/événements, mais pas de cycle de vie, classement ou pastille par bloc. | T04, puis règles départementales. |
| Sauvegarde | **À compléter** : snapshot SQLite unique ; archives des anciennes versions au lieu de chargement incompatible, testées. | Persister journal/horloge/RNG/config validée ; conserver les sauvegardes historiques. |
| IA de génération (§23) | **Absent** : aucune intégration trouvée. | Définir une tâche : remplissage borné des seuls paramètres délégués, validations moteur et gel du monde ; aucune IA ne calcule les résultats métier. |

### Écarts de calculs visibles et formules actuelles

- `tablet.js:achats/updateCost` calcule `prix × quantité` et `current_week + délai`.
  `game.js:placeOrder` recalcule aussi l’arrivée ; ces valeurs doivent venir du serveur.
- `tablet.js:clients` agrège le carnet par produit ; les écarts coût/délai/fiabilité
  du comparateur sont calculés dans `renderXY`. Le serveur devrait fournir les
  mesures métier de comparaison ; formatage et dimensions des barres restent de l’affichage.
- TRS actuel = moyenne des `line.efficiency`, pas disponibilité × performance × qualité (§14).
- OTIF actuel = livrées à l’heure ÷ (livrées + nouvelles commandes en retard)
  de la semaine ; le dénominateur demandé en §18 est les commandes livrées.
- `stockouts` compte les PF sous leur minimum, pas les passages à zéro et leur durée (§13).
- `quality_rate` part de volumes agrégés ; aucun défaut n’est attribué au produit/machine
  dans le journal. `purchases_cost` est remis à zéro au changement de semaine.
- Les devis font `quantité × prix`, sans transport ni douane ; ce n’est pas le coût
  d’achat livré par produit fini emballé (§10).

## 4. Dix départements : moteur avant interface (§10–§19)

Toutes les lignes ci-dessous sont **à compléter**. Les moteurs sont aujourd’hui
des méthodes de `SimulationEngine` et des agents externes, pas encore les fichiers
`engine/departments/*.py`. Chaque futur KPI départemental doit lire le journal.

| Département / tâche | Présent réutilisable | Moteur et données restant à réaliser | Interface restant à réaliser |
|---|---|---|---|
| Fournisseurs §10 / T10 | `Supplier`, `PurchaseOrder`, `SupplierQuote`, `SupplierAgent`, `quotes`; vendeurs filtrés par article, achats et fiabilité. Huit fournisseurs, ≥2 vendeurs par MP/PDR. | Offres distinctes avec IDs, capacité/MOQ/conditionnement, GPS/pays, routes non dominées coût-délai-risque, douane, confiance, commande automatique, répartition et bascule, annulation PREVU. Cinq fournisseurs n’ont qu’un article, contre 2–4 exigés. États, historique livraisons et KPIs complets. Source réseau manquante. | Comparateur existant à étendre ; carte réelle, crises et alternatives de trajets, configurations et droits, KPIs par offre/fournisseur. |
| Quai de déchargement §11 / T11 | `_block_dock_and_reception` crée un `Truck` au bloc fournisseur ; modèle et assets de quai. | File d’attente, états camion/quai, palettes et zone de dépose, temps unitaire, capacité, créneau, priorités et réceptionnaire partagé. Actuellement toutes les livraisons sont traitées pendant le tour, sans contention. | Page dédiée : occupation, attente, planning, passage prioritaire/hors créneau, configurations, alertes >1 h et zone pleine. |
| Bureau de réception §12 / T11 | Comptage des unités non conformes et message « quarantaine ». | Palettes/BL, contrôle et échantillonnage, capacité réelle de quarantaine, libération/renvoi/tri/dérogation, réclamations. Aujourd’hui les non-conformes ne deviennent aucune entité persistante ; les bons excédant le stock sont refusés plutôt que retenus en amont. Transmettre les défauts non détectés à la production. | Page, fiches de non-conformité, actions et droits, attente >2 h et alertes de quarantaine. |
| Stock MP/SF/PF §13 / T12 | `StockItem`, trois parties + PDR, paramètres communs, sortie nomenclature, passage SF, alertes stock + commandes en transit. | Lots FIFO/FEFO, emplacements par partie et palettes, kits réservés/complets et temps de préparation, surplus rebut, chariot/batterie/recharge, inventaire système/réel, réappro automatique/périodique et PF→OF. Pas seulement une capacité en unités par référence. | Une page filtrable parties/articles ; inventaire, urgence kit, courbes/ruptures/couverture/rotation et réglages avec droits. |
| Chaîne de production §14 / T13 | Quatre lignes, quatre machines, BOM simple par produit, OF, capacité par goulot de chaque demi-ligne, volume SF, pannes bloquantes et compteur d’outil. | Choix lignes identiques, 2–6 machines, pauses/réglage/transferts/buffers/opérateurs, déroulement par machine, kit complet, OF affecté à une ligne/priorité/date, annulation et historique. La production est agrégée avant tirage de panne ; changement d’outil instantané sans technicien. Pas d’OF automatique ni de boucle physique de retouche. | Vue état/goulot, trois onglets, planning/Pareto, priorités, lignes actives, affectations, méthodes intégrées et actions complètes. |
| Contrôle qualité §15 / T14 | Dans `_block_production` : défaut cumulé des machines, part récupérable et réussite de retouche dans JSON, comptages conformes/rebut. | Tirages par produit, file et temps de contrôle, échantillonnage/détection, origine défaut, lots bloqués/seuil, choix rebut/retouche, retour ligne puis contrôle et défauts clients non détectés. Les parts actuelles sont des volumes tronqués déterministes. | Page, Pareto, courbes, décisions bloquer/libérer et contrôle renforcé ; alertes de lot et file. |
| Emballage §16 / T14 | `packing_queue`, capacité issue du temps colis/filmage, cartons consommés, PF et blocage si PF plein. | Colis/palettes persistants, film consommable selon nomenclature, temps de filmage réel, règle de palette incomplète, priorités/tâches rangement. `ceil` compte actuellement une palette partielle comme palette ; quatre produits/colis dans JSON contre un dans l’exemple v3, choix à confirmer. | Page, encours/cadence/occupation, paramètres avec droits, actions priorité et palette incomplète. |
| Maintenance & PDR §17 / T15 | File de lignes, article `MAT-PDR`, une réparation/semaine configurée, consommation d’une PDR, remise en marche. | Interventions par machine, déplacement/consignation/MTTR, état en attente de pièce, probabilité de PDR, préventif par heures/produits et changement d’outil par technicien. Risque actuellement lié au MTBF sans compteur de préventif. Commandes PDR automatiques et références multiples. | Page, historique machine/planning, priorités goulot, préventifs, réglages PDR et alertes. |
| Logistique & transport §18 / T16 | Stock PF, priorité date due, capacité globale flotte, livraison/enlèvement et camions dans deux zones externes. | Préparation/chargement et quai partagé par camions clients/usine, palettes/camion, départ plein/délai/immédiat, trajets/retours et indisponibilité de chaque camion. Actuellement livraison instantanée au tour ; contrôle par capacité totale, pas par tournée. | Page, carte/planning, remplissage et attente, actions de priorité/départ incomplet et configurations. |
| Clients §19 / T16 | `CustomerAgent`, noms/demande variable dans JSON, commandes, dates dues, deux modes et annulation après retard configuré. | Entités client EXT-CLI-NN avec GPS/demande/tolérance par client, saisonnalité, acceptation/refus/perte, promesse réglable, urgence, OF automatique et réclamations qualité. Historique livré/annulé actuellement limité aux semaines récentes. | Carnet existant à étendre : décisions accepter/refuser/autre date/urgence, prévision et part client, carte et trois onglets. |

## 5. Tablette, outils et monde 3D (§5–§8)

| Élément | Statut et preuve | Suite |
|---|---|---|
| Tablette comme interface d’action | **À compléter** : achats, OF, maintenance depuis `tablet.js` ; joueur sans bureau dans la scène web. | Réutiliser les actions/API, T06 et T20–T29. |
| Accueil global | **Absent** pour §8 : le HUD 3D montre certains KPIs mais aucun accueil tablette avec plan des huit blocs + fournisseurs/clients, alertes triées, liens KPI, couverture/coût livré, objectifs configurés et horloge. | T06/T32. |
| Trois onglets par département | **Absent** : les six onglets actuels sont des fonctions transverses, pas KPIs / Outils / Configurations pour dix départements. | T06, puis une page après chaque moteur. |
| Règles avant démarrage et confirmation | **Absent** : setup identité/difficulté/fournisseurs et didacticiel, sans revue des droits ni confirmation des réglages initiaux. | T04/T06. |
| Pop-up rouge 4 s avec messages §5 | **Absent** : toast générique de 3,2 s dans `game3d.js` (5 s en 2D), sans motif de droit ou journal de tentative. | T04/T06. |
| Tableur | **Absent** : le comparateur est un tableau HTML, aucune grille à formules SOMME/MOYENNE/MIN/MAX/SI, sauvegarde des feuilles ou envoi au tableur. | T00/T07. Export CSV DEVRAIT : non réalisé, à prévoir. |
| Carte réelle | **Absent** : pas de GPS, réseau mondial, bibliothèque cartographique, zoom/clic sur routes ou bandeau de crise. | Choix T00 ; T07/T10. La carte outil demandée est distincte d’un bloc fournisseur 3D, exclu par v3. |
| Graphiques, planning, journal | **Absents** : barres décoratives et progression OF présentes ; pas de courbes depuis début, comparaison KPI, Pareto, planning jour/semaine par ressource ou journal filtrable. | T07 sur les données moteur. |
| Désactivation d’outils | **Absente**, aucune liste de droits/outils par partie. | T02/T04/T06/T07. |
| Clic bloc → page tablette | **À compléter** : `onCanvasClick` ouvre l’inspecteur puis déplace le personnage ; `BLOCK_ACTIONS` offre un bouton vers l’un des six onglets. | T33 doit ouvrir directement la page correspondante sans exiger le déplacement du joueur. |
| Fournisseurs/clients visibles comme camions | **Présent conforme** au principe de représentation web : pas de bâtiments fournisseurs/clients ; trois types de camions provenant de `state.trucks`. | Conserver ; synchroniser ultérieurement leurs états/temps avec le moteur (T33). |
| Huit blocs, méthodes dans production | **À compléter** : neuvième `bureau_etude` dans JSON, `layout.js`, `BLOCK_ROLES`, ameublement et guide. | Intégration additive : préserver la compatibilité des anciens IDs ; ne pas supprimer ce bloc dans T01. |
| Modularité visuelle | **À compléter** : noms et agents depuis état, mais `ZONES`, quatre positions de lignes/machines et nombres de racks fixés en JS. | Adapter le rendu au monde validé sans reconstruire l’usine 3D (T33 et périmètre à préciser). |
| Assets v3 | **À compléter / présence statique** : registre `assets.js`, personnages et ameublement dans `game3d.js`, modèles procéduraux pour quais, stocks, machines, qualité, emballage, PDR et camions. | Aucune certification visuelle complète des assets dans T01 ; tables d’attente/quarantaine/filmage ne prouvent pas leur simulation. Méthodes encore dans le bureau supprimé de la référence. |
| Godot | **À compléter / prototype distinct** : scène sol/caméra/lumière/NPC ; `main_controller.gd` lit les KPIs et appelle les anciennes API. `npc_manager.gd` crée quatre ouvriers colorés selon KPIs ; déplacement avec RNG local non seedé dans `worker_npc.gd`. | Aucune usine à huit blocs ni tablette dix pages trouvée dans cette scène. Ne pas modifier Godot dans ces tâches sans instruction spécifique. Aléatoire de déplacement/texture web et Godot purement visuel, distinct des tirages métier. |
| Interface 2D conservée | **À compléter** : `/static/index.html` utilise `game.js`, qui lit encore `safety_stock` absent de `StockItem` et propose tous les stocks aux achats ; les lignes sont présentées comme opérationnelles sans consulter leur panne. | Dette existante à affecter ; préserver les fichiers/endpoints historiques. Aucun correctif produit dans T01. |

## 6. Interactions, aléas, évaluation et livrables (§20–§24)

### Flux et effets en chaîne (§20)

Le chemin agrégé MP → SF → contrôle → emballage → PF → livraison est présent,
ainsi que matière insuffisante, panne de ligne, PDR manquante et attente à
l’emballage si cartons/PF indisponibles. Le test de flux actuel le vérifie partiellement.

Restent absents : échanges journalisés, files/ressources partagées, palettes
retenues dans leur zone d’origine quand le stock est plein, propagation du blocage
vers l’amont, kit intégral préalable, dérogation réception → défaut production,
produit non contrôlé → réclamation client, retouche revenant réellement en ligne.
La réception refuse les bonnes unités excédentaires ; la production peut continuer
à alimenter `packing_queue` sans capacité d’encours spécifiée. T31 doit tester ces
effets après T10–T16, sans inventer un plafond d’encours.

### Rapprochement AL-01…AL-34 (§21, §25)

Aucun code AL-NN n’est implémenté. « Proche » ci-dessous signifie proximité de
comportement, **jamais équivalence validée**. Quatre déclencheurs manuel, heure
fixée, condition et aléatoire seedé sont à créer dans T30 pour le catalogue documenté.

| ID | Intitulé défini dans la source disponible | Rapprochement courant / manque |
|---|---|---|
| AL-01 | Retard fournisseur | Proche : `SupplierAgent` repousse d’une semaine selon fiabilité ; pas de durée jours imposée ni déclencheur formateur. |
| AL-02 | Livraison non conforme | Proche : part de chaque commande tronquée depuis le taux fournisseur ; ni tirage par unité, ni palette persistante, ni dérogation. |
| AL-03 | Source manquante | Non décrit au §21 ; aucun identifiant trouvé dans le code. Demander le catalogue original. |
| AL-04 | Source manquante | Même réserve ; ne pas attribuer une panne ou un autre mécanisme à cet ID. |
| AL-05 | Source manquante | Même réserve ; effet/paramètres/département inconnus. |
| AL-06 | Source manquante | Même réserve ; effet/paramètres/département inconnus. |
| AL-07 | Lot défectueux | Absent : pas de lot entier ciblable rendu non conforme en réception/qualité. |
| AL-08 | Source manquante | Non décrit au §21 ; aucun rapprochement justifiable. |
| AL-09 | Source manquante | Non décrit au §21 ; aucun rapprochement justifiable. |
| AL-10 | Source manquante | Non décrit au §21 ; aucun rapprochement justifiable. |
| AL-11 | Conflit de quai | Absent moteur : animation de files de camions côté JS, sans contention temporelle serveur. |
| AL-12 | Source manquante | Non décrit au §21 ; aucun rapprochement justifiable. |
| AL-13 | Source manquante | Non décrit au §21 ; aucun rapprochement justifiable. |
| AL-14 | Blocage d’un passage | `red_sea_disruption` ne fait qu’augmenter globalement le risque de retard et la demande : pas de nœud/trajet BLOQUE ni recalcul. Bibliothèque de crises absente. |
| AL-15 | Surcoût de transport | Absent : pas de tronçon/mode/coût transport. |
| AL-16 | Droits de douane | Absent : pas de pays/catégorie pour douane. |
| AL-17 | Embargo, fournisseur indisponible | `Supplier.active` existe ; aucun effet d’embargo ni durée sur les offres. |
| AL-18 | Capacité réduite | Absent : pas de capacité par offre. |
| AL-19 | Hausse de prix | Proche : `materials_price_hike` multiplie tous les prix par 1,10 ; pas de cible offre/article ni paramètre %. |
| AL-20 | Panne imposée | Pannes seedées spontanées présentes ; pas d’action imposée sur une machine avec durée. |
| AL-21 | Absence d’opérateur | État absent défini mais sans affectation/effet arrêt. |
| AL-22 | Dérive qualité | Taux machine présent mais sans effet ciblé en points/durée. |
| AL-23 | Ralentissement | Cycle machine présent mais sans effet ciblé ni durée/recalcul dynamique. |
| AL-24 | Usure accélérée de l’outil | Compteur d’outil présent, pas d’effet ciblé sur durée de vie. |
| AL-25 | Rupture de kit | Matière insuffisante limite un volume et produit un message ; pas de blocage ciblé ligne/OF pour durée. |
| AL-26 | Absence du réceptionnaire | Pas d’indisponibilité partagée bloquant quai et réception. |
| AL-27 | Panne du chariot élévateur | Chariot visuel, aucune ressource moteur bloquant rangement/sortie/kits. |
| AL-28 | Erreur d’inventaire | Pas de séparation stock réel/système ni correction d’inventaire. |
| AL-29 | Pénurie d’emballages | Cartons à zéro limitent l’emballage, pas d’effet imposé pour durée. |
| AL-30 | Absence du technicien | Pas d’indisponibilité du technicien bloquant les interventions. |
| AL-31 | Camion de livraison en panne | Capacité de flotte agrégée, aucun camion individuel indisponible. |
| AL-32 | Pic de demande | `demand_multiplier` de l’événement mer Rouge est global ; pas de client/%/durée ciblés. |
| AL-33 | Commande urgente | Aucune commande injectée par aléa ni priorité urgente. |
| AL-34 | Annulation de commande | Annulation automatique après retard présente, pas de commande ciblée par formateur. |

Les probabilités 0,08/0,16 et amplitudes des événements de marché sont en dur dans
`agents.py`. La mention « mer Rouge » est un scénario simulé sans fiche historique
sourcée : elle ne satisfait pas la bibliothèque de crises (§21/§23).

### Évaluation, génération et livrables

| Attendu | Statut | Suite |
|---|---|---|
| Critères KPI + seuil + échéance, progression sans verdict | **Absent** : textes objectifs du HUD calculés depuis stocks/retards, pas de critères du scénario. | T32 / §22. |
| Bilan atteint/partiellement/non atteint, échec et débrief par cause | **Absent**, journal et fin de partie pédagogique non définis dans le code. | T32 ; préciser l’évaluation partielle et la durée, voir questions. Aucun module financier à ajouter (§25). |
| Livrable 1 | **Présent** : ce rapport, réserves documentaires explicites. | T01 ; rapprochement final des anciens IDs réservé jusqu’à réception du catalogue. |
| Livrable 2 | **À compléter** : base FastAPI/scénario/tablette/sauvegarde réutilisable. | T02–T07. |
| Livrable 3 | **À compléter** : dix moteurs/pages complètes non livrés. | T10–T29. |
| Livrable 4 | **À compléter** : JSON produit actuel présent ; annexe YAML et paramètres/droits manquants. | T02 et tâches départementales. Ne pas remplacer les quatre produits par un produit inventé. |
| Livrable 5 | **Absent** : un seul `default.json`, pas les trois démonstrations prescrites. | T32 : panne M3 + maintenance/réaffectation, AL-14 + bascule trajet, verrouillage point de commande + lot libre. |

## 7. Questions ouvertes et valeurs manquantes

Ces questions sont consignées sans choix implicite de valeur ou de règle.

| Réf. | Décision / source attendue | Dépendances |
|---|---|---|
| Q01 | T00 : confirmer l’horloge unique et la période ; proposition du board = journée 8 h et période 1 jour. Le DOIT §9 et le point ouvert §25 doivent être arbitrés avant T03. | T03, délais, application des configurations et KPIs. |
| Q02 | T00 : tableur maison ou bibliothèque ; bibliothèque cartographique. Leaflet est une suggestion du board, pas une décision. | T07 ; aucune bibliothèque installée par T01. |
| Q03 | Fournir « module fournisseurs et acheminement », annexe détaillée, réseau et bibliothèque de crises sourcées. | Validation routes/GPS/risques/coûts T02/T10/T30/T32. |
| Q04 | Fournir le catalogue usine original pour AL-03/04/05/06/08/09/10/12/13 ; confirmer le rapprochement AL-07 et AL-11 documentés. | T30 ; aucun effet inventé pour remplir les trous. |
| Q05 | Choisir le monde initial cible : produit(s), nomenclature complète, lignes identiques ou distinctes ; règles de compatibilité des quatre lignes existantes face à la plage 1–3 de la cible. Quatre produits/colis actuels ou un dans l’exemple v3 ? | T02/T13/T14 ; préserver champs/IDs et permettre les deux structures. |
| Q06 | Fournir/générer avec le formateur les valeurs requises absentes : durées de vie outils, temps rangement/sortie/kit, nomenclature avec composants/emballages/film, préventif, délais PDR/réclamation, taille/tolérance/saisonnalité clients et coordonnées, capacités palettes/flotte. Les exemples/valeurs actuelles ne deviennent pas des valeurs validées automatiquement. | T02, T10–T16. Garder `a_generer` et signaler les noyaux incomplets. |
| Q07 | Définir les formules de confiance fournisseur, agrégation du risque et quantité économique, explicitement ouvertes au §25. Préciser aussi la distribution autour du MTTR, la variabilité des délais et la probabilité de perte/annulation selon tolérance. | T10/T15/T16 ; pas de formules improvisées. |
| Q08 | Annexe A illustrative incomplète par rapport aux tableaux : GPS fournisseurs/clients, stock initial/valeur article, opérateurs, probabilités de détection/PDR, affectation quai, quantité commandée PDR, flotte utilisée et priorités clients notamment. Établir leur représentation avec le formateur ; l’extraction du PDF a une indentation altérée. | T02 : s’appuyer sur §4 et §10–§19, pas charger le texte extrait comme YAML. |
| Q09 | Définir seuils « file longue », « seuil approché », OF en retard/date prévue, arrêt prolongé et verdict partiellement atteint ; préciser fin/durée de partie et dates de péremption FEFO si activé. | Alertes T04/départements, T31/T32 ; ne pas inventer de seuil. |
| Q10 | Décrire l’interface formateur et attribuer explicitement l’intégration IA §23, la configuration de session/graines par joueur et l’évaluation finale. Ces fonctions n’ont pas de tâche dédiée détaillée dans le board actuel. | §23/§25 et portée future ; T01 n’ajoute aucun écran formateur. |
| Q11 | Préciser le rendu additif du bloc historique `bureau_etude` désormais intégré à production, et le périmètre de correction de l’ancienne UI 2D. | T33 / propriétaire UI ; aucun identifiant supprimé. |

## 8. Ordre de réalisation proposé selon le Task board

1. T02 : modèle de configuration, diagnostics explicites pour données manquantes,
   validation §4 et compatibilité avec le scénario courant. Q03/Q05–Q08 peuvent
   empêcher la validation d’un monde complet ; elles n’autorisent pas des valeurs inventées.
2. Après décision T00, T03 : horloge, journal, RNG et sauvegarde/reprise déterministe.
3. T04/T05 : droits, refus, alertes et calculs journalisés + API additive `/api/v2`.
4. T06/T07 : shell tablette, règles, trois onglets et outils, selon contrats serveur.
5. T10–T16 selon leurs dépendances : une tâche moteur avant sa page T20–T29.
6. T30/T31/T32 : catalogue documenté, quatre déclencheurs, effets en chaîne,
   démonstrations et critères. T33 relie les pages au monde existant.

Ce rapport ne tranche pas T00, n’implémente pas T02 et ne modifie aucun fichier
moteur, interface, test ou Godot. Chaque suite conserve son périmètre/sa branche.

## 9. Vérifications et limites

- `.venv/bin/python -m pytest -q` : **9 tests réussis**, 2026-11-01.
  `pytest` et `httpx` installés uniquement dans l’environnement local ; aucune
  dépendance de production modifiée. Tests existants : stock unifié, neuf blocs,
  mêmes KPIs à graine fixe, chemin matière, vendeur par article, camion au quai,
  deux modes clients, devis triés, archivage d’ancienne sauvegarde.
- Smoke FastAPI `TestClient`, base SQLite temporaire isolée : HTTP **200** pour `/`,
  `/health`, `/api/state`, `/api/scenarios`, `/api/tablet/suppliers`,
  `/api/tablet/compare?sku=MAT-01&quantity=500`, `/api/tablet/customer-orders`,
  puis `/api/new-game`, `/api/decisions` avec OF de 300 et `/api/next-turn` (semaine 2).
- Reprise RNG : nouvelle partie, quatre tours, chargement d’une seconde instance
  depuis la sauvegarde, puis un tour de chacune. Les états divergent : agents,
  alertes, commandes clients, KPIs, bilan, prochain ID, stocks et camions.
  `database.py` ne persiste que `GameState`, tandis que le constructeur remet RNG à 42.
- Audit du JSON : nombres d’offres MAT-01=3 ; MAT-02/03/04, MAT-CART et MAT-PDR=2.
  Articles par fournisseur SUP-01=3, SUP-02=3, SUP-03=2, SUP-04…08=1.
- Lecture visuelle des pages 39 et 41 du PDF pour vérifier l’annexe A ; extraction
  des 42 pages conservée. Les maquettes restent consultables dans le PDF.
- Pas de certification visuelle navigateur/Godot, ni de test exhaustif des règles
  futures. Les tests existants figent notamment neuf blocs : leur réussite ne vaut
  pas conformité v3. Les anciens aléas non documentés restent non rapprochables.
