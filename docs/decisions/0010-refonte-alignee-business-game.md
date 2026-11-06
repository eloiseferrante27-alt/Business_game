# 0010 : refonte alignée sur Business_game (génération, lobby, jeu, débrief)

Date : 2026-11-04. Statut : **accepté** (décisions de l'utilisateur du 04/11, §7). Réordonne les chantiers des ADR 0008 et 0009 sans changer leurs contrats.
Référence : `eloiseferrante27-alt/Business_game`, branche `contribution_amine`. Captures `-Tour` 1280x720 : 06 à 24.
Contexte : selon l'utilisateur, G-mix « ne fait pas ce qui est attendu » (générer avec l'IA des jeux de ce type), et
trois moments ne sont pas ergonomiques : générer, créer un lobby, jouer.

## 1. Business_game en bref

- **Jeu** : une usine de « produits du quotidien » décrite par un JSON (`default.json`) : 4 produits, 4 lignes de 4 machines,
  8 fournisseurs, 4 clients, 9 blocs, 12 agents. Aucun chiffre n'y est sourcé.
- **Boucle hebdomadaire** : lire les alertes, comparer les fournisseurs, acheter MP et pièces, lancer les OF, planifier les
  réparations, puis « Semaine suivante » (maintenance, quai, réception, production, qualité, emballage, livraisons ;
  annulation après 2 semaines de retard). On lit ensuite OTIF, rendement des lignes, qualité, stock et ruptures.
- **Formateur** : aucun écran (point ouvert Q10 de leur cahier des charges) ; il édite le JSON. Les droits verrouillé,
  initial et libre sont prévus, pas faits.
- **Joueur** : seul, sans compte ni lobby ; nom d'entreprise, difficulté, règles à cocher, puis usine 3D (three.js, 4 KPI,
  « prochaine décision »). **La tablette porte le jeu** : barre (période, 3 KPI, alertes, « Semaine suivante »), rail de
  11 départements avec pastille, onglets KPIs, Outils (comparateur, tableur, graphiques, planning, journal) et Configuration.
  Un clic sur un bloc 3D ouvre sa page.
- **Pas de débrief ni de fin de partie.** Stack : FastAPI, SQLite, three.js. Aucune IA dans le jeu.

## 2. Écarts entre G-mix et la référence, par gravité

**Critique**
1. *Génération* : l'IA ne conçoit rien (formulaire « Aucun texte à rédiger » et cases à cocher, 07c). `design.py` produit
   1 variable sur 17 ; ni route `/games/designs` ni worker. L'ADR 0008 n'est pas livré : c'est l'attente n° 1.
2. *En jeu* : la boucle de décision est illisible. Tablette à 3 onglets presque vides (« Outils » = Caméra, Aide),
   actions dispersées dans les menus 3D, KPI en texte brut, ni alerte ni « prochaine décision », pas de « Prêt ».
3. *Type de jeu* : l'usine du type de Business_game (pack usine) ne se génère pas encore. moteur-jeu y travaille.

**Majeur**
4. *Lobby* : liste plate où le code est noyé (08), création en 2 écrans. La salle est en texte brut (12, 13) : on n'y voit
   ni rôles tenus ou vacants, ni « prêt », ni bouton pour copier le code.
5. *Crédibilité* : nom hors secteur (« Atelier Fromager… · Équipement automobile »), « stopped » non traduit, erreurs
   techniques à l'écran (07, 17d).
6. *Relecture* : une longue modale de texte (10), sans aperçu 3D ni section à régénérer.

**Mineur** : le HUD a 2 lignes d'aide clavier et un bloc de KPI empilés (17) ; pas de didacticiel.
**G-mix est en avance**, à garder : comptes et rôles, multijoueur, PNJ à mémoire, notions sourcées, déterminisme, débrief (16).

## 3. Cible : ce que l'IA conçoit, ce que le moteur calcule

