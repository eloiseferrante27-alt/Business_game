# Pipeline Kafka

Kafka 4.3.1 en mode KRaft (sans ZooKeeper), un nœud. Hôte : `localhost:9092` ; conteneurs : `kafka:29092`.
Création automatique de topics désactivée : la liste fait foi dans `backend/gmix/messaging/topics.py` et
`python -m gmix.bootstrap` crée ceux qui manquent. Console : `.\scripts\infra.ps1 tools` puis http://localhost:8085.

## Topics

| Topic | Partitions | Rétention | Contenu |
|---|---|---|---|
| gmix.system.ping / gmix.system.pong | 1 | 1 h | diagnostic de bout en bout |
| gmix.game.events | 3 | 30 j | actions des joueurs, semaines simulées, état public des parties |
| gmix.npc.transcripts | 3 | 30 j | dialogues PNJ terminés (évaluation, débrief) |
| gmix.rag.commands / gmix.rag.events | 1 | 7 j | ingestion de documents |
| gmix.generation.commands | 1 | 7 j | demandes de conception d'un jeu par l'IA (API -> worker `generation`) |
| gmix.generation.events | 1 | 7 j | progression et résultat des conceptions (worker ; non relayé au WebSocket, le client interroge `GET /games/{id}/job`) |
| gmix.audit | 1 | 90 j | actions formateur et admin |
| gmix.dlq | 1 | 30 j | messages en échec avec l'erreur |

## Enveloppe (`gmix.messaging.envelope.Envelope`)

`id`, `type` (ex. `lobby.state`), `version`, `occurred_at`, `source`, `correlation_id`
(toute la chaîne), `causation_id` (message déclencheur), `actor` {user_id, role}, `lobby_id`, `client_id`
(session WebSocket à notifier), `payload`. Une réponse se construit avec `event.reply(type, source, payload)`.
Côté client, le format reçu est `{type, payload, meta}`.

## Événements en service

| Type | Topic | Émetteur -> destinataire | Payload |
|---|---|---|---|
| `lobby.state` | game.events | API -> WebSocket des membres du lobby | lobby_status, state (état public), action {type : start, advance ou action, by, module, summary} |
| `lobby.members` | game.events | idem | members [{user_id, display_name, game_role}] |
| `lobby.round` | game.events | idem ; consommé par le client Godot (`realtime.gd` -> `Session`, barre « prêt ») | round (prêts, vote, pause) |
| `npc.exchange` | npc.transcripts | API (non relayé) | npc_id, message, reply, intent, sources |
| `generation.requested` | generation.commands | API -> worker `generation` | job_id, game_id, sections, seed, note |
| `generation.progress`, `generation.completed`, `generation.failed` | generation.events | worker ; journal, non relayé par `api/ws.py` (`RELAYED_TOPICS` = pong et game.events) | job_id, game_id, étape et pourcentage ; titre, repli, essais, durée et tokens ; étape et erreur |
| `account.created`, `game.generated`, `game.design_requested`, `game.imported`, `game.spec_saved`, `game.layout_saved`, `game.params_saved`, `game.published`, `lobby.created`, `lobby.advanced`, `lobby.paused`, `lobby.event_forced` | audit | API | ids, graine et rôle de l'auteur |

Les actions et les semaines sont appliquées par l'API sous verrou de ligne (`gmix.game.engine`, fonctions
pures) : la réponse HTTP porte le nouvel état, `lobby.state` le diffuse aux autres membres. Kafka
indisponible : l'action est enregistrée quand même et les clients se resynchronisent par
`GET /api/v1/lobbies/{id}`. La conception d'un jeu par l'IA (`POST /games/designs`, `POST /games/{id}/design/regenerate`)
passe par Kafka : le worker `generation` (`.\scripts\worker.ps1 generation`) consomme `gmix.generation.commands`, appelle
la tâche `factory.design` et publie sur `gmix.generation.events` ; la progression se lit en base par `GET /games/{id}/job`. Si la commande ne part pas, l'API répond une erreur
et ne garde ni jeu ni job. Au démarrage, le worker passe en `failed` les jobs restés `running`. Seule la génération
par paramètres (`POST /games`, atelier, ADR 0006) reste synchrone et sans Kafka.

## Conventions

- Clé de partition : `lobby_id`, sinon `correlation_id` (ordre garanti pour une partie).
- Producteur idempotent, `acks=all`. Consommateurs : commit manuel après traitement (au moins une fois),
  handlers idempotents, erreur -> `gmix.dlq` puis commit (pas de blocage sur un message empoisonné).
- Groupes : un par type de worker (`worker-system`, `worker-generation`). Le relais WebSocket de l'API
  consomme sans groupe : chaque instance reçoit tout et ne notifie que ses propres clients.
- Le temps réel 3D ne passe pas par Kafka (voir docs/decisions/0002-kafka-hors-temps-reel.md).
