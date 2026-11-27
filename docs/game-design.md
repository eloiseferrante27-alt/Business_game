# Conception des business games

Deux packs de jeu (ADR 0007). Le pack principal est l'**usine** (`ai/packs/usine.yaml`, conçue par l'IA, ADR 0008
et 0010) ; l'**atelier** (`ai/simulation.yaml`, ADR 0006) est gelé et reste le repli par paramètres. Règles chiffrées :
`backend/gmix/game/engine.py` (atelier) et `gmix.game.factory` (usine). Les chiffres ci-dessous viennent de ces
fichiers au 2026-11-06 ; leur provenance (`source`, `calibre` ou `exemple`) est dans la section `values` du pack.
Beaucoup de valeurs de l'usine restent `exemple` (cahier de l'utilisateur, non sourcé) : ne pas les présenter
comme des données de référence.

## Ce qu'un business game garantit

1. **Vrai** : chaque notion transmise porte sa source (fiche du corpus ou norme citée) ; les agents ne disent
   que les chiffres calculés par le moteur et, pour une question de fond, les extraits du corpus.
2. **Cohérent** : la spec est validée (`gmix.game.spec.SimSpec`, références croisées), le plan respecte les règles
   de placement du pack (`check_placement`), puis la partie est jouée en pilote automatique avant d'être proposée.
3. **Pédagogique** : objectifs mesurés, débrief avec leçons tirées de la partie, aléas survenus, notions et
   sources, journal des décisions de l'équipe.
4. **Jouable** : un joueur passif finit en échec ; le pilote automatique atteint ou approche les cibles
   (mesures du 05/11 dans les notes de `criteria` du pack).

## Parcours du formateur

| Étape | Usine | Atelier |
|---|---|---|
| Création | brief libre en français, conçu par l'IA (aujourd'hui un appel `factory.design`, worker `generation` ; cible ADR 0013, T9 : cinq étapes, domaine, mécaniques, monde, personnages, parcours, et un contrôle) ; en cas d'échec, repli sur les paramètres par défaut | paramètres choisis dans un menu, génération sans modèle |
| Relecture | partie de référence du pilote automatique, plan 3D modifiable (retouches), régénération d'une section : `entreprise`, `objectifs` ou `personnages` | export, modification hors ligne, réimport validé |
| Publication | `POST /games/{id}/publish` après contrôle de la spec et du placement | idem |
| Lancement | groupe d'équipes (ADR 0011) : une équipe = un lobby = une entreprise ; débrief du groupe comparé | lobby |

Les routes et les droits sont dans docs/roles.md.

## Usine : le jeu

