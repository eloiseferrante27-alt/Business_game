# Rôles et droits

| Action | Joueur | Formateur | Admin |
|---|:-:|:-:|:-:|
| Rejoindre un lobby avec un code, jouer, parler aux agents | oui | observer, agir | oui |
| Voir ses propres résultats et son débrief | oui | - | oui |
| Générer un business game par paramètres et créer son lobby | - | ses lobbies | tous |
| Relire, exporter, modifier puis réimporter une spec | - | ses specs | toutes |
| Lancer une partie, forcer la semaine, mettre en pause, forcer un aléa ; voir les résultats de ses joueurs | - | ses lobbies | tous |
| Concevoir un jeu par l'IA, retoucher son plan, changer ses paramètres, régénérer une section, publier | - | ses jeux | tous |
| Créer un groupe d'équipes (un lobby par équipe) et lire son débrief comparé | joueur d'une équipe, une fois toutes les équipes finies | ses groupes | tous |
| Se déclarer « prêt » pour la semaine, voter sur les absents | oui (rôle choisi) | - | - |
| Proposer des documents pour le corpus RAG | - | oui | oui |
| Valider le corpus, gérer domaines, assets et modèles IA | - | - | oui |
| Gérer les comptes et les rôles, consulter l'audit | - | - | oui |

Règles d'implémentation (agent backend-api) :
- Rôle porté par `users.role` (`player`, `trainer`, `admin`) et vérifié sur chaque endpoint par une
  dépendance FastAPI ; la propriété (« ses lobbies ») est vérifiée en base, pas déduite du client.
- Toute action formateur ou admin qui modifie des données publie un événement sur `gmix.audit`.
- Le client Godot masque les menus selon le rôle, mais seule l'API fait foi.

Comptes : identifiant + mot de passe gérés par l'application (docs/decisions/0004-comptes-locaux.md).
Le premier admin est créé en ligne de commande, l'admin crée les formateurs, chaque formateur crée les comptes
de ses joueurs. Pas d'inscription libre en v1.

## Implémentation (backend/gmix/api)

