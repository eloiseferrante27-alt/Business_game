# G-mix — objectif et guide de jeu

## Le but

Vous dirigez une entreprise qui fabrique et livre des produits aux magasins. Votre objectif est de garder les produits disponibles, de faire tourner les lignes de production et de livrer les commandes à temps. La partie avance semaine par semaine. Suivez surtout l’OTIF (livraisons à l’heure et complètes), le TRS (efficacité de l’usine) et la valeur du stock.

## Avant de commencer

Dans l’écran de préparation, choisissez le nom de l’entreprise et la difficulté. Vous pouvez aussi ajouter des fournisseurs en indiquant leur nom, délai, fiabilité et coût. Les fournisseurs ajoutés seront disponibles dans le formulaire de commande. Le niveau « Découverte » donne de meilleures conditions de départ ; « Expert » rend les approvisionnements et la production plus difficiles.

## Commandes

- **W, A, S, D** : déplacer votre personnage.
- **Clic sur le sol** : envoyer le personnage à cet endroit.
- **Clic sur un élément** : l’inspecter et, pour un PNJ, l’approcher.
- **E près d’un PNJ ou d’un équipement** : interagir.
- **Clic droit maintenu puis glissé** : faire pivoter la caméra.
- **Molette** : zoomer ou dézoomer.
- **1** : ouvrir le formulaire de commande.
- **4** : planifier un ordre de fabrication (OF).
- **2** : afficher ou masquer l’inspecteur.
- **3** : recentrer la caméra.

## Une semaine de jeu

1. Parcourez l’entrepôt et consultez les stocks, les lignes et les membres de l’équipe.
2. Surveillez les stocks de matières premières et commandez auprès d’un fournisseur. Le délai détermine la semaine de réception.
3. Depuis **Ordre fab.** (ou la touche **4**), choisissez un produit, une quantité et le nombre de lignes en parallèle. La matière disponible et la capacité de la ligne limitent la fabrication.
4. Cliquez sur **Lancer la semaine** pour recevoir les commandes arrivées, produire les OF, appliquer les défauts qualité et servir la demande client.
5. Relisez l’OTIF, le TRS, la qualité, les volumes livrés et les alertes, puis ajustez vos décisions pour la semaine suivante.

Le parcours en haut de l’écran présente les acteurs externes et les départements : fournisseur, réception, stock MP, production, contrôle qualité, emballage, entrepôt PF et client. **Pilotage** transmet les commandes MP et les OF. Les machines d’une ligne sont en série, donc l’opération la plus lente fixe la cadence ; les lignes en parallèle augmentent la capacité.

Si une panne bloque une ligne, sélectionnez-la et planifiez l’intervention. Le technicien répare une ligne par semaine et consomme une pièce de rechange. Si le stock PDR est vide, commandez-en au fournisseur depuis **Commande MP**.

Les commandes et la partie sont conservées dans `backend/data/gmix.db`. Le bouton **Reprendre la sauvegarde** permet de continuer après fermeture du jeu. Créer une nouvelle partie remplace cette sauvegarde après confirmation.

## Didacticiel

Le didacticiel optionnel se lance après la création ou la reprise d’une partie. Il guide les déplacements, l’inspection, les commandes et le passage d’une semaine. Vous pouvez le passer à tout moment.
