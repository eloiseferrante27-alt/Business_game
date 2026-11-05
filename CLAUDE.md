@AGENTS.md

# Claude Code sur G-MIX

G-MIX devient un **générateur de business games** : un pack de domaine (données) + un constructeur (code)
produisent un scénario `backend/app/scenarios/<id>.json` que le moteur et la tablette jouent sans
changement (la 3D ne lit pas encore la disposition générée). Domaine actuel : supply chain. Voir `docs/generateur.md`.

## Commandes (depuis la racine)
- Tests : `cd backend; python -m pytest -q` et `node --test backend/tests/*.test.js`
- Générer un monde : `cd backend; python -m app.generator supply_chain --seed 42` (`--check` = valider sans écrire)
- Lancer le jeu : `start.bat` / `stop.bat` (Docker), ou `cd backend; python -m uvicorn app.main:app --reload`

## Équipe d'agents (.claude/agents)
La session principale coordonne et fait elle-même les petites tâches (moins de ~5 minutes ou un seul fichier
déjà connu) : déléguer coûte un contexte neuf, plus cher qu'une petite modification.

| Agent | Modèle | Possède | À lui pour |
|---|---|---|---|
| lecteur-specs | haiku | rien (lecture seule) | réponse citée tirée de docs/ sans charger 2 100 lignes |
| concepteur-monde | opus | `generator/domains/*/pack.json` | chiffres, plages, cohérence métier, nouveau domaine |
| moteur | sonnet | `backend/app` hors `static/`, `backend/tests/test_*.py` | moteur, API, générateur (noyau + build/validate) |
| interface | sonnet | `backend/app/static/`, `backend/tests/*.test.js` | tablette, outils, monde 3D |
| verificateur | sonnet | tests manquants, rapports | relecture indépendante, toutes les vérifications |
| scribe | haiku | AGENTS.md (board, log), COMMENT_JOUER.md, docs non métier | écritures mécaniques après coup |

Choix du modèle : mécanique (lecture ciblée, mise à jour de docs) -> haiku ; code -> sonnet ;
conception et exactitude métier -> opus. `Explore` (recherche large dans le code) reste permis ;
`general-purpose` est à éviter : il ne connaît ni les règles ni la propriété des fichiers.

Règles :
- Une question sur la spec -> `lecteur-specs` d'abord ; ne jamais lire en entier le cahier des charges.
- Un fichier = un propriétaire ; en parallèle seulement sur des fichiers disjoints.
- Brief (un agent ne voit pas la conversation) : objectif, fichiers et docs utiles, périmètre, critère de fin,
  compte rendu attendu. Donne les faits déjà établis pour qu'il ne les recherche pas.
- Compte rendu : fait · fichiers · vérifié (commande -> résultat réel) · reste et risques.
- Fin de chantier : `verificateur`, puis `scribe` pour AGENTS.md (Task board + Handoff log).
- Codex et Kimi gardent leur coordination (`scripts/orchestrate.py`, `docs/orchestration.md`).
