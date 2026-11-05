# 0011 : groupes d'équipes dans un lobby, connexions déclaratives, dépôt de travail

Date : 2026-11-05. Statut : **accepté** (décisions de l'utilisateur du 05/11, points P1 et P2 du
[cahier des attentes](../cahier-des-attentes.md)). Amende l'[ADR 0010](0010-refonte-alignee-business-game.md) §7.1.

## 1. Dépôt de travail

G-mix est importé dans `eloiseferrante27-alt/Business_game`, branche `contribution_Romain`, partie de
`contribution_amine`. Le code web de contribution_amine (FastAPI, SQLite, three.js) reste dans l'historique et sur sa
branche ; ses documents métier et ses données (`default.json`, `pack.json`) sont dans `docs/business_game/`, source
des valeurs `exemple` du pack usine (ADR 0010 §3).

## 2. P2 : un lobby regroupe plusieurs équipes (option B)

Décision : le formateur crée un **groupe** pour son groupe de travail ; le groupe contient N équipes ; **une équipe =
une entreprise**, jouée comme un lobby d'aujourd'hui. Le débrief du groupe compare les équipes.

Forme retenue (la plus petite qui garde tout le reste) : **chaque équipe reste une ligne `lobbies`**. Une table
`lobby_groups` (nom, code, formateur, jeu) les rassemble via `lobbies.group_id`. Ainsi l'état de partie, « prêt »,
vote sur les absents, avance, pause, aléa, chronologies, mémoire des PNJ, serveur de présence et événements Kafka
restent par lobby, donc par équipe, sans changement. Écartée : une table `lobby_teams` avec un état par équipe dans un
même lobby, qui aurait obligé à clé-er par équipe chaque mécanisme ci-dessus.

Contrat (`/api/v1/groups`, backend/gmix/api/routes/groups.py) :

| Route | Qui | Effet |
|---|---|---|
| `POST /groups` `{name, business_game_id, teams: 1..12, advance_mode}` | formateur du jeu, admin | crée le groupe et `teams` lobbies « Équipe 1…N » sur la spec figée du jeu |
| `GET /groups` | formateur : les siens ; joueur : ceux où il a une équipe ; admin : tous | liste |
| `GET /groups/{id}` | formateur, admin, membre d'une équipe | équipes (id, nom, joueurs, semaine, statut) ; code pour le formateur |
| `POST /groups/join` `{code, lobby_id?}` | tout compte | sans `lobby_id` : équipes du groupe ; avec : rejoint cette équipe |
| `GET /groups/{id}/debrief` | formateur, admin ; membre quand toutes les équipes ont fini | débrief de chaque équipe, côte à côte |

Règles : un joueur ne tient qu'**une équipe par groupe** (409 sinon, y compris par le code d'équipe de
`/lobbies/join`) ; les routes de partie restent celles de `/lobbies/{id}` (une équipe) ; un lobby sans groupe garde
le comportement actuel. Le pilotage « toutes les équipes à la fois » (avance, pause) n'est pas fait : le tableau de
bord (étape 7 de l'ADR 0010) appelle chaque équipe.

## 3. P1 : « parties de code simples » = connexions déclaratives (option A)

L'IA **choisit des liens** dans les énumérations du pack (activité -> département -> KPI -> asset), validés par
`SimSpec` ; elle n'écrit ni code ni formule (ADR 0008 inchangé). L'option B (expressions dans un langage restreint,
évaluées et bornées par le moteur) attend un ADR propre et un besoin que A ne couvre pas. L'option C (code exécuté)
est refusée.

## Conséquences

Migration `lobby_groups` + `lobbies.group_id` ; routes et tests (backend-api). Client Godot : écrans « groupe »
(création, code, cartes d'équipes, choix d'équipe) à l'étape 7 (godot-dev). Cahier des attentes : EX-13 et EX-22
deviennent « à faire » puis « partiel » une fois l'API livrée ; EX-32 suit le débrief du groupe.
