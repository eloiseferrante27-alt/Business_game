# 0013 : générer des mondes et des business games vraiment différents selon la demande du formateur

Date : 2026-11-21. Statut : **accepté** (décisions de l'utilisateur du 21/11, §6). Contrats de code écrits en T2
(24/11) : `spec.py` et [annexe 0013](0013-annexe-contrats.md), qui fait foi pour les champs, invariants et routes ;
`topics.py` inchangé.
Amende : ADR 0007 d.9 (plan en U : plan de référence et repli) ; ADR 0008 d.3, d.4 et d.6, et son annexe §4.1, §5,
§8, §9, §10 (pipeline en cinq agents, RAG à l'étape 1, série V) ; ADR 0009 d.1, d.2, contrat de `place_world` et
« Après » (placeur à graine, bâtiments simulés, tranches 2 et 3) ; ADR 0010 §3 et §7.3, annexe 0010 §7 (portée de la
conception). Ne touche pas aux principes : l'IA choisit dans des catalogues, le moteur calcule seul (ADR 0006),
chaque valeur a sa provenance (exigence n° 1).

## Contexte

Paroles de l'utilisateur : « il faut que ça génère vraiment des mondes et des business games différents en fonction
de ce qui est demandé par le formateur » (21/11) ; « je ne veux pas que le monde soit toujours le même » ; variation
« visuelle et structurelle, mais il peut avoir plusieurs bâtiments et pièces dans lesquels les joueurs, agents,
rôles, actions etc sont répartis » ; « une équipe d'agents spécialisés avec un orchestrateur et des sub-agents font le
monde avec l'aide de technologie procédurale et d'une expertise » (19/11).

Les ADR 0006 à 0012 ont rendu le jeu **juste** et **jouable**, mais pas **varié** : la conception par l'IA a été
réduite à un appel qui règle une seule usine (ADR 0010 §7.3, `factory.design`), et le placeur a été voulu sans
hasard (ADR 0009 d.1 et contrat de `place_world`). La documentation décrit ce jeu unique comme la cible
(prompt-projet.md §5 : « plan en U conservé » ; architecture.md : « hall de 48 x 30 m en U »).

## 1. Écart : ce que le formateur demande, ce qui en change vraiment

Relevé du 21/11 par lecture du code (`llm/factory_design.py`, `game/factory_generation.py`, `game/layout.py`,
`ai/packs/usine.yaml`, `godot/scenes/world/world.gd`). Oui = effet réel et visible ; en partie = effet limité ; non.

| Demande | Mécanique de jeu | Monde 3D | Constat |
|---|---|---|---|
| Secteur (`theme`) | en partie | non | 2 secteurs (industrie, automobile) : noms, prix, MP et libellés d'opérations changent ; mêmes machines m1-m4, même plan |
| Modules joués | oui | non | 3 modules (pilotage, production, maintenance) : joué ou pilote automatique ; les 11 départements sont toujours posés |
| Agents en plus, ton des agents | en partie | en partie | 1 agent possible (`direction`) ; le ton change le caractère, pas les faits |
| Difficulté, réglages (`tunings`) | oui | non | valeurs des profils du pack (9 clés réglables) |
| Durée, aléas, plan d'aléas | oui | non | 4 à 12 semaines, 6 aléas, 3 semaines imposées au plus |
| Nombre de produits | non | non | `limits.products: [1, 1, 1]` ; `Factory.product_id` unique (« toutes les lignes font ce produit ») |
| Nombre de lignes (option) | oui | **oui** | 1 à 3 lignes de 4 machines : la seule variation structurelle visible |
| Réseau (classe de distance) | oui | en partie | délais dérivés des km ; l'anneau de la carte change, toujours 3 fournisseurs (un par profil) et 1 client |
| Joueurs min et max | non | non | 3 rôles au plus, quel que soit le nombre de joueurs |
| Nom d'entreprise | non | non | texte seulement |
| Graine | en partie | non | tire le produit, l'entreprise, les pannes et la demande ; `place_world` ne la lit pas ; décor Godot à graine 42 (`world.gd:871`) |
| Consigne libre (brief) | en partie | non | traduite en choix ci-dessus (42/50 consignes respectées, prompt v4) ; aucun texte conçu : `design.objectives`, personnages, didacticiel et débrief ne sont produits par aucun module (Grep : seul `spec.py` les déclare) |
| Documents du formateur | non | non | aucune route de dépôt (EX-12) |
| Domaine | non | non | 15 domaines déclarés (`ai/domains.yaml`), 1 corpus (`knowledge/supply-chain/`, 53 fiches), 1 pack conçu par l'IA (usine), 1 pack gelé (atelier) |
| Demande hors pack | non | non | listée dans `design.unmet`, non simulée (voulu) |

Bilan : la demande règle des **chiffres** d'une usine unique ; elle ne change ni la **structure** (bâtiments,
départements, produits, réseau, rôles), ni le **visuel** (2 modèles de machine sur environ 8, 80 assets au
catalogue), ni les **textes** du jeu. Deux briefs très différents donnent le même monde à la couleur des KPI près.

## 2. Ce qui doit varier, et qui le décide

Règle de répartition (inchangée dans son esprit, étendue au monde) :
- **Données sourcées du pack** : tout ce qui est un fait ou un chiffre (catalogue fermé, provenance par valeur).
- **Procédural à graine** : tout ce qui est une disposition (tailles dans des bornes, positions, variantes d'assets,
  décor), contraint par des règles typées et testées. Même paramètres + même graine + mêmes retouches = même monde.
- **Agents IA** : le choix et la répartition dans un schéma fermé construit depuis le pack, et les textes sans chiffre.
- **Moteur seul** : tout effet, durée, coût, délai, indicateur, verdict, fait dit par un PNJ.

| Dimension | Données sourcées (pack) | Procédural (graine) | Agents IA (schéma) | Moteur seul |
|---|---|---|---|---|
| Secteur et domaine | domaines proposés (pack chargé, notions citées, assets couverts, audit signé ; ADR 0009 d.7) ; secteurs avec produits, MP, fournisseurs, clients réels ou `exemple` | aucun | domaine, pack, secteur, notions visées parmi celles du pack | moteur du pack (`engine: factory` ou `weekly`) |
| Modules et mécaniques | modules, actions, notions, aléas, réglages calibrés | aucun | modules joués, réglages, plan d'aléas, objectifs (verbe, notion, indicateur) | effets, pilote automatique, verdict |
| Rôles et PNJ | rôles par module et département, caractères, clés de faits (`agent.facts`), listes de prénoms | prénoms et figurants tirés si l'IA ne choisit pas | découpage des rôles selon le nombre de joueurs, nom, caractère, présentation, pièce de chaque PNJ | faits (`briefings`), états des agents |
| Produits et réseau | 1 à 4 produits par secteur avec nomenclature, 3 à 8 fournisseurs, 1 à 4 clients, classes de distance (km sourcés) | fournisseurs retenus dans la liste, place sur l'anneau | nombre de produits, de fournisseurs et de clients, classe de distance de chaque site | délais, prix, fiabilité, demande, OTIF |
| Bâtiments, pièces, affectation | archétypes de bâtiment (hall, entrepôt, bureaux, atelier de maintenance, laboratoire qualité), pièces permises, règles de zonage avec provenance (INRS, ISO 9001) | taille de chaque bâtiment dans ses bornes, position sur le site, partition en pièces, couloirs, portes | programme : combien de bâtiments, quel département dans quel bâtiment, où se tient chaque rôle | temps de trajet entre pièces et bâtiments (dérivé du plan), donc kits, transferts, interventions |
| Visuel | variantes d'assets par rôle d'objet (seulement `importe`), palettes, ambiances | variante de chaque objet, décor extérieur, écrit dans la spec (plus de graine 42 côté client) | ambiance (palette, saison, végétation) selon le brief | rien : l'état anime le monde, il ne le change pas |
| Sources du formateur | aucune (le document n'est pas une source du pack) | aucun | passages cités, pris parmi ceux que le formateur a validés | rien : aucun chiffre d'un document n'entre dans le moteur |

Ce qui ne bouge pas : la 3D ne montre que ce qui est calculé (ADR 0009 d.2, question 1). Un bâtiment séparé n'est
permis que parce que le moteur en tire un temps de trajet ; un bâtiment de pur décor reste interdit (§6.7).

Domaines : sur 15 déclarés, un seul est jouable aujourd'hui (supply chain, pack usine), et il penche vers la production
(TRS, goulot, pannes). La Première version en aura **deux** (§6.2) : la supply chain, variée en structure (T4, T5,
T7), et la **finance d'entreprise** (`finance-entreprise`, choisie le 21/11, §6.2), auditée comme la première (D1 à
D3). Les 13 autres restent grisés avec leur raison.

## 3. Architecture : l'équipe d'agents de conception

### 3.1 Options

| Option | Effet sur la variété | Rejet ou choix |
|---|---|---|
| A. Un LLM écrit le monde et les règles | maximal | rejeté : échec mesuré de l'ancien pipeline (ADR 0008, contexte) |
| B. Procédural seul, sans IA | le brief ne sert plus à rien | rejeté : contraire à la vision |
| C. Orchestrateur LLM qui appelle des sous-agents LLM | élevé | rejeté : un 3b qui planifie ajoute des appels et des erreurs, l'ordre est fixé par les dépendances |
| **D. Orchestrateur en code, cinq agents IA à sortie typée en série, placeur procédural, garde-fous** | élevé | **retenu** (§6.4) |

### 3.2 Les étapes

L'orchestrateur est du code déterministe dans le worker `generation` (module pur `gmix.game.design_pipeline`,
propriétaire moteur-jeu ; appels IA par pipeline-kafka). Les **cinq agents IA** sont les étapes 1, 2, 4, 6 et 7 ;
chacun est une **tâche** de ai/models.yaml, avec un schéma JSON construit depuis le pack et les sorties des étapes
précédentes : il ne peut citer qu'un id qui existe. L'étape 8 est un garde-fou (questions fermées), pas un agent de
conception. Un seul modèle chargé, étapes **en série**, cache par étape (une reprise retrouve les étapes faites).

