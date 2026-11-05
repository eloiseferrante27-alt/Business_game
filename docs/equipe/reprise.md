# Reprise de session (après /clear) - 05/11/2026

Ouvrir VS Code sur **ce dossier** (`Business_game-contribution_Romain`), pas sur son parent : sinon `.claude/` (agents,
réglages, orchestrateur) et CLAUDE.md ne sont pas chargés.

## État

- Branche `contribution_Romain`, 5 commits au-dessus de `contribution_amine` (import amine, import G-mix, groupes
  ADR 0011, verrou des groupes, équipe allégée). **Non poussée** : push décidé par l'utilisateur à la fin de la
  première version (après B4), voir plus bas.
- API de l'étape 7 livrée : `/ready` (prêt, vote sur les absents), `/pause`, `/event`, `/advance {ignore_absent}`,
  `state.alerts[]`, critères (annexe 0010 §1 à §3) ; `/api/v1/groups` (ADR 0011). Le client Godot n'appelle encore
  que `/advance`.
- `backend/tests/test_groups.py` écrit, **jamais lancé** (`test.ps1 -Integration`).

## À faire, dans l'ordre : une tranche = une session

0. qa-reviewer : `.\scripts\test.ps1 -Integration` ; un échec retourne à backend-api.
1. **B1 Pilotage de la partie** (godot-dev ; EX-24, 25, 27, 28, 29) :
   - `realtime.gd` `_route` : `lobby.round` -> nouveau signal `EventBus.lobby_round_changed(round)` ;
     `session.gd` tient `lobby["round"]`, `reload()` après une action `advance`, vue relue toutes les 15 s quand la
     partie tourne (`shortcut:` aucun événement à la déconnexion, annexe 0010 §1).
   - Joueur (tablette `tablet.gd` `READY_REASON`, salle `lobby_screen.gd` `_ready_button`) : « Prêt pour la semaine
     suivante » -> `POST /ready {ready}`, « k/n prêts » ; si `round.vote.open` : « Ignorer l'absent » / « Attendre »
     (`/ready {ready: true, absent}`) avec le décompte.
   - Formateur (`hud.gd` `_on_tool`, `lobby_screen.gd`) : Pause/Reprendre, « Déclencher un aléa » (`spec.events`),
     « Forcer la semaine » avec la case « absents en pilote automatique », prêt et connecté par joueur.
   - Barre du HUD : alertes de `state.alerts[]` (niveau, texte, bouton d'action prérempli si `action`), dans `GameText`.
   - Tests : étapes dans le parcours A de `flow_test.gd`, écrans dans `ui_tour.gd`. Fin : `godot.ps1 -Check`,
     `-Flow -NoLlm`, `-Tour` verts ; qa-reviewer ; documentaliste (cahier EX-24 à 28).
   - Puis `coach-equipe` (`team.ps1 -Report`) pour mesurer l'effet des règles de coût du 05/11.
2. **B2 Groupes** (EX-21, 22, 32) : création d'un groupe de N équipes (`home_screen.gd`), grand code + « Copier »,
   cartes d'équipes et choix d'équipe (`/groups/join`), débrief comparé (`/groups/{id}/debrief`).
3. **B3 Pages des départements** dans la tablette (EX-30), lecture seule hors du sien.
4. **B4 F2/F3 + J3** (EX-08, 31) : progression de la conception, sections à régénérer, mode construction, écran de
   débrief avec courbes ; `-Design` dans `scripts/godot.ps1` (devops) et `flow_test.gd` ; passe finale `-Tour` (EX-34).
5. **Première version** : `git push -u origin contribution_Romain` (le dépôt semble public : code sous licence non
   commerciale visible), vérifier `git ls-remote origin contribution_Romain` = HEAD.

## Règles de coût (appliquées dans CLAUDE.md et orchestrateur.md le 05/11)

Un chantier = une session · une mission = un livrable, nouvel agent après 60 tours ou une pause · fichier de plus de
300 lignes lu par plages, jamais relu sans modification · une capture lue une fois · comptes rendus de 15 lignes au
plus · ne pas relancer `stop.ps1` ni `docker compose down`.
