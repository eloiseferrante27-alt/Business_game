# 0012 : tranche B4, régénération par section de l'usine, débrief J3 en courbes, découpage B4a/B4b/B4c

Date : 2026-11-06. Statut : **accepté** (décisions de l'utilisateur du 06/11, en fin de document). Complète l'[ADR 0010](0010-refonte-alignee-business-game.md) §4 (F2, F3, J3)
et §6 étape 7, l'[annexe 0010](0010-annexe-contrats.md) §3, §4, §7 et §12, l'[ADR 0011](0011-groupes-d-equipes-et-connexions.md) §2.
Exigences : EX-08, EX-30 (reste), EX-31, EX-32 (courbes), EX-34.

## Contexte

- **Conception v0** (annexe 0010 §7, §12) : un seul appel `factory.design` rend des `GameParams`. Il n'y a ni section
  concept, cast ni journey, donc rien à « régénérer par section » au sens de l'annexe 0008. Le worker ignore
  `DesignRequest.fixed` et `players_min/max` (écart « à corriger » du §12).
- **F2 existe en partie** : `home_screen.gd` affiche les étapes et la barre en interrogeant `GET /games/{id}/job`
  toutes les 2 s. Il manque les champs de F1 (secteur, durée, joueurs, niveau, options), le temps écoulé et la
  progression dans la liste des jeux.
- **F3 n'existe pas** : la relecture est un texte (`GameText._design_review`). L'API du mode construction existe
  (`PUT /layout`, `PUT /params`, `recompile_layout`), mais pas son côté Godot.
- **J3** : `debrief` contient déjà `history`, `criteria[]` (verdict, `worst_week`, `event`), `events`, `log[]`
  (`kind` : decision, auto, alea), `notions` et `unsourced`. Godot l'affiche en texte (`GameText.debrief_bbcode`) à
  trois endroits : lobby, HUD et groupe. `panel_view.gd` a déjà un `LineChart`.
- **Défaut qui touche la régénération** : `games.py::_store` réécrit `brief` (en un résumé) et `review` à chaque
  `publish`, `/params` ou `/layout`. Après une retouche, le brief du formateur est perdu.

## Options

1. Régénération : (a) refaire toute la conception avec une consigne ; (b) **sections = groupes de clés de
   `GameParams`, les autres clés étant imposées au modèle**, par le mécanisme `fixed` qu'il faut de toute façon
   réparer pour F1 ; (c) livrer les sections concept, cast et journey de l'annexe 0008 (plusieurs appels, un prompt
   par section : une tranche entière à elle seule).
2. Courbes : (a) Godot trace `history[*][id]` ; (b) **le moteur rend, pour chaque critère, sa valeur arrêtée à chaque
   semaine**, calculée comme `final`.

## Décision

**1 (b)** : un seul mécanisme, `keep`, sert à F1 (`fixed`) et à F3. **2 (b)** : avec 2 (a), le client devrait savoir
que les ruptures de l'usine se comparent à une somme, l'OTIF à une moyenne et la trésorerie à une valeur finale. Une
semaine isolée tracée contre une cible de moyenne serait fausse (exigence n° 1). Le client ne calcule rien.

### §1. Régénération par section (contrat, `spec.py` fixé)

`spec.py` : `FactorySection = Literal["entreprise", "objectifs", "personnages"]`, `FACTORY_SECTIONS` (clés de
`GameParams` par section) et `RegenerateRequest {section, note (1 à 300 car.) | None, seed | None}`.

| Section F3 | Clés régénérées | Bouton |
|---|---|---|
| Entreprise | `theme` (`company_name` est gardé : le modèle ne le produit pas, voir Worker) | Régénérer |
| Produits, fournisseurs, rôles | aucune (modules, produits, options, réseau) | Paramètres (`PUT /params`) |
| Objectifs et aléas | `difficulty`, `tunings`, `events`, `event_plan` | Régénérer |
| Personnages | `agent_tone`, `extra_agents` | Régénérer |

**API** (backend-api) : `POST /api/v1/games/{id}/design/regenerate`, corps `RegenerateRequest`.
- Droits `Staff` et `owned_game` : 403 pour un joueur, 404 pour un autre formateur, l'admin a tous les jeux.
- 409 dans ces cas : un job `queued` ou `running` existe pour le demandeur ou pour ce jeu ; le jeu est `generating` ;
  un lobby `running` utilise le jeu (`_editable`) ; le jeu n'a pas été conçu par l'IA (`"attempts"` absent de
  `review`), avec le message « Ce jeu n'a pas été conçu par l'IA : modifiez ses paramètres ».