| # | Étape | Nature | Entrée | Sortie typée | Budget (3b) | Repli |
|---|---|---|---|---|---|---|
| 0 | accueil | code | brief, `fixed`, documents validés | brief filtré (injection), contraintes | 1 s | refus lisible |
| 1 | domaine et sources | IA `design.domain` + RAG | brief, domaines proposés, extraits RAG (corpus du domaine, passages validés du formateur) | `DomainChoice` : pack, secteur, notions visées (ids), passages retenus (ids) | 15 s | domaine et secteur du formulaire |
| 2 | mécaniques | IA `design.concept` (= `factory.design` étendu) | brief, `DomainChoice`, catalogue du pack | `ConceptChoice` : modules, réglages, aléas, produits, fournisseurs, clients, lignes, distances | 15 s | `default_params` |
| 3 | squelette chiffré | code (`generate`) | `GameParams` | produits, offres, lignes, machines (types par opération) | 1 s | aucun : déterministe |
| 4 | bâtiments et pièces | IA `design.world` | départements de la spec, archétypes et zonage du pack | `WorldPlan` : bâtiments (archétype, départements logés), ambiance | 20 s | programme de référence du pack (hall unique en U) |
| 5 | placeur | code (`layout.place_campus`) | `WorldPlan`, graine | bâtiments, pièces, blocs, portes, couloirs, décor | 3 s | 20 graines dérivées, puis programme de référence |
| 6 | rôles et PNJ | IA `design.cast` | rôles, pièces, caractères, nombre de joueurs | `CastPlan` : découpage des rôles, PNJ (nom, caractère, présentation, pièce) | 20 s | défauts du pack |
| 7 | parcours | IA `design.journey` | notions visées, passages retenus, indicateurs, panneaux, outils | `JourneyPlan` : titre, contexte, objectifs, didacticiel, débrief, panneaux et outils | 25 s | défauts du pack |
| 8 | contrôle d'exactitude | code, puis IA `design.fact_check` | spec complète | `FactReport` : erreurs par section | 5 s + 20 s | section fautive repliée |

