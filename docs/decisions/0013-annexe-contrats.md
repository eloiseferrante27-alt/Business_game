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
Bornes de jeu à poser par game-designer (provenance `calibre`, note) : usine `limits.suppliers: [3, 8, 3]`,
`limits.clients: [1, 4, 1]`, `limits.products: [1, 4, 1]` en T4, `limits.buildings: [1, 3, 1]` en T5.

## 2. Monde à plusieurs bâtiments (`Building`, `Room`, `World`, `Department.room_id`)

```python
class Building:  id: "b1".."b4" ; archetype: Code ; label: str (2-40) ; area: Rect ; entrance: Point ; style: Code
class Room:      id: "<bâtiment>.<pièce>" ; building_id ; kind: Code ; label (2-40) ; area: Rect
                 department_ids: list[Code] (1 au moins) ; doors: list[Point] (1 au moins)
class World:     template: "atelier" | "usine" | "campus" ; buildings: [] (4 au plus) ; rooms: [] ; ambiance: None
class Department: room_id: str | None = None
```

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

Producteur : `layout.place_campus(spec, plan: list[PlannedBuilding], seed: int) -> dict` (moteur-jeu, T5), pur et
déterministe à graine ; 20 graines dérivées de `seed`, puis repli sur le programme de référence. Plan vide :
`place_world` actuel (hall en U, `template: usine`). `apply_edits` reste sans graine.

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
    walls: wall_brick                     # ids d'assets (ai/assets.yaml, statut importe)
    door: door_industrial
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

`together` : pièces voisines (porte commune ou couloir de moins d'une cellule) ; `apart` : bâtiments différents ou
au moins deux cellules d'écart ; `same_building` : même bâtiment ; `max_walk_m` : `travel_min` à pied sous la valeur.

Exemple (extrait) :

```json
{"world": {"template": "campus", "ambiance": "hiver_industriel",
  "buildings": [{"id": "b1", "archetype": "hall_production", "label": "Hall A", "area": [0, 0, 48, 32],
                 "entrance": [24, 0], "style": "brique"}],
  "rooms": [{"id": "b1.atelier", "building_id": "b1", "kind": "atelier", "label": "Atelier",
             "area": [0, 0, 48, 24], "department_ids": ["ligne", "magasin_mp"], "doors": [[24, 24]]}]},
 "departments": [{"id": "ligne", "label": "Ligne", "area": [4, 4, 40, 20], "room_id": "b1.atelier"}]}
```

## 3. Usine variée et trajets (T4, T5)

| Ajout | Défaut | Sens |
|---|---|---|
| `BomItem.product_id: str \| None` | None = `Factory.product_id` | dès qu'un article le porte, mode plusieurs produits : chaque produit a au moins une ligne (`Line.product_id`) et une nomenclature ; sinon, règle actuelle (toutes les lignes font `Factory.product_id`) |
| `Factory.clients: list[Client]` (4 au plus) | [] : `customer` seul, acheteur de `product_id` | `Client = Customer + {id: "c1".."c4", name, product_id, site_id}` ; ids uniques, produit et site connus ; `customer` est alors ignoré par le moteur (le générateur y recopie `clients[0]`) |
| `Machine.type: Code \| None` | None : type unique | type du catalogue du pack pour l'opération (clé de provenance du type) |
| `Logistics.walk_m_per_min`, `forklift_m_per_min` | None (ensemble, ou aucune) | renseignées : trajets calculés, `kit_min` ne compte plus que la préparation ; None : `kit_min` et `repair_travel_min` fixes |

`Factory.product_id` reste le produit de référence (le premier). Les fournisseurs (3 à 8) n'ont besoin d'aucun champ :
`suppliers`, `offers` et les sites fournisseurs existent déjà.

Trajets (moteur-jeu, T5) : `layout.travel_min(spec, a: str, b: str, mode: Literal["marche", "chariot"]) -> float`,
pure, `a` et `b` ids de département ; plus court chemin par les portes et les entrées (distance de Manhattan sur la
grille, couloirs compris), divisé par la vitesse du mode. Kit = `kit_min` + `travel_min(magasin MP -> département de la
ligne, chariot)` ; dépannage = `travel_min(maintenance -> ligne, marche)` au lieu de `repair_travel_min`. Les
départements de départ sont déclarés par le pack (clé fixée par moteur-jeu et game-designer en T5). Provenance :
`logistics.walk_m_per_min`, `logistics.forklift_m_per_min`.

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

## 8. Plan d'exécution

| # | Étape | Agent | Fichiers | Critère de fin | Parallèle |
|---|---|---|---|---|---|
| 1 | Tests du §7 | qa-reviewer | backend/tests/test_spec_0013.py | `test.ps1 -Fast` vert | fin de T2 |
| 2 | T3 : docs (renvoi à cette annexe, §4.2 de l'ADR) | documentaliste | docs/ hors ADR | références à jour | avec 3, 4, 5 |
| 3 | T4 : bornes, secteurs, types de machine, variantes | game-designer | ai/packs/usine.yaml | `limits` du §1, provenance | avec 4 |
| 4 | T4 : `generate` (§1, §3), placeur à graine | moteur-jeu | game/generation.py, game/layout.py, tests | §7 vert, 8 empreintes sur 12 graines | avec 3 |
| 5 | D1 : corpus finance | rag-knowledge, game-designer | knowledge/finance-entreprise/ | §4.1 sourcé et daté | avec 3, 4 |
| 6 | T5 : archétypes, zonage, `place_campus`, `travel_min`, Godot campus | game-designer, assets-3d, moteur-jeu, godot-dev | §2, §3 | ADR 0013 T5 | après 4 |
| 7 | T8 : routes, worker `rag`, passages, publication | backend-api, pipeline-kafka, rag-knowledge, godot-dev | §5, §6 | droits des 3 rôles testés | après 6 |
| 8 | D2 : pack et module finance (§4) | game-designer puis moteur-jeu | ai/packs/finance-entreprise.yaml, game/factory_game.py, game/finance.py | un test par action, VAN du §4.4 | avec 7 |
| 9 | T9 : section `monde`, étapes du §6 | ia-runtime, pipeline-kafka, moteur-jeu | §5, §6 | ADR 0013 T9 | après 7, 8 |
| 10 | Relecture | qa-reviewer | - | `test.ps1 -Integration`, `-Flow` | toujours en dernier |

## 9. Points ouverts

- Base des jours (365 calendaires et CA hors taxe dans le jeu, contre 360 et CA TTC à la Banque de France) et taux
  proportionnel des prêts (`rate_year / 52`) : à confirmer par game-designer en D1, avec citation, avant D2.
- Même `discount_rate` côté clients et fournisseurs : simplification, à séparer en D2 si les sources divergent.
- `Factory.lot_size`, `pf_min` et `pf_max` restent communs à tous les produits en T4 ; un réglage par produit serait un
  ajout facultatif (règle commune).