- Effet : `GenerationJob(kind="regenerate_<section>", request={sections: [section], seed, note})`, avec une graine du
  modèle tirée si elle est absente ; le jeu passe en `generating` ; `generation.requested` est publié avec la charge
  utile inchangée de l'annexe 0008 §5 ; audit `game.design_requested` avec `section`. Réponse 202 `{job_id}`.
- Si la publication échoue : 503, le job est supprimé et le jeu reprend son statut.
- `_store` (correctif) : il **fusionne** `review` (`game.review | nouveau`) et ne réécrit pas `brief` d'un jeu conçu
  (`"attempts" in review`).

**IA** (ia-runtime), signature fixée :
`async def design_factory(llm, brief, *, seed=0, pack_id="usine", keep: dict | None = None, note: str | None = None)`.
- `design_schema(pack, keep)` retire du schéma les clés gardées : `options` retire tous les `option_*`, `network`
  retire `network`.
- Les paramètres valent `{**choix_du_modèle, **keep}` : `keep` l'emporte toujours, y compris dans le repli
  (`{**default_params, **keep}`).
- Le prompt `factory.design` passe à la version suivante. Il reçoit les variables `kept` (les choix gardés,
  « clé : valeur ») et `note` (« aucune » si absente), entre délimiteurs comme le brief. Si `looks_like_injection(note)`,
  la consigne est ignorée et une raison est ajoutée.

**Worker** (pipeline-kafka) :
- Job `design` : `keep = params.fixed | {players_min, players_max}`, lu dans `game.params`, qui est le
  `DesignRequest` rangé par `POST /designs`.
- Job `regenerate_<s>` : `keep` = les `spec.params` du jeu sans les clés de `FACTORY_SECTIONS[s]` **que le schéma de
  `design_schema` produit** (avec `seed`, donc la graine du jeu ne change pas). Une clé de la section absente du
  schéma reste gardée : `company_name` ne change pas quand on régénère « Entreprise » (code du worker, `_keep`, fait
  foi). Le modèle reçoit la graine du job.
- Régénération réussie : `generate`, puis rejeu de `spec.layout_edits` par `recompile_layout`, comme dans
  `update_params`. Les retouches qui ne tiennent plus vont dans `review.dropped`. `review` reçoit `section`.
- Régénération en repli (`fallback`) : **la spec ne change pas**, `review.fallback = true` avec ses raisons, le job
  réussit.
- Dans tous les cas, le jeu repasse en `draft` et `brief` n'est pas touché. Les étapes et les pourcentages de la
  progression restent ceux de l'annexe 0010 §7.

Kafka : aucun topic ni type nouveau (`topics.py` inchangé). Seules les valeurs de `sections` changent pour l'usine.
VRAM : `factory.design` sert le même modèle que `npc.dialogue` (annexe 0010 §12), donc rien n'est déchargé.

### §2. Débrief J3 (contrat, aucun nouveau champ hors `series`)

`debrief.criteria[]` reçoit `series: list[float | None]` (moteur-jeu, dans `engine.criteria_verdicts`, pour les deux
packs) :
- sa longueur est `weeks_played` ;
- l'élément w est la valeur du critère calculée exactement comme `final`, sur les semaines 1 à w : moyenne cumulée
  pour `otif`, `trs` et `good_share`, somme cumulée pour les ruptures de l'usine, valeur de la semaine pour les
  ruptures de l'atelier et pour `cash` ;
- `series[-1] == final` (testé, sur les deux packs et 3 graines).

Godot (godot-dev), même écran pour le joueur, le formateur et l'admin :
- **En-tête** : un verdict par critère, par exemple « partiel (S3 : panne L2) », tiré de `worst_week` et `event`.
- **Courbes** : une par critère (`series`), avec la cible et le seuil partiel en pointillés, et les aléas de
  `events[]` marqués « S3 : titre ». La légende écrit les valeurs : la couleur n'est jamais seule.
