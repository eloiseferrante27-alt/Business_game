# Générateur de mondes G-MIX

But : produire, pour n'importe quel domaine, un monde de business game **jouable et cohérent**, de façon
reproductible (même graine ⇒ même monde). Domaine actuel : supply chain (monde v3).

## Le processus

```
pack.json (données du domaine)     build(pack, rng, params)        validate(monde)          save()
catalogues, plages, ratios,   ──►  tirages avec random.Random   ──► règles du domaine   ──► backend/app/scenarios/<id>.json
blocs, disposition, sources        (graine), calculs dérivés        (cahier §4 + moteur)      ──► /api/scenarios, /api/new-game
```

1. **Pack** (`backend/app/generator/domains/<domaine>/pack.json`) : tout ce qui varie (catalogues de noms,
   plages de valeurs, nombres d'éléments, ratios, disposition des zones) et, dans `_sources`, l'origine de
   chaque plage. `base_scenario` désigne un scénario existant dont on reprend ce qui ne varie pas.
2. **Constructeur** (`domains/<domaine>/__init__.py`, fonction `build`) : tire les éléments, puis **calcule**
   les valeurs dérivées au lieu de les tirer. Exemple supply chain : point de commande = consommation ×
   meilleur délai + stock de sécurité ; capacité de stock = (point de commande + quantité) × marge.
3. **Validation** (`validate`, même fichier) : contrôles du cahier des charges §4 (MTTR < MTBF, au moins 2 offres
   par article acheté, point de commande suffisant, capacités suffisantes) et références attendues par le
   moteur. Elle s'applique aussi à un scénario écrit à la main : `default.json` la passe.
4. **Noyau** (`backend/app/generator/__init__.py`) : charge le domaine, fixe la graine, ajoute la trace
   `generation` (domaine, graine, paramètres, version du pack), refuse un monde invalide, écrit le fichier.
   Il fournit aussi `place_zones` (disposition générique en rangées avec allées). Il ne connaît aucun domaine.

Le fichier écrit a exactement le format de `scenarios/default.json` (+ `layout` et `generation`) : le moteur
et la tablette le jouent sans modification.

## Commandes (depuis `backend/`)

| Commande | Effet |
|---|---|
| `python -m app.generator supply_chain --seed 42` | écrit `scenarios/supply-chain-42.json` |
| `... --products 3 --machines 5` | impose des paramètres (sinon tirés dans le pack) |
| `... --id demo-tp1` | choisit l'identifiant du scénario |
| `... --check` | génère et valide sans écrire |
| `python -m app.generator --validate default` | valide un scénario existant |

Puis lancer une partie avec `scenario_id` = l'identifiant affiché (`POST /api/new-game`).

## Ajouter un domaine

1. `concepteur-monde` décrit le domaine : blocs, flux, décisions du joueur, KPIs, contraintes de cohérence.
2. Créer `domains/<domaine>/pack.json` (données) et `domains/<domaine>/__init__.py` avec
   `build(pack, rng, params) -> dict` et `validate(monde) -> list[str]`. Rien à changer dans le noyau.
3. Tant que le moteur ne simule que la supply chain, un nouveau domaine exige aussi ses règles de simulation.
   C'est le vrai chantier : le format de scénario actuel est celui de l'usine v3.
4. Tests : copier le modèle de `backend/tests/test_generator.py` (graines multiples, reproductibilité,
   partie jouée par le moteur).

## Limites actuelles (supply chain)

- Une ligne par produit, comme le moteur actuel. Les « N lignes identiques pour un produit » de la v3 §4.6
  ne sont pas générées : le moteur ne garantit pas encore le partage des OF entre lignes.
- Unité de temps : la semaine (moteur actuel). Le point de commande utilise le délai nominal, pas le délai
  effectif (fiabilité). À revoir avec T00 (journée de 8 h).
- Blocs, agents, profils de difficulté, qualité, emballage, transport et PDR sont repris de `default.json`.
- `layout.zones` est produit (la chaîne s'allonge avec le nombre de machines), mais le monde 3D garde encore
  sa disposition fixe de `static/layout.js` : à brancher (tâche `interface`).
- Les catalogues de noms et les plages sont des hypothèses encadrant `default.json`, à valider par le formateur.