Un jeu G-mix devient l'équivalent de `default.json`, conçu à partir d'un brief. L'IA **choisit** dans les catalogues du
pack usine ; elle n'écrit aucun nombre (ADR 0008, inchangé).

| L'IA choisit (énumérations du pack) | Le moteur calcule (`engine`, `factory`, `layout`) |
|---|---|
| Entreprise (nom du secteur, accroche, contexte, client principal) | Capacités, stocks initiaux, trésorerie calés sur la demande |
| 1 à 4 produits avec nomenclature MP -> SF -> PF ; 1 à 3 lignes | Gammes, cadences, pannes (MTBF), défauts, rendement |
| 3 à 8 fournisseurs, une classe de distance chacun, au moins 2 offres par article | Délais, prix, fiabilité tirés à la graine |
| 1 à 4 clients et un profil de demande (stable, saisonnier, pic) | Commandes, retards, annulations, OTIF |
| Départements tenus par des joueurs, les autres en pilote automatique | Effets des actions, coûts, alertes avec leur gravité |
| Décisions ouvertes, avec un droit par réglage (verrouillé, initial, libre) | Refus côté API et refus journalisés |
| 4 à 6 KPI d'accueil ; critères de réussite (KPI, profil de seuil, semaine) | Verdict (atteint, partiel, non) ; partie de référence |
| 0 à 3 aléas prévus (type, semaine) | Tirage des aléas ; journal des causes (décision, règle, aléa) |
| Personnages, didacticiel, questions de débrief | Faits que disent les PNJ (`briefings`) |

