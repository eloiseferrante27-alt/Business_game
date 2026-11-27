# 0013, annexe : contrats (tranche T2)

Statut : accepté (24/11), écrit en T2 de l'[ADR 0013](0013-generation-de-mondes-et-de-jeux-differents.md) ; fait foi
sur l'esquisse de son §3.5. Code : `backend/gmix/game/spec.py`. `topics.py` inchangé.

Règles communes :
- `SimSpec.version` reste 2. **Tout champ ajouté est facultatif** ; sa valeur par défaut redonne le comportement
  actuel. Une spec v2 existante (packs, jeux générés, fixtures) reste valide sans changement.
- Trois niveaux de contrôle : `SimSpec` (références et invariants ci-dessous), `layout.check_placement` (géométrie),
  l'API (droits, validation des passages, publication).
- Un propriétaire de tranche peut ajouter un champ **facultatif** à un modèle de cette annexe sans nouvel ADR, en
  mettant l'annexe à jour dans la même tranche (l'architecte relit). Un champ obligatoire ou un changement de sens
  passe par l'architecte.
- Chaque nombre d'un pack vient de `values` avec sa provenance, et il est repris dans `spec.provenance` (exigence n° 1).
  Un passage d'un document du formateur n'est **jamais** la provenance d'une valeur (`ValueStatus` inchangé).

## 1. Paramètres (`GameParams`, `FIXABLE`)

| Champ | Type, défaut | Contrôle | Produit par | Lu par |
|---|---|---|---|---|
| `suppliers` | `int \| None`, None (1 à 8) | refusé si le pack n'a pas `limits.suppliers` ; dans ses bornes | formateur (`fixed`), `design.concept` | `generate` (T4) |
| `clients` | `int \| None`, None (1 à 4) | idem, `limits.clients` | idem | `generate` (T4) |
| `buildings` | `int \| None`, None (1 à 4) | idem, `limits.buildings` ; égal à `len(world_plan)` si les deux sont donnés | formateur, `design.world` | `place_campus` (T5) |
| `ambiance` | `Code \| None`, None | clé de `pack["ambiances"]` | formateur, `design.world` | `place_campus`, Godot |
| `world_plan` | `list[PlannedBuilding]`, [] (4 au plus) | archétype dans `pack["building_archetypes"]` ; un département dans un seul bâtiment | `design.world` (étape 4) | `place_campus` |

`PlannedBuilding = {archetype: Code, department_ids: list[Code] (1 au moins)}`. None ou vide : défauts actuels
(3 fournisseurs, un par profil ; 1 client ; hall unique en U). `FIXABLE` gagne `buildings`, `suppliers`, `clients`,
`ambiance` (`products` y était). `generate` reste déterministe : mêmes paramètres (plan compris) et même graine, même
spec ; le plan vit dans les paramètres pour qu'une retouche des paramètres (`PUT /games/{id}/params`) rejoue le monde.
`network` (`dict[str, str]`, {} : défauts du pack), site -> classe de distance, est aussi dans `FIXABLE` (merge
b483971) : site de `pack["network"]["sites"]`, classe dans ses `distances` (« réseau : ... »), lu par `layout`.
Bornes de jeu à poser par game-designer (provenance `calibre`, note) : usine `limits.suppliers: [3, 8, 3]`,
`limits.clients: [1, 4, 1]`, `limits.products: [1, 3, 1]` (la zone de production tient 3 lignes au plus, une ligne
par produit), `limits.buildings: [1, 3, 1]` en T5. **Repli (26/11)** : tant que le moteur ne joue qu'un produit et un
client (§3 bis, tranche T4b), le pack usine porte `products: [1, 1, 1]` et `clients: [1, 1, 1]` ; `GameParams` refuse
donc 2 et plus (422 à l'API, jamais 500). Les bornes cibles reviennent avec T4b.

## 2. Monde à plusieurs bâtiments (`Building`, `Room`, `World`, `Department.room_id`)

```python
class Building:  id: "b1".."b4" ; archetype: Code ; label: str (2-40) ; area: Rect ; entrance: Point ; style: Code
class Room:      id: "<bâtiment>.<pièce>" ; building_id ; kind: Code ; label (2-40) ; area: Rect
                 department_ids: list[Code] (1 au moins) ; doors: list[Point] (1 au moins)
class World:     template: "atelier" | "usine" | "campus" ; buildings: [] (4 au plus) ; rooms: [] ; ambiance: None
                 decor: Decor | None = None
class Decor:     seed: int ; items: list[DecorItem] (45 au plus)
class DecorItem: asset: Code ; position: Point (x, z) ; rotation: float (degrés, 0 par défaut)
class Department: room_id: str | None = None
```

Décor (T4) : produit par `layout.place_world` (moteur-jeu), graine dérivée de `spec["seed"]`, avec la taille du hall
(`world.size`, jusqu'à 60 x 42 m ; `Point` sans borne dans `SimSpec`). Éléments `nat_tree`, `nat_tree_oak`,
`nat_tree_pine`, `nat_bush` dans une couronne de 8 m autour de la carte, hors des sites (2 m) et des liens (3 m) ;
ces marges sont garanties par le producteur, `SimSpec` ne vérifie que le format. Consommateur : Godot, qui place
`items` tels quels. `decor` absent ou `items` vide : Godot garde son tirage à graine fixe 42 (specs v2 existantes).

Invariants vérifiés par `SimSpec` (`_campus_errors`) :
1. `buildings` vide : `template` n'est pas `campus`, `rooms` est vide, aucun `room_id` (comportement actuel).
2. `buildings` non vide : `template == "campus"` ; le moteur `factory` accepte `usine` ou `campus`.
3. Ids de bâtiment et de pièce uniques ; une pièce commence par `<building_id>.` et son bâtiment existe.
4. `archetype` dans `pack["building_archetypes"]` ; `Room.kind` dans `building_archetypes[a]["rooms"]` ;
   `world.ambiance` dans `pack["ambiances"]` ; `style` dans les `styles` de cette ambiance (de toutes, si None).
5. Bâtiment dans `world.bounds` ; pièce dans son bâtiment ; aucune zone vide ou inversée.
6. Chaque département intérieur (`external` faux) est logé dans **une seule** pièce, et `Department.room_id` la
   désigne (les deux sens concordent) ; un département externe n'est dans aucune pièce.
7. Chaque bâtiment a au moins une pièce (un bâtiment de pur décor est interdit, ADR 0013 §6.7).

Invariants de `layout.check_placement` (moteur-jeu, T5) : bâtiments disjoints, séparés d'une allée d'au moins une
cellule du campus ; `entrance` sur le bord du bâtiment ; chaque porte sur le bord de sa pièce ; l'aire d'un département
dans celle de sa pièce ; un chemin praticable de l'entrée à chaque porte ; règles de zonage du pack respectées.

Producteur : `layout.place_campus(spec, pack, plan, seed) -> dict` (moteur-jeu, T5), pur et déterministe à graine ;
algorithme, repli et appelants : §2 bis (27/11, fait foi). Plan de moins de 2 bâtiments : `place_world` actuel (hall
en U, `template: usine`). `apply_edits` reste sans graine.

Clés de pack (game-designer, T5 ; contrôle de format ajouté par moteur-jeu dans `_check_world_keys`) :

```yaml
campus:
  cell_m: 4                       # pas de la grille du site (values, provenance)
building_archetypes:
  hall_production:
    label: Hall de production
    size_cells: [[8, 6], [16, 12]]        # [min, max] (largeur, profondeur), en cellules du campus
    rooms:                                # kind -> blocs (départements) permis
      atelier: {label: Atelier, blocks: [ligne, magasin_mp, magasin_pf]}
      bureau: {label: Bureaux, blocks: [planification]}
    walls: prop_wall_panel                # ids d'assets (ai/assets.yaml, statut importe) ; façade = Building.style
    door: prop_door_industrial
zoning_rules:                             # type dans spec.ZONING_KINDS, chacune avec provenance
  - {type: together, departments: [magasin_mp, ligne], provenance: {status: source, citation: "..."}}
  - {type: apart, departments: [peinture, soudage], provenance: {status: calibre, note: "..."}}
  - {type: same_building, departments: [qualite, ligne], provenance: {...}}
  - {type: max_walk_m, departments: [maintenance, ligne], value: dist_max_maintenance}   # clé de values
ambiances:
  hiver_industriel: {label: Hiver, palette: gris, season: hiver, vegetation: rare, styles: [brique, bardage]}
variants:                                 # rôle d'objet (ElementRole) -> assets interchangeables
  machine: [mach_lathe_a, mach_lathe_b]
```

`together` : même pièce, ou même bâtiment et aires à une cellule ou moins (§2 bis, écart 5) ; `apart` : bâtiments différents ou au
moins deux cellules d'écart ; `same_building` : même bâtiment ; `max_walk_m` : `layout.path_m` (mètres) au plus la
valeur (§2 bis).

Exemple (extrait) :

```json
{"world": {"template": "campus", "ambiance": "hiver_industriel",
  "buildings": [{"id": "b1", "archetype": "hall_production", "label": "Hall A", "area": [0, 0, 48, 32],
                 "entrance": [24, 0], "style": "brique"}],
  "rooms": [{"id": "b1.atelier", "building_id": "b1", "kind": "atelier", "label": "Atelier",
             "area": [0, 0, 48, 24], "department_ids": ["ligne", "magasin_mp"], "doors": [[24, 24]]}]},
 "departments": [{"id": "ligne", "label": "Ligne", "area": [4, 4, 40, 20], "room_id": "b1.atelier"}]}
```

## 2 bis. Tranche T5 : décisions et plan (27/11, fait foi sur §2 et §3)

### Décision 1. `ambiances`, `walls`, `style` : contrat valide, aucun renommage

`ambiances` n'est pas une clé inventée : elle est au contrat depuis T2 (§1 `GameParams.ambiance`, §2 point 4,
`SimSpec._campus_errors`). Sens fixé :
- `building_archetypes.<a>.walls` et `.door` : ids d'assets (géométrie du module de mur, porte d'entrée), au catalogue
  et hors `a_sourcer` ; `required_assets` les compte. `place_campus` les recopie dans `Building.walls` et
  `Building.door` (facultatifs, ajoutés le 27/11 ; None : défaut de Godot), car Godot ne lit que la spec.