| Endpoints | Qui |
|---|---|
| `POST /api/v1/auth/login`, `GET /auth/me`, `POST /auth/password` | tout compte actif |
| `POST/GET /api/v1/users` | formateur (crée des joueurs, voit les siens), admin (tout) |
| `GET /api/v1/games/options`, `POST /games`, `POST /games/import`, `GET /games`, `GET/PUT /games/{id}(/spec)` | formateur (ses business games), admin |
| `GET /api/v1/games/options` | formateur, admin (liste aussi les packs et leur couverture d'assets) |
| `POST /games/designs` (202, usine seulement), `GET /games/{id}/job` | formateur (ses jeux), admin ; 409 si une conception du même compte est en cours ; 422 si des assets du pack manquent (sauf `force=true`, admin, audité) |
| Cible ADR 0013, T8 (non livré ; contrats : [annexe 0013 §5](decisions/0013-annexe-contrats.md)) : `POST`, `GET` et `DELETE /games/{id}/documents`, `PUT /games/{id}/documents/{doc}/excerpts/{excerpt}` (validation d'un passage) | formateur propriétaire et admin ; joueur 403 ; autre formateur 404 ; recherche RAG filtrée par jeu |
| `PUT /games/{id}/layout`, `PUT /games/{id}/params`, `POST /games/{id}/publish`, `POST /games/{id}/design/regenerate` (202) | formateur (ses jeux), admin ; 409 si le jeu est en `generating` ou joué par un lobby en cours ; `regenerate` : 409 aussi si le jeu n'a pas été conçu par l'IA ; `layout` et `params` repassent le jeu en `draft`, `publish` le met en `ready` après contrôle de la spec et du placement |
| `POST /api/v1/groups` (201) | formateur, admin : crée le groupe et N équipes (un lobby chacune) sur un jeu `ready` |
| `GET /groups` | formateur (ses groupes), joueur (groupes où il tient une équipe), admin (tous) ; le code d'accès n'est rendu qu'au formateur et à l'admin |
| `POST /groups/join` | tout compte : sans `lobby_id`, liste les équipes du code ; avec, entre dans l'équipe |
| `GET /groups/{id}`, `/{id}/debrief` | formateur du groupe, admin, joueurs d'une de ses équipes ; débrief joueur quand toutes les équipes ont fini |
| `POST /api/v1/lobbies`, `/{id}/start`, `/{id}/advance`, `/{id}/pause`, `/{id}/event` | formateur du lobby, admin (`advance` : forçage de la semaine ; `pause` : `{paused}` ; `event` : remplace l'aléa annoncé, 422 si inconnu du jeu) ; 409 si la partie n'est pas en cours |
| `POST /lobbies/{id}/ready` | membre qui a choisi un rôle (409 sinon) : « prêt » et bulletin sur les absents ; en mode `auto`, la semaine avance quand tous les attendus sont prêts ou que la majorité des connectés vote « ignorer » (EX-24) |
| `GET /lobbies/{id}/weeks/{week}/timeline` | membres, formateur, admin ; 404 si le tour n'est pas simulé (usine) |
| `POST /lobbies/join`, `PUT /{id}/role`, `POST /{id}/actions`, `POST /{id}/npcs/{agent}/talk`, `GET /{id}/npcs/{agent}/memory`, `POST /{id}/presence` | membres ; le formateur agit sur tous les modules |
| `GET /api/v1/lobbies`, `/{id}`, `/{id}/debrief` | membres, formateur, admin ; débrief joueur en fin de partie seulement |
| `WebSocket /ws` (en-tête `Authorization: Bearer`), `POST /system/ping` | tout compte / formateur et admin |

- Un lobby, un groupe ou un jeu d'un autre formateur répond 404 (pas d'énumération) ; une partie de l'ancien modèle répond 410.
- Actions (annexe 0010 §5, `engine.act`) : un joueur n'agit que sur les actions de **son** rôle (409 « Cette action
  revient au rôle « X » », ou « Choisissez un rôle ») ; le formateur et l'admin agissent partout ; une action sans
  titulaire tourne en pilote automatique (`Action.autopilot`), sauf la semaine où le formateur y a agi.

## Rôles de jeu (T7, ADR 0013 annexe §3 ter)

- Le pack déclare `roles` et `role_plans` (tout pack). Usine : 10 rôles aux intitulés ROME v62 (`knowledge/supply-chain/rome-metiers-roles-usine.md`), 5 plans.
- Le nombre de rôles suit les membres hors formateur jusqu'au lancement, puis se fige dans `lobbies.settings["seats"]` ; une arrivée n'efface les choix que si elle change le plan.

| Joueurs | Rôles de l'usine |
|---|---|
| 1 | `responsable_usine` |
| 2 | `responsable_flux`, `responsable_atelier` |
| 3 | `responsable_production`, `chef_de_ligne`, `responsable_maintenance` (rôles des modules) |
| 4 | `acheteur`, `ordonnanceur`, `chef_de_ligne`, `responsable_maintenance` |
| 5 | `acheteur`, `ordonnanceur`, `chef_de_ligne`, `technicien_methodes`, `chef_equipe_maintenance` (`priorite_reparation` et `pieces_rechange`) |
| 6 | plan à 5 ; le 6e joueur double `acheteur` (U2, 27/11) |

- `POST /{id}/leave` (204) : un membre ne retire que lui-même ; 409 « Vous n'êtes pas dans ce lobby » ; 409 « La partie est lancée : vous ne pouvez plus quitter le lobby » ; 404, 410. Les rôles des autres ne sont effacés que si le plan change ; `lobby.members` est publié et le partant est désabonné du WebSocket. Client : bouton « Quitter le lobby » (avec confirmation) dans la salle d'attente.
- `PUT /{id}/role` : 422 « Ce rôle n'est pas proposé à {n} joueurs » ; 409 tant qu'un rôle du plan est libre ; 409 après le lancement. `engine.assign_seats` attribue les rôles au lancement.
- `GET …/memory` ne rend que les échanges du joueur qui le demande ; l'agent, lui, se souvient de ceux de
  tout le lobby.
- Mots de passe scrypt, jeton d'accès de 8 h, 5 essais de connexion par identifiant et adresse en 5 min.
- Premier admin : `backend\.venv\Scripts\python -m gmix.tools.create_user --username admin --role admin`.
