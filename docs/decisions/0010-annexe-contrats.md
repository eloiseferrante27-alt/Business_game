# 0010, annexe : contrats des étapes 4 à 7

Statut : accepté (05/11) ; relu contre le code livré aux étapes 4 à 6 le 05/11 : écarts acceptés ou à corriger au
§12, qui prime sur le reste du texte. Complète l'[ADR 0010](0010-refonte-alignee-business-game.md) (étape 3 du §6).
Sans redite de l'[annexe 0008](0008-annexe-contrat-conception.md), qui reste le contrat de la conception par l'IA
(sauf sa livraison réduite sur l'usine, notée en tête de son §5).

Règles communes :
- Les droits sont vérifiés par l'API : `_access` (404 pour un non-membre), `_require_manager` (403), et
  `GameRuleError` devient 409. Godot ne fait que griser.
- Toute règle de jeu est une fonction pure de `gmix.game.engine` (ou de `factory_game`), avec ses tests. Aucun
  texte de cette annexe n'appelle un modèle.
- **Kafka : aucun topic nouveau, `topics.py` ne change pas.** Les événements de partie vont sur `GAME_EVENTS` (clé
  `lobby_id`, enveloppe `Envelope` actuelle). La conception utilise `GENERATION_*`, qui existent déjà.
- Les ajouts à `spec.py` listés ici sont **délégués à moteur-jeu à l'étape 4**, qui travaille déjà dans
  `backend/gmix/game/`. Ils sont tous facultatifs, avec une valeur par défaut, et `version` reste 2.

## 1. Mode d'avancée, « prêt », pause, forçage, aléa du formateur (backend-api ; moteur-jeu pour le moteur)

**Stockage** : dans `lobbies.settings`, une colonne JSONB qui existe déjà. Pas de migration.
```
settings = {"advance_mode": "auto" | "manual", "paused": bool,
            "ready": {"week": int, "users": [user_id str],
                      "ballots": {user_id str: "ignore" | "wait"}}}   # vote sur les absents (05/11)
```
`ready.week` différent de `state.week` signifie que personne n'est prêt et qu'aucun bulletin n'existe. Une avance
remet donc l'appel et le vote à zéro sans écriture de plus.

**Vue** : `_view` et `lobby.round` ajoutent `round` :
```
round = {advance_mode, paused, week, ready: [user_id], expected: [user_id], ready_count: int, expected_count: int,
         connected: [user_id], absent: [user_id],
         vote: {open: bool, voters: int, ignore: int, wait: int, ballots: {user_id: choice},
                decision: "ignore" | "wait" | None}}
```
- `expected` est la liste des membres qui ont un `game_role`. Le formateur n'y figure pas, sauf s'il a pris un rôle.
- `connected` regroupe les attendus qui ont une session WebSocket abonnée au lobby :
  `WebSocketHub.watchers(lobby_id) -> set[str]` (`api/ws.py`, backend-api).
  - shortcut : le hub est en mémoire, ce qui suppose un seul processus d'API. À revoir avec plusieurs workers
    uvicorn.
- `absent` regroupe les attendus non connectés.

**Absents : vote des connectés** (décision de l'utilisateur, 05/11, backend-api) :
- Le vote s'ouvre (`vote.open`) en mode `auto`, hors pause, quand tous les connectés sont prêts et qu'il reste au
  moins un absent. Les absents sont recalculés à chaque appel de `/ready` et de la vue.
- Les votants sont les connectés attendus (`voters`). Chacun vote avec `POST /ready {ready: true, absent: "ignore" | "wait"}`
  et peut changer son bulletin tant que la décision n'est pas prise. Un bulletin qui arrive sans vote ouvert donne
  409.
- Règle de décision, évaluée à chaque bulletin :
  - `ignore` l'emporte dès que `ignore > voters / 2` : l'avance part aussitôt (même transaction) ;
  - `wait` l'emporte dès que `wait >= voters / 2` : **l'égalité vaut « attendre »**, on ne joue pas à la place d'un
    joueur sans majorité.
- Le département ignoré passe en pilote automatique pour la semaine. L'API appelle
  `engine.advance(held_roles = rôles tenus - rôles des absents)` ; aucun changement de moteur n'est nécessaire.
  - Une décision que l'absent a déjà prise dans la semaine (entrée `decision` au journal) est gardée.
  - La semaine suivante, l'absent redevient attendu.
- Après « attendre », rien n'avance tant que l'absent n'est pas revenu et prêt. Son retour ferme le vote : l'appel
  normal reprend.
- Le formateur garde la main : `POST /advance {ignore_absent: bool = false}` force l'avance, quel que soit le vote.
  - `true` : les modules des absents passent en pilote automatique, comme après « ignorer ».
  - `false` : comportement actuel ; leurs réglages restent ceux de la semaine passée.

| Route | Droits | Effet | Réponses |
|---|---|---|---|
| `POST /api/v1/lobbies` | Staff + `owned_game` | `LobbyCreate` reçoit `advance_mode: Literal["auto","manual"] = "auto"`, écrit dans `settings` | 201 ; 409 si le jeu n'est pas `ready` ; 422 |
| `POST /api/v1/lobbies/{id}/ready` `{ready: bool, absent: "ignore" \| "wait" \| null = null}` | membre avec un rôle | ajoute ou retire l'utilisateur de `ready.users`, sous verrou de ligne ; `absent` dépose ou change un bulletin. Si `advance_mode == "auto"`, que la partie n'est pas en pause, que `expected` n'est pas vide et que tous les attendus sont prêts, ou que le vote décide « ignorer » : avance dans la même transaction (voir plus bas) | 200 `{round, state}` ; 404 pour un non-membre ; 409 si la partie n'est pas `running`, si le membre n'a pas de rôle, ou s'il vote sans vote ouvert ou sans être connecté ; 422 pour un choix inconnu ou un bulletin avec `ready: false`. Idempotent |
| `POST /api/v1/lobbies/{id}/pause` `{paused: bool}` | Staff + gestionnaire | met `settings.paused` à jour | 200 `{round}` ; 403 ; 404 ; 409 si la partie n'est pas `running` |
| `POST /api/v1/lobbies/{id}/advance` `{ignore_absent: bool = false}` (corps facultatif) | Staff + gestionnaire | c'est le **forçage**, valable aussi en pause, en mode `manual` et contre le vote | inchangées |
| `POST /api/v1/lobbies/{id}/event` `{event_id}` | Staff + gestionnaire | `engine.force_event` : l'aléa remplace celui qui est annoncé et s'applique à la prochaine avance | 200 `{state}` ; 403 ; 404 ; 409 si la partie n'est pas `running` ; 422 si `event_id` n'est pas dans `spec.events` |

**Avance** : `/advance` et la fin d'appel passent par une seule fonction `_advance(lobby, user, auto: bool)`. Elle
reprend le corps actuel de `/advance` (chronologie, `CLOSED`, arrêt du serveur de partie) et appelle
`engine.advance(spec, state, held_roles=<rôles tenus>)`.

**Moteur** (moteur-jeu) :
- `advance(spec, state, *, autopilot_all=False, held_roles: set[str] | None = None)`. Avec `None`, rien ne change
  (tests et pilote automatique). Sinon, les modules joués sont ceux des rôles tenus et ceux qui ont au moins une
  entrée `kind="decision"` dans le journal de la semaine. Les autres passent en pilote automatique. Le pack
  atelier suit la même règle avec son ensemble `active`.
  - Décision du 05/11 : quand le formateur agit sur un module libre, ce module quitte le pilote automatique pour la
    semaine. Il le retrouve la semaine suivante, puisque le journal de cette semaine-là ne porte plus d'entrée.
    Un test le garde.
- `force_event(spec, state, event_id) -> state`. Elle écrit au journal une entrée `kind="alea"`, `by="formateur"`.

**Événements sur `GAME_EVENTS`** :
- `lobby.round {round}`, à chaque « prêt », bulletin ou pause qui ne déclenche pas d'avance. `round.vote` porte le
  vote. Pas d'événement à la déconnexion : la vue suivante recalcule `absent`.
- `lobby.state`, dont l'action prend un type parmi `start`, `advance`, `action`, `event`, comme aujourd'hui. Pour
  `advance`, l'action ajoute `auto: bool`, `ready: "k/n"` et `ignored: [role_id]` (vide sans absent ignoré).

**Invariants** :
- Une semaine n'avance qu'une fois, grâce au verrou de ligne ; deux « prêt » simultanés n'avancent pas deux fois.
- L'appel « prêt » ne survit pas à une avance.
- Un joueur n'avance jamais seul la partie en mode `manual`.
- Un absent n'est ignoré que par une majorité stricte des connectés ou par le formateur.

## 2. `state.alerts[]` (moteur-jeu ; seuils : game-designer)

`public_state` ajoute la racine `alerts`, et `PUBLIC_ROOTS` reçoit `"alerts"` (le test d'égalité reste valable).
Le calcul est pur, à partir de l'état courant. Une liste vide reste présente.
```
alerts[] = {id: str,                     # stable d'un appel à l'autre : "reorder:c1", "breakdown:l2.m3", "late:o12"
            level: "info" | "warning" | "critical",
            department_id: Code | None,   # page de la tablette qui l'affiche
            module_id: str | None,        # module qui peut agir
            text: str,                    # français, chiffres du moteur, modèle de texte du pack, <= 120 car.
            ref: str | None,              # clé visuelle 3D (stock:c1, line:l2), pour la surbrillance
            action: {module_id, action_id, values} | None}   # bouton « Commander » prérempli (valeurs validées par _validate)
```
- Ordre : `critical`, puis `warning`, puis `info`. Huit alertes au plus.
- Alertes de la tranche 1 (pack usine) :
  - point de commande atteint (position matière inférieure ou égale au point de commande) ;
  - arrêt d'une ligne faute de matière lors de la dernière semaine ;
  - machine en panne ou usure au-dessus du seuil ;
  - commande en retard ;
  - trésorerie négative ;
  - aléa annoncé pour la semaine qui vient.
- game-designer : bloc `alerts:` du pack, avec les seuils, les modèles de texte et la provenance de chaque seuil.
  - Format livré (accepté, §12) : liste `{id, level, department_id, module_id, when, text, action?, threshold?,
    status, citation | note}`. `text` est un gabarit à `{clés}` de la vue ; `when` et `action` décrivent le
    déclencheur et le bouton, que le moteur code (le pack ne s'exécute pas). Une alerte absente du pack n'est pas
    émise.
  - Usine : pas d'alerte d'usure (aucun seuil sourcé) ; à la place, `trs_low` (TRS de la semaine passée sous 73 %).
  - `ref` livrés : `mp:c1`, `machine:<id>`, `line:<id>`, `component:<id>`, `dock`.

## 3. Critères de réussite, partie de référence, valeurs non sourcées (moteur-jeu ; marges : game-designer)

`spec.py` :
```python
class Criterion(BaseModel):
    id: str                       # dans INDICATORS[moteur], sauf good_share (pas d'objectif)
    label: str
    op: Literal[">=", "<="]
    target: float                 # = targets.* (cash : targets.cash_final)
    partial: float | None = None  # seuil du « partiel » ; None : atteint ou non
SimSpec.criteria: list[Criterion] = []   # vide (anciens jeux) : dérivé de targets, sans partiel
```
- La génération remplit les critères à partir de `targets` et du bloc `criteria:` du pack (marge du partiel par
  difficulté, avec provenance).
  - Format livré (accepté, §12) : `{id, margin: {decouverte, equilibre, expert}}` (même unité que la cible ;
    `partial = target ∓ margin`) ou `{id, partial_share}` (part de la cible, pour `cash`), lu par
    `generation.apply_rules`. Un pack sans bloc `criteria:` (l'atelier, `ai/simulation.yaml`) n'a pas de partiel.
- `debrief` ajoute :
  ```
  criteria[] = {id, label, unit, op, target, partial, final,
                verdict: "atteint" | "partiel" | "non_atteint" | "sans_objet",
                worst_week: int | None, event: str | None}
  ```
  - `final` se calcule comme `kpis[].final`.
  - `worst_week` est la semaine la plus défavorable. `event` est le titre de l'aléa de cette semaine, ce qui donne
    « partiel (S3 : panne L2) ».
- `kpis[]` (avec `met`) reste, pour la compatibilité.
- **Partie de référence (F3)** :
  - `autopilot_check(spec)` ajoute `criteria: [{id, final, verdict}]` et `playable: bool` (aucun critère
    `non_atteint`). Le résultat est rangé, comme aujourd'hui, dans `business_games.review.autopilot`.
  - Godot affiche « OTIF 96 %, TRS 91 %, 0 rupture : jouable ».
  - Le `review.verdict` de l'annexe 0008 (calage) reste réservé aux jeux conçus.
- **Valeurs non sourcées** : la fonction pure `generation.unsourced(spec)` rend
  `[{key, status: "calibre"|"exemple", note}]`.
  - Elle lit `spec.provenance`, dont les entrées ont un `status` différent de `source`.
  - La génération copie la provenance des `placement_rules` du pack sous la clé `placement_rules.<id>`.
  - L'API range le résultat dans `review.unsourced`, au même endroit que `autopilot` (`games.py`, `_store`).
  - Le débrief l'expose aussi : `debrief.unsourced`.

## 4. Causes au journal, pour le débrief (moteur-jeu)

Chaque entrée de `state.log` reçoit `kind` et `ref` :
```
log[] = {week, kind: "decision" | "auto" | "alea", module: str | None, action: str | None,
         user_id: str | None, name: str | None, by: "joueur" | "formateur" | "moteur", summary: str, ref: str | None}
```
- `decision` : `act`, comme aujourd'hui. `by` vaut `formateur` si `manager` est vrai et que l'acteur n'a pas le
  rôle du module.
- `auto` : `advance` écrit une entrée par module en pilote automatique, avec le résumé de la règle appliquée.
- `alea` : l'aléa appliqué à l'avance (`by="moteur"`, ou `"formateur"` s'il vient de `force_event`) ;
  `ref = event_id`.

Les anciennes entrées, sans `kind`, se lisent comme des `decision`. `debrief.log` est déjà complet : Godot sépare
« vos décisions » (`decision`) de « ce que le hasard a imposé » (`alea`). Pas de nouvelle racine.

## 5. Droits par département (moteur-jeu, backend-api)

- `spec.py` : `Role.department_id: Code | None = None`. La génération y met le département de la première station
  du module (`Station.department_id`). Le validateur vérifie qu'il est dans `spec.departments`.
- Règle de `engine.act`, qui remplace « un rôle libre laisse le module à tous » :
  - un non-gestionnaire n'agit que sur le module de **son** rôle (`actor.role == module.role_id`). Sinon, 409
    « Cette action revient au rôle « X » », ou « Choisissez un rôle » s'il n'en a pas ;
  - le gestionnaire agit partout. Un module libre tourne en pilote automatique (§1), sauf la semaine où le formateur
    y a agi.
- Un réglage (`state.settings`) ne change que par une action. Le droit sur un réglage est donc celui de l'action de
  son module. Aucun champ de plus.
- Godot :
  - la page de `my_role.department_id` est active ;
  - les autres pages sont en lecture seule ;
  - les boutons d'alerte (`alerts[].action`) sont grisés si le module n'est pas le mien.

| Opération | joueur (membre) | formateur du lobby | autre formateur | admin |
|---|---|---|---|---|
| voir le lobby, la vue, le débrief en fin de partie | oui | oui | 404 | oui |
| `ready` | oui, s'il a un rôle | oui, s'il a un rôle | 404 | oui, s'il a un rôle |
| `actions` sur son module | oui | oui (tous) | 404 | oui (tous) |
| `actions` sur un autre module | 409 | oui | 404 | oui |
| `pause`, `advance`, `event`, `start` | 403 | oui | 404 | oui |
| `/games/designs` et routes de jeu | 403 | ses jeux | 404 | tous |

## 6. Règles à cocher (J1) (moteur-jeu ; textes : game-designer)

- `spec.py` : `GameRule{id: Code, text: str (<= 200), citation: str | None}` et `SimSpec.game_rules: list[GameRule] = []`.
  - Les textes sont des gabarits du pack (`game_rules:`), complétés par la génération avec les valeurs de la spec.
  - Exemple : « Une commande en retard de plus de N semaines est annulée », où N est le chiffre du moteur.
  - Une règle sans mécanique dans le moteur n'est pas publiée.
  - Décision du 05/11 : l'annulation d'une commande après N semaines de retard est reportée. Sa règle n'est donc pas
    publiée en v1, et la tranche 1 n'ajoute pas cette mécanique au moteur.
- Godot affiche les cases et bloque « Entrer dans l'usine » tant que tout n'est pas coché.
- **Reporté : l'enregistrement serveur des cases.** C'est un accusé de lecture, pas un droit. Rien ne dépend de lui
  côté API.

## 7. Conception par l'IA, `/games/designs` (annexe 0008 §1 et §3 à §6, inchangée sauf ce qui suit)

- **Usine seulement** (décision 3 du §7) :
  - `POST /designs` renvoie 422 `{message: "La conception par l'IA ne concerne que l'usine", missing: []}` si
    `pack != "usine"`. L'admin n'y fait pas exception.
  - « Générer sans IA » reste `POST /games`, valable pour tous les packs.
- Correspondance de F1 vers `DesignRequest` :

  | Champ F1 | Champ de `DesignRequest` |
  |---|---|
  | « Décrivez votre jeu » | `brief` (20 à 2 000 caractères, texte libre) |
  | Secteur | `fixed.theme` |
  | Durée | `fixed.weeks` |
  | Joueurs | `players_min` et `players_max` |
  | Niveau | `fixed.difficulty` |
  | Options avancées | `fixed.modules`, `events`, `products` |

  Godot n'envoie que les champs que le formateur a touchés.
- Statuts du jeu : `generating`, puis `draft` (succès ou repli), puis `ready` (`publish`) ; ou bien `failed` (erreur
  d'infrastructure, sans spec).
- **Livré en v0 (accepté, §12)** : un seul appel de la tâche `factory.design` (`gmix.llm.factory_design`) qui rend
  des `GameParams` du pack usine, puis `generate` ; pas de sections concept, cast ni journey, ni de `relax`.
  - Étapes : `brief` 5, `concept` 10, `simulation` 40, `checks` 90, `done` 100 ; `attempt` vaut 1.
  - `generation.failed.stage` ∈ {`design`, `interrupted`} ; `generation.completed` = `{job_id, game_id, title,
    fallback, unmet, attempts, duration_ms, tokens}`.
  - `review` = `{autopilot, unsourced, fallback, reasons, unmet, attempts}` (pas de `verdict`, `warnings` ni
    `repairs`).
  - Réparations : 2 au plus, puis repli sur les paramètres par défaut du pack (`fallback: true`).
  - Les puces ci-dessous sur les sections et `relax` restent la cible de l'annexe 0008, non livrée.
- Le statut du job et l'étape de progression suivent l'annexe 0008 §5.
- Réparations : 2 par section au plus, puis repli déterministe :
  - concept : `design.fallback` et `review.fallback = true` ;
  - cast : squelette ;
  - journey : défauts du pack.
- `relax` est appelé 4 fois au plus. Le repli est aussi pris si Ollama est absent ou si le job dépasse 600 s : le
  job réussit quand même.
- F1 « Annuler » : **reporté**. Aucune route d'annulation dans l'annexe 0008. Le job va à son terme ou se replie à
  600 s, et Godot cache la barre.
- VRAM : une conception décharge le modèle de dialogue (ADR 0008, question 2). Le 409 « séance en cours » de
  l'annexe 0008 §6 s'applique.

## 8. Règle de placement `protected_path` (moteur-jeu ; règles du pack : game-designer ; barrière : assets-3d)

`spec.py` :
- `RULE_KINDS` reçoit `"protected_path"` ;
- `needs["protected_path"] = ("a", "b", "barrier", "crossings_max", "one_way")` ;
- `a` et `b` sont des blocs, des départements, des clés de `network.sites` ou `usine` (accepté, §12) ; `barrier` et
  `one_way` sont des `bool` ;
- `crossings_max` est un `int` supérieur ou égal à 0 ;
- `ElementRole` reçoit `"barriere"`.

`layout.py`, `check_placement` :
- Le chemin de a à b est la polyligne du `Link` qui relie a à b, s'il y en a un. Sinon, c'est le tronçon de
  `world.forklift_route` entre les points les plus proches de a et de b. Sans chemin, le message est
  « règle <id> : aucune circulation entre a et b. »
- `crossings_max` : on compte les intersections du chemin avec les autres liens et tronçons de `forklift_route`,
  hors extrémités communes. Au-delà de `crossings_max`, le message est
  « règle <id> : le chemin a -> b croise k fois une autre circulation, n au plus. »
- `one_way` : aucun lien de b vers a ne doit partager un segment avec le chemin. Sinon, le message est
  « règle <id> : le chemin a -> b est à double sens. »
- `barrier` : tout objet de rôle `poste` situé à moins de `PROTECT_M` du chemin doit avoir un objet de rôle
  `barriere` dans cette bande. Sinon, le message est « règle <id> : « <label> » à x m du chemin a -> b, sans
  barrière. »
  - `PROTECT_M = 1.5` est une constante de layout.py, de statut `calibre`. Sa note est relue par game-designer.
- Le placeur pose les barrières le long des chemins qui ont `barrier: true`. Une barrière n'est pas éditable : elle
  n'est pas dans `EDITABLE_ROLES`.

Règles du pack (game-designer, INRS ED 6350 relue à la source le 05/11 ; paires `a`/`b` proposées, game-designer
les fixe) :
- voie PL (`fournisseur` -> `reception`, `entrepot_pf` -> `client`) : `one_way: true` (§ 4.1 p. 10),
  `crossings_max: 1` (« croise une seule fois », § 4.1 p. 11) ;
- transbordement : `crossings_max: 0` (aucune allée chariot, § 4.4 p. 15) ;
- flux chariots `stock_mp` -> `production` et `entrepot_pf` -> quai : `barrier: true`.
  - « matérialisé au sol », « barrières, glissières ou bastaings » (§ 4.4 p. 14).
  - Cela couvre aussi la règle voisine : emballage et contrôle « séparés des flux chariots par des protections
    fixées au sol » (§ 4.4 p. 15). Il n'y a donc pas de septième type à créer.

assets-3d : `prop_safety_barrier` (procédural, un module de 1 m, statut et licence au catalogue), dans
`ai/assets.yaml` et `godot/assets/`.

## 9. Besoins Godot : contrat ou report

| Besoin | Contrat |
|---|---|
| « Prêt » par joueur, avance automatique | §1 : `round`, `POST /ready`, `lobby.round` |
| Vote sur un joueur déconnecté | §1 « Absents » : `round.vote`, `POST /ready {absent}`, `/advance {ignore_absent}` |
| Mode d'avancée à la création (F4) | §1 : `LobbyCreate.advance_mode` |
| Pause, forcer l'avance, déclencher un aléa (F5) | §1 : `/pause`, `/advance`, `/event` |
| `state.alerts[]` | §2 |
| `/games/designs` avec brief libre | §7 ; « Annuler » reporté |
| Règles à cocher | §6 ; enregistrement serveur reporté |
| Partie de référence et valeurs non sourcées (F3) | §3 : `review.autopilot.{criteria, playable}`, `review.unsourced` |
| Droits par département (J2) | §5 |
| Débrief : critères, causes (J3) | §3 et §4 |
| Comparer aux autres sessions du même jeu | **reporté** : tranche 2 (ADR 0010 §5) |
| Minuteur de semaine | **reporté** : non demandé (décision 2 du §7 : prêt ou forçage) |

## 10. Ordre et propriétaires

| # | Agent | Fichiers | Critère de fin | Parallèle |
|---|---|---|---|---|
| 4a | moteur-jeu | `game/spec.py` (`criteria`, `game_rules`, `Role.department_id`, `alerts` dans `PUBLIC_ROOTS`, `protected_path`, `barriere`) | `test.ps1 -Fast` vert, packs actuels toujours chargés | d'abord |
| 4b | moteur-jeu | `engine.py`, `factory_game.py`, `factory_generation.py`, `generation.py`, `layout.py`, tests | §1 (moteur), §2 à §6, §8 testés : avance avec `held_roles`, `force_event`, verdict partiel, `unsourced`, refus hors département, trois messages `protected_path` | après 4a |
| 4c | game-designer | `ai/packs/usine.yaml` | blocs `alerts`, `criteria`, `game_rules` et règles `protected_path`, tous avec provenance ; `load_pack` passe | après 4a, en parallèle de 4b |
| 4d | assets-3d | `ai/assets.yaml`, `godot/assets/` | `prop_safety_barrier` au catalogue ; `assets.ps1` passe | dès maintenant |
| 5 | backend-api | `api/routes/lobbies.py`, `games.py`, `api/ws.py` (`watchers`), tests d'API | §1 (dont le vote sur les absents : majorité, égalité, `ignore_absent`), §3 (rangement de la revue), §5 (matrice testée pour les 3 rôles), §7 (422 hors usine, puis annexe 0008 §6) | en parallèle de 4b, branché sur ses signatures ; tests verts après 4b |
| 6 | ia-runtime, puis pipeline-kafka | `ai/models.yaml`, prompts, evals ; `workers/generation.py` | annexe 0008 §4, §5 et §8 sur l'usine | en parallèle de 4 et 5 |
| 7 | godot-dev | `godot/scenes/` (main, lobby, tablet, world/hud.gd, tools) | §9 couvert ; `-Flow -Design` avec et sans `-NoLlm`, et `-Tour`, verts | après 5 et 6 |
| 8 | documentaliste | `docs/kafka.md` (`lobby.round`, actions), `docs/roles.md` (matrice du §5), `docs/game-design.md` | docs alignées sur cette annexe | après 7 |
| 9 | qa-reviewer | tests manquants | `test.ps1 -Integration`, `smoke.ps1`, `-Flow -Design` verts | fin |

Fichiers disjoints : 4b, 4c et 4d peuvent tourner ensemble, et 5 tourne avec 6. `spec.py` est touché une seule fois,
à l'étape 4a.

## 11. Décisions de l'utilisateur (05/11)

1. **Joueur déconnecté** : les connectés votent « ignorer » ou « attendre ». La majorité stricte fait ignorer,
   l'égalité fait attendre. Le département ignoré passe en pilote automatique pour la semaine, et le formateur peut
   toujours forcer (§1, « Absents »).
2. **Module libre** : quand le formateur y agit, le pilote automatique de ce module s'arrête pour la semaine, puis
   reprend la suivante (§1, « Moteur »).
3. **Annulation après N semaines de retard** : reportée. Sa règle à cocher n'est pas publiée en v1 (§6).

## 12. Écarts de livraison des étapes 4 à 6 (relecture du 05/11)

Ce paragraphe prime sur le reste de l'annexe. « Accepté » : le code fait foi, le texte ci-dessus est aligné.

**Acceptés**
- `Factory.pf_max` (`int | None`, ≥ 0) et `Factory.mp_safety_days` (`float`, défaut 1) : réglages de pack dans
  `spec.py`, sans effet sur les contrats d'API.
- `protected_path` : `a` et `b` acceptent les clés de `network.sites` et `usine` (§8), nécessaires à la voie PL.
- Moteur : `advance(spec, state, *, autopilot_all=False, held_roles=None)` ; `generation.unsourced` et
  `generation.apply_rules` ; `autopilot_check` avec `criteria` et `playable` ; journal public (`recent_log`) sans les
  entrées `auto` (le débrief les garde) ; alertes lues dans le pack, triées par niveau, 8 au plus (§2).
- API : `/ready` renvoie `{round, state}` ; 422 sur un bulletin `absent` avec `ready: false` ; 409 si aucun vote
  n'est ouvert ou si le votant n'est pas connecté (§1) ; structure de `round.vote` ; migration `7c2e9a4b1d58`
  (`generation_jobs.request` JSONB, aller-retour).
- Conception : livraison v0 en un appel `factory.design` (§7) ; pas de `DELETE /games/{id}` ni d'annulation
  (reportés).
- Pack usine : `criteria` en `margin` / `partial_share` (§3) ; `alerts` en liste (§2).

**À corriger** (propriétaire)
- moteur-jeu :
  - `spec.py` `_check_world_keys` : `sites` n'est défini que si `network` existe (NameError sur une règle
    `protected_path` sans réseau) ;
  - `_check_pack` ne valide pas les blocs `alerts` et `criteria` du pack (ids, niveaux, marges) ;
  - `engine.common_alerts` écrit `cash_negative` et `event` en dur : lire le gabarit du pack, comme `factory_game` ;
  - `factory_game._alerts` : `out[-1]["text"] = …` modifie l'alerte précédente quand `breakdown` est absent du pack ;
  - `act(occupied_roles=…)` est inutilisé : à retirer après backend-api.
- game-designer (`ai/packs/usine.yaml`) :
  - `breakdown.level` est de la prose (« critical si … ») : un niveau fixe, ou deux entrées avec `when` distincts ;
  - notes périmées (`criteria` « à implémenter », `trs_low` « à ajouter par moteur-jeu », alertes « en dur ») ;
  - règles `protected_path` de la voie PL (`one_way`, `crossings_max: 1`) et du transbordement (`crossings_max: 0`)
    du §8 : à ajouter, ou à justifier par écrit ; seule `postes_proteges_chariots` existe.
- backend-api (`games.py`, `lobbies.py`) :
  - `_store` réécrit `review` à `publish`, `/params` et `/layout`, et efface `fallback`, `reasons`, `unmet` et
    `attempts` : fusionner au lieu d'écraser ;
  - `getattr` devenu inutile autour de `unsourced` ;
  - retirer le passage de `occupied_roles` ;
  - 409 « séance en cours » de l'annexe 0008 §6 : non codé ; sans effet en pratique tant que `factory.design` et
    `npc.dialogue` servent le même modèle (`small`), à coder avant tout changement de modèle.
- ia-runtime puis pipeline-kafka (`factory_design.py`, `workers/generation.py`) :
  - `DesignRequest.fixed` et `players_min/max` sont ignorés : `fixed` prime sur le modèle et ses champs sortent du
    schéma demandé ;
  - pas de borne de 600 s : au-delà, repli sur les défauts du pack et job réussi (§7).
- documentaliste : `docs/kafka.md`, charges utiles `generation.*` de la livraison v0 (§7).

**Décision sur `playable` en expert** (graines vues à False : atelier 5, usine 7)
- `playable` reste informatif. Il ne bloque ni `publish` ni la revue F3, et aucune règle de calage n'est ajoutée :
  en expert, le pilote automatique (règles simples) n'a pas à atteindre les cibles ; c'est le joueur qui doit faire
  mieux.
- Godot : en expert, « exigeant : le pilote automatique manque <critères non_atteint> » ; ailleurs, « à revoir ».
- moteur-jeu ajoute un test : `playable` vrai en `decouverte` et `equilibre`, graines 5 à 8, atelier et usine. S'il
  échoue, moteur-jeu le signale à l'architecte au lieu de recaler les chiffres (game-designer décide).

**Risques ouverts**
- Le décompte des connectés (`hub.watchers`) suppose un seul processus d'API (hub en mémoire) : plusieurs workers
  uvicorn fausseraient `round` et le vote. Passage à plusieurs processus = nouvel ADR (présence partagée).
- Conception v0 sans `verdict` de calage : un jeu conçu peut être publié sans contrôle de difficulté autre que
  `playable` (informatif).
