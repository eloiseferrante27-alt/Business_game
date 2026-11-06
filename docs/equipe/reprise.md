# Reprise de session (après /clear) - 06/11/2026

VS Code s'ouvre sur le dossier parent `G_mix-Generateur-Business_Games` (choix de l'utilisateur, 05/11). L'équipe y vit,
hors git : `../CLAUDE.md` et `../.claude/` (agents, réglages, `ownership.json`), retirés du dépôt le 05/11 (ils restent
dans l'historique). Commandes à lancer en `.\Business_game-contribution_Romain\scripts\...`.

## État

- Branche `contribution_Romain` poussée le 06/11 : push 1e46f51..44ae345 sur `origin`. Commits bed8e8b (B1 à B3, 15 fichiers)
  et 44ae345 (LICENSE.md non commercial remis, décision du 06/11 ; historique non réécrit). Les licences des assets de tiers (Kenney, icônes) restent.
- Rétro `docs/equipe/retro-2026-11-06.md` : propositions 1 et 2 appliquées, 3 rejetée. `orchestrateur.md` réduit à 60 lignes, avec la règle « documentaliste après le dernier correctif » ; devops sait faire commit et push.
- `team.ps1 -Run <agentId>` affiche « Erreurs d'outil » ; `-Json` ajoute `tool_error_details` (scripts/team_metrics.py, backend/tests/test_team_metrics.py). `test.ps1 -Fast` : ruff OK, pytest 762 passés. Les erreurs godot-dev examinées sont surtout des « PowerShell : Exit code 1 » dus au stderr de Docker.
- Fin de session du 06/11 commitée et poussée (mesure des erreurs d'outil, rétro, docs).
- API de l'étape 7 livrée : `/ready` (prêt, vote sur les absents), `/pause`, `/event`, `/advance {ignore_absent}`,
  `state.alerts[]`, critères (annexe 0010 §1 à §3) ; `/api/v1/groups` (ADR 0011).
- B0 fait le 05/11 : `test.ps1 -Integration` -> pytest 798 passés (dont test_groups.py), `godot.ps1 -Check` 144
  fichiers OK (le premier passage échouait seulement sur le premier import des .glb dans ce dossier).
- Le venv backend a été réinstallé sur le bon chemin le 05/11.

## À faire, dans l'ordre : une tranche = une session

1. **B1 Pilotage de la partie : fait le 05/11** (EX-24, 25, 27 en partie, 28, 29 en partie), non commité : barre `GmixRoundBar` (tablette et salle), alertes `state.alerts[]`, relecture 15 s, `lobby.round` routé.
   Vérifié : `-Check` 145 fichiers OK, `-Tour` 0 défaut, `-Flow -NoLlm` 537 vérifications à l'époque (étape A.5b ; 560 depuis B2), `test.ps1 -Integration` 796 passés, 2 échecs hors B1 (`test_groups` ordre du débrief ; Ollama injoignable). Reste : coach-equipe (`team.ps1 -Report`).
2. **B2 Groupes : fait le 06/11** (EX-21, 22, 32 en partie), non commité : « Nombre d'équipes » (2 à 12) dans « Lancer une session », écran `group` (`GmixGroupScreen`), code + « Copier », cartes d'équipes, choix d'équipe (`/groups/join`, repli sur `/lobbies/join` si 404), débrief comparé (`/groups/{id}/debrief`). Le joueur n'a pas de liste de groupes à l'accueil (« Mes parties »). `-Tour` : 3 captures (17 à 19).
   Vérifié le 06/11 : `-Check` 146 fichiers OK, `-Tour` 212 écrans 0 défaut, `-Flow -NoLlm` 560 vérifications 0 échec (étape A.5c), `test.ps1 -Integration` ruff OK, pytest 799 passés 0 échec, Godot OK.
3. **B3 Pages des départements : fait le 06/11, poussé (bed8e8b)** (EX-30 en partie), Godot seul (aucun changement d'API ni de moteur) : tablette à une page `dept:<id>` par département (`spec.departments`, modules regroupés par `roles[].department_id`), sinon une page par module. Droits comme `engine.act` : formateur et admin partout, joueur sur le module de son rôle, formulaires grisés sans rôle ou avec la raison « Cette action revient au rôle « X » » ; point « ● » et « C'est votre département » / « lecture seule pour vous ». Alertes sur la page de leur département (repli module) et dans la vue générale. Helpers `Session.my_role()` et `Session.module_block()`.
   Vérifié le 06/11 : `-Check` 146 fichiers OK, `-Tour` 220 écrans 0 défaut (captures 25 `-dept-prod`, `-dept-ach`), `-Flow -NoLlm` 574 vérifications 0 échec (correctif des modules sans département fait) (étape A.5d `_check_tablet_roles`), `test.ps1 -Integration` ruff OK, pytest 799 passés 0 échec, Godot OK ; qa-reviewer : bon pour commit. Reste : le vrai formulaire du HUD (`hud.gd::_blocked_reason`) n'est pas exercé par flow_test (bouton factice) ; ouverture d'une page par clic sur une zone `dept:` du monde non faite (restes de B3 à reprendre avec B4).
4. **B4a Débrief en courbes et clic de zone : fait le 06/11**, non commité (EX-30, 31, 32 ; ADR 0012). `debrief.criteria[].series` (`engine._series`), 14 leçons réécrites (faits calculés, reliées aux fiches knowledge/supply-chain, sans contrefactuel ; `trs_drift` et `WEAR_TRS` présentés comme règles non sourcées), écran `GmixDebrief` (courbes, causes, leçons, notions, non sourcées), clic de zone `dept:<id>`, captures ui_tour 16b et 16c, `godot.ps1 -Flow -Pack <slug>`.
   Vérifié le 06/11 : qa-reviewer `test.ps1 -Integration` ruff OK, pytest 808 passés 0 échec, `-Check` 147 fichiers OK, `-Tour` 228 écrans 0 défaut ; après correctifs `-Flow -NoLlm` 602 vérifications 0 échec, `-Flow -NoLlm -Pack usine` 344 0 échec, `test.ps1 -Fast` 772 passés. **`-Tour` non rejoué après le dernier correctif de `world.gd` (clic de zone)** : à relancer. Verdict qa-reviewer : bon pour commit.
5. **B4b Régénération de sections (EX-08) : prochaine tranche** ; sections de l'usine (`FACTORY_SECTIONS`, `RegenerateRequest` déjà dans `spec.py`), F2, `-Flow -Design`. Découpage et tableau des étapes : ADR 0012 (b1 à b6). Décision de l'utilisateur (06/11) : régénérer une section d'un jeu publié le repasse en brouillon, à republier. B4a va être commité et poussé (devops) avant le début de B4b.
6. **B4c Mode construction (EX-34)** : après B4b ; passe finale `-Tour` ; peut se couper en B4c1 et B4c2 (ADR 0012).
7. **Première version** : commit et push de chaque tranche (`git push`), LICENSE.md non commercial inclus (décision du 06/11).

## Hors G-mix

Le dépôt public `claude-skills-and-team-for-every-project` est poussé (`C:\_Documents-Romain\claude-skills-and-team-for-every-project`, main 7215cd7..f3fc3ff, commits en adresse noreply).

## Règles de coût (appliquées dans CLAUDE.md et orchestrateur.md le 05/11)

Un chantier = une session · une mission = un livrable, nouvel agent après 60 tours ou une pause · fichier de plus de
300 lignes lu par plages, jamais relu sans modification · une capture lue une fois · comptes rendus de 15 lignes au
plus · ne pas relancer `stop.ps1` ni `docker compose down`.