- **Causes**, en trois colonnes tirées de `log[].kind` : « Vos décisions » (`decision`, avec `by`), « Pilote
  automatique » (`auto`), « Ce que le hasard a imposé » (`alea`).
- **Bas de page** : notions et leurs sources, `unsourced` (« valeurs non sourcées : n »), « Débrief comparé » si le
  lobby a un groupe.
- **Débrief comparé** (`/groups/{id}/debrief`) : les mêmes courbes, une série par équipe, et la légende donne le
  `final` de chacune.
- `history` reste affiché en tableau. La comparaison entre sessions hors groupe reste reportée (annexe 0010 §9).

### §3. Clic sur une zone du monde (EX-30, Godot seul)

Un clic sur une zone ou un bloc dont la référence est `dept:<id>` (`world.gd::_refs`) ouvre `tablet.open("dept:<id>")`.
Les droits restent ceux de B3, et l'API tranche toujours.

### §4. `-Design` (devops)

`godot.ps1 -Flow -Design [-NoLlm]` :
- démarre le worker `generation` s'il est absent (même règle que `smoke.ps1`) ;
- passe `--only=D --pack=usine`, plus `--no-llm` si `-NoLlm` est demandé ;
- refuse `-Design` sans `-Flow`.

Parcours D de `flow_test.gd` :
- **Sans `--no-llm`** : F1 avec des champs touchés, progression, F3, régénération de « personnages » qui laisse les
  autres clés intactes, publication.
- **Avec `--no-llm`** : un brouillon obtenu par `POST /games` puis `PUT /params`, F3 affiché, « Régénérer » qui
  renvoie 409 avec son message, publication.

## Conséquences

- **Découpage**, une tranche par session :
  - **B4a**, J3, courbes et clic : EX-30, EX-31, EX-32 ;
  - **B4b**, F1/F2/F3 et `-Design` : EX-08 ;
  - **B4c**, mode construction (ADR 0009 points 8, 9 et 12) et passe finale `-Tour` : EX-34. (06/11) Le mode
    construction (c1) passe après la Première version ; seule la passe `-Tour` (c2) reste avant.
- **B4c dépasse probablement une session**, à cause de la grille, du fantôme, de la palette, du rétablissement et du
  menu, dans `world.gd` (1 209 lignes). Si c'est le cas : B4c1 pour la grille, le fantôme, le déplacement et le refus
  422 ; B4c2 pour la palette, le retrait, le rétablissement et le menu.
- L'aperçu 3D de F3 vient avec B4c : en B4b, F3 n'affiche que des cartes.
- La régénération n'existe que pour les jeux conçus. La cible de l'annexe 0008 (concept, cast, journey) reste
  ouverte.
- **À trancher par game-designer** (exigence n° 1) :
  - les textes de `_lessons` (`engine.py`, `factory_game.py`) affirment des contrefactuels que le moteur n'a pas
    calculés, par exemple « commander au point de commande […] les aurait évités ». Il faut les réécrire en faits
    calculés, chacun relié à une notion sourcée ;
  - faut-il une courbe de valeur du stock pour l'usine ? Elle est absente de `history` et demande une valorisation
    des stocks avec sa provenance.

## Plan d'exécution

