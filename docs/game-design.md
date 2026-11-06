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
| Création | brief libre en français, conçu par l'IA (`factory.design`, worker `generation`) ; en cas d'échec, repli sur les paramètres par défaut | paramètres choisis dans un menu, génération sans modèle |
| Relecture | partie de référence du pilote automatique, plan 3D modifiable (retouches), régénération d'une section : `entreprise`, `objectifs` ou `personnages` | export, modification hors ligne, réimport validé |
| Publication | `POST /games/{id}/publish` après contrôle de la spec et du placement | idem |
| Lancement | groupe d'équipes (ADR 0011) : une équipe = un lobby = une entreprise ; débrief du groupe comparé | lobby |

Les routes et les droits sont dans docs/roles.md.

## Usine : le jeu

| Élément | Valeur (`ai/packs/usine.yaml`) |
|---|---|
| Monde | hall de 48 x 30 m en U, 11 départements dont 2 externes (fournisseur, client), reliés par des routes |
| Lignes | 1 à 3 (défaut 2), 4 machines en série chacune |
| Durée | 4 à 12 semaines (défaut 6) |
| Semaine | 5 jours de 480 min, début à 8 h, pas de 5 min ; pauses de 10, 20 et 10 min ; simulée minute par minute puis rejouée en 3D |
| Secteurs | industrie, automobile (un produit) |
| Difficultés | découverte (charge 80 %), équilibré (85 %), expert (92 %, livraison à J+1) |
| Aléas | niveau aucun, rares (probabilité 0,25) ou fréquents (0,5) ; 6 aléas : retard de transport, hausse des matières, commande exceptionnelle, creux de demande, lot de matière non conforme, vague de chaleur |
| Cibles | OTIF 95 %, TRS 78 %, 0 jour-ligne en rupture de matière, trésorerie finale >= départ + 60 % du gain du pilote automatique |
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
