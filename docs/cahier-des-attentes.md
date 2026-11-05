# Cahier des attentes de G-mix

Référence unique de ce qui est attendu du produit. Rédigé le 2026-11-05 à partir de docs/prompt-projet.md, des ADR
0004 à 0011 et de docs/blocages.md. Il ne remplace pas les ADR : il les rassemble et donne à chaque attente un
identifiant et un état. Pour piloter : lire la section 9 (tableau) et la section 10 (points à trancher).

États : **fait** (le code ou une doc à jour le prouve), **partiel** (une partie existe, la note dit laquelle),
**à faire**, **à trancher** (une décision de l'utilisateur manque). Relevé du 2026-11-05 par lecture du code ; aucune
commande de test n'a été relancée pour ce document.

## 1. Vision

G-mix génère des business games en mini open world 3D, dans la direction artistique des Sims. Le formateur décrit
ce qu'il veut (paramètres, brief, documents) ; une IA locale conçoit le jeu ; un moteur déterministe calcule la
partie. Les joueurs jouent en équipe dans l'usine, avec des personnages (PNJ) qui disent les faits calculés.

**Exigence n° 1 : les connaissances transmises sont vraies et sourcées.** Conséquences : chaque valeur du jeu porte une
provenance (`source`, `calibre` ou `exemple`) ; aucune source n'est inventée ; ce qui n'est pas sourcé est affiché au
formateur et au débrief. Décisions prises : domaine prioritaire supply chain ; comptes locaux (ADR 0004) ;
parties en réseau local et à distance (ADR 0005) ; tout est local, aucun LLM externe ; référence de jeu : le
Business_game d'une collègue de l'équipe (ADR 0010) ; interfaces ergonomiques, chaleureuses, au vouvoiement.

## 2. Rôles

| Rôle | Peut |
|---|---|
| Joueur | Rejoindre un lobby par code, tenir un département, décider, dialoguer avec les PNJ, lire le débrief |
| Formateur | Créer et régler des jeux, les modifier, les publier, créer et piloter ses lobbies, suivre la partie, débriefer |
| Admin | Tout ; crée les comptes ; accès aux outils réservés (import/export de spec, pack non couvert) |

Matrice complète : docs/roles.md.

## 3. Parcours du formateur

| Étape | Ce qui est attendu |
|---|---|
| 1. Paramètres | Secteur et pack, modules, départements joués, difficulté, durée, aléas, niveau de joueurs, **mode de saisie des décisions** (section 3.1) |
| 2. Prompt et documents | Un brief libre (20 à 2000 caractères) et des documents (cours, études de cas) qui alimentent la conception ; ils passent par le RAG (`knowledge/`, SOURCES.md) |
| 3. Génération | « Concevoir avec l'IA » (usine) ou « Générer sans IA » (repli atelier, instantané). Suivi de l'avancement, annulation |
| 4. Mode créateur | Sur le jeu généré : ajuster assets, modules, activités ; régénérer une section ; l'IA propose et fait les connexions nécessaires (section 3.2) |
| 5. Publication | Brouillon -> publié. Pas de lobby sur un brouillon ; valeurs non sourcées listées avant publication |
| 6. Lobby et équipes | Créer un lobby pour un groupe de travail, y regrouper les équipes, code d'accès à copier |
| 7. Tableau de bord | Pendant la partie : avancement, indicateurs, alertes, prêts, absents ; actions du formateur (section 3.3) |
| 8. Débrief | Critères atteints / partiels / non, causes (décision, règle, aléa), notions et sources, valeurs non sourcées, comparaison entre équipes |

### 3.1 Modes de saisie des décisions (paramètre du formateur)

Aujourd'hui le moteur ne connaît que deux types de champ : `choice` (liste) et `int` (nombre), dans
`ActionField` de backend/gmix/game/spec.py. Le formateur doit pouvoir choisir, par jeu ou par module :

| Mode | Usage typique | État du contrat |
|---|---|---|
| Formulaire | Plusieurs champs validés ensemble (commande : article, fournisseur, palettes) | existe (`Action.fields`) |
| Choix parmi des options | Fournisseur, ligne, priorité | existe (`choice`) |
| Saisie chiffrée | Quantité, lots | existe (`int`, bornes et pas) |
| Curseur | Taux, niveau de stock de sécurité | à faire (même `int`, présentation à ajouter) |
| Choix multiple | Plusieurs lignes ou articles à la fois | à faire |
| Texte libre | Justification, plan d'action, noté mais non calculé | à faire ; ne doit jamais changer le calcul |
| Interaction dans le monde 3D | Cliquer un bloc, un camion, une machine pour décider (menu contextuel Sims) | partiel (menus contextuels existent) |

Règle : quel que soit le mode, le moteur valide et calcule ; le client n'envoie que des valeurs que le moteur sait lire.

### 3.2 Mode créateur

Édition du jeu généré avant publication. Existant : éditeur de grille spécifié par l'ADR 0009 d.8
(routes `PUT /api/v1/games/{id}/layout` et `/params`, retouches limitées aux rôles `decor` et `affichage` et au
déplacement dans le bloc). Attendu en plus : ajouter ou retirer un asset, un module, une activité ; l'IA propose les
connexions (par exemple relier une nouvelle activité à son département, à ses KPI et à ses assets) ; toute
modification repasse par la validation (`SimSpec`, `check_placement`, essai en pilote automatique).

### 3.3 Tableau de bord

Le formateur voit en direct : semaine courante, indicateurs, alertes, état « prêt » par département, joueurs
connectés, vote sur un absent, journal des causes. Il peut forcer l'avance, mettre en pause, déclencher un aléa,
observer en 3D. Le client expose déjà un onglet « Supervision » de la tablette selon le pack ; la page de pilotage
complète est l'étape 7 de l'ADR 0010.

## 4. Parcours du joueur

1. Se connecter (compte local). 2. Saisir le code du lobby. 3. Choisir un département libre et prendre
connaissance des règles. 4. Entrer dans l'usine 3D. 5. Lire alertes et KPI, ouvrir la page de son département
(tablette ou clic sur un bloc), décider, parler aux PNJ. 6. Se déclarer « prêt ». 7. Voir la semaine se jouer, puis le
débrief. Les pages des autres départements sont en lecture seule.

## 5. Génération des mondes

| Élément | Règle |
|---|---|
| Pack | Un domaine = un fichier `ai/packs/<id>.yaml` + des assets, pas du code. Pack actif : usine (`ai/packs/usine.yaml`) ; atelier gelé (repli sans IA) |
| Paramètres | `GameParams` (spec.py) : modules, difficulté, durée, aléas, joueurs, graine ; mêmes paramètres = même spec |
| Conception par l'IA | Concept -> personnages -> parcours ; l'IA **choisit** dans les catalogues du pack, n'écrit ni chiffre, ni coordonnée, ni lien (ADR 0008) |
| Documents du formateur | Interrogés par le RAG pour nourrir le choix et les textes ; une notion hors pack ou hors document cité est interdite |
| Assets | Prédéfinis (`ai/assets.yaml`, `godot/assets/`) ; un pack n'est proposé que si tous ses assets sont importés |
| Placement | Placeur déterministe (`backend/gmix/game/layout.py`) sur grilles carte, site, bloc ; règles d'implantation avec provenance |
| Chiffres | Ceux du pack, chacun avec `source`, `calibre` ou `exemple` ; les non sourcés sont listés |
| Justesse | Validation `SimSpec` -> `check_design` -> essai en pilote automatique ; 2 réparations au plus, puis repli déterministe |
| Parties de code simples | Connexions déclaratives choisies dans les énumérations du pack (P1 A, ADR 0011 §3) |

## 6. Une partie

| Notion | Fonctionnement |
|---|---|
| Entreprise | Une par équipe, un département par joueur ; un groupe réunit N équipes (ADR 0011) |
| Semaine | Lecture des alertes, décisions, puis avance : maintenance, quai, réception, production, qualité, livraisons |
| Avance | Automatique quand tous les joueurs « prêts » ; le formateur force ou met en pause |
| Absent | Les connectés votent « ignorer » (département en pilote automatique pour la semaine) ou « attendre » ; majorité stricte, égalité = attendre |
| Pilote automatique | Joue les modules non tenus ; s'arrête pour la semaine sur un module libre où le formateur agit |
| Aléas | Prévus par le jeu (0 à 3) ou déclenchés par le formateur ; tirés à la graine, rejouables |
| Alertes | Niveaux, texte court, action proposée ; 8 au plus, lues dans le pack |
| Critères | KPI, seuil, seuil partiel, semaine ; verdict atteint, partiel ou non ; partie de référence |
| Réseau | Parties en réseau local et à distance ; un serveur Godot par lobby pour la présence |

## 7. Rôle de l'IA

| L'IA fait | L'IA ne fait jamais |
|---|---|
| Concevoir concept, personnages, parcours en choisissant dans les catalogues | Inventer un chiffre, une source, une coordonnée ou un lien |
| Faire parler les PNJ en une ou deux phrases avec leur caractère | Dire autre chose que les faits calculés par le moteur (`briefings`) |
| Filtrer les messages des joueurs (tev1), chercher dans le corpus (RAG) | Calculer ou juger une partie |
| Proposer des connexions et des réparations, validées ensuite par le moteur | Exécuter du code non validé (point P1) |

Modèles locaux (Ollama), tâches de `ai/models.yaml`, budgets : docs/ai-runtime.md.

## 8. Construction

```
 Godot (client) --HTTP/WS--> API FastAPI --> PostgreSQL (+pgvector), RustFS
                                  |
                                  +--> Kafka --> workers (génération, dialogues IA) --> Ollama
 moteur pur (gmix.game) appelé par l'API sous verrou ; 3D temps réel = réseau Godot, pas Kafka
```

Détail : docs/architecture.md, docs/kafka.md.

## 9. Tableau des attentes

| Id | Attente | Critère vérifiable | État | Référence |
|---|---|---|---|---|
| EX-01 | Exigence n° 1 : savoir vrai et sourcé | Chaque valeur du pack a une provenance ; `unsourced` liste le reste ; débrief les affiche | partiel : calibrage non relu, corpus provisoire (blocages.md 2 et 3) | ADR 0007 d.8 ; docs/blocages.md |
| EX-02 | Domaine supply chain prioritaire | Pack `usine` chargé par `load_pack`, premier du menu | fait | ai/packs/usine.yaml ; ADR 0007 |
| EX-03 | Comptes locaux | Connexion par identifiant et mot de passe, rôles | fait | ADR 0004 ; backend/gmix/api/routes/accounts.py |
| EX-04 | Rôles joueur, formateur, admin | Matrice testée pour les 3 rôles | partiel : droits par département testés à l'étape 5, matrice docs/roles.md à aligner (étape 8) | docs/roles.md ; ADR 0010 annexe §5 |
| EX-05 | Parties en réseau local et à distance | Salle de jeu en LAN ; à distance testée sur un hébergement | partiel : LAN prévu, distance non testée, hébergement à choisir | ADR 0005 ; docs/blocages.md 5 |
| EX-06 | Tout local, aucun LLM externe | Appels via tâches de `ai/models.yaml` vers Ollama | fait | docs/ai-runtime.md ; ai/models.yaml |
| EX-07 | Génération paramétrée instantanée sans IA | `POST /api/v1/games` répond en moins d'une seconde | fait (route présente ; budget mesuré non revérifié) | ADR 0006 ; backend/gmix/api/routes/games.py |
| EX-08 | Conception par l'IA (concept, personnages, parcours) | `POST /games/designs` 202, job suivi par `GET /games/{id}/job`, médiane 3 min | partiel : API et worker livrés (étapes 5 et 6), écran F2 et `-Flow -Design` à l'étape 7 | ADR 0008 ; ADR 0010 §3 ; backend/gmix/workers/generation.py |
| EX-09 | L'IA conçoit seulement l'usine ; atelier = repli sans IA | 422 hors usine ; « Générer sans IA » reste | partiel : 422 prévu (annexe §7), repli présent côté accueil | ADR 0010 §7.3 |
| EX-10 | Brief libre de 20 à 2000 caractères | Brief trop court refusé avec message lisible | fait | backend/gmix/api/routes/games.py ; godot/scenes/main/home_screen.gd |
| EX-11 | Paramètres et brief ensemble | Un même formulaire envoie paramètres et brief | partiel : brief et formulaire séparés dans home_screen.gd | ADR 0010 §4 F1 |
| EX-12 | Documents du formateur alimentent la génération (RAG) | Un document déposé est ingéré et cité dans le jeu conçu | à faire : aucune route de dépôt par jeu | knowledge/ ; point P4 |
| EX-13 | Parties de code simples pour les connexions | Connexions produites, validées, jamais exécutées telles quelles | à faire : forme déclarative retenue (P1 A) | ADR 0011 §3 |
| EX-14 | Mode de saisie des décisions choisi par le formateur | Un paramètre par jeu ou module ; client le respecte | à faire : seuls `choice` et `int` existent | spec.py `ActionField` ; section 3.1 |
| EX-15 | Monde posé sur grilles, déterministe | Même spec, même monde ; `check_placement` sans erreur | partiel : moteur et tests présents, `test.ps1 -Fast` non relancé le 2026-11-05 | ADR 0009 ; backend/gmix/game/layout.py |
| EX-16 | Placement fondé sur le métier, règles sourcées | Chaque règle a une provenance ; violation refusée | partiel : règles `calibre` sans source, règles `protected_path` de la voie PL manquantes | ADR 0010 annexe §12 ; docs/blocages.md |
| EX-17 | Assets prédéfinis, pack proposé si couvert à 100 % | `pack_coverage("usine")["ratio"] == 1.0` | partiel : à relancer, assets en cours de modification | ADR 0009 d.7 ; ai/assets.yaml |
| EX-18 | Mode créateur : ajuster assets, modules, activités | Éditeur utilisable dans le client avant publication | partiel : routes `/layout` et `/params` existent, aucun écran client trouvé | ADR 0009 d.8 ; section 3.2 |
| EX-19 | L'IA aide et fait les connexions dans le mode créateur | Une modification déclenche une proposition validée | à trancher | point P3 |
| EX-20 | Publication, pas de lobby sur un brouillon | `POST /games/{id}/publish` ; lobby refusé sur brouillon | fait côté API ; bouton « Publier » présent | backend/gmix/api/routes/games.py ; home_screen.gd |
| EX-21 | Lobby par groupe de travail avec code | Création, code copiable, rejoindre par code | partiel : création et code existent, « Copier » et cartes à l'étape 7 | ADR 0010 §4 F4 ; lobby_screen.gd |
| EX-22 | Un lobby regroupe plusieurs équipes | Équipes dans un lobby, une entreprise chacune | partiel : API `/api/v1/groups` livrée (tests d'intégration écrits, non lancés), écrans Godot à l'étape 7 | ADR 0011 §2 ; backend/gmix/api/routes/groups.py |
| EX-23 | Une entreprise par session, un département par joueur | Un rôle par joueur, rôles pris visibles | partiel : choix de rôle présent, cartes de rôles à l'étape 7 | ADR 0010 §7.1 |
| EX-24 | Avance quand tous sont prêts ; forcer ; pause | Routes `/ready`, `/pause`, `/advance` | partiel : API livrée, client n'appelle que `/advance` | ADR 0010 annexe §1 ; lobbies.py |
| EX-25 | Joueur absent : vote ignorer ou attendre | Majorité stricte, égalité = attendre, 409 sans vote ouvert | partiel : API livrée, écran client à faire | ADR 0010 §7.6 |
| EX-26 | Module libre agi par le formateur : pilote arrêté pour la semaine | Test moteur `held_roles` | fait côté moteur | ADR 0010 annexe §11 ; backend/gmix/game/engine.py |
| EX-27 | Alertes et critères de réussite avec verdict partiel | `state.alerts[]`, `criteria`, verdict atteint, partiel ou non | partiel : moteur et API livrés, affichage client à faire | ADR 0010 annexe §2 et §3 |
| EX-28 | Aléas prévus et déclenchés par le formateur | Route `/event` | fait côté API ; menu formateur à l'étape 7 | lobbies.py |
| EX-29 | Tableau de bord du formateur | Page de pilotage de la section 3.3 | partiel : onglet Supervision de la tablette, pas de page complète | tablet.gd ; ADR 0010 §4 F5 |
| EX-30 | Pages des départements dans la tablette | Une page par département, lecture seule hors du sien | à faire (étape 7) | ADR 0010 §6 étape 7 |
| EX-31 | Débrief joueur et formateur | `GET /lobbies/{id}/debrief`, écran J3 avec courbes et causes | partiel : route et affichage simple présents, écran J3 à l'étape 7 | ADR 0010 §4 J3 |
| EX-32 | Comparaison entre équipes ou sessions d'un jeu | Débrief comparatif | partiel : `GET /groups/{id}/debrief` met les débriefs côte à côte, écran à l'étape 7 | ADR 0011 §2 |
| EX-33 | PNJ qui disent les faits calculés et se souviennent | Dialogue sur `briefings`, 6 derniers échanges | fait (garde-fou des nombres de `npc.py` en attente de décision) | ADR 0006 ; docs/blocages.md |
| EX-34 | Interfaces ergonomiques, chaleureuses, au vouvoiement | `-Tour` vert aux 4 tailles, police 15 px au moins | partiel : textes de l'étape 1 livrés, passe finale à l'étape 7 | `.\scripts\godot.ps1 -Tour` ; ADR 0010 §6 |
| EX-35 | Tenable sur le poste (RTX 3060 6 Go) | Conception 3 min en médiane, 10 au plus | partiel : budget décidé, mesure sur l'usine à faire | ADR 0008 d.4 ; `.\scripts\check-env.ps1` |
| EX-36 | Capacité d'une séance réelle (une vingtaine de joueurs) | Dialogues simultanés tenus | à trancher : GPU insuffisant, taille des lobbies inconnue | docs/blocages.md 4 |
| EX-37 | Licence du jeu de référence | Reprise sans crédit décidée (autrice dans l'équipe) | partiel : décision prise ; blocages.md et prompt-projet.md à aligner (étape 9) | ADR 0010 §7.5 |
| EX-38 | Docs et QA du chantier 0010 | Étapes 8 (docs) et 9 (QA) faites | à faire | ADR 0010 §6 |

Décompte au 2026-11-05 (après ADR 0011) : 38 attentes ; fait 9, partiel 22, à faire 5, à trancher 2.

## 10. Points à trancher

### P1. Code généré par l'IA (attente 1) — tranché le 05/11 : A, B plus tard (ADR 0011 §3)

| | |
|---|---|
| Décision en jeu | ADR 0006 (simulation par paramètres, sans modèle), ADR 0008 (l'IA ne produit ni chiffre ni lien), sécurité (aucun code arbitraire exécuté sur le serveur ou chez les joueurs), exigence n° 1 |
| Option A | Connexions **déclaratives** : l'IA choisit des liens dans des énumérations du pack (activité -> département -> KPI -> asset) ; `SimSpec` les valide |
| Option B | **Expressions** dans un langage restreint (formules sur indicateurs, sans boucle ni appel système), évaluées par le moteur, bornées et testées |
| Option C | Code exécuté tel quel : refusée (sécurité, justesse invérifiable) |
| Recommandation | A d'abord (compatible avec l'ADR 0008), B pour les besoins que A ne couvre pas, après un ADR. Appeler « parties de code simples » ces connexions et expressions, jamais du code libre |

### P2. Un lobby, plusieurs équipes (attente 6) — tranché le 05/11 : B (ADR 0011 §2)

| | |
|---|---|
| Décision en jeu | ADR 0010 §7.1 : une entreprise partagée par session, un département par joueur ; comparaison par plusieurs lobbies du même jeu |
| Option A | Statu quo : un lobby = une équipe ; le groupe de travail est une étiquette, la comparaison passe par plusieurs lobbies |
| Option B | Un lobby contient N équipes ; **une équipe = une entreprise** ; le débrief compare les équipes ; l'avance de semaine reste par équipe ou commune |
| Recommandation | B, car elle suit la demande (tout le groupe dans un lobby) sans casser « une entreprise par équipe ». Coûts : table d'équipes, état par équipe, avance et votes par équipe ; amender l'ADR 0010 §7.1 |

### P3. IA hors de l'usine dans le mode créateur (attente 4)

| | |
|---|---|
| Décision en jeu | ADR 0010 §7.3 : l'IA ne conçoit que l'usine |
| Option A | L'aide du mode créateur reste limitée à l'usine (pack usine) : cohérent avec la décision |
| Option B | L'aide s'étend à l'atelier et aux futurs packs |
| Recommandation | A : le mode créateur n'ajoute pas de domaine, il règle un jeu usine ; l'atelier se modifie à la main. Revoir B quand un second domaine existera |

### P4. Documents du formateur et licence des sources

| | |
|---|---|
| Décision en jeu | Exigence n° 1 : un document déposé n'est pas une source vérifiée |
| Recommandation | Le document est déclaré dans SOURCES.md du jeu, cité par passage, et marqué « fourni par le formateur » ; rien n'est ingéré sans cette déclaration |

## 11. Références non vérifiées

Aucune commande de test n'a été rejouée pour ce document ; les états reposent sur la lecture du code du 2026-11-05.
