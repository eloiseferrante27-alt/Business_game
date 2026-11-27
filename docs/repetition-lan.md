# Répétition d'une séance en salle (LAN, 3 postes)

Cadre : LAN, 3 à 6 joueurs (docs/equipe/reprise.md, priorité 2). Vous êtes formateur sur un poste et joueur sur les
deux autres (ou avec deux comptes joueurs). Hôte constaté le 18/11 : IP Wi-Fi `192.168.11.100` (`172.22.64.1` est
l'interface WSL : à ignorer). Si l'IP a changé, relevez-la avec `ipconfig` et remplacez-la partout ci-dessous.

## Avant

| # | Étape | Où | Vérification |
|---|---|---|---|
| 1 | Réseau en profil **Privé** (Paramètres, Réseau et Internet, Wi-Fi, propriétés) sur l'hôte et sur les postes joueurs | tous | `Get-NetConnectionProfile` : `NetworkCategory = Private` |
| 2 | Ouvrir le pare-feu de l'hôte (PowerShell **en administrateur**, une fois). L'API est en TCP ; les serveurs de partie Godot (ENet) sont en **UDP** (`game_server_ports` = 7000-7049, backend/gmix/settings.py) : `New-NetFirewallRule -DisplayName "G-mix API LAN" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private ; New-NetFirewallRule -DisplayName "G-mix parties" -Direction Inbound -Protocol UDP -LocalPort 7000-7049 -Action Allow -Profile Private` | hôte | `Get-NetFirewallRule -DisplayName "G-mix*"` : 2 règles |
| 3 | Lancer : `.\scripts\start.ps1 -Lan -NoGame` | hôte | fenêtre API ouverte, « API prête » |
| 4 | Santé depuis un autre poste : ouvrir `http://192.168.11.100:8000/health` dans un navigateur | poste joueur | réponse JSON (pas `/api/v1/health`) |
| 5 | Sur l'hôte : `.\scripts\godot.ps1 -Export` (produit `build\windows\G-mix.exe`, modèles d'export 4.7.2 requis). Copier `G-mix.exe` sur chaque poste joueur (clé USB ou partage) ; aucune installation de Godot | hôte, joueurs | l'exe s'ouvre sur l'écran de connexion |
| 6 | Créer 2 comptes joueurs (compte admin, écran formateur ou `backend\.venv\Scripts\python -m gmix.tools.create_user --username <id> --role player`) | hôte | connexion possible |
| 7 | Lancer `G-mix.exe` sur chaque poste et saisir `192.168.11.100:8000` à la connexion (`http://` ajouté, adresse mémorisée dans `user://client.cfg`) | tous | accueil affiché selon le rôle |

## Pendant

Cochez au fur et à mesure ; tout écart va dans la grille de relevé.

| # | Étape | À observer |
|---|---|---|
| 1 | Formateur : créer une session de groupe (au moins 2 équipes), noter le code | code affiché, cartes d'équipes |
| 2 | Joueurs : saisir le code (groupe d'abord, sinon lobby) | entrée par code et par groupe |
| 3 | Joueurs : choisir équipe et rôle | choix pris en compte chez tous |
| 4 | Entrer dans l'atelier ; marcher à ZQSD (clavier AZERTY réel), à la souris, au clic | déplacements, collisions, aucun caractère en QWERTY |
| 5 | Voir les autres joueurs bouger | **latence ressentie** : décalage, saccades |
| 6 | Ouvrir la tablette : son département se modifie, les autres sont en lecture seule | droits par département |
| 7 | Tous cliquent « Prêt » ; un joueur quitte volontairement ; vote sur l'absent | vote avec 2 joueurs, issue du vote |
| 8 | Formateur : pause, puis événement | effet sur tous les postes |
| 9 | Parler à un PNJ | réponse, délai, texte lisible |
| 10 | Formateur : passer la semaine | mise à jour des KPI sur chaque poste |
| 11 | Débrief, puis débrief comparé du groupe | contenu, sources, lisibilité |
| 12 | Palette « ardoise » : regarder chaque écran (accueil, salle, atelier, tablette, débrief) sur chaque poste | contrastes, texte coupé, tailles |

## Après

1. Hôte : `.\scripts\stop.ps1` (volumes gardés).
2. Remplir la grille ci-dessous ; une ligne par constat, une capture par ligne de gravité 3 ou plus (touche Impr. écran,
   chemin du fichier dans la colonne Capture).
3. Transmettre la grille à l'orchestrateur : chaque ligne devient une tâche pour le propriétaire du dossier concerné.

Gravité : 1 = gêne, 2 = contournable, 3 = bloque une étape, 4 = bloque la séance.

| Constat | Poste (hôte, J1, J2) | Gravité (1-4) | Capture |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |

## Questions pour l'utilisateur

- Le pare-feu n'est pas encore ouvert : vous l'ouvrirez le jour de la répétition (étape 2 d'« Avant »). Date à fixer.
- La connexion depuis `G-mix.exe` n'a pas encore été essayée à la main : première chose à noter dans la grille.
