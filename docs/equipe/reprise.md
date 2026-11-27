# Reprise de session (après /clear) - état au 27/11/2026 (le détail des tranches B date du 06/11)

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
   Vérifié le 06/11 : qa-reviewer `test.ps1 -Integration` ruff OK, pytest 808 passés 0 échec, `-Check` 147 fichiers OK, `-Tour` 228 écrans 0 défaut ; après correctifs `-Flow -NoLlm` 602 vérifications 0 échec, `-Flow -NoLlm -Pack usine` 344 0 échec, `test.ps1 -Fast` 772 passés. `-Tour` rejoué depuis le correctif de `world.gd` : 236 écrans, 0 défaut. Verdict qa-reviewer : bon pour commit.
5. **B4b Régénération de sections (EX-08), version courte : fait le 06/11, poussé (commit d843c7e, push 6000cb1..d843c7e).** Rétro B4 (`retro-2026-11-06-b4.md`) faite, ses 3 propositions appliquées le 06/11. ADR 0012 (b1 à b6). Décision : régénérer une section d'un jeu publié le repasse en brouillon, à republier. **B4 terminé ; B4c c1 (mode construction) reporté.**
   - b1 (prompt `factory.design` v3, `keep` et `note`, éval 13/15), b2 (route regenerate, `_store` fusionne `review`), b3 (worker `_keep`), b4 (écran `godot/scenes/draft/draft_screen.gd`, F1 « Imposer », F2 « n % » et temps écoulé), b5 (`godot.ps1 -Flow -Design`, relance du worker `generation` périmé), b6 (qa).
   - Palettes : 3 claires (`chaud`, `sauge`, `ardoise`) par `GMIX_PALETTE=<id>` ou `--palette=<id>` ; **Depuis le 06/11 (choix de l'utilisateur), « ardoise » (bleu et blanc) est la palette par défaut ; « cacao » reste disponible. Changement commité et poussé le 06/11 avec la rétro B4 (commit qui suit d843c7e).** Finitions de la palette : le « × » des fenêtres prend la couleur du texte et les interrupteurs sont teintés.
   - Vérifié le 06/11 : qa-reviewer `test.ps1 -Integration` ruff OK, 822 passés, `smoke.ps1` OK, `-Tour` 236 écrans 0 défaut, « bon pour commit ». Après correctifs : `-Check` 148 OK ; `-Flow -NoLlm` 602 et `-Pack usine` 344 0 échec ; `-Flow -NoLlm -Design` 96 et `-Flow -Design` (modèle) 72, 0 échec.
   - Défauts mineurs laissés : `regenerate_design` non atomique (comme `create_design`) ; en cas de repli, `review` garde d'anciens `autopilot` et `dropped` ; le contrôle « Mes jeux sans doublon » ne couvre pas un jeu en cours de conception.

## Session du 19/11 : priorité 3, audit de l'exigence n° 1 (point d'étape avant commit)

**Fait**
- Audit (game-designer, `docs/audits/`) : protocole, puis 10 jeux générés par ia-runtime (`ai/evals/results/audit-2026-11-19/`), tous refusés ; 15 défauts D1 à D15 dans `docs/audits/liste-a-signer.md`, fiches dans `docs/audits/jeux-ia/`. Aucun chiffre inventé : tous calculés par le moteur.
- Prompt `factory.design` v4 : respect des consignes 30/50 -> 42/50 avec qwen2.5:3b, conservé (le 7b : 45/50 mais 27 s ; comparatif `ai/evals/results/design-consignes-2026-11-19/`). `degenerate()` refuse les `unmet` dégénérés. Contrôle C1 de l'audit fiabilisé.
- Pack : source retirée, textes conformes au moteur, vouvoiement, sigles expliqués, fragments par niveau.
- Moteur : alerte `breakdown_goulot` ; chiffres à la française (`num()`) ; pitch selon les réglages effectifs ; fait « 1 406 minutes au total » ; TRS sans les pauses, conforme à la fiche OEE (décision de l'orchestrateur) ; commande initiale en expert (`factory.initial_order`, typée `InitialOrder` par l'architecte) ; marge des ruptures par ligne ; tests de temps relatifs à une boucle de référence.
- Vérifié par qa-reviewer : `test.ps1 -Integration` 846 passés, `-Flow -NoLlm` 686, `-Flow -Design` 72 ; après correctifs `-Flow -NoLlm -Pack usine` 428, 0 échec. `test.ps1 -Fast` : devops le relance avant commit. Rien n'est commité à la rédaction de cette note (devops commite juste après).
- Comptes : l'utilisateur a le compte admin `romain` ; l'ancien `admin` est supprimé ; `start.ps1` recrée `admin` s'il manque.
- Écarts de propriété pour la prochaine rétro : ia-runtime a modifié docs/ai-runtime.md et ai/evals/README.md ; moteur-jeu a modifié spec.py. Tous deux validés ensuite.

**Décision de l'utilisateur, 19/11 : monde 3D variable** (aussi dans docs/blocages.md). Le monde varie en apparence ET en structure : plusieurs bâtiments et pièces entre lesquels sont répartis joueurs, agents, rôles et actions. Chantier juste après l'audit, avant le garde-fou des PNJ.
- Vision : selon paramètres, consigne ou documents fournis, une équipe d'agents IA spécialisés (orchestrateur et sous-agents) conçoit le monde, avec génération procédurale et expertise métier.
- Contraintes à rappeler à l'architecte : un seul modèle 3b sur 6 Go de VRAM, donc agents en série ; conception 3 min en médiane, 10 au plus (ADR 0008, qui avait ramené trois appels à un seul) ; le moteur seul calcule les chiffres.
- Constat du 19/11 : `layout.place_world` n'utilise pas la graine (ADR 0009) ; hall toujours 48 x 30 m ; décor Godot figé (arbres, graine 42) ; 2 modèles de machine sur environ 8 ; toujours 3 fournisseurs et 1 produit.

## Session du 21/11 : ADR 0013 accepté, audit T0 au second tour

**Décision de l'utilisateur, 21/11** (ADR 0013 §6, `docs/decisions/0013-generation-de-mondes-et-de-jeux-differents.md`) : ADR complet avant la Première version ; second domaine jouable, la finance d'entreprise (trésorerie et BFR d'une PME), en plus de la supply chain (`finance-entreprise`, moteur `factory`, D0 fait le 21/11) ; documents du formateur comme source (chaque passage validé, provenance « formateur », aucun chiffre de document dans le moteur) ; orchestrateur en code et 5 agents IA en série ; budget de conception inchangé (3 min en médiane, 10 au plus) ; 3b partout (interprétation de l'architecte, à confirmer par l'utilisateur : le 7b est un choix fait à l'éval, tâche par tâche, sans bascule en cours de job). Rien de cela n'est livré : le monde reste le hall en U, un seul domaine est jouable, le brief ne produit aucun texte.

**Fait le 21/11 (commité)** : préventif P2 et P3 (formes du goulot 3/2/1, 200 € de dégâts, cible TRS 80 %), pannes évitées exposées dans le débrief, textes du préventif ; deux fiches au corpus (TRS fr, Weibull NIST), corpus réingéré, couverture 34/37 ; TRS présenté comme une convention ; champ `damage_per_failure` dans `spec.py` ; affichage `bottlenecks` dans Godot ; C1 de l'audit fiabilisé ; `test.ps1 -Fast` 805 passés.

**Audit T0, second tour** (`docs/audits/liste-a-signer.md`, fiches `jeux-ia/J01-t2.md` à `J10-t2.md`, sorties `ai/evals/results/audit-2026-11-21/`) : 0 conforme, 5 à corriger, 5 refusés.

**T0 clos le 21/11, commité (ffed981 et 352fce5)**

Troisième tour (`ai/evals/results/audit-2026-11-21-t3/`, fiches `docs/audits/jeux-ia/J0x-t3.md`) : aucun échec automatique ; 3 jeux conformes, J05, J08 et J09, **signés par l'utilisateur le 21/11** ; 7 jeux « exacts, respect de la demande à améliorer », repris en T9 ; aucun refusé. Liste : `docs/audits/liste-a-signer.md` (tenue par game-designer).

| Correction | Résultat |
|---|---|
| Prompt `factory.design` v5 (`current=`, `clean_unmet`), le worker passe `current=` | régénérations changées 6 fois sur 6, `unmet` justes 30 fois sur 30 (`ai/evals/results/design-consignes-2026-11-21/`) |
| Pack usine | fournisseur standard limité à `proche`, marge expert 6, notes de calibrage |
| Moteur | textes D16, D7, D13, D15 ; avertissement `passive_wins` ; D19 (bilan non chiffrable) en cours de correction |
| Godot | avertissements dans la relecture et le brouillon ; le parcours usine joue les semaines et vérifie les goulots (bug « margin » corrigé) |
| ADR 0010 | second domaine décidé |

Reporté : D17 (critère « pannes évitées au goulot », refus si le passif gagne, tranche T3 de l'audit) ; D8 (coïncidences de C1) ; couverture RAG `trs_oee` (rag-knowledge) ; interprétation « 3b partout » (7b, à confirmer par l'utilisateur). Vérifications chiffrées du T0 : point d'étape qa-reviewer du 21/11 (avant les corrections du 3e tour) `test.ps1 -Integration` 858 passés, `-Flow -NoLlm` 686, `-Flow -Pack usine` 428, `-Tour` 236 écrans 0 défaut ; remplacées par les mesures de T2 ci-dessous.

Écarts de propriété pour la prochaine rétro : ia-runtime a encore modifié docs/ai-runtime.md ; godot-dev a relancé la pile (`start.ps1 -NoGame`), réservé à devops ; trois agents interrompus le 21/11 par la limite d'API.

**T2 fait le 24/11, commité (b11aa8f)** : contrats de la § 3.5 de l'ADR 0013 dans `backend/gmix/game/spec.py` : `Building`, `Room`, `World` (gabarit `campus`), `PlannedBuilding`, `Client`, `Finance`, `LoanOffer`, `Investment`, `Due`, `Loan`, `TrainerExcerpt`, plus `DesignRequest.domain` et `document_ids`. Champs facultatifs, `version` reste 2. Annexe `docs/decisions/0013-annexe-contrats.md` nouvelle ; aucun topic Kafka changé ; tests : `backend/tests/test_spec_0013.py` (38).

Mesures qa-reviewer, 24/11 : `test.ps1 -Integration` ruff OK, pytest 903 passés, Godot 148 fichiers OK ; `-Flow -NoLlm` 686 vérifications, 0 échec ; `-Flow -NoLlm -Pack usine` 514, 0 échec (nouvelle référence, c'était 428) ; `-Tour` 236 écrans, 0 défaut. Verdict : bon pour commit. Le hash du commit sera noté ensuite.

**Session du 27/11 : corrections, T5, T6 — commités et poussés (bcf8b89, 8f36f11..bcf8b89)**

Commit bcf8b89 « T5, T6 : campus de 1 à 3 bâtiments, trajets calculés, garde-fou des nombres des PNJ ; corrections D1 ». `test.ps1 -Fast` : 953 passés avant le commit. Avec 1 bâtiment, aucun chiffre de la partie de référence ne change.

| Livré | Détail |
|---|---|
| T5 campus | 1 à 3 bâtiments (`params.buildings`, `limits.buildings` `[1, 3, 1]`) ; archétypes `hall_production` (40 m de large au minimum), `entrepot`, `atelier_maintenance`, une pièce par département, zonage (`together`, `apart`, `max_walk_m` 150 m) ; `layout.place_campus` (20 tirages à graine, puis disposition de référence, sinon `LayoutError`) et `travel_min` ; chemins qui ne traversent pas les autres pièces, `protected_path` sur tout le chemin (INRS ED 6350) ; moteur : kit 8 + t (chariot occupé 8 + 2t), technicien qui marche, palette vers l'entrepôt ; vitesses sourcées dans 2 fiches de `knowledge/supply-chain/` (marche 75 m/min, Bohannon 1997 ; chariot 100 m/min, règle de jeu, R4323-51) ; assets `prop_wall_panel`, `prop_door_industrial`, `prop_floor_slab` ; Godot `_build_campus`, 164 images/s au pire cas ; 1 bâtiment : jeu de référence inchangé |
| Commande | `.\scripts\godot.ps1 -Flow -NoLlm -Pack usine -Buildings <2\|3>` (campus de bout en bout) ; `flow_test --fixture=campus2\|campus3` sans API |
| T6 garde-fou | `npc.py` remplace par la réponse de secours une réplique qui cite un nombre absent des faits (tolérances : arrondi, semaine, nombres de la question) ; `numbers()` lit « 62.7054 » ; vrai modèle : 9 répliques remplacées sur 152, 0 faux positif ; `eval_dialogue` utilise `npc.numbers` ; EX-33 fait ; clé `guard` non exposée au client (correctif backend-api) |

Mesures qa-reviewer, 27/11 : `test.ps1 -Integration` 1005 passés, 1 échec corrigé depuis (clé `guard`) ; `-Flow -NoLlm` 687 ; `-Pack usine` 522 ; `-Buildings 3` 530 ; `-Flow -Design` 72 ; `-Tour` 236 écrans, 0 défaut ; `smoke.ps1` OK.

Restes :
- R314-2 lu seulement en traduction : l'utilisateur doit coller le texte Légifrance.
- Base de 365 jours des pénalités de retard : hypothèse non sourcée.
- Durées des kits et des palettes sans les pauses : à noter dans la provenance (game-designer).
- Le chariot ne limite pas encore une partie de 4 semaines : recalibrage possible si l'utilisateur le veut.
- `-Integration` et `-Flow` non relancés après le correctif de la route de dialogue (`pop` de `guard` dans `lobbies.py`).
- Rétrospective `coach-equipe` : [retro-2026-11-27.md](retro-2026-11-27.md), 3 propositions appliquées.

**T4b fait le 27/11 (1 à 3 produits, 1 à 4 clients, correction de l'ingestion RAG, sources de la finance), commitée en 9f5a0a3 et poussée (bcf8b89..9f5a0a3, contribution_Romain).** Détail : docs/game-design.md (section T4b), restes dans docs/blocages.md.

**T7 (rôles de jeu de 1 à 6 joueurs) : faite le 27/11, à commiter.** Merge du commit d'Amine (b9b9445) en b483971, poussé : conception par l'IA, passerelle compatible OpenAI (docs/ai-runtime.md), tableur SurExel (`check_surexel.gd`, 11 cas, lancé par `-Check`). Détail : docs/roles.md, restes dans docs/blocages.md.

Mesures qa-reviewer, 27/11 : `test.ps1 -Integration` 1107 passés, 0 échec, 0 erreur (correctif `_release_db_pool` de `test_timeline.py`, à confirmer) ; `-Flow` 815 ; `-Flow -Pack usine` 529 ; `-Flow -Pack usine -Products 3 -Clients 4 -Buildings 3` 552 ; `-Flow -Design` 72 ; `-Flow -Roles` 51 ; `-Tour` 256 écrans ; `smoke.ps1` OK.

Restes de T4b : seuil d'OTIF de 90 codé en dur (`game_text.gd`) ; `pf_min` par produit et plafond de produits finis en palettes reportés à D3 ; pas de champ « Clients » au formulaire du formateur (T10) ; faits des PNJ à 3 produits non mesurés par les évaluations.

**Prochaine action : commiter T7, puis (T8, D2)**, T9, D3, T10, T11 (Première version). Ordre de l'ADR 0013 : T7 -> (T8, D2) -> T9.

**Session du 24-26/11 : T3, T4 (sauf T4b), D1 — commité et poussé le 26/11 (8f36f11, push b11aa8f..8f36f11)**

T2 commité et poussé (b11aa8f). T3 fait le 24/11. Validé par qa-reviewer le 26/11, avant commit.

| Livré | Détail |
|---|---|
| T4 (sauf multi-produits) | `layout.place_world` tire de la graine la taille du hall (48 x 30 m plus 0, 4, 8 ou 12 m) et le décor `world.decor` (45 éléments au plus ; `DecorItem`, `Decor` dans `spec.py`) ; `world_fingerprint` : 9 mondes distincts sur 12 graines par secteur ; Godot lit le décor de la spec (repli sur sa graine 42 pour les anciens jeux) ; 3 à 8 fournisseurs (`params.suppliers`) ; types de machine m1 à m4 par rang (`Machine.type`). Produits et clients étaient à 1 à cette date (bornes du pack `[1,1,1]`, levées en T4b) |
| D1 | `knowledge/finance-entreprise/` : 12 fiches (dont R314-2 et VAN de l'OQLF) ; `ai/evals/finance-entreprise.rag.jsonl` : Rappel@4 14/14 ; `docs/audits/finance-entreprise-conventions.md` : jours calendaires base 365, tout hors taxe, taux `rate_year/52`. Réserves de D1 levées le 27/11 : R314-2 lu en français sur codes.droit.org ; base 365 : principe sourcé (directive 2011/7/UE), chiffre = convention |

Mesures qa-reviewer, 26/11 : `test.ps1 -Integration` 935 passés, 0 échec, Godot 148 fichiers OK ; `-Flow -NoLlm` 687 ; `-Flow -NoLlm -Pack usine` 522 ; `-Flow -Design` 72, tous à 0 échec ; `-Tour` 236 écrans, 0 défaut ; `smoke.ps1` OK. Verdict : bon pour commit. Le hash sera noté après le commit.

Défauts mineurs ouverts : `test_game_flow.py:174` (test de budget sensible à la charge du poste, moteur-jeu) ; `spec.py:137` `GameParams.products` vaut 3 par défaut alors que le pack usine borne à 1 (à confirmer par l'architecte) ; contrôle `clients >= products` à écrire dans `GameParams` en T4b.

T5, T6 et T4b : faits le 27/11 (le contrôle `clients >= products` et les bornes ci-dessus sont réglés par T4b).

Écarts pour la rétro : le 24/11, moteur-jeu a fait `git stash` puis `stash pop` (git est à devops) ; rag-knowledge a tenté d'écrire dans `ai/evals/` ; l'ajout d'un contrôle dans `GameParams` a été refusé à l'architecte par les permissions ; le brief de 4a supposait le champ `decor` déjà dans le contrat.

Points ouverts venus de T2 : D1 : base de jours 365 avec CA hors taxe, contre 360 avec CA TTC à la Banque de France, et taux proportionnel des prêts `rate_year / 52` ; D2 : test de la VAN (100 000, 30 000, 5 ans, 8 % donnent 19 781,30) à écrire avec `gmix.game.finance` ; T8 : route `POST /games/documents` (corps brut), les PNJ ne citent jamais les passages du formateur ; T9 : section « monde » de la régénération ; à confirmer par l'utilisateur : « 3b partout ».

Ordre complet : T3, T4 et D1 en parallèle, T5 avec T6, T7, (T8, D2), T9, D3, T10, T11 (Première version), environ 24 sessions.

Notés pour plus tard : règle `events: aucun` avec un `event_plan` dans `GameParams` (architecte) ; `numbers()` lit « 62.7054 » comme 62705 (T6) ; J10 sort en industrie si le secteur n'est que dans le texte du brief (le formateur peut l'imposer).

Cadre de la démo : LAN, 3 à 6 joueurs ; le jeu à distance vient après la Première version.

| # | Chantier | Références |
|---|---|---|
| 1 | B4b fait et poussé (06/11) ; palette « ardoise » par défaut, commitée et poussée | ADR 0012 ; EX-08 |
| 2 | **Préparée le 18/11, commitée et poussée (c218212, push 7c99529..c218212 ; `backend/p.out` supprimé, dépôt propre ; rétro du 18/11 faite, `retro-2026-11-18.md`)** : parcours B de flow_test (`-Flow -NoLlm` 686 vérifications, `-Flow` 813), `test_lobbies_absent_vote.py` (`test.ps1 -Integration` : 829 passés), export `godot.ps1 -Export` (`build/windows/G-mix.exe`, connexion depuis l'exe non essayée à la main). **Reste la répétition réelle** : pare-feu à ouvrir le jour même (TCP 8000, UDP 7000-7049, profil Privé), 3 postes, souris et clavier AZERTY réels, fermer les applications lourdes sur l'hôte (le poste était à 100 % CPU à cause du client Riot) ; le test de budget mesure désormais un rapport à une boucle de référence, robuste à la charge, et ne détecte plus qu'une régression d'environ 2x ; date à fixer par l'utilisateur ([fiche pas à pas](../repetition-lan.md)) | EX-05 (LAN), 22, 23, 25 |
| 3 | **Clos le 21/11, = T0 de l'ADR 0013** : exigence n° 1 : troisième tour sans échec, 3 jeux signés (J05, J08, J09), 7 repris en T9 ; reste D17, D8, `trs_oee`, notion `rupture_de_stock` | ADR 0010 ; EX-01, EX-16 ; docs/audits/ |
| 3b | **ADR 0013 accepté le 21/11** (mondes et jeux variés, second domaine, documents du formateur) : l'ordre des chantiers après T0 est celui de la § 5 de l'ADR (T2 à T11, environ 25 sessions) ; le garde-fou des nombres (ligne 4) devient T6, la dette de l'annexe 0010 (ligne 5), la passe `-Tour` (ligne 6) et la Première version (ligne 7) deviennent T10 et T11 | docs/decisions/0013 ; docs/blocages.md |
| 4 | Garde-fou des nombres de `npc.py` : **fait le 27/11 (T6)** | EX-33 |
| 5 | Dette « À corriger » de l'annexe 0010 (T10) | ADR 0010 annexe |
| 6 | Passe finale `-Tour` (T10) | EX-34 ; ADR 0012 c2 |
| 7 | Docs, puis **Première version** (T11) : commit et push de chaque tranche (`git push`), LICENSE.md non commercial inclus | décision du 06/11 |

Après la Première version : mode construction (B4c c1), EX-14, 19, 29 (page F5 complète), 36, EX-05 à distance. EX-12 (documents du formateur) passe avant la Première version (T8, ADR 0013).

## Hors G-mix

Le dépôt public `claude-skills-and-team-for-every-project` est poussé (`C:\_Documents-Romain\claude-skills-and-team-for-every-project`, main 7215cd7..f3fc3ff, commits en adresse noreply).

## Règles de coût (appliquées dans CLAUDE.md et orchestrateur.md le 05/11)

Un chantier = une session · une mission = un livrable, nouvel agent après 60 tours ou une pause · fichier de plus de
300 lignes lu par plages, jamais relu sans modification · une capture lue une fois · comptes rendus de 15 lignes au
plus · ne pas relancer `stop.ps1` ni `docker compose down`.