| # | Agent | Fichiers | Livrable et critère de fin | Dépend de, parallèle |
|---|---|---|---|---|
| a1 | moteur-jeu | `game/engine.py` (`criteria_verdicts` l. 329-361, `debrief` l. 282-317), `factory_game.py` (`debrief` l. 528-555), tests engine et factory | §2 `series` ; `test.ps1 -Fast` vert | — ; en parallèle de a2 et a3 |
| a2 | game-designer | relecture seule (`_lessons` : engine.py l. 801-840, factory_game.py l. 558-589) | textes corrigés et notion de chaque leçon, rendus dans son compte rendu ; avis sur la courbe de stock | — ; en parallèle |
| a3 | godot-dev | `scenes/debrief/` (nouveau), `tablet/panel_view.gd` (`LineChart` : partiel et repères), `lobby/lobby_screen.gd`, `world/hud.gd` (débrief), `group/group_screen.gd`, `world/world.gd` (clic §3), `tools/ui_tour`, `tools/flow_test` | §2 et §3 ; `godot.ps1 -Check`, `-Tour` (0 défaut), `-Flow -NoLlm` vert | travail sur une fixture avec `series`, puis vérification après a1 |
| a4 | moteur-jeu | `_lessons` des deux packs, tests | textes de a2 appliqués ; `test.ps1 -Fast` | après a1 et a2 |
| a5 | qa-reviewer, puis documentaliste | tests manquants ; cahier EX-30/31/32, reprise.md | `test.ps1 -Integration` vert | fin de B4a |
| b1 | ia-runtime | `llm/factory_design.py`, `ai/prompts/factory.design.md`, tests, `tools/eval_factory_design.py` si besoin | §1 IA : les clés gardées ne changent jamais (test), schéma réduit, consigne bornée ; `test.ps1 -Fast` ; `python -m gmix.tools.eval_factory_design` sans régression | — ; en parallèle de b2 et b3 |
| b2 | backend-api | `api/routes/games.py`, tests d'API | §1 API : route, 409, 503, `_store` corrigé, matrice des 3 rôles testée ; `test.ps1 -Fast` | — ; en parallèle |
| b3 | pipeline-kafka | `workers/generation.py`, tests du worker | §1 worker : `keep`, repli sans changement, retouches rejouées ; `test.ps1 -Integration` | tests verts après b1 |
| b4 | godot-dev | `scenes/main/home_screen.gd` (F1 vers `fixed` ; temps écoulé et « n % » reportés, décision 3), `scenes/draft/` (F3, nouveau), `main/main.gd`, `tools/flow_test` (parcours D), `tools/ui_tour` | F3 avec ses quatre sections, Régénérer avec consigne, Paramètres, Publier ; `-Check`, `-Tour` | après b2 ; en parallèle de b5 |
| b5 | devops | `scripts/godot.ps1` | §4 ; `godot.ps1 -Flow -Design -NoLlm` vert après b4 | en parallèle de b4 |
| b6 | qa-reviewer, puis documentaliste | tests ; `docs/kafka.md` (`sections` de l'usine, `regenerate_*`), cahier EX-08, reprise.md | `test.ps1 -Integration`, `smoke.ps1`, `-Flow -Design` avec et sans `-NoLlm` | fin de B4b |
| c1 | godot-dev | `world/world.gd`, `world/sims_view.gd`, `world/hud.gd` (menu en mode construction), `scenes/draft/` (bouton), `tools/*` | ADR 0009 critère 12 : `-Tour` aux 4 tailles, parcours D (déplacer, retirer, annuler, rétablir, refus affiché, publication), 45 images/s | **reporté après la Première version** (décision 2 ci-dessous) |
| c2 | qa-reviewer, puis documentaliste | tests, passe `-Tour` finale (EX-34), docs | `test.ps1 -Integration`, `-Tour`, `-Flow -Design` | fin |

Parallèles : a1, a2 et a3 n'ont aucun fichier commun, de même que b1, b2 et b3, puis b4 et b5. `flow_test.gd` et
`ui_tour.gd` n'ont qu'un seul agent par tranche (godot-dev).

## Décisions de l'utilisateur (06/11)

1. **La régénération repasse le jeu en brouillon** : régénérer une section d'un jeu publié (`ready`) le remet en
   `draft`, à republier (déjà écrit au §1, Worker : « le jeu repasse en `draft` »). Le 409 d'un lobby `running` reste.
2. **c1 (mode construction) est reporté après la Première version.** B4c se réduit à la passe finale `-Tour` (c2,
   EX-34). L'aperçu 3D de F3 part avec c1 : F3 reste en cartes pour la Première version.
3. **B4b en version courte** : le temps écoulé et le « en conception (n %) » de F2 dans la liste des jeux sont
   reportés. b4 livre F1 vers `fixed`, F3 et la progression déjà affichée par `home_screen.gd`.
4. **Ordre jusqu'à la Première version** : B4b court ; répétition en salle en LAN ; exigence n° 1 (10 jeux conçus,
   relus et signés : ADR 0010 §6 étape 8) ; garde-fou des nombres de `npc.py`, activé avant la démo (contrat : ADR
   0007, « Ce qui reste ouvert ») ; dette de l'annexe 0010 §12 ; passe `-Tour` (c2) ; Première version.
5. **Démo en LAN, 3 à 6 joueurs** (ADR 0005 : serveur de partie par lobby). La répétition en salle le vérifie.
