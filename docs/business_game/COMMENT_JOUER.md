# G-mix — objectif et guide de jeu (monde v3)

## Démarrer et arrêter le jeu

Depuis l’explorateur de fichiers, double-cliquez sur `start.bat` pour construire et démarrer le jeu avec Docker, attendre que l’API soit prête, puis ouvrir l’interface dans le navigateur. Pour arrêter le jeu, double-cliquez sur `stop.bat`. L’arrêt conserve la sauvegarde et les autres données.

## Le but

Vous pilotez une usine qui fabrique et livre des produits. Gardez les produits disponibles, faites tourner les lignes et livrez les commandes clients complètes et à l’heure. La partie avance semaine par semaine. Suivez surtout l’OTIF (commandes livrées complètes et à l’heure), le rendement des lignes, la qualité et la valeur du stock.

## Le monde

Le monde reprend le croquis du document « Mon monde v3 – blocs, agents et assets ».

- **En haut, le STOCK**, en trois parties avec les mêmes paramètres (stock initial, minimum, point de commande, quantité commandée, capacité max) : stock de MP, stock de semi-finis, stock de produits finis. Agent : le magasinier-cariste.
- **En dessous, l’USINE** (cadre en pointillés) :
  - Quai de déchargement : chauffeur fournisseur, réceptionnaire.
  - Bureau de réception : réceptionnaire.
  - Chaîne de production : responsable de production, chef de ligne, opérateurs de machine.
  - Emballage : emballeur.
  - Logistique & Transport : magasinier, chauffeur livreur, chauffeur client.
  - Contrôle qualité : contrôleur qualité.
  - Maintenance et stock PDR : technicien de maintenance.
- **Vous, le joueur**, n’avez pas de bureau : vous pilotez l’usine à distance avec votre tablette.
- **Fournisseurs et clients** sont des variables du scénario : dans le monde, on ne voit que leurs camions. Les camions fournisseurs arrivent au quai de déchargement. Nos camions de livraison partent du quai d’expédition, où certains clients viennent aussi charger avec leur propre camion.

La matière suit ce chemin, repris par la barre du haut : quai → bureau de réception → stock MP → chaîne de production (passage par le stock de semi-finis après M2) → contrôle qualité → emballage → stock PF → logistique & transport.

## Commandes

- **W, A, S, D** : déplacer votre personnage. **Maj** : courir.
- **Clic sur le sol** : aller à cet endroit.
- **Clic sur un bloc** : ouvrir sa page dans la tablette. **Clic sur un agent, une machine ou un équipement** : afficher sa fiche.
- **Barre du haut** : ouvrir la page du département.
- **E** près d’un agent ou d’un équipement : interagir.
- **1** ou **T** : ouvrir la tablette.
- **2** : afficher l’inspecteur. **3** : recentrer la caméra.
- **R** : afficher ou masquer le toit.
- **Clic droit maintenu puis glissé** : tourner la caméra. **Molette** : zoomer.

## La tablette

Ouvrez `/tablet` directement ou depuis l’usine 3D. L’accueil présente le plan des **huit blocs**, les fournisseurs et clients, les indicateurs et les alertes. Les dix départements ont les onglets **KPIs**, **Outils** et **Configurations**.

- **Fournisseurs** : choisissez une matière ou une PDR, comparez les offres puis passez une commande réelle.
- **Stock / Production** : consultez les disponibilités et lancez les ordres de fabrication.
- **Maintenance** : planifiez la réparation d’une ligne en panne ; les pièces sont consommées par le moteur.
- **Réception, Qualité, Emballage, Logistique et Clients** : suivez les bilans, files et échéances réellement simulés.
- **Outils** : tableaux filtrables, tableur à formules avec export CSV et sauvegarde locale par partie, plan d’usine, courbes historiques, planning et journal.
- **Configurations** : consultez les réglages. Les paramètres sans droit explicitement accordé restent verrouillés ; une tentative est refusée par le serveur et enregistrée dans le journal.

Avant une nouvelle partie, lisez et confirmez les règles. **Simuler la période suivante** avance d’une semaine. L’OTIF reste vide avant la première livraison ; il correspond ensuite aux commandes livrées complètes à l’heure parmi les commandes livrées.

## Une semaine de jeu

1. Consultez les alertes de la tablette : les références sous leur point de commande sont signalées, mais rien n’est commandé tout seul.
2. Comparez les fournisseurs et achetez la matière. Le délai du fournisseur fixe la semaine d’arrivée du camion.
3. Lancez les OF. La matière disponible, la capacité de la ligne et la place dans le stock de semi-finis limitent la production.
4. Cliquez sur **Lancer la semaine** : réception des camions, production, contrôle qualité, emballage, puis expéditions.
5. Relisez l’OTIF, le rendement, la qualité et les alertes, puis ajustez vos décisions.

Si une machine tombe en panne, sa ligne s’arrête : son voyant passe au rouge. Planifiez l’intervention depuis le département **Maintenance** ; le technicien répare une ligne par semaine et consomme une pièce de rechange. Un client annule sa commande après deux semaines de retard.

## Scénarios

Toutes les valeurs du monde (fournisseurs, produits, stocks, gamme, demande, transport, blocs et agents) sont dans `backend/app/scenarios/default.json`. Un nouveau scénario est un nouveau fichier dans ce dossier.

La partie est sauvegardée dans `backend/data/gmix.db`. **Reprendre la sauvegarde** permet de continuer après fermeture du jeu.

## Assets 3D

Chaque asset de la checklist v3 a une entrée dans `backend/app/static/assets.js` (modèle procédural). Pour le remplacer par un vrai modèle 3D (.glb), il suffit de changer la fonction `build` de cette entrée.

## Périmètre actuel et suite du cahier des charges

La tablette utilise le moteur réel, sans données de démonstration. Le journal et l’état du générateur aléatoire sont conservés avec la sauvegarde ; reprendre une partie conserve ses tirages futurs.

Cette version conserve le moteur hebdomadaire existant. Le passage à la journée de 8 h et aux vitesses ×1–×60 attend la décision T00 et l’implémentation de l’horloge. Le fichier Annexe A `world.yaml`, les droits Initial/Libre, la carte géographique avec itinéraires, le Pareto métier, les 34 aléas et les trois scénarios pédagogiques restent à réaliser. Aucun seuil de victoire n’est ajouté sans définition du scénario.

Voir `docs/jeu-live.md` pour le détail technique et les écarts restants.