- `Building.style` : valeur de la variante `style` de l'asset `walls` (matériau), tirée à graine dans
  `ambiances[world.ambiance].styles`. Un style n'est pas un asset et n'entre pas dans `required_assets`.
- `palette`, `season`, `vegetation` : aucun consommateur en T5. `_check_world_keys` n'accepte que `reference`, `ete`
  et `normale` (l'aspect actuel) tant que Godot n'en rend pas d'autre (une valeur ignorée serait une contrainte ignorée).

### Décision 2. Palette vers l'entrepôt PF : dans T5, dernière étape du moteur

Sans elle, l'archétype `entrepot` sépare emballage et entrepôt PF par un passage instantané, ce qu'interdit l'ADR 0013
§6.7. C'est le chronométrage d'un passage qui existe déjà (palette filmée -> PF) : aucune action, aucun indicateur,
ordre de `advance` inchangé, aucune migration ; la règle d'arrêt (nouvel ADR si `simulate` ou `advance` sont
restructurés) n'est pas atteinte. **Garde-fou** : si le code exige plus (autre ressource que le chariot, ordre des
événements du jeu de référence changé), moteur-jeu s'arrête ; repli décidé d'avance : `limits.buildings: [1, 2, 1]`
sans `entrepot`. Règle, en campus seulement (vitesses renseignées) :
- l'emballage attend (`pk_wait`) que le chariot prenne la palette filmée ; le chariot sert d'abord une palette en
  attente (elle bloque l'emballage), puis les kits ; prise seulement si une place PF est libre en comptant les
  palettes en route (place réservée à la prise) ;
- arrivée à prise + `pallet_handling_min` + t, chariot libre à prise + `pallet_handling_min` + 2t, avec
  t = `travel_min(spec, "emballage", "entrepot_pf", "chariot")` ; stock PF et événement `palette` à l'arrivée ;
- état : `fs["fk"]["transit"]` (palettes en route, lu avec défaut 0), fin de trajet persistée comme les kits en vol
  (`inflight`) ; le conducteur reste `agent_stock_mp` ; `forklift_busy_min` compte les palettes.
- `Logistics.pallet_handling_min: float | None` (ajouté le 27/11, None = 0), copié de `values`
  `trajet.manutention_palette_min`, provenance `logistics.pallet_handling_min`.

### Décision 3. Trajets : règles valides, forme exacte

- Vitesses renseignées **si et seulement si** `spec.factory` et 2 bâtiments ou plus (contrôle `SimSpec`). Un bâtiment
  (hall en U) : `kit_min` et `repair_travel_min` fixes, jeu de référence inchangé.
- Kit : chariot occupé `kit_min + 2t`, kit remis à la ligne à `kit_min + t`, t = trajet `stock_mp -> production` au
  chariot ; `kit_min` (8) ne compte plus que la préparation. Technicien : trajet `maintenance -> production` à pied, aller
  seul, remplace `repair_travel_min` partout (`_tech_try`, `tech_stats.busy_min`, `trs_factors`).
- Départs et arrivées fixés par le code, pas par le pack (la clé prévue au §3 est abandonnée) :
  `layout.TIMED_LINKS = {"kit": ("stock_mp", "production", "chariot"), "repair": ("maintenance", "production",
  "marche"), "pallet": ("emballage", "entrepot_pf", "chariot")}` ; `factory` l'importe (pas d'import circulaire).
- Formes (layout.py, pures, sans pack : le moteur ne lit que la spec) :