Chiffres : ceux du pack, avec leur provenance ; ceux de `default.json` y entrent en `exemple` jusqu'à leur sourçage.
**Écarté** : reprendre la stack web de la référence (on perdrait Godot, le multijoueur, la caméra ; elle n'a ni formateur
ni lobby). On reprend ses données, ses formules (corrigées selon son rapport d'écart) et la structure de sa tablette.

## 4. Parcours cibles

**F1-F2 Formateur : générer.** C'est le premier écran ; les onglets Mes jeux et Mes sessions affichent des cartes.
```
+-- G-mix · Formateur ------------------------ [Nouveau jeu] [Mes jeux] [Mes sessions] [Comptes] --+
| Décrivez votre jeu : [ Licence pro, 3 joueurs. Une conserverie rate ses livraisons de fin de mois ] |
| Secteur [Agroalimentaire v]  Durée [6 semaines v]  Joueurs [3 v]  Niveau [Équilibré v]             |
| > Options avancées (départements joués, aléas, produits)                                          |
| [ Concevoir avec l'IA ]                              Générer sans IA (instantané)                  |
| Conception [######----] étape 2/3 : personnages · 1 min 40                          [Annuler]      |
+---------------------------------------------------------------------------------------------------+
```
**F3 Ajuster et publier.** Chaque section se régénère. Le mode construction (ADR 0009) s'ouvre depuis l'aperçu.
```
+-- Brouillon : Conserverie du Val ------------------- [Paramètres] [Mode construction] [Publier] --+
| Entreprise         [Régénérer] | Aperçu 3D de l'usine (caméra Sims)                               |
| Produits, fournisseurs, rôles  |------------------------------------------------------------------|
| Objectifs et aléas [Régénérer] | Partie de référence : OTIF 96 %, TRS 91 %, 0 rupture : jouable  |
| Personnages        [Régénérer] | Valeurs non sourcées : 4 [voir]                                  |
+--------------------------------+------------------------------------------------------------------+
```
**F4 Créer une session.** « Lancer une session » sur un jeu publié ouvre une modale : nom prérempli et mode d'avancée
(question 2). Le code s'affiche ensuite en grand, avec un bouton « Copier ». **F5 Piloter.**
```
+-- Session « Groupe du 04/11 » · Conserverie du Val ---------------- Code VG8W5E [Copier] --------+
| Semaine 2/6 | OTIF 96 % | TRS 91 % | Ruptures 0 | Trésorerie 19 367 € | Alertes (2)               |
| Achats : Léa M., prête  ·  Production : Karim B., pas prêt  ·  Maintenance : pilote automatique     |
| [Semaine suivante (1/2 prêts)] [Déclencher un aléa v] [Observer en 3D] [Débrief]                  |
+--------------------------------------------------------------------------------------------------+
```
**J1 Rejoindre.** Le joueur saisit le code, choisit un rôle sur une carte (libre, ou pris par un autre), coche les règles
comme dans la référence, puis entre dans l'usine. **J2 Jouer.** La barre reste visible en 3D. La tablette (touche T ou clic sur un bloc) s'ouvre sur la page de mon
département ; les autres pages sont en lecture seule.
```
+-- Sem. 2/6 | OTIF 96 % | TRS 91 % | Stock 12 766 € | Alertes (2) | [Prêt pour la semaine suivante] -+
| Usine        o | Achats (votre rôle)                            [KPIs] [Actions] [Outils]            |
| Achats       o | ! Cuve inox : point de commande atteint                                 [Commander] |
| Stock        o | Aciers du Rhône  3 j  95 %  4,20 €  [Commander]   [Comparer les offres]              |
| Production   o | Parler à Noah (réceptionnaire) · Notion : point de commande (source)               |
+----------------+------------------------------------------------------------------------------------+
```
**J3 Débrief** (même écran pour le joueur et le formateur).
```
+-- Débrief · Groupe du 04/11 --------------------------------------------------------------------+
| OTIF >= 95 % : atteint | TRS >= 85 % : partiel (S3 : panne L2) | Trésorerie : non atteint          |
| Courbes : OTIF, TRS, stock, trésorerie      | Vos décisions / ce que le hasard a imposé           |
| Notions et sources · Valeurs non sourcées · Comparer aux autres sessions de ce jeu               |
+-------------------------------------------------------------------------------------------------+
```

## 5. Sort de l'existant
| Élément | Sort |
|---|---|
| Comptes, rôles, lobbies, PNJ et mémoire partagée, débrief, moteur, placeur et grilles, caméra Sims, assets procéduraux | **Garder** |
| Pipeline de conception de l'ADR 0008 | **Garder**, et le livrer en priorité, sur l'usine |
| Pack usine | **Adapter** : aligner sur `default.json` (blocs, gammes, offres, clients, agents) et sourcer |
| Tablette ; HUD et menus contextuels | **Adapter** : la tablette devient l'écran de jeu ; la barre devient compacte ; un menu ouvre la page du département |
| Écrans d'accueil, de relecture et de lobby | **Refaire** selon le §4 |
| Pack atelier | **Geler** : il ne sert plus qu'à « Générer sans IA » (question 3) |
| Éditeur de grille (ADR 0009) | **Garder**, mais le livrer après les parcours (étape 7) : la référence n'en a pas |
| Import/export JSON ; tableur, carte et planning de la référence | **Réserver** à l'admin ; **reporter** à la tranche 2 (comparateur, journal, graphiques d'abord) |

