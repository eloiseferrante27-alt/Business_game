# Jeu connecté — GAME-01 et UI-01

Cette livraison remplace le mock de la tablette par les décisions et données du moteur existant. Elle ne déclare pas terminées les tâches T02–T05, T07, T10–T32 : leurs exigences complètes restent au tableau.

## Parcours livré

Nouvelle partie avec confirmation des règles → plan huit blocs et partenaires → comparaison fournisseur et achat MP/PDR → OF → simulation d’une semaine → consultation des réceptions, stocks, production, qualité, emballage et livraisons → maintenance et décisions suivantes. Le clic 3D ouvre la page correspondante. Aucun bureau joueur ni bloc méthodes supplémentaire n’est affiché ; son identifiant historique est conservé et redirigé vers Production.

Les dix pages partagent KPIs / Outils / Configurations. Cinq espaces outils : tableur local (SOMME, MOYENNE, MIN, MAX, SI, références, CSV), plan d’usine, courbes, planning des commandes et journal. Pas de données de démonstration en production.

## Socle et compatibilité

- `/api/v2/tablet` : snapshot lu depuis le journal ; `/new-game`, `/next-turn`, `/actions`, `/configuration`. Les anciens endpoints restent disponibles.
- Journal append-only : temps hebdomadaire, élément, avant/après, cause decision/regle/alea ; rejeu, historique et refus. Les tirages identiques répétés restent des événements distincts.
- Sauvegarde transactionnelle SQLite de l’état, des entrées nouvelles et de `random.Random.getstate()`. Les générations précédentes du journal restent conservées. Une sauvegarde ancienne reçoit un instantané initial sans reconstitution inventée du passé.
- Indicateurs tablette lus depuis le journal. OTIF corrigé = commandes livrées à l’heure / commandes livrées ; taux de service = quantité livrée à l’heure / quantité totale demandée. Les ordres supprimés du carnet récent restent dans le calcul historique. Avant observation, valeur absente. Le champ legacy `trs` est présenté comme rendement des lignes : il ne constitue pas le TRS complet du cahier des charges.
- Configurations actuellement verrouillées faute de droit formateur approuvé. Rejet 403 et journal serveur. La gestion complète Verrouillé/Initial/Libre reste T04.
- Fichiers partagés ajoutés/modifiés : `engine/journal.py`, `engine/kpis.py`, `engine/tablet.py`, `simulation.py`, `database.py`, `main.py`. Les responsables T03/T05 doivent repartir de cette base. `models.py`, les IDs et endpoints historiques sont conservés.

## Questions et écarts à poursuivre

T00 : valider journée de 8 h / période d’un jour et choix des bibliothèques tableur/carte. Le moteur reste hebdomadaire sans commandes fictives de pause/vitesse. Le petit tableur livré est un carnet local ; il ne préjuge pas du choix définitif de bibliothèque.

T02 : Annexe A et validation du monde ; aucun `world.yaml` incomplet ou paramètre inventé n’est proposé. La configuration JSON existante reste utilisée. Le modèle de production reste celui du jeu existant, pas encore les N lignes identiques configurables de v3.

T04 : droits complets et cycle persistant d’alertes ; les couleurs actuelles proviennent des ruptures, seuils, pannes et retards existants. Carte GPS/itinéraires et Pareto : données et calculs moteur à fournir. T30 : catalogue complet et quatre modes de déclenchement à réaliser. T32 : critères de réussite et scénarios à définir. Les sources manquantes et questions Q01–Q11 du rapport T01 restent ouvertes.

## Vérification

Tests Python : rejeu, déterminisme, persistance/reprise RNG, générations, décisions réelles, refus serveur, OTIF et compatibilité legacy. Tests Node : adaptateur HTTP, erreurs, absence de mock, formules et sécurité du tableur. Parcours navigateur : responsive, comparaison, achat/OF, simulation, refus et accès depuis la 3D.
