# Reprise de session (après /clear) - 05/11/2026

VS Code s'ouvre sur le dossier parent `G_mix-Generateur-Business_Games` (choix de l'utilisateur, 05/11). L'équipe y vit,
hors git : `../CLAUDE.md` et `../.claude/` (agents, réglages, `ownership.json`), retirés du dépôt le 05/11 (ils restent
dans l'historique). Commandes à lancer en `.\Business_game-contribution_Romain\scripts\...`.

## État

- Branche `contribution_Romain` poussée le 05/11 sur `origin` (b25c81a, 7 commits au-dessus de `contribution_amine`),
  **sans LICENSE.md** : retiré de tout l'historique avant le push, à la demande de l'utilisateur ; ne pas le remettre.
  Les licences des assets de tiers (Kenney, icônes) restent.
- API de l'étape 7 livrée : `/ready` (prêt, vote sur les absents), `/pause`, `/event`, `/advance {ignore_absent}`,
  `state.alerts[]`, critères (annexe 0010 §1 à §3) ; `/api/v1/groups` (ADR 0011).
- B0 fait le 05/11 : `test.ps1 -Integration` -> pytest 798 passés (dont test_groups.py), `godot.ps1 -Check` 144
  fichiers OK (le premier passage échouait seulement sur le premier import des .glb dans ce dossier).
- Le venv backend a été réinstallé sur le bon chemin le 05/11.

## À faire, dans l'ordre : une tranche = une session

1. **B1 Pilotage de la partie : fait le 05/11** (EX-24, 25, 27 en partie, 28, 29 en partie), non commité : barre `GmixRoundBar` (tablette et salle), alertes `state.alerts[]`, relecture 15 s, `lobby.round` routé.
   Vérifié : `-Check` 145 fichiers OK, `-Tour` 0 défaut, `-Flow -NoLlm` 537 vérifications (étape A.5b), `test.ps1 -Integration` 796 passés, 2 échecs hors B1 (`test_groups` ordre du débrief ; Ollama injoignable). Reste : coach-equipe (`team.ps1 -Report`).
2. **B2 Groupes** (EX-21, 22, 32) : création d'un groupe de N équipes (`home_screen.gd`), grand code + « Copier »,
   cartes d'équipes et choix d'équipe (`/groups/join`), débrief comparé (`/groups/{id}/debrief`).
3. **B3 Pages des départements** dans la tablette (EX-30), lecture seule hors du sien.
4. **B4 F2/F3 + J3** (EX-08, 31) : progression de la conception, sections à régénérer, mode construction, écran de
   débrief avec courbes ; `-Design` dans `scripts/godot.ps1` (devops) et `flow_test.gd` ; passe finale `-Tour` (EX-34).
5. **Première version** : commit et push de chaque tranche (`git push`), toujours sans LICENSE.md.

## Règles de coût (appliquées dans CLAUDE.md et orchestrateur.md le 05/11)

Un chantier = une session · une mission = un livrable, nouvel agent après 60 tours ou une pause · fichier de plus de
300 lignes lu par plages, jamais relu sans modification · une capture lue une fois · comptes rendus de 15 lignes au
plus · ne pas relancer `stop.ps1` ni `docker compose down`.