## 6. Étapes (plan pour l'orchestrateur)
| # | Agent | Fichiers | Critère de fin | Ordre |
|---|---|---|---|---|
| 0 | moteur-jeu | backend/gmix/game/ | `POST /games` génère une usine ; `test.ps1 -Fast` vert | fait |
| 1 | godot-dev (**première livraison visible**) | godot/scenes/main, lobby, tablet, world/hud.gd, tools | F1, F4, F5, J1 et J2 sur l'API actuelle, avec le rail tiré de `spec.modules` ; textes traduits ; erreurs lisibles ; `-Tour` (4 tailles) et `-Flow` verts ; captures avant/après | fait (lancée le 04/11) |
| 2 | game-designer | ai/packs/usine.yaml ; noms d'entreprise par secteur | pack aligné, ≥ 2 offres par article, provenance de chaque valeur, `load_pack` passe | après 0 |
| 3 | architecte | [annexe 0010](0010-annexe-contrats.md) (fait le 05/11 ; ajouts à spec.py délégués à l'étape 4, topics.py inchangé) | contrat : mode d'avancée et « prêt », `state.alerts[]`, critères, causes au journal, droits par réglage | après 0 |
| 4 | moteur-jeu | engine, factory, design.py et leurs tests | alertes, critères, verdict partiel, causes ; étape 5 de l'annexe 0008 | fait (05/11) ; écarts à corriger : annexe §12 |
| 5 | backend-api | api/routes, db, alembic | « prêt » et avance de la semaine, aléa déclenché par le formateur, `/games/designs`, droits testés pour les 3 rôles | fait (05/11) ; écarts à corriger : annexe §12 |
| 6 | ia-runtime, puis pipeline-kafka | ai/models.yaml, prompts, evals ; workers/generation.py | étapes 4, 8 et 11 de l'annexe 0008 sur l'usine ; médiane de 3 min | fait en v0 (05/11) ; écarts à corriger : annexe §12 |
| 7 | godot-dev | main (F2, F3), tablet (pages des départements), J3, mode construction | `-Flow -Design` vert avec et sans `-NoLlm` ; `-Tour` vert | en cours : B1 à B4a faits (06/11), puis B4b ; mode construction après la Première version (ADR 0012, décisions du 06/11) |
| 8 | game-designer | relecture | 10 jeux conçus, relus et signés | après B4b et la répétition en LAN (ADR 0012, décision 4) |
| 9 | documentaliste | docs/, blocages.md, prompt-projet.md | docs à jour, mention de licence revue | après 8 |
| 10 | qa-reviewer | tests manquants | `test.ps1 -Integration`, `smoke.ps1`, `-Flow -Design` verts | fin |

**Risques** : l'étape 1 liste les champs d'API manquants sans les inventer ; l'étape 3 attend l'étape 0 (`spec.py` en
cours) ; une conception (7b) expulse le modèle de dialogue de la VRAM (ADR 0008, question 2) ; docs/prompt-projet.md
mentionne encore l'accord de l'autrice, à aligner sur la décision 5 du §7 (étape 9).

## 7. Décisions de l'utilisateur (04/11)

1. **Une entreprise partagée par session**, un département par joueur. Pour comparer des équipes, on lance plusieurs
   lobbies du même jeu, que le débrief compare. **Amendé par l'[ADR 0011](0011-groupes-d-equipes-et-connexions.md)
   §2** (05/11) : une entreprise par équipe ; un groupe réunit plusieurs équipes d'un même jeu, et son débrief les
   compare.
2. **La semaine avance automatiquement** quand tous les joueurs sont « prêts » ; le formateur peut forcer l'avance ou
   mettre en pause (contrat à l'étape 3, API à l'étape 5).
3. **L'IA ne conçoit que l'usine de type Business_game.** Le pack atelier est gelé, gardé comme repli « Générer sans IA ».
4. **L'étape 1 (godot-dev) démarre maintenant**, en parallèle de l'étape 0.
5. **Licence** (décision de l'utilisateur, redite le 29/10 et le 03/11) : l'autrice de la référence est une collègue de
   son équipe ; la reprise du code ne demande pas de crédit. Les crédits d'assets et de polices de tiers restent.
   La mise à jour de docs/prompt-projet.md et de docs/blocages.md revient à documentaliste (étape 9).
6. **(05/11)** Si un joueur est déconnecté, les connectés votent « ignorer » ou « attendre » (majorité stricte ;
   l'égalité fait attendre ; le département ignoré passe en pilote automatique pour la semaine ; le formateur peut
   forcer). Quand le formateur agit sur un module libre, son pilote automatique s'arrête pour la semaine, puis
   reprend. L'annulation d'une commande après N semaines de retard est reportée : sa règle n'est pas publiée en v1.
   Contrats : [annexe 0010](0010-annexe-contrats.md), §1, §6 et §11.
