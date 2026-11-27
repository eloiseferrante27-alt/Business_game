# Orchestration locale Codex + Kimi Pro

Le lanceur utilise les CLI déjà connectés sur ce Mac. Codex coordonne le moteur,
les API et la revue ; Kimi utilise explicitement `kimi-code/k3.1-pro` pour la
tablette. Aucun compte Higgsfield, nouvelle clé API ou serveur exposé n’est
nécessaire. Les appels modèle passent par les connexions existantes de chaque
CLI et consomment leur quota habituel.

## Vérifier la configuration

Depuis le dépôt :

```sh
.venv/bin/python scripts/orchestrate.py doctor
.venv/bin/python scripts/orchestrate.py doctor --live
.venv/bin/python scripts/orchestrate.py status
```

`doctor` vérifie les binaires et leur configuration/authentification locale.
`--live` ajoute deux réponses de connexion minimales dans un dépôt temporaire,
sans code projet transmis ni outil disponible pour le profil Kimi de test.
Le modèle Codex reste celui de la configuration utilisateur ; Kimi Pro est fixé
dans `config/orchestration.toml`. Le lanceur retrouve aussi l’installation
officielle `~/.kimi-code/bin/kimi` si le PATH de l’IDE est incomplet.

Le lanceur peut se trouver dans un autre worktree : ajouter
`--repo /chemin/vers/business_game` **avant** la sous-commande. La configuration
et les profils sont toujours résolus à côté du script, jamais depuis une copie
non contrôlée située dans le worktree du worker.

## Confier une tâche

Écrire un fichier UTF-8 de consignes avec les critères de réussite. Exemple
pour T02, une fois T01 fusionnée et marquée `done` dans le board :

```sh
.venv/bin/python scripts/orchestrate.py prepare T02 --agent codex \
  --brief /tmp/t02-consignes.md \
  --scope config/world.yaml \
  --scope backend/app/engine/ \
  --scope tests/test_config.py \
  --scope requirements.txt
.venv/bin/python scripts/orchestrate.py run T02
.venv/bin/python scripts/orchestrate.py review T02
```

Les valeurs de scope sont des fichiers exacts ou des répertoires terminés par
`/`. `AGENTS.md` est ajouté implicitement pour la ligne de tâche et le handoff.
Choisir le périmètre le plus précis qui couvre la tâche. Les périmètres permis
par rôle sont dans le TOML ; Kimi ne peut pas réserver `models.py` ou le moteur.

Pour une tâche UI, la commande a la même forme avec `--agent kimi`, son ID du
board, son brief et par exemple `--scope backend/app/static/tablet/` et les
fichiers de tests correspondants. Ne pas lancer T07 avant les décisions T00
sur les bibliothèques si elles sont nécessaires à son implémentation. Les
dépendances détaillées du board doivent refléter les décisions réelles.

`prepare` vérifie le board commité dans la branche locale `contribution_amine`
du dépôt passé via `--repo` : tâche `todo`,
dépendances explicitement terminées et références documentaires présentes
dans la branche de base. Une expression groupée comme `T02–T05` n’est pas
devinée : détailler les dépendances du board avant la préparation. Les lignes
UI groupées T20–T29 doivent être détaillées par département avant leur lancement.
Les états des autres worktrees et les changements non commités du checkout
principal ne remplacent pas ceux de la base. Cela évite de lancer un outil UI
sur une base qui ne contient pas encore son moteur ou son shell.

Le lanceur crée une branche `codex/T02-work` ou `kimi/Txx-work` depuis
`contribution_amine`, puis un worktree frère dans
`../business_game-worktrees/tasks/`. Il committe d’abord la prise en charge.
Il ne change jamais la branche ou les fichiers du checkout principal. Un
worktree préexistant n’est jamais écrasé. Si le commit de prise en charge échoue,
le registre garde `prepare_failed` et les chemins créés. Corriger la cause
(par exemple un hook Git), puis répéter exactement `prepare` avec le même
agent et périmètre : le worktree enregistré est repris sans suppression.
La branche locale de base doit être mise à jour selon le workflow Git
habituel avant la préparation.

## Travail simultané et passage de relais

Deux processus `run` peuvent fonctionner depuis deux terminaux : au maximum
un worker Codex et un worker Kimi. Les tâches réservent leurs périmètres dans
un registre commun ; deux tâches actives ne peuvent pas réserver les mêmes
fichiers métier. Les mises à jour AGENTS.md restent propres à chaque branche,
puis se réconcilient lors des PR.

```sh
.venv/bin/python scripts/orchestrate.py status
```