Garde-fous, dans l'ordre de l'étape 8 : `SimSpec`, `check_design`, `check_placement`, texte sans chiffre, chaque
notion citée a sa citation, chaque passage du formateur cité est validé, partie d'essai en pilote automatique
(jouable en découverte, exigeant en expert, ADR 0008 d.2) ; puis seulement une question fermée par texte au modèle
(« ce texte affirme-t-il autre chose que la notion ou le passage cité ? »). Une section fautive a 2 réparations au
plus (avec la liste des erreurs), puis son repli : le formateur reçoit toujours un jeu jouable. Plafonds : 60 s par
étape, 10 min par job (§3.3).

### 3.3 Budget, modèles et poste

- Budget **inchangé** (§6.5) : 3 min en médiane, 10 min au plus, puis repli des sections restantes. Estimation
  nominale : 5 appels de conception et 1 contrôle de 5 à 25 s sur qwen2.5:3b (une conception v4 prend 4 à 7 s), soit
  1 min 30 environ ; 3 min avec 2 réparations.
- Modèles (§6.6) : chaque tâche `design.*` pointe sur qwen2.5:3b dans ai/models.yaml. Une tâche dont le 3b échoue aux
  critères de l'éval (annexe 0008 §8) passe sur qwen2.5:7b **pour cette tâche seulement** ; le choix se fait à l'éval,
  jamais à l'exécution (pas de bascule de modèle en cours de job : 7 à 27 s de chargement, dialogue délogé). Une
  conception qui sert une tâche sur le 7b est refusée (409) pendant un lobby en cours (ADR 0008 question 2).
- VRAM : 3b (2,3 Go) et embeddinggemma (0,7 Go) tiennent ensemble ; le dialogue des PNJ reste servi pendant une
  conception. Avec le 7b (4,9 Go), l'étape 1 fait ses embeddings avant de le charger.
- RAM : rien en plus (même worker, étapes en série). Les documents du formateur sont découpés et indexés par le worker
  RAG existant (`gmix.rag.commands`), hors du job de conception.
