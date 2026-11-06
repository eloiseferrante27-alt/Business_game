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
- API de pilotage livrée (ADR 0010) : `/ready` (prêt, vote sur les absents), `/pause`, `/event`, `/advance {ignore_absent}`,
  `state.alerts[]`, critères (annexe 0010 §1 à §3) ; `/api/v1/groups` (ADR 0011).
- B0 fait le 05/11 : `test.ps1 -Integration` -> pytest 798 passés (dont test_groups.py), `godot.ps1 -Check` 144
  fichiers OK (le premier passage échouait seulement sur le premier import des .glb dans ce dossier).
- Le venv backend a été réinstallé sur le bon chemin le 05/11.

## Tranches : une tranche = une session

1. **B1 Pilotage de la partie : fait le 05/11, commité (bed8e8b)** (EX-24, 25, 27 en partie, 28, 29 en partie) : barre `GmixRoundBar` (tablette et salle), alertes `state.alerts[]`, relecture 15 s, `lobby.round` routé.
   Vérifié : `-Check` 145 fichiers OK, `-Tour` 0 défaut, `-Flow -NoLlm` 537 vérifications à l'époque (étape A.5b ; 560 depuis B2), `test.ps1 -Integration` 796 passés, 2 échecs hors B1 (`test_groups` ordre du débrief ; Ollama injoignable). Reste : coach-equipe (`team.ps1 -Report`).
2. **B2 Groupes : fait le 06/11, commité (bed8e8b)** (EX-21, 22, 32 en partie) : « Nombre d'équipes » (2 à 12) dans « Lancer une session », écran `group` (`GmixGroupScreen`), code + « Copier », cartes d'équipes, choix d'équipe (`/groups/join`, repli sur `/lobbies/join` si 404), débrief comparé (`/groups/{id}/debrief`). Le joueur n'a pas de liste de groupes à l'accueil (« Mes parties »). `-Tour` : 3 captures (17 à 19).
   Vérifié le 06/11 : `-Check` 146 fichiers OK, `-Tour` 212 écrans 0 défaut, `-Flow -NoLlm` 560 vérifications 0 échec (étape A.5c), `test.ps1 -Integration` ruff OK, pytest 799 passés 0 échec, Godot OK.
