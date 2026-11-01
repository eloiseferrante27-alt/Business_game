# G-mix — objectif et guide de jeu (monde v3)

## Le but

Vous pilotez une usine qui fabrique et livre des produits. Gardez les produits disponibles, faites tourner les lignes et livrez les commandes clients complètes et à l’heure. La partie avance semaine par semaine. Suivez surtout l’OTIF (commandes livrées complètes et à l’heure), le TRS (efficacité de l’usine), la qualité et la valeur du stock.

## Le monde

Le monde reprend le croquis du document « Mon monde v3 – blocs, agents et assets ».

- **En haut, le STOCK**, en trois parties avec les mêmes paramètres (stock initial, minimum, point de commande, quantité commandée, capacité max) : stock de MP, stock de semi-finis, stock de produits finis. Agent : le magasinier-cariste.
- **En dessous, l’USINE** (cadre en pointillés) :
  - Quai de déchargement : chauffeur fournisseur, réceptionnaire.
  - Bureau de réception : réceptionnaire.
  - Chaîne de production : chef de ligne, opérateurs de machine.
  - Emballage : emballeur.
  - Logistique & Transport : magasinier, chauffeur livreur, chauffeur client.
  - Contrôle qualité : contrôleur qualité.
  - Bureau d’étude des méthodes de production : responsable de production.
  - Maintenance et stock PDR : technicien de maintenance.
- **Vous, le joueur**, n’avez pas de bureau : vous pilotez l’usine à distance avec votre tablette.
- **Fournisseurs et clients** sont des variables du scénario : dans le monde, on ne voit que leurs camions. Les camions fournisseurs arrivent au quai de déchargement. Nos camions de livraison partent du quai d’expédition, où certains clients viennent aussi charger avec leur propre camion.

La matière suit ce chemin, repris par la barre du haut : quai → bureau de réception → stock MP → chaîne de production (passage par le stock de semi-finis après M2) → contrôle qualité → emballage → stock PF → logistique & transport.

## Commandes

- **W, A, S, D** : déplacer votre personnage. **Maj** : courir.
- **Clic sur le sol** : aller à cet endroit.
- **Clic sur un bloc, un agent, une machine ou un équipement** : afficher sa fiche.
- **Barre du haut** : aller directement à l’entrée d’un bloc.
- **E** près d’un agent ou d’un équipement : interagir.
- **1** ou **T** : ouvrir la tablette.
- **2** : afficher l’inspecteur. **3** : recentrer la caméra.
- **R** : afficher ou masquer le toit.
- **Clic droit maintenu puis glissé** : tourner la caméra. **Molette** : zoomer.

## La tablette

- **Fournisseurs** : tous les fournisseurs du monde, avec leur prix par matière, leur délai, leur fiabilité et leur taux de non-conformité.
- **Comparateur** : coût total, arrivée prévue et quantité conforme attendue pour chaque fournisseur ; cochez deux fournisseurs pour comparer X et Y.
- **Achats MP** : passer une commande de matière ou de pièces de rechange, et suivre les commandes en cours.
- **Commandes clients** : ce qu’il faut servir, l’échéance, le mode (livraison par nos camions ou enlèvement par le client) et le statut.
- **Ordres de fabrication** : lancer un OF et suivre son avancement (semi-finis, puis produits terminés).
- **Stocks & alertes** : les 3 parties du stock et le stock PDR, les alertes au point de commande, et les lignes en panne à réparer.

## Une semaine de jeu

1. Consultez les alertes de la tablette : les références sous leur point de commande sont signalées, mais rien n’est commandé tout seul.
2. Comparez les fournisseurs et achetez la matière. Le délai du fournisseur fixe la semaine d’arrivée du camion.
3. Lancez les OF. La matière disponible, la capacité de la ligne et la place dans le stock de semi-finis limitent la production.
4. Cliquez sur **Lancer la semaine** : réception des camions, production, contrôle qualité, emballage, puis expéditions.
5. Relisez l’OTIF, le TRS, la qualité et les alertes, puis ajustez vos décisions.

Si une machine tombe en panne, sa ligne s’arrête : son voyant passe au rouge. Planifiez l’intervention depuis l’onglet **Stocks & alertes** ; le technicien répare une ligne par semaine et consomme une pièce de rechange. Un client annule sa commande après deux semaines de retard.

## Scénarios

Toutes les valeurs du monde (fournisseurs, produits, stocks, gamme, demande, transport, blocs et agents) sont dans `backend/app/scenarios/default.json`. Un nouveau scénario est un nouveau fichier dans ce dossier.

La partie est sauvegardée dans `backend/data/gmix.db`. **Reprendre la sauvegarde** permet de continuer après fermeture du jeu.

## Assets 3D

Chaque asset de la checklist v3 a une entrée dans `backend/app/static/assets.js` (modèle procédural). Pour le remplacer par un vrai modèle 3D (.glb), il suffit de changer la fonction `build` de cette entrée.