```python
PATH_CELL_M = 1.0  # shortcut : grille fixe de la recherche hors bâtiments ; passer au pas du campus si trop lent
def path_points(spec: dict, a: str, b: str) -> list[list[float]]   # ids de département ; polyligne (m)
def path_m(spec: dict, a: str, b: str) -> float                     # longueur de path_points
def travel_min(spec: dict, a: str, b: str, mode: Literal["marche", "chariot"]) -> float  # path_m / vitesse
```

  Point d'un département : centre de son `area`. Même pièce : Manhattan. Même bâtiment : centre -> porte de sa pièce ->
  porte de l'autre -> centre (minimum sur les portes ; tronçons entre portes et entrées : décision 4, écart 3). Bâtiments différents :
  centre -> porte -> entrée, puis plus court chemin 4-voisins hors bâtiments (cellules de `PATH_CELL_M` dans
  `world.bounds` élargi de 8 m, cellules d'un bâtiment interdites), entrée -> porte -> centre. `LayoutError` :
  département inconnu, sans `area` ou sans `room_id`, aucun chemin, ou vitesses None (`travel_min`).
- Appelants : `factory.Plant.__init__` (une fois, les 3 `TIMED_LINKS`, si les vitesses sont renseignées),
  `layout.check_placement` (`max_walk_m`, en mètres) et `_forklift_route` (ci-dessous). Ni Godot ni l'API.

### Décision 4. `place_campus`

`place_campus(spec: dict, pack: dict, plan: list[dict], seed: int) -> dict` : même retour que `place_world`, plus
`world.buildings`, `world.rooms` et `departments[].room_id`. `place_world` gagne `hall: list[float] | None = None`
(boîte qui remplace le hall pour `_build_network`, bornes et décor).
- Appel : `recompile_layout` (seul point d'entrée : `factory_generation`, route des retouches, worker de génération)
  appelle `place_campus` si le plan compte 2 bâtiments ou plus, sinon `place_world` (un plan d'un bâtiment loge tout dans le hall en U). Plan = `params.world_plan`, sinon
  `default_plan(pack, params.buildings, seed)` : b1 = premier archétype du pack (`hall_production`), les n - 1 autres
  tirés à graine parmi les suivants ; chacun prend les départements intérieurs listés dans ses `rooms.*.blocks`, b1 le
  reste. `factory_generation` écrit vitesses et `pallet_handling_min` dès que le plan compte 2 bâtiments (values
  `trajet.*`, provenance `logistics.<champ>`).
- Tentative k (graine `f"{seed}:campus:{k}"`) :
  1. Chaque bâtiment garde la disposition relative du hall en U (aires du pack) de ses départements, translatée en
     bloc ; aucun nouveau placement interne.
  2. Taille = boîte du groupe arrondie à la cellule `campus.cell_m`, plus une marge tirée de 0 à 2 cellules par axe,
     bornée par `size_cells` (groupe trop grand : tentative échouée) ; groupe collé au bord z max (le quai reste au mur),
     décalé à graine en x dans la marge (pas de 0,5 m).
  3. Bâtiments en rangée selon x, bords z max alignés (côté camions), ordre tiré, allée de 1 ou 2 cellules tirée ;
     rangée centrée sur x = 0.
  4. Entrée au milieu du bord z min (côté opposé aux camions) ; `spawn` à 2 m devant l'entrée de b1.
  5. Pièces : **une par département**, id `<b>.<département>`, `kind` = pièce de l'archétype qui le liste, `label` du
     département, `area` = aire du département, une porte au milieu du bord côté `front` du département. (Le hall en U
     n'a pas de découpage en rectangles disjoints par fonction ; le contrat permet plusieurs départements par pièce,
     le producteur T5 n'en met qu'un.)
  6. Style tiré dans l'ambiance (`params.ambiance`, sinon la première du pack, écrite dans `world.ambiance`) ; `walls`
     et `door` recopiés ; `label` = label de l'archétype.
  7. Pose actuelle sur les aires déplacées (`place_world(..., hall=boîte du campus)`) ; `template: campus`, `size` =
     taille de b1 ; décor hors bâtiments et sites. `_forklift_route` : entre deux ancres de bâtiments différents,
     insère `path_points` au lieu du segment droit.
  8. Acceptée si `check_placement == []` (écart 1 ci-dessous).
- Ordre : k = 1 à 20, puis k = 0 (référence : b1 au milieu de la rangée, les autres dans l'ordre du plan, marges 0,
  allée 1 cellule ; écart 2). Si k = 0 échoue :
  `LayoutError` (bug ; les tests couvrent tous les plans valides du pack). **Pas de repli sur le hall en U** : le monde
  contredirait `params.buildings` sans le dire (une contrainte n'est jamais ignorée).
- `check_placement`, si `world.buildings` : bâtiments disjoints à une cellule au moins, alignés sur la grille du
  campus, tailles dans `size_cells` ; entrée sur le bord ; porte sur le bord de sa pièce ; aire du département dans sa
  pièce ; pièces d'un bâtiment disjointes ; chemin entre toutes les entrées ; `zoning_rules` (sens du §2). Règles
  `adjacent` et `flow` : une paire dans deux bâtiments n'est permise que si c'est un `TIMED_LINKS`
  (« passage non chronométré entre bâtiments : a -> b »), sinon contiguïté comme aujourd'hui ; `protected_path` sur la
  route du chariot, sortie comprise.

### Écarts d'implémentation de l'étape 4 (`place_campus`, 27/11, architecte)

1. **Validé.** Tentative acceptée sur `check_placement == []` seul : la spec est partielle à ce stade, `generate`
   valide la spec complète ensuite. Condition : les tests A valident la spec complète (`SimSpec`) pour les 3 plans et
   les 12 graines ; un refus à ce stade est un bug du placeur, pas un tirage à rejouer.
2. **Validé.** Référence k = 0 : b1 au milieu de la rangée, les autres dans l'ordre du plan de part et d'autre
   (texte de la décision 4 corrigé). L'ordre strict mettait l'atelier en bout de rangée à 161 m de la maintenance,
   au-delà de `max_walk_m` (150) : la référence doit passer pour tous les plans valides.
3. **Refusé.** Exclure du test de barrière les segments qui touchent une porte ou une entrée cache le cas même que la
   règle protège : la route du chariot traversait le bureau du pilotage, donc des postes fixes (INRS ED 6350 § 4.4,
   `postes_proteges_chariots`). « Intérieur supposé libre » (décision 3) ne vaut que pour une longueur, pas pour la
   sécurité. **Correctif (moteur-jeu, layout.py, test_campus.py)** : généraliser `_outside_path` en une recherche
   4-voisins à boîte et rectangles interdits passés en paramètres ; dans `path_points` (donc `path_m` et la route
   du chariot), chaque tronçon porte -> entrée et porte -> porte suit cette recherche dans l'`area` du bâtiment,
   aires des autres pièces interdites (pièces de départ et d'arrivée permises), à la place du Manhattan ; aucun
   chemin : `LayoutError` (tentative échouée). Test de barrière et croisements sur tout le chemin, sans exclusion ;
   les barrières sont posées le long de ce chemin. Tests : route `production -> entrepot_pf` qui ne coupe aucune pièce
   tierce, poste à moins de `PROTECT_M` d'un tronçon intérieur sans barrière -> message, `max_walk_m` (150) toujours
   tenu par la référence k = 0 sur les 3 plans.
4. **Validé.** `recompile_layout` remet `buildings`, `rooms` et `ambiance` à vide quand une spec campus repasse à
   1 bâtiment (sinon `template` et `buildings` se contredisent) ; `room_id` part avec les départements de
   `place_world`, et des vitesses restées renseignées sont refusées par `SimSpec._campus_errors` (pas d'écart
   silencieux). Test : spec campus recompilée à 1 bâtiment -> monde égal à la référence, hors clés nulles.
5. **Validé.** `zoning_rules` contrôlées seulement si `world.buildings` est non vide : le hall en U reste la référence
   (règles de l'ADR 0010) et n'a ni pièces ni `room_id`. Sens fixé (le §2 est aligné) : `together` = même pièce, ou
   même bâtiment à une cellule **ou moins** ; `apart` = bâtiments différents, ou deux cellules au moins dans un même
   bâtiment.

### Contrôles à ajouter (moteur-jeu, dans `spec.py`, avec la mise à jour des tests qu'ils cassent)

- `GameParams._world_choice_errors` : archétype en double ; département sans pièce dans son archétype ; plan non vide
  qui ne loge pas tous les départements intérieurs du pack ; paire `together` ou `same_building` dans deux bâtiments
  prévus. Casse `test_spec_0013.py` l. 92-93 (plan d'un seul département) : fixture à compléter.
- `SimSpec._campus_errors` : vitesses renseignées sans `factory` ni 2 bâtiments, ou 2 bâtiments sans vitesses. Casse
  l. 326-327 (vitesses sans bâtiment) : attendre le refus.
- `_check_world_keys` : `campus.cell_m` positif et multiple de `grid.site_cell_m` ; archétypes (`label`, `size_cells`
  entiers, min <= max, `rooms` à `label` et `blocks` de départements intérieurs, un bloc dans une seule pièce par
  archétype, `walls` et `door`) ; `zoning_rules` (type de `ZONING_KINDS`, 2 départements connus, `value` clé numérique
  de `values` pour `max_walk_m`, provenance) ; `ambiances` (`label`, `styles` non vide, valeurs de la décision 1).

### Plan d'exécution T5

| # | Agent | Fichiers | Travail | Critère de fin | Parallèle |
|---|---|---|---|---|---|
| 1 | moteur-jeu | game/spec.py (contrôles ci-dessus), tests/test_spec_0013.py | contrôles et tests cassés mis à jour | `test.ps1 -Fast` vert | avec 2, 3 |
| 2 | game-designer | ai/packs/usine.yaml | notes du pack alignées (ci-dessous), `limits.buildings` laissé à [1, 1, 1] | provenance de chaque valeur | avec 1, 3 |
| 3 | assets-3d (en cours) | ai/assets.yaml, godot/assets/ | `prop_wall_panel` (`variants: [style, hauteur]`, styles `bardage` et `brique`), `prop_door_industrial`, hors `a_sourcer` | `assets.ps1` vert | avec 1, 2 |
| 4 | moteur-jeu | game/layout.py, game/factory_generation.py, tests/test_campus.py | `TIMED_LINKS`, `path_points`, `path_m`, `travel_min`, `default_plan`, `place_campus`, `place_world(hall=)`, `check_placement`, appelants | tests A ci-dessous | après 1 |
| 5 | moteur-jeu | game/factory.py, tests/test_factory_campus.py | kit, technicien, `trs_factors` (décision 3) | tests B | après 4 |
| 6 | moteur-jeu | game/factory.py, même test | palette (décision 2) | tests C | après 5 |
| 7 | godot-dev | godot/scenes/world/world.gd (ou campus.gd) | `template: campus` : un bâtiment par `buildings` (murs `walls` en modules, `style` -> variante `style`, porte `door` à l'entrée, défaut si l'asset manque), pas de hall unique, zones des départements comme aujourd'hui, clic de pièce = département, caméra sur `bounds` | `godot.ps1 -Check`, `-Tour` sur une spec campus de fixture | après 4 (fixture), avec 5, 6 |
| 8 | moteur-jeu | game/layout.py (`required_assets`) | compte `walls` et `door` | `pack_coverage("usine")` = 1,0 | après 3 et 6 |
| 9 | game-designer | ai/packs/usine.yaml | `limits.buildings: [1, 3, 1]` | tests A à C verts sur le pack réel | après 8 |
| 10 | devops | scripts/godot.ps1 | `-Flow -Buildings 3` (partie campus scriptée) | `-Flow -Buildings 3` vert | après 9, avec 11 |
| 11 | documentaliste | docs/game-design.md, docs/architecture.md | campus, trajets, palette | références à jour | après 9 |
| 12 | qa-reviewer | - | relecture | `test.ps1 -Integration`, `-Tour`, `-Flow`, `-Flow -Buildings 3`, 45 images/s | toujours en dernier |

Tests attendus (moteur-jeu) :
- A : `path_m` même pièce (Manhattan), même bâtiment (par les portes), deux bâtiments avec un troisième entre eux (détour
  plus long que Manhattan) ; `LayoutError` (département inconnu, vitesses None) ; `default_plan` ; pour chacun des
  3 plans valides de l'usine (hall + entrepôt, hall + maintenance, les trois) et 12 graines : spec valide,
  `check_placement == []`, pilote automatique 2 semaines sans erreur ; empreintes distinctes (`world_fingerprint`)
  au moins 8 sur 12 graines à 3 bâtiments, 6 à 2 ; même graine -> même spec ; repli k = 0 (les tirages refusés par
  monkeypatch) puis `LayoutError` ; zonage violé (`together`, `apart`, `max_walk_m` à 10 m, paire de flux non
  chronométrée) -> message ; **référence** : `buildings` None et 1 -> spec égale à celle d'avant T5 (empreinte prise
  avant de coder, hors clés nulles ajoutées) et empreintes de `test_factory.py` inchangées ; budget de génération tenu.
- B : kit remis à `kit_min + t`, chariot libre à `kit_min + 2t` ; trajet du technicien = trajet à pied ;
  `trs_factors` le lit.
- C : conservation (emballage + en route + PF) ; capacité PF jamais dépassée en comptant les palettes en route ;
  palette servie avant un kit au même instant ; sauvegarde et reprise d'un tour avec une palette en route ; ancien état
  sans `transit` relu.

Pack (game-designer, étape 2) : commentaire « clé inventée » sans objet (décision 1) ; `trajet.formules` : kit remis à
8 + t, chariot occupé 8 + 2t ; `zonage.marche_max_maintenance_m` : mesuré au centre de la production, pas à chaque
machine ; `trajet.manutention_palette_min` : arrivée à 1 + t, chariot libre à 1 + 2t ; les entrées des bâtiments sont
côté opposé aux camions ; fiche Bohannon 1997 hors corpus à demander à rag-knowledge (vitesse non dite par les PNJ
tant qu'elle n'est pas sourcée au corpus).

## 3. Usine variée et trajets (T4, T5)

| Ajout | Défaut | Sens |
|---|---|---|
| `BomItem.product_id: str \| None` | None = `Factory.product_id` | dès qu'un article le porte, mode plusieurs produits : chaque produit a au moins une ligne (`Line.product_id`) et une nomenclature ; sinon, règle actuelle (toutes les lignes font `Factory.product_id`) |
| `Factory.clients: list[Client]` (4 au plus) | [] : `customer` seul, acheteur de `product_id` | `Client = Customer + {id: "c1".."c4", name, product_id, site_id}` ; ids uniques, produit et site connus ; `customer` est alors ignoré par le moteur (le générateur y recopie `clients[0]`) |
| `Machine.type: str \| None`, motif `^[a-z][a-z0-9_]{1,29}$` | None : type unique | clé de `pack["machine_types"]` (`m1`..`m4` dans l'usine ; le chiffre est permis ici car la clé vient du pack, jamais d'un texte conçu), vérifiée par `SimSpec` (« type inconnu du pack ») |
| `Logistics.walk_m_per_min`, `forklift_m_per_min` | None (ensemble, ou aucune) | renseignées : trajets calculés, `kit_min` ne compte plus que la préparation ; None : `kit_min` et `repair_travel_min` fixes (§2 bis, décision 3) |
| `Logistics.pallet_handling_min` | None (= 0) | prise et dépose d'une palette PF au chariot, en campus (§2 bis, décision 2) |
| `Building.walls`, `Building.door` | None (défaut Godot) | assets de l'archétype recopiés par `place_campus` (§2 bis, décision 1) |

`Factory.product_id` reste le produit de référence (le premier). Les fournisseurs (3 à 8) n'ont besoin d'aucun champ :
`suppliers`, `offers` et les sites fournisseurs existent déjà. Un site par fournisseur : le premier d'un profil garde
le site du pack (`fournisseur_<profil>`), les suivants le clonent en `fournisseur_<profil>_b`, `_c`… dans l'ordre des
offres (lettres : un code n'a pas de chiffre), même classe de distance donc même délai (`layout._build_network`).

Clients et produits : **chaque produit a au moins un client et un client n'achète qu'un produit**, donc
`clients >= products` (`clients` None : autant que de produits). Contrôle à poser en T4b dans
`GameParams._world_choice_errors` (422 à l'API) ; d'ici là, les bornes du §1 à 1 suffisent, et le garde-fou
`ValueError` de `generate_factory` reste en place pour un appel direct.

## 3 bis. Moteur à plusieurs produits et clients (tranche T4b)

Change l'intérieur de `factory.simulate` (forme de l'état, kit, emballage, client) : hors T4, reporté en T4b (ADR 0013
§5). L'ordre de `factory_game.advance` ne change pas ; aucune action ne gagne de champ.

| Sujet | Règle |
|---|---|
| Lignes | une ligne fait un seul produit (`Line.product_id`) ; lignes = max(option `lines`, `products`), 3 au plus ; produit k sur les lignes k, k + P… ; machines propres à chaque ligne (déjà le cas), types tirés par les opérations du produit |
| Matière | une MP par produit (`item.mp` du secteur) : composant `c<k>`, `BomItem(product_id, component_id, per_unit)` |
| Fournisseurs | chaque fournisseur propose chaque matière : une offre par (matière, fournisseur), ids `o1`, `o2`… par matière puis fournisseur (1 produit : ids actuels) ; coût = coût de la MP x `cost_factor` du profil |
| Stocks | MP par composant, PF par produit ; capacités `mp_capacity_pallets` et `pf_capacity_pallets` communes (un magasin, un entrepôt) ; `lot_size`, `pf_min`, `pf_max` communs (§9) |
| Ressources | quai, chariot, contrôle réception, contrôle qualité, emballage, technicien : partagés, files FIFO déjà en place ; chaque lot, palette et commande porte son produit ou son composant |
| Clients | client i achète le produit ((i - 1) mod P) + 1 ; demande calibrée du produit (comme aujourd'hui) divisée entre ses clients (au moins 1 par jour) ; un camion et un site par client (`client`, puis `client_b`, `_c`, `_d`, comme les fournisseurs) ; une commande porte `client_id` et `product_id` ; l'enlèvement ne prend que le PF de son produit |
| Pilote automatique | OF par ligne sur le PF de son produit ; point de commande par composant, offre standard de chaque composant |
| Recette | `advance` : chiffre d'affaires = somme par produit de (expédié x `products[k].price`) |
| Indicateurs | OTIF, TRS, ruptures, trésorerie : agrégés (cibles inchangées) ; table par produit (expédié, OTIF, stock PF) dans `public_state` et le débrief |
| PNJ | faits par produit ou composant (3 au plus) pour stock MP, entrepôt PF, production ; le PNJ client parle du client `c1` seul (ses commandes, ses faits) |
| État | une partie en cours à l'ancienne forme (`mp.units`, `pf.units`) est relue par une mise à niveau pure dans `factory` (testée) ; jamais de migration de base |

Tests attendus (moteur-jeu) : 2 et 3 produits, 1 à 4 clients jouables au pilote sur les 2 secteurs ; 1 produit et
1 client : spec et rapport de tour identiques à la référence ; conservation de la matière par composant et du PF par
produit ; un client n'emporte jamais un autre produit ; mise à niveau de l'ancien état ; budget de génération tenu.

Compléments du 27/11 (relecture du code à bcf8b89, plan de T4b) : manques du tableau, qui font partie de T4b.

1. Nomenclature : `factory.Plant` refuse toute nomenclature de plus d'un article (`factory.py` l. 45), alors que
   `SimSpec` accepte `BomItem.product_id` : une spec à 2 produits importée passe la validation, puis lève une erreur
   500 au premier tour. `SimSpec` exige donc un article par produit, sans `product_id` = `Factory.product_id`
   (« usine : produit p1 : une seule matière (2 articles) ») et une matière par produit (« usine : matière c1
   partagée par p1 et p2 ») ; la fixture `two_products()` de `test_spec_0013.py` prend `c2`. Fait (spec.py, 27/11).
2. Palette de matière : `Logistics.units_per_pallet_mp` est unique, mais chaque MP du pack a son `units_per_pallet`
   (120 ou 150). Ajout facultatif `Component.units_per_pallet: int | None = None` (> 0 ; None : valeur de
   `logistics`) ; le générateur ne le renseigne que pour `c2` et `c3`. Fait (spec.py, 27/11).
3. Commande initiale : `Factory.initial_order` ne sert que `c1`. Ajout `Factory.initial_orders: list[InitialOrder]`
   (2 au plus, vide par défaut) pour `c2` et `c3`, même forme que `initial_order` : `{offer_id, pallets (> 0),
   arrival_day (>= 0, jour ouvré depuis le début de partie)}`. `SimSpec` : offre connue (« usine : commande initiale
   sur une offre inconnue o99 »), une commande initiale par matière au plus, `initial_order` compris (« usine : une
   commande initiale par matière au plus (c1) ») ; même règle n° 5a. Fait (spec.py, 27/11).
4. Capacités communes : l'occupation du magasin est la somme, par matière, des palettes entamées (unités divisées par
   la palette de la matière, arrondi au-dessus) plus les palettes posées ; celle de l'entrepôt, la somme par produit
   (une palette ne porte qu'un produit). Le générateur répartit les plafonds au prorata des lignes du produit
   (`n_k / lignes`) : stocks MP et PF de départ, place libre de la commande initiale.
5. Seuils PF : `pf_min` et `pf_max` restent communs (§9), calculés sur la plus forte demande d'un produit et plafonnés
   à la capacité PF divisée par P. Avec un produit : formule actuelle.
6. Emballage : une palette en cours par produit ; les bons passent en FIFO comme aujourd'hui.
7. Clients : la demande d du produit k est répartie entre ses n clients, `d // n` chacun et 1 de plus pour les
   `d % n` premiers. Créneau (`pickup_window_min`), délai promis, variabilité et commandes par jour : ceux de
   `customer`. Noms : `themes.<secteur>.client`, puis `extra_clients` dans l'ordre. `SimSpec` vérifie le
   `Client.pickup_window_min` de chaque client comme celui de `customer` (« créneau d'enlèvement du client c1 :
   0 <= début < fin <= 480 minutes attendu ») et, si `clients` n'est pas vide, qu'aucun produit n'est sans client
   (« usine : produit p2 sans client ») ; contrôles faits (spec.py, 27/11). Sites : `layout._build_network` clone le
   site `client` en `client_b`, `_c`, `_d` (comme les fournisseurs).
8. Tirages : produit k = `theme.products[(i + k - 1) mod n]`, i étant le tirage actuel (aucun tirage de plus) ; le
   flux de hasard du client `c1` garde sa clé actuelle, les autres clients y ajoutent leur id.
9. Non-régression (1 produit, 1 client) : `Factory.clients` reste vide. « Identique » = mêmes valeurs pour toutes les
   clés de la référence, hors `provenance` et `panels` (le pack change en T4b) ; seules clés nouvelles permises :
   `initial_orders: []`, `units_per_pallet: null`, `by_product` et, dans les commandes client, `client_id` et
   `product_id`. La référence est capturée avant toute modification du code (étape 1 du plan). `generate` passe par
   `SimSpec.model_dump` : dès l'étape 2, sa spec porte `factory.initial_orders: []` et `components[].units_per_pallet:
   null` ; la comparaison de `test_t4b_contract.py` retire ces clés à leur valeur vide avant d'égaler (jamais une
   nouvelle capture).
10. Vue publique : `factory.stocks.mp` a une entrée par matière ; `factory.stocks.pf` reste l'agrégat (Godot et le
    panneau `bandeau_pf` inchangés) ; ajout `factory.by_product: [{product_id, name, quantity, pallets, shipped,
    otif}]`, une ligne par produit même à 1 ; `orders.customer[]` gagne `client_id` et `product_id`. Historique
    (`history[]`) et débrief : `by_product` (mêmes champs, sur la semaine ou la partie). Racines inchangées.
11. `GameParams` : contrôle seulement si le pack déclare `limits.clients` (l'atelier n'a pas de clients). Nombre
    effectif = `clients`, ou `products` s'il est None ; il tient dans `limits.clients` et vaut au moins `products`
    (« clients : au moins un par produit (3 produits, 2 clients) »). Fait dans `_world_choice_errors` (27/11) ; le
    garde-fou `ValueError` de `generate_factory` (l. 37-39) est retiré à l'étape 4 (moteur-jeu).

Trajets (moteur-jeu, T5) : remplacé par le §2 bis, décision 3 (27/11).

## 3 ter. Rôles répartis entre joueurs (tranche T7, 27/11)

Lecture du critère « droits testés pour les 3 rôles » : ce sont les 3 rôles de l'application (joueur, formateur,
admin, docs/roles.md), comme en T8 et dans la matrice de l'annexe 0010 §5. Les rôles de jeu sont testés à part,
pour chaque nombre de joueurs de 1 à 6.

Décisions de l'utilisateur (27/11) :

- **U1** : le nombre de rôles suit le nombre de membres jusqu'au lancement, puis se fige dans `settings["seats"]`.
- **U2** : à 6 joueurs, deux joueurs partagent un rôle ; aucune action nouvelle, donc 5 rôles au plus pour l'usine.

### Modèle

Un **rôle** de jeu est un ensemble d'actions ; un **plan** dit quels rôles sont tenus à n joueurs. Le droit d'agir
passe du module à l'action : la règle de l'annexe 0010 §5 (`actor.role == module.role_id`) devient « l'action
appartient au rôle de l'acteur dans le plan du lobby ».

```python
class Action(BaseModel):          # + 1 champ
    autopilot: str | None = None  # journal si cette action seule est en pilote automatique ; None : module.autopilot

class Role(BaseModel):            # + 1 champ ; module_id : module de la page de tablette (department_id)
    actions: list[str] = Field(default_factory=list)  # ids d'action de spec.modules ; vide : celles de module_id

class RolePlan(BaseModel):
    players: int = Field(ge=1, le=6)
    roles: list[str] = Field(min_length=1, max_length=6)

SimSpec.role_plans: list[RolePlan] = Field(default_factory=list)  # vide : un seul plan, tous les spec.roles
```

Contrôles `SimSpec` (moteur-jeu, messages testés) :
- `action {a} : identifiant en double` (ids d'action uniques dans `spec.modules`, toujours) ;
- `rôle {r} : action inconnue {a}` ; `rôle {r} : module {m} sans action de ce rôle` (si `actions` non vide) ;
- `plans de rôles : {n} joueurs en double` ; `plan à {n} joueurs : rôle inconnu {r}` ;
- `plan à {n} joueurs : action {a} sans rôle` et `plan à {n} joueurs : action {a} tenue par {k} rôles` : chaque
  plan partage les actions de `spec.modules`, chacune une fois ;
- `rôle {r} : dans aucun plan` (si `role_plans` non vide, sauf rôle d'un module : `Module.role_id` reste exigé).

Panneaux et PNJ attitrés : aucun champ. La page de tablette reste `Role.department_id` ; l'interlocuteur du rôle est
le PNJ de ce département (`agents[].department_id`), déjà dans la spec.

### Pack (game-designer) et génération (moteur-jeu)

```yaml
roles:                    # T7 : rôles en plus de modules.*.role (dont les actions sont celles du module)
  acheteur:
    title: Acheteur·se
    mission: Commander la matière à temps, au bon fournisseur
    module: pilotage
    actions: [commander_mp]
role_plans:               # joueurs -> rôles ; chaque plan couvre chaque action une fois
  3: [responsable_production, chef_de_ligne, responsable_maintenance]
modules:
  pilotage:
    actions:
      - id: commander_mp
        autopilot: "MP commandée au fournisseur standard au point de commande"  # module découpé seulement
```

`factory_generation._modules` lit ces clés pour tout pack (D2 déclare ainsi DAF, trésorier, credit manager et
comptable fournisseurs, sans code de droits à écrire) : rôles des modules joués, `actions` écrites en clair ; rôles
du pack filtrés sur les actions des modules joués, rôle vide retiré, puis plan vide retiré ; `role_plans` triés par
`players`. Pack sans `role_plans` (atelier) : `[]`. `CastPlan` (T9) ne touche pas aux plans en T7.

Plans proposés pour l'usine (titres et missions : game-designer, qui les valide) :

| Joueurs | Rôles (actions) |
|---|---|
| 1 | `responsable_usine` (les 5 actions) |
| 2 | responsable_flux (commander_mp, lancer_of) ; responsable_atelier (les 3 autres actions) |
| 3 | les 3 rôles actuels des modules : le jeu de référence |
| 4 | `acheteur` (`commander_mp`) ; `ordonnanceur` (`lancer_of`) ; `chef_de_ligne` ; `responsable_maintenance` |
| 5 | plan à 4, maintenance scindée : technicien_methodes (preventif), chef_equipe_maintenance (priorite_reparation) |
| 6 | pas de plan déclaré : le plan à 5 ; le 6e joueur double `acheteur` (U2), sauf s'il choisit un autre rôle |

Qualité et expédition n'ont aucune action dans le pack usine : pas de rôle en T7, 5 rôles au plus (U2, qui
remplace « 3 à 6 rôles » de la ligne T7 de l'ADR).

Règle « un rôle libre avant un doublon », pour toutes les specs : tant qu'un rôle du plan est libre, `PUT /role` sur
un rôle pris est refusé (409) ; une fois tous les rôles pris, un joueur peut doubler le rôle de son choix. Au
lancement, `assign_seats` donne d'abord les rôles libres, puis double les rôles dans l'ordre du plan à partir du
premier : à 6 joueurs sans choix, le 6e double `acheteur`, premier rôle du plan à 5. Ce rôle est le plus chargé en
décisions (une matière par produit, 3 au plus en T4b). Les deux titulaires agissent l'un et l'autre ; le journal
nomme l'auteur de chaque décision (`log[].name`).

### Fonctions pures (`gmix.game.engine`, moteur-jeu)

- `role_plan(spec, players) -> list[str]` : sans `role_plans`, tous les `spec.roles` ; sinon le plan au plus grand
  `players <= n`, ou le plus petit plan si n est en dessous (0 se lit 1). Un pack peut donc omettre 1 et 2 joueurs.
- `role_actions(spec, role_id) -> set[str]` : `Role.actions`, ou les actions de `module_id` si la liste est vide.
- `action_owners(spec, plan | None) -> dict[str, str]` : action -> rôle du plan ; `None` : `module.role_id`.
- `assign_seats(plan, members: list[tuple[str, str | None]]) -> dict[str, str]`, membres dans l'ordre d'entrée :
  garde un choix valide, donne ensuite les rôles libres dans l'ordre du plan, puis, s'il n'en reste plus, refait le
  tour du plan depuis le premier (binôme).
- `act(..., plan: list[str] | None = None)` : le gestionnaire agit partout ; sinon `owners[action] == actor.role`,
  ou 409 « Cette action revient au rôle « {titre du rôle propriétaire} » », ou « Choisissez un rôle » sans rôle.
  `occupied_roles` reste ignoré (dette de l'annexe 0010).
- `played_actions(spec, state, autopilot_all, held_roles) -> set[str]` : `None` -> toutes ; sinon actions des rôles
  tenus, plus celles au journal de la semaine (`kind` `decision`). `played_modules` en dérive (modules d'au moins
  une action jouée) : le moteur hebdomadaire ne change pas.
- `factory_game.advance(spec, state, played)` : `played` devient l'ensemble des actions. `_autopilot` décide par
  action : `commander_mp` -> règle `order`, `lancer_of` -> `launch`, `proteger_goulot` -> `aucune`, `preventif` ->
  `goulot`, `priorite_reparation` -> `arrivee` ; `None` si les deux actions de pilotage sont jouées.
- `_week_entries` : un module sans action jouée garde son entrée actuelle ; un module joué en partie a une entrée
  par action non jouée, avec `action.autopilot`.

Invariant : une spec sans `role_plans`, et une spec T7 jouée avec les rôles du plan à 3, donnent les mêmes
`history` et `public_state` que la référence `backend/tests/fixtures/t7_reference.json`, prise avant tout changement,
pour chacun des 8 sous-ensembles de rôles tenus (2 secteurs, graines 1 à 3, 6 semaines).

### Stockage, attribution, refus (backend-api, `api/routes/lobbies.py`)

- Stockage : `LobbyMember.game_role` (id du rôle, inchangé) ; `lobbies.settings["seats"]` = n, figé par `start`.
  Aucune migration.
- n = membres du lobby hors formateur du lobby (`trainer_id`) : compté en direct pendant l'attente, figé au
  lancement. Quand une entrée change le plan, les rôles hors du nouveau plan sont remis à `null`.
- Attribution : le joueur choisit son rôle dans le plan (`PUT /role`) ; `start` donne un rôle à chaque membre qui
  n'en a pas (`assign_seats`). Le formateur n'attribue pas. Un joueur entré après le lancement choisit lui-même.
- Vue (`GET /lobbies/{id}`) et charge utile de `lobby.members` (gmix.game.events, sans nouveau topic) :
  `seats: {players: n, roles: [id], owners: {action_id: role_id}}`, sans clé `frozen` (n suit les arrivées
  jusqu'au lancement, puis se fige). L'événement `lobby.members` (join, `PUT /role`, `start`) porte
  `{members: [{user_id, display_name, game_role}], seats}` ; le client le lit par le signal
  `lobby_members_changed(members, seats)` (`realtime.gd`).

| Cas | Code | Message |
|---|---|---|
| action d'un autre rôle du plan | 409 | « Cette action revient au rôle « Acheteur·se » » |
| action sans rôle | 409 | « Choisissez un rôle » |
| `PUT /role` absent de la spec | 422 | « Rôle inconnu dans ce business game » (inchangé) |
| `PUT /role` hors du plan à n | 422 | « Ce rôle n'est pas proposé à {n} joueurs » |
| `PUT /role` pris alors qu'un rôle du plan est libre | 409 | « Rôle déjà pris par {nom} : choisissez un rôle libre » |
| changement de rôle après le lancement | 409 | « Le rôle ne change plus une fois la partie lancée » (inchangé) |

409 et non 403 : le compte a le droit d'agir dans le lobby, c'est une règle de partie (annexe 0010 §5) ; 403 reste
réservé au rôle de l'application (joueur sur une route de formateur).

| Opération | joueur avec rôle | joueur sans rôle | formateur du lobby | autre formateur | admin |
|---|---|---|---|---|---|
| `actions` d'une action de son rôle | 200 | 409 | 200 | 404 | 200 |
| `actions` d'une action d'un autre rôle | 409 | 409 | 200 | 404 | 200 |
| `PUT /role` (attente) | 200, 409 ou 422 | 200, 409 ou 422 | 409 (non membre) | 404 | 409 (non membre) |
| `start` (avec attribution) | 403 | 403 | 200 | 404 | 200 |

### Formateur et admin, HUD (godot-dev)

- Formateur et admin : la salle d'attente montre le plan à n joueurs, le titulaire de chaque rôle et « les rôles
  libres sont attribués au lancement » ; en partie, toutes les actions restent permises et la tablette nomme le
  titulaire de chaque action. Ils ne sont dans `expected` que s'ils ont rejoint le lobby (annexe 0010 §1).
- HUD et tablette : `Session.module_block(module_id)` devient `action_block(module_id, action_id)`, qui lit
  `seats.owners`, ou `module.role_id` en repli (fixtures sans `seats`). Seuls les formulaires, outils et boutons
  d'alerte des actions d'un autre rôle sont grisés, avec « Revient à {nom} ({titre}) : allez en discuter. ». Une page
  de tablette est active si une de ses actions est à moi. La ligne « Votre rôle : titre · mission » ne change pas.
- La salle d'attente ne liste que `seats.roles`.

### Compatibilité

Specs déjà en base (sans `role_plans` ni `Role.actions`) : un plan unique (tous les rôles), propriétaire =
`module.role_id`, pilote automatique par module comme avant ; aucune migration de spec. Deux règles de lobby valent
pour toutes les specs : un rôle libre est pris avant de doubler un rôle, et `start` attribue un rôle à ceux qui n'en
ont pas.

### Exemples (étape 1 du plan : `backend/tests/test_t7_contract.py`)

Valide : spec usine générée, à laquelle on ajoute

```json
{"roles": [{"id": "acheteur", "title": "Acheteur·se", "mission": "Commander la matière à temps",
            "module_id": "pilotage", "actions": ["commander_mp"]},
           {"id": "ordonnanceur", "title": "Ordonnanceur·se", "mission": "Lancer les OF à temps",
            "module_id": "pilotage", "actions": ["lancer_of"]}],
 "role_plans": [{"players": 3, "roles": ["responsable_production", "chef_de_ligne", "responsable_maintenance"]},
                {"players": 4, "roles": ["acheteur", "ordonnanceur", "chef_de_ligne", "responsable_maintenance"]}]}
```

(les deux rôles ajoutés aux 3 rôles des modules). Relu par `SimSpec` sans clé perdue, `Action.autopilot` compris.
Refusés, avec les mots attendus : `acheteur.actions = ["x"]` -> « action inconnue x » ; plan 4 sans `ordonnanceur`
-> « action lancer_of sans rôle » ; plan 4 avec `responsable_production` en plus -> « tenue par 2 rôles » ; deux
plans à 4 -> « 4 joueurs en double » ; `players: 0` ou `7` -> erreur de champ ; `acheteur.module_id = "production"`
-> « module production sans action » ; rôle `x` hors des plans -> « dans aucun plan ». Et `generate` à chaque borne de
`limits` (fonction `check_bounds` de test_t4b_contract.py), avant et après l'étape 3b.

Écarts de l'étape 1 tranchés (27/11, architecte ; code : `SimSpec._role_errors`) :
1. Un seul fichier, `tests/test_t7_contract.py`, porte la référence et le contrat : `test_t7_reference.py` n'existe
   pas, les commandes des étapes 1a et 3b ci-dessous le remplacent.
2. La référence joue l'atelier à 2 produits : c'est le minimum de `ATELIER_LIMITS`, aucun changement de contrat.
3. `Role.module_id` n'est pas « le module de la 1re action » : c'est la page de tablette. Avec `actions` non vide, ce
   module doit tenir au moins une action du rôle (« module {m} sans action de ce rôle »), dans n'importe quel ordre.
4. Trois refus de plus, au contrat ci-dessus et testés : id d'action en double, `players` à 0 (erreur de champ),
   « plan à {n} joueurs : rôle inconnu {r} ». Ces messages passent avant les autres contrôles de `_references`, qui
   n'en rend que 10.

### Plan d'exécution T7 (lignes relevées le 27/11, après le merge b483971)

Vérification commune : `.\scripts\test.ps1 -Fast` vert, plus la commande de l'étape.

1. a. fait (27/11), moteur-jeu : `tests/fixtures/t7_reference.json` et, dans `tests/test_t7_contract.py`, la
   référence (8 sous-ensembles des 3 rôles, `held_roles`), les exemples ci-dessus et `check_bounds` ; le code
   nouveau en `xfail(strict=True)`. Commande : `pytest backend\tests\test_t7_contract.py` (python du venv).
   b. fait (27/11), architecte : `game/spec.py`, `Action.autopilot`, `Role.actions`, `RolePlan`,
   `SimSpec.role_plans`, `SimSpec._role_errors` (appelé dans `_references`) ; xfail retiré des 11 tests de 1b
   (relecture et 10 refus). Restent en xfail : 5 tests de 3a, 2 de 3b. Grep `^.{121,}` sur spec.py vide.
2. game-designer, après 1b (sans `Action.autopilot`, la clé `autopilot` copiée dans la spec serait perdue) :
   `ai/packs/usine.yaml`, `roles:` et `role_plans:` (après `modules:`, l. 1436-1502), `autopilot` des actions de
   `pilotage` et `maintenance`. Commande : `pytest backend\tests\test_spec_contract.py`. En parallèle de 3a.
3. a. moteur-jeu, après 1b : `engine.py` `role_plan`, `role_actions`, `action_owners`, `assign_seats`, `act`
   (l. 88-121, argument `plan`) ; `tests/test_t7_roles.py` (plans de 1 à 6 joueurs, refus et messages).
   b. moteur-jeu, après 2 et 3a : `played_actions` et `advance` (l. 124-165), `_week_entries` (l. 168-180) ;
   `factory_game._autopilot` (l. 189-218) et `advance` (l. 224-231) ; `factory_generation._modules` (l. 197-207) et
   `department_id` des rôles (l. 79-81). Commande : `pytest backend\tests\test_t7_contract.py` vert sans changer la
   référence, xfail de 3b retirés. En parallèle de 4.
4. backend-api, après 3a : `api/routes/lobbies.py` `join` (l. 260-275), `_view` (l. 160-178), `choose_role`
   (l. 326-340), `start_game` (l. 343-350), `module_action` (l. 484-503, `plan` au lieu de `occupied_roles`),
   charge de `lobby.members` ; `tests/test_lobbies_t7.py` (matrice et refus ci-dessus, n de 1 à 6, remise à `null`).
   Commande : `.\scripts\test.ps1 -Integration`.
5. godot-dev, codé avec 4 sur ce contrat, vérifié après 4 : `autoload/session.gd` `module_block` (l. 74-88) ->
   `action_block` ; `world/hud.gd` `_blocked_reason` (l. 413-421, appelants l. 341 et 579) ; `tablet/tablet.gd`
   (l. 299, `_role_of` l. 369-376, pages l. 390-410) ; `lobby/lobby_screen.gd` (l. 115-153) ;
   `flow_test.gd` `_check_tablet_roles` (l. 1125-1173). Commande : `.\scripts\godot.ps1 -Check` puis `-Tour`.
6. devops : `gmix/tools/ui_accounts.py`, scénario `flow` (l. 35-42) : `GMIX_FLOW_PLAYER3_TOKEN` à `PLAYER6`.
   Commande : `.\scripts\godot.ps1 -Flow -NoLlm` vert, comptes nettoyés.
7. godot-dev, après 3b, 4, 5 et 6 : `flow_test.gd`, parcours `R` dans les parcours par défaut (l. 114) : 6 joueurs
   (l'un par l'interface, 5 par `_raw`), plan relu à chaque entrée, choix remis à `null`, attribution au lancement,
   409 sur l'action d'un autre, 200 sur la sienne et pour le formateur. Commande : `.\scripts\godot.ps1 -Flow -NoLlm`.
8. documentaliste, avec 7 : docs/roles.md (matrice), docs/kafka.md (`lobby.members.seats`), docs/game-design.md,
   godot/README.md (`action_block`). Commande : Grep de `module_block` hors code, vide.
9. qa-reviewer, en dernier : `.\scripts\test.ps1 -Integration`, `godot.ps1 -Flow`, `-Flow -Pack usine`, `smoke.ps1`.

## 4. Module finance du moteur `factory` (D2)

### 4.1 Activation et paramètres

Actif si et seulement si `spec.finance` est présent (le générateur le recopie de la section `finance:` du pack, nombres
pris dans `values`). `spec.finance` exige `spec.factory`. Les actions de `FINANCE_ACTIONS` sont refusées sans lui.

| `Finance` | Type | Source attendue (D1) |
|---|---|---|
| `customer_terms_days`, `supplier_terms_days` | int, 0 à 60 | Code de commerce L441-10 (plafond) ; usage du secteur |
| `customer_late_share`, `customer_late_weeks` | float 0-1, int 0-12 | Observatoire des délais de paiement (retards) |
| `overdraft_limit` | float ≥ 0 | calibre ; agios au taux `economy.interest_rate_week` |
| `discount_rate` | float 0-0,1 | escompte pour paiement anticipé (client et fournisseur, même taux) |
| `factoring_fee_rate` | float 0-0,1 | coût d'une cession (commission et financement) |
| `dunning_cost` | float ≥ 0 | coût d'une relance |
| `late_penalty_rate_year`, `recovery_fee` | float, float | L441-10 (pénalités), D441-5 (indemnité forfaitaire) |
| `discount_rate_year` | float 0-0,3 | taux d'actualisation de la VAN |
| `loan_offers: list[LoanOffer]` (4 au plus) | `{id, kind, label, rate_year, max_principal, weeks}` | Webstat (taux des crédits aux entreprises, daté) |
| `investments: list[Investment]` (3 au plus) | `{id, label, machine_id, capex, life_years, annual_cash_flow, residual_value, effects}` | dossier d'investissement (calibre) |

Provenance : `finance.<champ>`, `finance.loan_offers.<id>.<champ>`, `finance.investments.<id>.<champ>`.
Contrôles `SimSpec` : ids d'offre et d'investissement uniques ; `machine_id` connu ; `effects` : clés dans
`MACHINE_EFFECTS` (`cycle_min`, `mtbf_h`, `mttr_h`, `setup_min`, `defect_rate`), facteurs positifs.

### 4.2 État (`state["finance"]`, puis `public_state`)

`{"receivables": [Due], "payables": [Due], "loans": [Loan], "investments": [ids faits], "agios": float,
"penalties": float}` ; `Due = {id, counterparty, amount, due_week, late}`, `Loan = {id, offer_id, principal,
rate_week, weeks_left}` (modèles de `spec.py`, pour les tests). `PUBLIC_ROOTS` gagne `finance` en D2, dans le même
commit que `public_state` (un test garde l'égalité) ; pas avant.

### 4.3 Semaine (ordre dans `factory_game.advance`, après la simulation de l'usine)

1. Ventes expédiées : une créance par client et par semaine, `amount` = quantité x prix, `due_week` = semaine +
   ceil(`customer_terms_days` / 7). Achats de MP reçus : une dette par fournisseur, idem avec `supplier_terms_days`.
   Ce sont les seuls règlements qui cessent d'être immédiats ; les autres coûts restent payés comptant.
2. Créances échues : tirage à graine (`spec.seed`, semaine, id) ; avec la probabilité `customer_late_share`, la
   créance passe `late`, `due_week += customer_late_weeks` ; sinon encaissée. Créance en retard encaissée : plus
   pénalités (`amount x late_penalty_rate_year x jours de retard / 365`) et `recovery_fee`.
3. Dettes échues, par `due_week` croissante, tant que `cash - montant >= -overdraft_limit` ; sinon `late`, reportée
   d'une semaine, pénalités dues au paiement (même formule).
4. Prêts : intérêts `principal x rate_week` (`rate_week = rate_year / 52`, taux proportionnel) ; `emprunt` :
   amortissement constant `principal / weeks_left` ; `credit_court_terme` : capital remboursé à `weeks_left == 0`.
5. Agios : `max(0, -cash) x economy.interest_rate_week`, cumulés dans `agios`.
6. Indicateurs (§4.5).

### 4.4 Actions (handlers de moteur-jeu, un test par action)

| Action | Champs (`ActionField`) | Effet | Refus (`GameRuleError`, 409) |
|---|---|---|---|
| `proposer_escompte` | `receivable` (choice, source `receivables`) | `due_week` = semaine + 1, `amount x (1 - discount_rate)` | créance en retard ou inconnue |
| `relancer_client` | `receivable` | créance en retard : `due_week` = semaine + 1 ; coût `dunning_cost` | créance pas en retard |
| `affacturer` | `receivable` | encaissée cette semaine, `amount x (1 - factoring_fee_rate)` ; sans recours | créance inconnue |
| `payer_fournisseur` | `payable` (source `payables`) | payée maintenant, `amount x (1 - discount_rate)` | découvert dépassé |
| `emprunter` | `offer` (source `loan_offers`), `amount` (int) | `cash += amount`, prêt créé | `amount > max_principal`, prêt de cette offre en cours |
| `investir` | `investment` (source `investments`) | `cash -= capex` ; `effects` multiplient les champs de la machine dès la semaine suivante | déjà fait, découvert dépassé |

VAN : `finance.npv(capex, annual_cash_flow, life_years, rate_year, residual_value=0) -> float` (module pur
`gmix.game.finance`) = `-capex + somme(CF / (1+r)^t, t = 1..n) + RV / (1+r)^n`. Cas de test : 100 000, 30 000, 5 ans,
8 % -> 19 781,30 (à 0,01 près). Le flux annuel est l'estimation du dossier, pas le résultat simulé : le débrief
compare les deux.

### 4.5 Indicateurs (`FINANCE_INDICATORS`, permis dans `criteria` et `objectives` si `spec.finance`)

`CA_jour` = CA cumulé / (7 x semaines écoulées) ; `achats_jour` idem sur les achats de MP ; 0 si le dénominateur est
nul. `net_cash` = `cash` - capital des crédits court terme ; `wcr_days` = (stocks valorisés au coût + créances -
dettes) / `CA_jour` ; `dso` = créances / `CA_jour` ; `dpo` = dettes / `achats_jour` ; `agios` = cumul. Jours
calendaires, sans TVA (écart avec la Banque de France, base 360 et CA TTC : §9).

## 5. Conception et documents du formateur

- `Section = "domain" | "concept" | "world" | "cast" | "journey"` (clés de `DesignOrigin.sections`).
- `DesignRequest` gagne `domain: str | None` (slug ; le pack doit être de ce domaine, sinon 422) et
  `document_ids: list[UUID]` (5 au plus, sans doublon). En T8, l'API vérifie que chaque document appartient à
  l'acteur (admin : tous), sinon 404, et qu'il est indexé, sinon 409.
- Régénération (T9, pas avant : elle ne régénérerait rien) : `FactorySection += "monde"`,
  `FACTORY_SECTIONS["monde"] = frozenset({"world_plan", "ambiance"})`.
- `TrainerExcerpt = {id: "<document_id>#<n>" (n à partir de 1), document_id, title (1-120), text (1-600),
  validated}` ; `SimSpec.trainer_excerpts` (10 au plus) ne garde que les passages **cités**, par
  `DesignObjective.excerpt_ids` (2 au plus). Contrôles : ids uniques et cohérents avec `document_id`, chaque citation
  connue, chaque passage cité. Un brouillon peut citer un passage non validé ; `POST /games/{id}/publish` relit
  `validated` en base, recopie la valeur dans la spec et répond 422 (liste des ids) si un passage cité ne l'est pas.
- Les passages servent aux étapes 1 (`design.domain`) et 7 (`design.journey`) ; Godot les affiche « source du
  formateur, non vérifiée par G-mix ». **Les PNJ ne les citent pas** (ils ne disent que les faits du moteur ; un
  passage peut contenir des nombres que le garde-fou T6 remplacerait). Aucun nombre d'un passage n'entre dans le moteur.

REST (T8, backend-api) :

| Route | Rôles | Réponse |
|---|---|---|
| `POST /games/documents?title=...` (corps brut, sans jeu : dépôt avant la conception) | formateur, admin ; joueur 403 | 201 `{document_id, title, media_type, size, status: "en_cours"}` |
| `POST /games/{id}/documents?title=...` (rattache à un brouillon) | propriétaire du jeu, admin ; joueur 403 ; autre formateur 404 | 201, idem |
| `GET /games/{id}/documents` | idem | 200 `[{document_id, title, status, excerpts: [{id, n, text, validated, cited}]}]` |
| `DELETE /games/{id}/documents/{doc}` | idem | 204 (détache ; supprime objet et passages si aucun autre jeu ne le lie) ; 409 si le jeu est publié |
| `PUT /games/{id}/documents/{doc}/excerpts/{n}` corps `{"validated": bool}` | idem | 200 `{id, validated}` ; 404 inconnu |

Formats : corps brut (pas de multipart, aucune dépendance ajoutée), `Content-Type` `application/pdf` (couche texte
exigée, pas d'OCR : 422 « document sans texte »), `text/markdown` ou `text/plain` en UTF-8 ; 5 Mo par fichier (413) ;
5 documents par jeu ; 200 000 caractères extraits au plus ; segments de 600 caractères au plus, coupés aux
paragraphes puis aux phrases, 400 par document au plus. Stockage : bucket `gmix-knowledge`, clé
`formateur/<owner_id>/<document_id>.<ext>`. Base (alembic) : `trainer_documents(id, owner_id, title, media_type, size,
sha256, status: en_cours | pret | echec, created_at)`, `game_documents(game_id, document_id)` ; les passages (n°,
texte, `validated`, embedding) sont des segments du RAG avec `document_id` et `owner_id` (rag-knowledge). Recherche :
filtrée par les documents liés au jeu (ou par `document_ids` pendant la conception), jamais ceux d'un autre formateur.

## 6. Kafka

Aucun topic nouveau. `generation.progress.stage` prend une valeur de `spec.DesignStage` : `domaine`, `concept`,
`simulation`, `monde`, `placement`, `personnages`, `parcours`, `controle` (le worker v0 émet `concept`, `simulation`,
`checks` ; `checks` devient `controle` en T9). Documents (T8), sur les topics déjà déclarés, groupe `worker-rag`,
clé `correlation_id = document_id`, traitement idempotent (une réindexation remplace les segments) :

| Type | Topic | Émetteur -> destinataire | Payload |
|---|---|---|---|
| `document.requested` | gmix.rag.commands | API -> worker `rag` (nouveau, `worker.ps1 rag`) | document_id, owner_id, object_key, media_type, sha256 |
| `document.indexed` | gmix.rag.events | worker ; journal (statut lu par `GET /games/{id}/documents`) | document_id, excerpts, chars |
| `document.failed` | gmix.rag.events | idem | document_id, error |
| `document.uploaded`, `document.deleted`, `excerpt.validated` | gmix.audit | API | ids, rôle de l'auteur |

## 7. Tests à écrire en T2 (qa-reviewer, `backend/tests/test_spec_0013.py`)

1. Non-régression : chaque pack de `ai/packs/` et l'atelier, `generate(default_params(pack))` puis
   `SimSpec.model_validate` passe ; `world.buildings == []`, `finance is None`, `trainer_excerpts == []`.
2. `GameParams` : `suppliers=5` sur usine -> erreur « non réglable » ; `ambiance="xx"` -> « ambiance inconnue » ;
   `world_plan=[{archetype: "xx", ...}]` -> « archétype inconnu » ; départements répétés -> « un seul bâtiment ».
3. `DesignRequest` : `fixed={"buildings": 2}` sur usine -> ValueError (pack sans `limits.buildings`) ;
   `domain="finance-entreprise"` avec `pack="usine"` -> « n'appartient pas » ; `domain="supply-chain"` -> valide ;
   `document_ids` en double -> erreur ; 6 documents -> erreur.
4. Campus (spec usine générée, pack patché par monkeypatch de `load_pack` avec un archétype, une ambiance) : un
   bâtiment, une pièce logeant tous les départements intérieurs, `room_id` posés, `template="campus"` -> valide ;
   puis une mutation chacune -> message attendu : `template="usine"` (« hors d'un world.template ») ; bâtiment sans
   pièce (« pur décor ») ; département non logé (« dans aucune pièce ») ; `room_id` absent (« room_id None au lieu
   de ») ; pièce hors du bâtiment ; `kind` non permis ; `style` inconnu ; `rooms` sans `buildings`.
5. `Room` id `b5.atelier` et `Building` id `x1` -> ValidationError ; `TrainerExcerpt` id `autre#1` ou `<uuid>#0` ->
   erreur.
6. Passages : spec avec `design` (fixture existante), un passage cité par un objectif -> valide ; passage non cité
   -> « cité par aucun objectif » ; `excerpt_ids` inconnu -> « absent de trainer_excerpts » ; `validated=False` reste
   valide (brouillon).
7. Finance : spec usine + `finance` minimal (`customer_terms_days=30`, `supplier_terms_days=45`, `overdraft_limit`,
   `discount_rate_year`) -> valide ; critère `dso` permis avec finance, refusé sans ; `investments.machine_id` inconnu,
   `effects={"vitesse": 1.1}` et `{"mtbf_h": 0}` -> erreurs ; `finance` sur l'atelier -> « moteur factory requis » ;
   module avec action `investir` sans `finance` -> « module finance absent » ; `customer_terms_days=61` -> erreur.
8. Usine variée : `bom` avec `product_id` sur 2 produits et 2 lignes -> valide ; produit sans ligne ou sans
   nomenclature -> erreur ; sans `product_id`, le test existant « différent de celui de l'usine » reste vert ;
   `clients` en double ou produit inconnu -> erreur ; `walk_m_per_min` seul -> « se renseignent ensemble ».
9. `test_spec_contract.py` existant inchangé et vert (dont la mutation `template="atelier"`).
10. T4b (étape 1 du plan, moteur-jeu) : `generate` à chaque borne de `limits` (min, max et défaut de chaque clé, puis
    toutes au max) -> `SimSpec` relit la spec sans clé perdue ni exception ; `GameParams(products=3, clients=2)` ->
    « au moins un par produit » ; `products=3` sans `clients` -> 3 clients ; atelier à 4 produits -> valide ;
    2 articles sans `product_id` -> « une seule matière » ; `c1` pour p1 et p2 -> « partagée » ;
    `Client.pickup_window_min` hors de la journée -> « créneau d'enlèvement », « 480 » ; produit sans client ->
    « produit p2 sans client » ; `units_per_pallet=0` -> erreur ; `initial_orders` (forme `InitialOrder` :
    `{offer_id, pallets, arrival_day}`) sur une offre inconnue -> « o99 », ou seconde commande de `c1` -> « c1 ».

## 8. Plan d'exécution

| # | Étape | Agent | Fichiers | Critère de fin | Parallèle |
|---|---|---|---|---|---|
| 1 | Tests du §7 | qa-reviewer | backend/tests/test_spec_0013.py | `test.ps1 -Fast` vert | fin de T2 |
| 2 | T3 : docs (renvoi à cette annexe, §4.2 de l'ADR) | documentaliste | docs/ hors ADR | références à jour | avec 3, 4, 5 |
| 3 | T4 : bornes, secteurs, types de machine, variantes | game-designer | ai/packs/usine.yaml | `limits` du §1, provenance | avec 4 |
| 4 | T4 : `generate` (§1, §3), placeur à graine | moteur-jeu | game/generation.py, game/layout.py, tests | §7 vert, 8 empreintes sur 12 graines | avec 3 |
| 5 | D1 : corpus finance | rag-knowledge, game-designer | knowledge/finance-entreprise/ | §4.1 sourcé et daté | avec 3, 4 |
| 6 | T5 : archétypes, zonage, `place_campus`, `travel_min`, Godot campus | game-designer, assets-3d, moteur-jeu, godot-dev | §2 bis (plan détaillé) | ADR 0013 T5 | après 4 |
| 6 bis | T7 : rôles répartis | 5 agents (§3 ter) | §3 ter | matrice testée, `-Flow` à 6 | après T4b |
| 7 | T8 : routes, worker `rag`, passages, publication | backend-api, pipeline-kafka, rag-knowledge, godot-dev | §5, §6 | droits des 3 rôles testés | après 6 |
| 8 | D2 : pack et module finance (§4) | game-designer puis moteur-jeu | ai/packs/finance-entreprise.yaml, game/factory_game.py, game/finance.py | un test par action, VAN du §4.4 | avec 7 |
| 9 | T9 : section `monde`, étapes du §6 | ia-runtime, pipeline-kafka, moteur-jeu | §5, §6 | ADR 0013 T9 | après 7, 8 |
| 10 | Relecture | qa-reviewer | - | `test.ps1 -Integration`, `-Flow` | toujours en dernier |

## 9. Points ouverts

- Base des jours, assiette et taux des prêts : tranchés en D1 (`docs/audits/finance-entreprise-conventions.md`).
  Jours calendaires (7 par semaine) comme L441-10 ; la BdF compte 360 jours (DSO 1,4 % plus court, dit au débrief).
  Tout hors taxe : sans TVA, le ratio HT/HT égale le ratio TTC/TTC de la BdF. Taux proportionnel `rate_year / 52`,
  convention du TEG des crédits professionnels (Code de la consommation, R314-2) ; `rate_year` est un taux nominal,
  converti depuis le taux actuariel BdF dans le pack.
- Même `discount_rate` côté clients et fournisseurs : simplification, à séparer en D2 si les sources divergent.
- `Factory.lot_size`, `pf_min` et `pf_max` restent communs à tous les produits en T4 ; un réglage par produit serait un
  ajout facultatif (règle commune). T4b : calcul des seuils communs au complément 5 du §3 bis.