| Élément | Valeur (`ai/packs/usine.yaml`) |
|---|---|
| Monde | référence : hall de 48 x 30 m en U, 11 départements dont 2 externes (fournisseur, client), reliés par des routes ; monde de référence (1 bâtiment). Depuis T5 (27/11) : campus de 1 à 3 bâtiments à pièces (hall, entrepôt, atelier de maintenance), trajets calculés (kit 8 + t, technicien qui marche à 75 m/min, chariot à 100 m/min, palette vers l'entrepôt) ; les durées de trajet ignorent les pauses |
| Lignes | 1 à 3 (défaut 2), 4 machines en série chacune |
| Durée | 4 à 12 semaines (défaut 6) |
| Semaine | 5 jours de 480 min, début à 8 h, pas de 5 min ; pauses de 10, 20 et 10 min ; simulée minute par minute puis rejouée en 3D |
| Secteurs | industrie, automobile (1 à 3 produits depuis T4b) |
| Difficultés | découverte (charge 80 %), équilibré (85 %), expert (92 %, livraison à J+1) |
| Aléas | niveau aucun, rares (probabilité 0,25) ou fréquents (0,5) ; 6 aléas : retard de transport, hausse des matières, commande exceptionnelle, creux de demande, lot de matière non conforme, vague de chaleur |
| Cibles | OTIF 95 %, TRS 80 % (`criteria.trs` de `ai/packs/usine.yaml`, recalibré le 19/11 de 78 à 80, convention du jeu ; T0 signé le 21/11), 0 jour-ligne en rupture de matière, trésorerie finale >= départ + 60 % du gain du pilote automatique |
| Notions | 17 (goulot, TRS, loi de Little, point de commande, OTIF, etc.), chacune rattachée à une fiche du corpus |

Réglages que l'IA peut choisir (`tunables`) : fréquence des pannes, défauts des machines, charge, délai promis,
variabilité de la demande, fiabilité des fournisseurs, stocks de départ. Une clé prend la valeur d'un autre profil
de difficulté, jamais un nombre inventé.

### Modules, rôles et actions

| Module | Rôle | Actions |
|---|---|---|
| Pilotage | Responsable de production | `lancer_of` (ordres de fabrication par lots de 24), `commander_mp` |
| Production | Chef·fe de ligne | `proteger_goulot` |
| Maintenance | Responsable maintenance | `preventif`, `priorite_reparation` |

Un module sans titulaire tourne en pilote automatique (sauf la semaine où le formateur y agit).

## Ce qui varie selon la demande (cible ADR 0013 ; état livré au 21/11 : la demande règle des chiffres d'une usine unique)

| Dimension | Données sourcées du pack | Procédural à graine (T4, T5) | Agents IA (T9) | Moteur seul |
|---|---|---|---|---|
| Secteur et domaine | secteurs, produits, notions citées | aucun | choix du domaine, du secteur, des notions visées | moteur du pack |
| Modules et mécaniques | modules, actions, aléas, réglages | aucun | modules joués, réglages, plan d'aléas, objectifs | effets, verdict |
| Rôles et PNJ (T7) | rôles, caractères, clés de faits | prénoms, figurants | découpage des rôles, caractères, présentations | faits des PNJ |
| Produits et réseau | 1 à 3 produits, 3 à 8 fournisseurs, 1 à 4 clients (T4b) | choix dans les listes | nombres, classes de distance | délais, prix, OTIF |
| Bâtiments et pièces | archétypes, zonage sourcé | tailles, positions, pièces, portes | programme de bâtiments | temps de trajet |
| Visuel | variantes d'assets importés | variante par objet, décor | ambiance | rien |
| Sources du formateur (T8) | aucune | aucun | passages validés cités | aucun chiffre de document |

Aujourd'hui (27/11, T4, T5 et T4b livrés) : 1 à 3 produits, 3 à 8 fournisseurs (`params.suppliers`), 1 à 4 clients, types de machine m1 à m4 par rang, 1 à 3 bâtiments (`params.buildings`) ou hall en U, taille et décor tirés de la graine, 3 rôles, aucun texte conçu. Règle : le moteur seul calcule, une disposition vient de la graine, l'IA choisit dans un schéma fermé.

**Plusieurs produits et clients (T4b, pack usine)** :

| Règle | Détail |
|---|---|
| Bornes | `limits.products` [1,3,1], `limits.clients` [1,4,1] ; au moins un client par produit ; clients = produits par défaut |
| Lignes | une par produit : lignes = max(option `lines`, produits) |
| Demande | partagée à parts égales (`partage_demande = parts_egales`) : `d // n`, plus 1 pour les `d % n` premiers clients |
| Clients c2 à c4 | sites `client_b`, `client_c`, `client_d` clonés par `layout._build_network` ; le PNJ client ne parle que de c1 |
| Calibrage (plus d'un produit seulement) | `factory_generation._calibrate` : entrepôt de produits finis à 30 palettes à 3 lignes (`entrepot_pf.lignes_cahier`, loi de Little) ; camion de matière du pilote : `factory_game._truck` ; une partie à 1 produit reste identique |
| Affichage | bloc « Par produit » (`report.by_product`, `godot/scenes/common/game_text.gd`) si plus d'un produit ; vue publique `factory.by_product` ; commandes avec `client_id` et `product_id` ; faits des PNJ par matière et par produit |
| Tests | `backend/tests/test_t4b_contract.py` + `fixtures/t4b_reference.json` (12 parties) ; régénération : `cd backend; .venv\Scripts\python -m tests.test_t4b_contract` |

Mesures du 27/11 : 3 produits, 3 ou 4 clients, 3 difficultés, 2 secteurs, graines 1 à 3, 1 et 3 bâtiments : jouable 6/6 partout, OTIF minimal 98,6, au plus 2 semaines de rupture en expert. 3 produits, 4 clients, 3 bâtiments : `advance` 0,109 s, vue publique 22 188 caractères, génération environ 1,0 s ; quai à 4 clients environ 35 min de chargement par jour, aucun camion après 16 h. Le chariot garde sa vitesse (sourcée) même s'il ne limite pas 4 semaines.

**Second domaine** : la finance d'entreprise (trésorerie et BFR d'une PME), décidé le 21/11 (ADR 0013 §6.2) (`finance-entreprise`, moteur `factory`, D0 fait) ; pack, corpus et audit en D1 à D3, non livrés.

## Atelier (pack gelé)

Simulation hebdomadaire d'une chaîne logistique. Hall de 32 x 24 m, 4 à 12 semaines, 1 à 7 modules.
Menu : secteur (industrie, agroalimentaire, santé, automobile), modules joués, agents en plus (cliente,
fournisseur, direction), caractère des agents, difficulté, aléas, semaines, produits, nom d'entreprise, joueurs.

| Module | Rôle | Action (poste de l'atelier) | Sans joueur |
|---|---|---|---|
| Approvisionnement | Acheteur·se | commander : offre (délai, fiabilité, prix, minimum) et quantité (quai de réception, rack composants) | point de commande, fournisseur standard |
| Production | Responsable de production | planifier une ligne (ligne) | deux semaines de couverture |
| Maintenance | Responsable maintenance | niveau d'entretien d'une ligne (ligne) | préventif |
| Qualité | Responsable qualité | part des lots contrôlés (poste qualité) | un lot sur deux |
| Commercial | Commercial·e | niveau de prix d'un produit (bureau) | prix catalogue |
| Transport | Responsable transport | mode de livraison (quai d'expédition) | messagerie |
| Finance | Contrôleur·se de gestion | découvert autorisé (bureau) | pas de contrainte |

Objectifs de l'atelier : OTIF, TRS, ruptures, trésorerie finale. Le pilote automatique gagne en difficulté
« découverte » et peine en « expert » (vérifié par les tests du moteur).

Ajouter un secteur à l'atelier : entrée `themes` de ai/simulation.yaml, quatre produits (prix, coût, demande,
ligne) avec leur composant et trois fournisseurs (rapide, standard, économique). Les tests vérifient chaque
secteur dans les trois difficultés.

## Déroulement d'une semaine (EX-24)

La semaine avance quand tous les joueurs attendus (ceux qui ont choisi un rôle) sont « prêts », pas quand le
formateur la clôt. Le formateur garde la main :

| Cas | Effet |
|---|---|
| Mode `auto` (défaut), tous prêts | la semaine est simulée dans la même transaction |
| Mode `auto`, tous les connectés prêts, des absents | vote des connectés : majorité stricte pour « ignorer » (l'égalité vaut « attendre ») ; les rôles des absents ignorés passent en pilote automatique |
| Mode `manual` | la semaine n'avance que par le forçage du formateur (`/advance`) |
| Pause du formateur (`/pause`) | aucune avance automatique tant qu'elle dure |
| Aléa forcé (`/event`) | remplace l'aléa annoncé, appliqué à la prochaine avance |

L'état public est diffusé à tout le lobby (`lobby.state`, `lobby.round`).

## Agents PNJ

Un agent par module retenu, plus les agents choisis (usine : un agent parlant par département, plus la direction
et des figurants sans dialogue : opérateurs, chauffeurs). Chacun a un rôle, des tâches, un caractère (préfixe et
style) et une zone de patrouille. Le moteur lui donne ses faits de la semaine ; un fait urgent affiche « ! »
au-dessus de sa tête et devient sa réplique quand un joueur approche. Le dialogue (`npc.dialogue`) répond en
une ou deux phrases à partir de ces faits et se souvient des six derniers échanges du lobby avec lui.
Caractères disponibles (usine) : bienveillant, exigeant, pressé, méthodique, sceptique.