- Mesure : `ai/evals/game.design.jsonl` gagne une série V (variété) : 12 briefs supply chain contrastés qui doivent
  donner au moins 8 structures distinctes (empreinte du programme de bâtiments, produits, réseau, rôles), 4 briefs du
  second domaine (finance d'entreprise) où l'étape 1 choisit `finance-entreprise` 4 fois sur 4, et les critères de l'annexe 0008 §8 par étape.

### 3.4 Ce qui change par rapport aux ADR 0007 à 0010

- 0008 d.4 prévoyait 3 sections (concept, cast, journey) ; la v0 en fait 1. 0013 en fait 5 (domaine, mécaniques,
  monde, personnages, parcours) plus un contrôle, et rend les textes conçus (0008 d.1, jamais livrés pour l'usine).
- 0008 d.4 excluait le RAG : l'étape 1 l'utilise, pour choisir et citer, jamais pour un chiffre.
- 0008 d.3 (B) : la bibliothèque de primitives n'est extraite que si le second domaine ne tient pas dans un moteur
  existant ; ce cas sort de l'estimation (§5, risques) et demande un ADR.
- 0009 d.1 et contrat de `place_world` : le placeur devient **déterministe à graine** (au lieu de « sans hasard ») et
  gagne un niveau bâtiment ; `apply_edits` (d.8) reste sans graine. Le critère 0009-1 (même spec, même monde) tient.
- 0007 d.9 : le plan en U et le quai unique deviennent le **programme de référence** du pack usine et le repli du
  placeur.
- 0010 §7.3 (« l'IA ne conçoit que l'usine ») est remplacé par §6.2 : l'IA conçoit l'usine variée et le second
  domaine ; l'atelier (moteur `weekly`) reste gelé, puisque le second domaine choisi, la finance d'entreprise,
  réutilise le moteur `factory` (§6.2).

### 3.5 Contrats (fixés en T2 le 24/11 : `spec.py` et [annexe 0013](0013-annexe-contrats.md))

Esquisse d'origine, gardée pour l'historique ; **l'annexe fait foi**. Écarts de T2 : `Room` est aussi lié par
`Department.room_id` (deux sens, vérifiés) ; le plan du monde vit dans `GameParams.world_plan` (rejouable) ; la section
`monde` de la régénération n'entre dans le code qu'en T9 ; les passages sont cités par `DesignObjective.excerpt_ids`
et jamais par un PNJ ; `POST /games/documents` (sans jeu) s'ajoute pour déposer avant la conception ; usine variée
(produits, clients, types de machine) et module finance sont typés (annexe §3 et §4).

`spec.py`, champs facultatifs, `version` reste 2 (une spec existante reste valide) :

```python
class Building(BaseModel):
    id: str                      # b1..b4
    archetype: Code              # pack["building_archetypes"]
    label: str
    area: Rect                   # sur la grille du site (campus)
    entrance: Point
    style: Code                  # variante de façade, pack["ambiances"][...]["styles"]

class Room(BaseModel):
    id: str                      # <bâtiment>.<pièce>
    building_id: str
    kind: Code                   # pack["building_archetypes"][a]["rooms"]
    label: str
    area: Rect
    department_ids: list[Code]   # départements logés (un département = une pièce)
    doors: list[Point] = Field(min_length=1)

class TrainerExcerpt(BaseModel): # T8 : passage d'un document du formateur, cité tel quel
    id: str                      # <document_id>#<n° de segment>
    document_id: uuid.UUID
    title: str
    text: str = Field(max_length=600)
    validated: bool = False      # coché par le formateur ; publication refusée (422) si un passage cité ne l'est pas

class World:                     # ajouts
    template: Literal["atelier", "usine", "campus"]
    buildings: list[Building] = []   # vide : hall unique actuel
    rooms: list[Room] = []
    ambiance: Code | None = None
class Department:                # ajout
    room_id: str | None = None
class SimSpec:                   # ajout
    trainer_excerpts: list[TrainerExcerpt] = []
Section = Literal["domain", "concept", "world", "cast", "journey"]   # clés de DesignOrigin.sections
class DesignRequest:             # ajouts
    domain: str | None = None    # slug proposé ; sinon choisi à l'étape 1
    document_ids: list[uuid.UUID] = []   # T8 ; 5 au plus
FIXABLE += {"buildings", "products", "suppliers", "clients", "ambiance"}
```

`ValueStatus` reste `source | calibre | exemple` : un passage du formateur n'est jamais la provenance d'une valeur.
Godot l'affiche « source du formateur, non vérifiée par G-mix », distinct des notions du corpus.

Pack : `building_archetypes` (bornes de taille en cellules, pièces permises, assets de murs et de portes),
`zoning_rules` (types testés : `together`, `apart`, `same_building`, `max_walk_m`, chacun avec provenance),
`ambiances`, `variants` par rôle d'objet, `campus.cell_m`. Moteur : `layout.travel_min(spec, a, b)` (pure) remplace
`Logistics.kit_min` et `repair_travel_min` fixes ; vitesse de marche et de chariot en `values` avec provenance.
Second domaine : `ai/packs/finance-entreprise.yaml` avec `engine: factory` (moteur existant ; un autre moteur
demanderait un ADR) et `knowledge/finance-entreprise/` (SOURCES.md). Module `finance` ajouté au moteur `factory`, actif
seulement si le pack le déclare (le pack usine ne change pas) : échéanciers `receivables` et `payables` dans l'état
(`{id, counterparty, amount, due_week}`, même mécanique que `pending` / `arrival_week`) ; découvert et agios repris du
moteur `weekly` (`OVERDRAFTS`, `interest_rate_week`) ; prêts `{principal, rate_week, weeks_left}` ; investissement
machine dont la VAN est calculée par une fonction pure du moteur (taux d'actualisation en `values` avec provenance).
Ces champs, les actions et les KPI finance (trésorerie nette, BFR en jours de CA, DSO, DPO, agios cumulés) sont fixés
en T2 dans `spec.py`. `ai/domains.yaml` gagne `audit: signe` à la signature de D3, et
`GET /games/options` ne propose un domaine au formateur que si son pack est couvert à 100 % et son audit signé
(l'admin peut l'essayer avant, ADR 0009 d.7).
Kafka : aucun topic nouveau ; `generation.progress.stage` prend `domaine`, `concept`, `simulation`, `monde`,
`placement`, `personnages`, `parcours`, `controle` (docs/kafka.md). Documents : `gmix.rag.commands`, déjà déclaré.
REST : `POST /games/designs` gagne `domain` et `document_ids` ; `POST /games/{id}/design/regenerate` gagne la section
`monde` ; T8 : `POST|GET|DELETE /games/{id}/documents` et `PUT /games/{id}/documents/{doc}/excerpts/{excerpt}`
(validation d'un passage), formateur propriétaire et admin ; joueur 403 ; autre formateur 404 ; la recherche RAG des
passages est filtrée par jeu (aucun passage d'un autre formateur). Droits testés côté API pour les 3 rôles. Formats et
tailles (PDF, Markdown, texte ; plafond par fichier) fixés dans l'annexe 0013.

## 4. Révision de la documentation et des ADR

### 4.1 ADR (architecte, fait le 21/11)

| ADR | Endroit marqué « amendé par 0013 » |
|---|---|
| 0007 | en-tête ; d.9 (§3.4) ; annexe usine, « Plan en U, hall de 48 x 30 m » (§3.4) |
| 0008 | en-tête ; d.3 (§3.4, §6.2) ; d.4 (§3.2) ; d.6 (§3.3) |
| 0008 annexe | en-tête ; §4.1 et §5 (remplacés par §3.2 et l'annexe 0013) ; §8 (complété par §3.3) ; §9 (complété par §5) ; §10 (suite : §5) |
| 0009 | en-tête ; d.1 (§3.4) ; d.2 (§2, §6.7) ; contrat « Pur, sans hasard » de `place_world` (§3.4) ; « Après » tranches 2 et 3 (§5) |
| 0010 | en-tête ; §3 (§2, T4) ; §7.3 (§6.2) ; annexe 0010 §7 « Livré en v0 » (T9) |

### 4.2 Documents (documentaliste, après cette décision ; tranche T3)

Règle : décrire l'état livré tel qu'il est et la cible avec sa tranche (« cible ADR 0013, T9 ») ; ne jamais écrire
comme livré ce qui ne l'est pas. Les numéros de ligne sont ceux du 21/11 : se repérer au texte cité.

| Fichier | Endroit | Texte attendu ou sens de la réécriture |
|---|---|---|
| docs/architecture.md | l. 31 et flux 1 (l. 55, « `factory.design` ») | « Conception : aujourd'hui un appel `factory.design` ; cible (ADR 0013, T9) : orchestrateur en code `gmix.game.design_pipeline` (worker `generation`), cinq tâches IA en série (`design.domain`, `design.concept`, `design.world`, `design.cast`, `design.journey`) et un contrôle `design.fact_check`. » |
| docs/architecture.md | l. 88 (« sans hasard ») ; table des mondes l. 93 (« hall de 48 x 30 m en U ») | « placeur déterministe à graine (ADR 0013 §3.4, T4) ; `apply_edits` sans graine » ; « 1 à 3 bâtiments à pièces, trajets calculés (cible T5) ; hall en U = programme de référence et repli » ; ajouter une ligne « second domaine : finance d'entreprise, moteur `factory` (D1-D3) » |
| docs/architecture.md | table des ADR | 0012 « accepté » ; ajouter 0013 « accepté (21/11) : mondes et jeux variés, équipe d'agents de conception, second domaine, documents du formateur » |
| docs/prompt-projet.md | §1 (l. 20) ; §2 attendus 2 et 3 (l. 45-46) ; §3 chaîne (l. 64) | « 3 appels » -> cinq étapes IA (domaine, mécaniques, monde, personnages, parcours) et un contrôle ; v0 = un appel jusqu'à T9 |
| docs/prompt-projet.md | §5 l. 125 (« plan en U conservé ») et l. 132 (« pur et sans hasard ») | « plan en U = programme de référence du pack et repli du placeur » ; « pur et déterministe à graine : mêmes paramètres, même graine, mêmes retouches = même monde (critère 0009-1) » |
| docs/prompt-projet.md | §2, fin de la table | ajouter l'attendu 11 « Variété selon la demande : série V, 12 briefs -> 8 structures au moins » et l'attendu 12 « Second domaine jouable, audité et signé » |
| docs/cahier-des-attentes.md | §1 (l. 13-15) et §4 (« dans l'usine », « entrer dans l'usine ») | « dans le monde du jeu (un à trois bâtiments : hall, entrepôt, bureaux…) » |
| docs/cahier-des-attentes.md | §5 (l. 87-97) | réécrire d'après §2 de cet ADR (qui décide quoi : pack, graine, agents IA, moteur) |
| docs/cahier-des-attentes.md | EX-12 (l. 150) et l. 180 | EX-12 : « à faire, avant la Première version (ADR 0013, T8) : chaque passage cité est validé par le formateur, provenance `formateur`, aucun chiffre d'un document dans le moteur » ; retirer EX-12 de la liste « Après la Première version » |
| docs/cahier-des-attentes.md | après EX-38 | ajouter EX-39 « Variété mesurée » (série V, T9) ; EX-40 « Bâtiments et pièces, trajets calculés » (T5) ; EX-41 « Équipe d'agents de conception, 3 min en médiane, 10 au plus » (T9) ; EX-42 « Second domaine jouable et audité » (D1-D3) ; relire EX-09 et EX-15 au regard de §2 |
| docs/game-design.md | l. 3-4 ; l. 25 (création) ; l. 36 (monde) ; l. 43 (cible TRS 78 %) | création : cible en cinq étapes (T9) ; monde : référence en U, cible 1 à 3 bâtiments (T5) ; TRS : reprendre la valeur de `ai/packs/usine.yaml` après la signature de T0, sans la recopier avant |
| docs/game-design.md | nouvelle section après « Usine : le jeu » | « Ce qui varie selon la demande » : table §2 résumée ; « Second domaine : finance d'entreprise (trésorerie et BFR d'une PME industrielle, usine en pilote automatique), D1-D3 » |
| docs/ai-runtime.md | l. 8, l. 91-92, l. 113, section « factory.design » (l. 192) | tâches cibles `design.*` (T9), budgets par étape (table §3.2), 3b par défaut, 7b par tâche seulement si l'éval du 3b échoue, 409 pendant un lobby ; `game.design.*` non appelées, remplacées en T9 |
| docs/kafka.md | l. 44 (progression) | étapes `domaine` … `controle` (§3.5) en cible T9 ; aucun topic nouveau ; documents par `gmix.rag.commands` (T8) |
| docs/roles.md | routes de jeu | routes documents et validation des passages (§3.5) : formateur propriétaire et admin, joueur 403, autre formateur 404 (cible T8) |
| docs/blocages.md | l. 22 (« Monde 3D variable ») ; l. 114 (« Quels autres domaines ») ; l. 21 (liste reportée) | « décidé : ADR 0013 accepté le 21/11 » ; « décidé le 21/11 : un second domaine jouable avant la Première version, la finance d'entreprise (ADR 0013 §6.2) » ; retirer EX-12 de la liste reportée |
| docs/equipe/reprise.md | l. 69 (ligne 3b) ; l. 75 | ordre des chantiers = §5 de cet ADR ; retirer EX-12 de « Après la Première version » |
| CLAUDE.md du dossier parent (hors dépôt) | présentation (« jouée dans un atelier Godot ») ; « Décisions : domaine prioritaire supply chain » | « jouée dans un monde Godot généré (un à trois bâtiments, assets du catalogue) » ; « supply chain plus finance d'entreprise (ADR 0013) » ; à soumettre à l'utilisateur avant écriture |

## 5. Plan de tranches (une tranche = une ou plusieurs sessions)

Ordre : T0 -> T2 -> (T3, T4, D1) -> T5 (avec T6) -> T7 -> (T8, D2) -> T9 -> D3 -> T10 -> T11. Chaque tranche finit
par qa-reviewer (`test.ps1 -Integration`, `-Flow`, `smoke.ps1`).

| # | Tranche | Propriétaires | Fichiers | Critère de fin | Sessions | Parallèle |
|---|---|---|---|---|---|---|
| T0 | **Audit de l'exigence n° 1, en cours** : préventif P1 à P4, recalibrage, régénération des 10 jeux, nouvel audit, signature | game-designer, moteur-jeu, ia-runtime | docs/audits/, ai/packs/usine.yaml, game/ | liste à signer signée par l'utilisateur | 3 | - |
| T1 | Décision de l'utilisateur sur 0013 | utilisateur | ce fichier | **fait le 21/11** (§6) | 0 | - |
| D0 | Liste courte du second domaine, puis choix | game-designer (liste : moteur réutilisé, corpus disponible, assets couverts, coût d'audit) ; utilisateur (choix) | docs/audits/ (note de choix) | **fait le 21/11** : `finance-entreprise`, moteur `factory` (§6.2) | 0 | avec T0 |
| T2 | Contrats et annexe 0013 (§3.5) | architecte | spec.py, topics.py si besoin, docs/kafka.md, `0013-annexe-contrats.md` | `test.ps1 -Fast` vert, specs v2 existantes valides | 1 | après T1 et D0 |
| T3 | Révision documentaire (§4.2) | documentaliste | docs/ hors ADR et audits | références périmées corrigées | 1 | avec T4 et D1 |
| T4 | Variété dans l'usine : 1 à 4 produits, 3 à 8 fournisseurs, 1 à 4 clients, types de machine par opération, placeur à graine, variantes d'assets, décor écrit dans la spec | moteur-jeu ; game-designer (secteurs, variantes, sources) ; godot-dev (décor lu dans la spec, graine 42 retirée) | game/, ai/packs/usine.yaml, godot/scenes/world | 12 graines x 2 secteurs : au moins 8 empreintes de monde distinctes, `check_placement` vide, jeux jouables | 3 | game-designer en parallèle de moteur-jeu |
| D1 | Corpus de la finance d'entreprise : Légifrance (Code de commerce L441-10 et D441-5 : plafonds des délais de paiement, pénalités, indemnité forfaitaire), PCG de l'ANC (règlement n° 2014-03 : comptes clients, fournisseurs, banques), Observatoire des délais de paiement (Banque de France : DSO et DPO moyens), Webstat (taux des crédits aux entreprises) ; notions : BFR, trésorerie nette, DSO/DPO, escompte, affacturage, découvert, crédit court terme, emprunt, VAN | rag-knowledge (`knowledge/finance-entreprise/`, SOURCES.md, `ingest.ps1 -Domain finance-entreprise`, couverture) ; game-designer (notions et citations) | knowledge/finance-entreprise/ | chaque notion visée a sa fiche et sa citation ; chaque moyenne (DSO, DPO) et chaque taux est daté (année du rapport, date de la série) ; couverture mesurée | 1 | avec T4 (fichiers disjoints) |
| T5 | Monde à plusieurs bâtiments et pièces, temps de trajet calculés | game-designer (archétypes, zonage sourcé) ; assets-3d (murs, portes, intérieurs) ; moteur-jeu (`place_campus`, `travel_min`) ; godot-dev (campus, portes, caméra, clic de pièce) | ai/packs/usine.yaml, ai/assets.yaml, godot/assets/, game/layout.py, game/factory.py, godot/scenes/world | 1 à 3 bâtiments, `pack_coverage` 100 %, `-Tour` et `-Flow` verts, 45 images/s | 5 | assets-3d en parallèle de game-designer |
| T6 | Garde-fou des nombres des PNJ (EX-33) | moteur-jeu, ia-runtime | game/npc.py, ai/evals/ | réplique avec un nombre absent des faits remplacée ; `numbers()` lit « 62.7054 » | 1 | avec T5 (fichiers disjoints) |
| T7 | Rôles répartis : 3 à 6 rôles selon le nombre de joueurs, découpés sur les actions existantes (approvisionnement, ordonnancement, production, maintenance, qualité, expédition) | game-designer, moteur-jeu, backend-api (droits) | ai/packs/usine.yaml, game/engine.py, api/routes | droits testés pour les 3 rôles, 6 joueurs en `-Flow` | 2 | - |
| T8 | Documents du formateur (EX-12) : dépôt, découpage, validation de chaque passage par le formateur, citation `formateur` | backend-api (routes, droits, base) ; rag-knowledge (ingestion par jeu, recherche filtrée) ; ia-runtime (passages dans les prompts) ; godot-dev (dépôt, cases de validation, mention « source du formateur ») | api/routes, db, alembic, rag/, ai/prompts, godot/scenes/draft | un document déposé, un passage validé est cité dans le jeu conçu ; publication refusée si un passage cité n'est pas validé ; aucun chiffre du document dans la spec moteur ; joueur 403, autre formateur 404 | 2 | rag-knowledge en parallèle de backend-api |
| D2 | Pack finance d'entreprise sur le moteur `factory` : trésorerie et BFR d'une PME industrielle, l'usine du pack tournant en pilote automatique (`_autopilot`) ; mécaniques : délais clients (escompte, relance, affacturage), délais fournisseurs et financement (découvert, crédit court terme, emprunt), un investissement machine jugé à la VAN ; rôles joueurs DAF, trésorier, credit manager, comptable fournisseurs ; PNJ banquier ; pièces : comptabilité, bureau du DAF, agence bancaire dans un second bâtiment (campus T5) | game-designer d'abord (`ai/packs/finance-entreprise.yaml` : secteur, module `finance`, valeurs avec provenance, notions citées, archétypes, zonage, rôles, banquier) ; moteur-jeu (module `finance` de §3.5 : la vente expédiée devient une créance et l'achat de MP une dette à échéance au lieu du règlement immédiat de `factory_game.advance`, découvert et agios, prêts, VAN pure, un handler testé par action, pilote automatique ; le pack usine reste identique) ; assets-3d (bureaux, guichet, agence, `pack_coverage` 100 %) ; backend-api (droits des 4 rôles, si T7 ne les lit pas déjà dans le pack) ; godot-dev (échéancier et prêts au HUD, si le panneau générique ne suffit pas) | ai/packs/finance-entreprise.yaml, game/factory_game.py, backend/tests/, ai/assets.yaml, godot/assets/ | jeu jouable en découverte, exigeant en expert ; tests du pack usine inchangés et verts ; `-Flow -Pack finance-entreprise` vert ; proposé à l'admin seulement. Arrêt : si le module demande de changer `factory.simulate` ou l'ordre de `advance` au-delà des échéanciers, nouvel ADR (§6.2) | 3 | assets-3d en parallèle de moteur-jeu ; avec T8 (fichiers disjoints) |
| T9 | Équipe d'agents de conception (§3) | ia-runtime (tâches, prompts, série V) ; pipeline-kafka (worker, étapes) ; moteur-jeu (`design_pipeline`, contrôles) ; godot-dev (étapes affichées, section « monde ») | ai/, workers/, game/, godot/scenes/draft | série V : 8 structures sur 12 en supply chain, second domaine choisi 4 fois sur 4 ; médiane sous 3 min, maximum sous 10 ; `-Flow -Design` vert | 3 | moteur-jeu en parallèle d'ia-runtime |
| D3 | Audit d'exactitude final : la finance d'entreprise (délais légaux relus sur Légifrance, DSO, DPO et taux datés, VAN recalculée à la main sur un jeu ; protocole docs/audits/protocole-jeux-ia.md, jeux conçus par l'équipe d'agents) et les valeurs ajoutées par T4, T5 et T7 (secteurs, archétypes, zonage, vitesses) | game-designer ; moteur-jeu (mesures) ; ia-runtime (régénération) ; utilisateur (signature) | docs/audits/, ai/packs/, ai/domains.yaml (`audit: signe`) | liste à signer signée ; le second domaine proposé au formateur | 1,5 | - |
| T10 | Dette de l'annexe 0010, passe finale `-Tour`, docs | backend-api, godot-dev, documentaliste | divers | EX-34 vert | 2 | - |
| T11 | **Première version** : commit et push | devops | - | push fait | 0,5 | - |
| QA | Fin de chaque tranche | qa-reviewer | tests manquants | `test.ps1 -Integration`, `-Flow`, `smoke.ps1` | inclus | toujours en dernier |

Total jusqu'à la Première version : environ **26,5 sessions** (21 pour l'ADR complet, documents compris, plus 5,5 pour
la finance d'entreprise : 4 selon game-designer, qui réutilise 60 à 70 % du moteur `factory`, plus l'audit D3), 22,5
si D1 et D2 tiennent en parallèle de T4 et T8. Rangs : l'audit T0 reste **premier**
(varier les mondes multiplie les valeurs à sourcer : il faut d'abord la barre de justesse) ; le second domaine est
choisi pendant T0 pour que T2 en fixe les contrats ; son pack vient après T5 et T7, dont il reprend les schémas de
bâtiments et de rôles ; l'audit D3 vient après T9 pour relire des jeux conçus par l'équipe d'agents. La répétition en
LAN ne dépend d'aucune tranche.

## 6. Décisions de l'utilisateur (21/11)

1. **Ampleur** : l'ADR 0013 complet avant la Première version (variété de l'usine, monde à plusieurs bâtiments, rôles
   répartis, documents du formateur, équipe d'agents de conception), environ 21 sessions.
2. **Domaines** : la supply chain plus **un second domaine jouable** dès la Première version, avec un nouvel audit
   d'exactitude (+4 sessions : D0 à D3). Ce n'était pas l'option recommandée (A, supply chain seule) ; c'est le choix
   de l'utilisateur. Il doit réutiliser un moteur existant (`factory` ou `weekly`) ; sinon, nouvel ADR et nouvelle
   estimation. **Choix du 21/11 (D0) : la finance d'entreprise** (`finance-entreprise` dans ai/domains.yaml), sur la
   proposition recommandée de game-designer : trésorerie et BFR d'une PME industrielle, dont l'usine tourne en pilote
   automatique en arrière-plan ; joueurs DAF, trésorier, credit manager, comptable fournisseurs ; PNJ banquier ;
   comptabilité, bureau du DAF et agence bancaire dans un second bâtiment. **Moteur réutilisé : `factory`** (l'usine
   simulée produit les ventes et les achats), plus un module `finance` (§3.5) : créances et dettes à échéance sur le
   modèle des commandes en transit, découvert et agios repris du moteur `weekly`, prêts, VAN d'un investissement
   machine. Réutilisation estimée à 60 à 70 % par game-designer ; 4 sessions (D1, D2) plus l'audit D3. Sources :
   Légifrance, PCG de l'ANC, Observatoire des délais de paiement (Banque de France), Webstat ; risque faible, mais les
   moyennes de DSO et de DPO et les taux du moment restent à vérifier et à dater (D1, relus en D3).
3. **Documents du formateur** : oui, avant la Première version (T8). Chaque passage cité est validé par le formateur,
   sous la provenance « formateur » ; aucun chiffre d'un document n'entre dans le moteur.
4. **Orchestrateur** : du code déterministe qui enchaîne 5 agents IA en série, avec garde-fous (option D, §3.2).
5. **Budget de conception** (non posée, recommandation appliquée) : inchangé, 3 min en médiane, 10 au plus.
6. **Modèle par étape** (non posée, recommandation appliquée) : qwen2.5:3b partout ; le 7b seulement en repli d'une
   étape qui échoue à l'éval, et refusé pendant un lobby en cours (§3.3). **Interprétation de l'architecte, à
   confirmer par l'utilisateur** : « en repli » est lu comme un choix fait à l'éval, tâche par tâche (la tâche
   `design.*` dont le 3b échoue pointe sur le 7b dans ai/models.yaml), et non comme une bascule du 3b vers le 7b
   pendant un job qui échoue (7 à 27 s de chargement, dialogue des PNJ délogé de la VRAM). Si l'utilisateur voulait
   la bascule en cours de job, §3.3 et le budget de 10 min sont à revoir.
7. **Bâtiments** (non posée, recommandation appliquée) : ils ont un effet calculé, les trajets `travel_min` entre
   pièces et bâtiments ; un bâtiment de pur décor reste interdit.

## Conséquences

- Positives : deux demandes différentes donnent deux mondes différents en structure, en visuel et en textes, mesuré
  par la série V ; deux domaines jouables ; la justesse reste garantie par le moteur, les provenances, le contrôle
  d'exactitude et deux audits signés (T0, D3).
- Coûts : la Première version recule d'environ 19,5 sessions (il en restait 7) ; plus de valeurs à sourcer
  (archétypes, zonage, vitesses de marche et de chariot, nouveaux secteurs, second domaine) ; assets à fabriquer
  (murs, portes, intérieurs, assets du second domaine).
- Risques : qualité du 3b par étape non mesurée (prompts sous 4 500 jetons pour `num_ctx` 6144) ; rendu Godot de
  plusieurs bâtiments (images par seconde, caméra Sims en intérieur) ; un placeur à graine qui échoue doit retomber
  sur le plan de référence sans jamais bloquer ; T4 change `Factory.product_id`, donc des tests du moteur ; si le module
  `finance` demande de changer `factory.simulate` ou l'ordre de `advance`, la finance sort des 5,5 sessions (nouvel
  ADR) ; le pack usine doit rester identique une fois le module ajouté (ses tests le prouvent) ; un passage du formateur peut contenir des chiffres :
  il est cité tel quel, jamais lu par le moteur ni repris par un PNJ (garde-fou T6).