3. **B3 Pages des départements : fait le 06/11, poussé (bed8e8b)** (EX-30 en partie), Godot seul (aucun changement d'API ni de moteur) : tablette à une page `dept:<id>` par département (`spec.departments`, modules regroupés par `roles[].department_id`), sinon une page par module. Droits comme `engine.act` : formateur et admin partout, joueur sur le module de son rôle, formulaires grisés sans rôle ou avec la raison « Cette action revient au rôle « X » » ; point « ● » et « C'est votre département » / « lecture seule pour vous ». Alertes sur la page de leur département (repli module) et dans la vue générale. Helpers `Session.my_role()` et `Session.module_block()`.
   Vérifié le 06/11 : `-Check` 146 fichiers OK, `-Tour` 220 écrans 0 défaut (captures 25 `-dept-prod`, `-dept-ach`), `-Flow -NoLlm` 574 vérifications 0 échec (correctif des modules sans département fait) (étape A.5d `_check_tablet_roles`), `test.ps1 -Integration` ruff OK, pytest 799 passés 0 échec, Godot OK ; qa-reviewer : bon pour commit. Reste : le vrai formulaire du HUD (`hud.gd::_blocked_reason`) n'est pas exercé par flow_test (bouton factice) ; ouverture d'une page par clic sur une zone `dept:` du monde non faite (restes de B3 à reprendre avec B4).
4. **B4a Débrief en courbes et clic de zone : fait le 06/11, commité 6000cb1, poussé (e3733e1..6000cb1)** (EX-30, 31, 32 ; ADR 0012). `debrief.criteria[].series` (`engine._series`), 14 leçons réécrites (faits calculés, reliées aux fiches knowledge/supply-chain, sans contrefactuel ; `trs_drift` et `WEAR_TRS` présentés comme règles non sourcées), écran `GmixDebrief` (courbes, causes, leçons, notions, non sourcées), clic de zone `dept:<id>`, captures ui_tour 16b et 16c, `godot.ps1 -Flow -Pack <slug>`.
   Vérifié le 06/11 : qa-reviewer `test.ps1 -Integration` ruff OK, pytest 808 passés 0 échec, `-Check` 147 fichiers OK, `-Tour` 228 écrans 0 défaut ; après correctifs `-Flow -NoLlm` 602 vérifications 0 échec, `-Flow -NoLlm -Pack usine` 344 0 échec, `test.ps1 -Fast` 772 passés. **`-Tour` non rejoué après le dernier correctif de `world.gd` (clic de zone)** : à relancer. Verdict qa-reviewer : bon pour commit.
5. **B4b Régénération de sections (EX-08), version courte : fait le 06/11, pas encore commité.** ADR 0012 (b1 à b6). Décision : régénérer une section d'un jeu publié le repasse en brouillon, à republier. **B4 terminé ; B4c c1 (mode construction) reporté.**
   - b1 (prompt `factory.design` v3, `keep` et `note`, éval 13/15), b2 (route regenerate, `_store` fusionne `review`), b3 (worker `_keep`), b4 (écran `godot/scenes/draft/draft_screen.gd`, F1 « Imposer », F2 « n % » et temps écoulé), b5 (`godot.ps1 -Flow -Design`, relance du worker `generation` périmé), b6 (qa).
   - Palettes : 3 claires (`chaud`, `sauge`, `ardoise`) par `GMIX_PALETTE=<id>` ou `--palette=<id>` ; défaut cacao sombre inchangé. **Choix de l'utilisateur en attente.**
   - Vérifié le 06/11 : qa-reviewer `test.ps1 -Integration` ruff OK, 822 passés, `smoke.ps1` OK, `-Tour` 236 écrans 0 défaut, « bon pour commit ». Après correctifs : `-Check` 148 OK ; `-Flow -NoLlm` 602 et `-Pack usine` 344 0 échec ; `-Flow -NoLlm -Design` 96 et `-Flow -Design` (modèle) 72, 0 échec.
   - Défauts mineurs laissés : `regenerate_design` non atomique (comme `create_design`) ; en cas de repli, `review` garde d'anciens `autopilot` et `dropped` ; le contrôle « Mes jeux sans doublon » ne couvre pas un jeu en cours de conception.

## À faire, ordre validé par l'utilisateur le 06/11

Cadre de la démo : LAN, 3 à 6 joueurs ; le jeu à distance vient après la Première version.

| # | Chantier | Références |
|---|---|---|
| 1 | B4b fait (06/11) : à commiter ; choix de palette en attente | ADR 0012 ; EX-08 |
| 2 | **Prochaine étape** : répétition d'une séance en salle en LAN : parcours joueur B de flow_test, vote sur un absent avec 2 joueurs, souris et clavier AZERTY réels, 3 postes, pare-feu ouvert | EX-05 (LAN), 22, 23, 25 |
| 3 | Exigence n° 1 : relire et signer 10 jeux conçus par l'IA ; notes périmées de ai/packs/usine.yaml (l. 336 et 370, à revérifier) ; notion `rupture_de_stock` | ADR 0010 ; EX-01, EX-16 |
| 4 | Garde-fou des nombres de `npc.py` : décision OUI, à activer avant la démo | EX-33 |
| 5 | Dette « À corriger » de l'annexe 0010 | ADR 0010 annexe |
| 6 | Passe finale `-Tour` | EX-34 ; ADR 0012 c2 |
| 7 | Docs, puis **Première version** : commit et push de chaque tranche (`git push`), LICENSE.md non commercial inclus | décision du 06/11 |

Après la Première version : mode construction (B4c c1), EX-12, 14, 19, 29 (page F5 complète), 36, EX-05 à distance.

## Hors G-mix

Le dépôt public `claude-skills-and-team-for-every-project` est poussé (`C:\_Documents-Romain\claude-skills-and-team-for-every-project`, main 7215cd7..f3fc3ff, commits en adresse noreply).

## Règles de coût (appliquées dans CLAUDE.md et orchestrateur.md le 05/11)

Un chantier = une session · une mission = un livrable, nouvel agent après 60 tours ou une pause · fichier de plus de
300 lignes lu par plages, jamais relu sans modification · une capture lue une fois · comptes rendus de 15 lignes au
plus · ne pas relancer `stop.ps1` ni `docker compose down`.
