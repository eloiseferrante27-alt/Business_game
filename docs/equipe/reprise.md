# Reprise de session (après /clear) - 05/11/2026

VS Code s'ouvre sur le dossier parent `G_mix-Generateur-Business_Games` (choix de l'utilisateur, 05/11). L'équipe y vit,
hors git : `../CLAUDE.md` et `../.claude/` (agents, réglages, `ownership.json`), retirés du dépôt le 05/11 (ils restent
dans l'historique). Commandes à lancer en `.\Business_game-contribution_Romain\scripts\...`.

## État

- Branche `contribution_Romain` poussée le 05/11 sur `origin` (b25c81a, 7 commits au-dessus de `contribution_amine`),
  sans LICENSE.md à l'époque. Décision de l'utilisateur du 06/11 (inverse de celle du 05/11) : LICENSE.md (licence non
  commerciale de G-mix) est remis dans un nouveau commit, historique non réécrit. Les licences des assets de tiers (Kenney, icônes) restent.
- API de l'étape 7 livrée : `/ready` (prêt, vote sur les absents), `/pause`, `/event`, `/advance {ignore_absent}`,
  `state.alerts[]`, critères (annexe 0010 §1 à §3) ; `/api/v1/groups` (ADR 0011).
- B0 fait le 05/11 : `test.ps1 -Integration` -> pytest 798 passés (dont test_groups.py), `godot.ps1 -Check` 144
  fichiers OK (le premier passage échouait seulement sur le premier import des .glb dans ce dossier).
- Le venv backend a été réinstallé sur le bon chemin le 05/11.

## À faire, dans l'ordre : une tranche = une session

1. **B1 Pilotage de la partie : fait le 05/11** (EX-24, 25, 27 en partie, 28, 29 en partie), non commité : barre `GmixRoundBar` (tablette et salle), alertes `state.alerts[]`, relecture 15 s, `lobby.round` routé.
   Vérifié : `-Check` 145 fichiers OK, `-Tour` 0 défaut, `-Flow -NoLlm` 537 vérifications à l'époque (étape A.5b ; 560 depuis B2), `test.ps1 -Integration` 796 passés, 2 échecs hors B1 (`test_groups` ordre du débrief ; Ollama injoignable). Reste : coach-equipe (`team.ps1 -Report`).
2. **B2 Groupes : fait le 06/11** (EX-21, 22, 32 en partie), non commité : « Nombre d'équipes » (2 à 12) dans « Lancer une session », écran `group` (`GmixGroupScreen`), code + « Copier », cartes d'équipes, choix d'équipe (`/groups/join`, repli sur `/lobbies/join` si 404), débrief comparé (`/groups/{id}/debrief`). Le joueur n'a pas de liste de groupes à l'accueil (« Mes parties »). `-Tour` : 3 captures (17 à 19).
   Vérifié le 06/11 : `-Check` 146 fichiers OK, `-Tour` 212 écrans 0 défaut, `-Flow -NoLlm` 560 vérifications 0 échec (étape A.5c), `test.ps1 -Integration` ruff OK, pytest 799 passés 0 échec, Godot OK. Reste : coach-equipe en attente.
3. **B3 Pages des départements : fait le 06/11** (EX-30 en partie), non commité, Godot seul (aucun changement d'API ni de moteur) : tablette à une page `dept:<id>` par département (`spec.departments`, modules regroupés par `roles[].department_id`), sinon une page par module. Droits comme `engine.act` : formateur et admin partout, joueur sur le module de son rôle, formulaires grisés sans rôle ou avec la raison « Cette action revient au rôle « X » » ; point « ● » et « C'est votre département » / « lecture seule pour vous ». Alertes sur la page de leur département (repli module) et dans la vue générale. Helpers `Session.my_role()` et `Session.module_block()`.
   Vérifié le 06/11 : `-Check` 146 fichiers OK, `-Tour` 220 écrans 0 défaut (captures 25 `-dept-prod`, `-dept-ach`), `-Flow -NoLlm` 574 vérifications 0 échec (correctif des modules sans département fait) (étape A.5d `_check_tablet_roles`), `test.ps1 -Integration` ruff OK, pytest 799 passés 0 échec, Godot OK ; qa-reviewer : bon pour commit. Reste : le vrai formulaire du HUD (`hud.gd::_blocked_reason`) n'est pas exercé par flow_test (bouton factice) ; ouverture d'une page par clic sur une zone `dept:` du monde non faite ; coach-equipe en attente.
4. **B4 F2/F3 + J3** (EX-08, 31) : **prochaine tranche** ; progression de la conception, sections à régénérer, mode construction, écran de
   débrief avec courbes ; `-Design` dans `scripts/godot.ps1` (devops) et `flow_test.gd` ; passe finale `-Tour` (EX-34).
5. **Première version** : commit et push de chaque tranche (`git push`), LICENSE.md non commercial inclus (décision du 06/11).

## Hors G-mix

Le dépôt public `claude-skills-and-team-for-every-project` est prêt en local (`C:\_Documents-Romain\claude-skills-and-team-for-every-project`), pas encore poussé : `gh auth login` d'abord, puis refaire le commit avec l'adresse noreply GitHub.

## Règles de coût (appliquées dans CLAUDE.md et orchestrateur.md le 05/11)

Un chantier = une session · une mission = un livrable, nouvel agent après 60 tours ou une pause · fichier de plus de
300 lignes lu par plages, jamais relu sans modification · une capture lue une fois · comptes rendus de 15 lignes au
plus · ne pas relancer `stop.ps1` ni `docker compose down`.