Le registre et les comptes rendus sont dans
`git rev-parse --git-common-dir` → `gmix-orchestration/`. `status` donne les
chemins exacts. Chaque exécution conserve `prompt.txt`, `stdout.log`,
`stderr.log`, `answer.txt`, `handoff.json` et les sorties pytest. Ces données
restent locales et ne sont pas ajoutées à Git. Les dossiers/fichiers créés
par le lanceur sont privés par défaut (umask 077).

Le brief de la tâche suivante doit inclure le contrat API et les décisions
du handoff précédent. La transmission ne repose pas sur une mémoire de chat
partagée entre deux fournisseurs. Aucun nouveau travail de jeu n’est lancé
automatiquement par l’installation de cette configuration.

## Vérifications, correction et PR

Après le worker, le lanceur vérifie les fichiers modifiés, y compris ceux déjà
commités par l’agent, puis exécute pytest. Il refuse une sortie hors périmètre,
une tâche inachevée et les liens symboliques ajoutés/modifiés. Les vérifications
spécifiques UI doivent aussi être demandées dans le brief. Les changements
autorisés et testés sont commités localement avant revue ; un hook qui change
leur contenu invalide cette étape. Le code `review`
signifie que ces vérifications ont réussi ; il ne vaut pas approbation du code.

`review` lance Codex en lecture seule et conserve son rapport. La revue est
liée à l’empreinte de l’état testé ; une modification impose de tester et
revoir à nouveau. Pour corriger après une revue ou reprendre un échec :

```sh
.venv/bin/python scripts/orchestrate.py retry T02
.venv/bin/python scripts/orchestrate.py run T02
.venv/bin/python scripts/orchestrate.py review T02
```

`retry` conserve les modifications existantes. Une branche inattendue est
rattachée à la branche prévue uniquement par avance rapide, avec une branche
`recovery/...` conservant les commits ; les fichiers non commités restent en
place. Des branches divergentes imposent une intégration manuelle des commits,
et la reprise refuse de modifier une branche utilisée par un autre worktree.

Chaque exécution possède un identifiant unique, un verrou de tâche hérité par
le worker et un fichier `process.json` par groupe de processus. Si le
coordinateur meurt mais que son worker survit, `retry` et `run` refusent tout
second lancement. Consulter les logs et le PGID enregistré, terminer proprement
cet ancien groupe, puis relancer `retry`. Le lanceur ne tue aucun processus
sur la seule base d’un PID ancien. Si le crash précède l’écriture des
métadonnées, la reprise reste bloquée par défaut ; après avoir vérifié
manuellement qu’aucun processus n’agit encore dans ce worktree, utiliser
`retry T02 --confirm-stopped`. Cette option ne contourne ni un verrou actif
ni un groupe enregistré encore vivant. Un PGID réutilisé peut imposer une
inspection manuelle plutôt qu’une récupération automatique. Aucun reset,
suppression de worktree ou force-push n’est effectué. Les logs expliquent les refus.
Utiliser `retry T02 --brief /tmp/t02-corrections.md` pour transmettre les
réponses humaines ou les corrections demandées par la revue au prochain run.

Lire la revue, corriger ses constats et suivre AGENTS.md pour pousser la branche
et ouvrir la PR vers `contribution_amine`. Amine fusionne. Après mise à jour de
la branche locale de base, `close T02` vérifie que la tête testée/revue est
effectivement intégrée avant de libérer sa réservation. Après squash ou rebase,
indiquer explicitement le commit d’intégration :

```sh
.venv/bin/python scripts/orchestrate.py close T02 --integrated-commit <sha>
```

Ce commit doit appartenir à `contribution_amine` et contenir les changements
testés : leur patch inverse doit s’appliquer à son arbre dans un index Git
temporaire. Une simple référence à un commit sans ces changements est refusée.
Cette preuve ne modifie ni la branche ni le worktree et reste dans le registre.
Les worktrees sont conservés. Aucune fusion n’est déclenchée par le lanceur.

Le contrôle de périmètre est une vérification après exécution, pas une barrière
de sécurité du système de fichiers. Un worktree isole les modifications Git.
Codex utilise `workspace-write` pour implémenter et `read-only` pour revoir ;
Kimi `--prompt` utilise ses permissions non interactives, avec un profil limité
aux outils lecture/édition/shell, sans délégation ni MCP. Les règles du profil
demandent de ne lire aucun secret ni d’accéder aux autres worktrees.

## Sources des interfaces CLI

- [Exécution Codex et collecte d’une réponse finale](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex)
- [Options Kimi et exécution non interactive](https://moonshotai.github.io/kimi-code/en/reference/kimi-command.html)
- [Profils Kimi et liste des outils](https://moonshotai.github.io/kimi-code/en/customization/agents.html)

Pas d’activation du mode expérimental Tower : le coordinateur local conserve
les branches, contrôles et passages de relais des deux CLI.
