# Mon monde v3 – blocs, agents et assets

Nov 1, 2026 · v3, document de référence unique (remplace la v1 du 22 octobre et la v2 du 29 octobre). Mise à jour : le bureau d’étude des méthodes est supprimé ; son agent, ses assets et ses paramètres sont dans la chaîne de production.

L’usine est découpée en 8 blocs, transcrits du croquis : le schéma, les agents de chaque bloc, la liste minimale des assets 3D à créer, puis les paramètres et le fonctionnement de chaque élément.

## 1. Le schéma

**L’usine en 8 blocs : un stock en 3 parties et 7 blocs d’activité**

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ STOCK  ·  agent : magasinier-cariste  ·  mêmes paramètres pour les 3 parties                        │
│ ┌──────────────────────────────┐ ┌──────────────────────────────┐ ┌──────────────────────────────┐  │
│ │         Stock de MP          │ │     Stock de semi-finis      │ │   Stock de produits finis    │  │
│ └──────────────────────────────┘ └──────────────────────────────┘ └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐
╎  USINE (cadre en pointillés)                                                                        ╎
╎ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ╎
╎ │     Quai de     │ │    Bureau de    │ │    Chaîne de    │ │    Emballage    │ │   Logistique &  │ ╎
╎ │   déchargement  │ │    réception    │ │    production   │ │                 │ │    Transport    │ ╎
╎ │                 │ │                 │ │                 │ │                 │ │                 │ ╎
╎ │    Chauffeur    │ │  Réceptionnaire │ │   Responsable   │ │    Emballeur    │ │    Chauffeurs   │ ╎
╎ │   fournisseur   │ │                 │ │  de production  │ │                 │ │    Magasinier   │ ╎
╎ │  Réceptionnaire │ │                 │ │  Chef de ligne  │ │                 │ │                 │ ╎
╎ │                 │ │                 │ │    Opérateurs   │ │                 │ │                 │ ╎
╎ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘ ╎
╎ ┌───────────────────────────────────────────────┐ ┌───────────────────────────────────────────────┐ ╎
╎ │                Contrôle qualité               │ │            Maintenance et stock PDR           │ ╎
╎ │                                               │ │                                               │ ╎
╎ │               Contrôleur qualité              │ │           Technicien de maintenance           │ ╎
╎ │                                               │ │                                               │ ╎
╎ │                                               │ │                                               │ ╎
╎ └───────────────────────────────────────────────┘ └───────────────────────────────────────────────┘ ╎
└╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┘

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ JOUEUR  ·  pilote de l’usine, sans bureau                                                           │
│ À distance, avec sa tablette : commandes clients, achats de MP,                                     │
│ lancement des ordres de fabrication                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Fournisseurs et clients : des variables du scénario, visibles comme camions.
```

Les éléments rayés sur le croquis (visualisation des fournisseurs, carte) ne sont pas repris. La matière suit ce chemin : quai → bureau de réception → stock MP → chaîne de production (avec passage possible par le stock de semi-finis) → contrôle qualité → emballage → stock PF → logistique & transport.

**Un seul stock.** MP, semi-finis et PF sont trois parties du même stock, avec les mêmes paramètres de base : stock initial, stock minimum, point de commande, quantité commandée, capacité maximum. Le monde reste modulable : chaque scénario règle ces valeurs.

**Deux quais.** Le quai de déchargement reçoit les camions des fournisseurs. La logistique & transport fait face aux clients : elle livre avec ses propres camions, et certains clients viennent charger au quai d’expédition avec leur camion.

Le joueur pilote l’usine à distance avec sa tablette : commandes clients, achats de MP, lancement des ordres de fabrication. Il n’a pas de bureau, pour éviter les allers-retours entre les blocs. **The tablet is the player’s global interface.** It reaches what has no physical block: the list of suppliers in the world with their prices, lead times and reliability, a spreadsheet to compare the cost of supplier X against Y, customer orders, and launching production orders.

**Fournisseurs et clients.** Ce sont des variables du scénario (délais, fiabilité, demande…). Dans le monde 3D, on ne voit que leurs camions qui arrivent et repartent.

## 2. Les agents de chaque bloc

| Bloc | Agents | Rôle dans le bloc |
| --- | --- | --- |
| Quai de déchargement | Chauffeur fournisseur (externe), réceptionnaire | Amener le camion, décharger les palettes |
| Bureau de réception | Réceptionnaire | Contrôler la livraison, l’enregistrer, étiqueter les palettes |
| Stock (MP, semi-finis, PF) | Magasinier-cariste | Ranger, sortir dans l’ordre d’arrivée, préparer les kits, suivre les 3 stocks |
| Chaîne de production | Responsable de production, chef de ligne, opérateurs de machine | Définir les gammes, les nomenclatures et les temps ; lancer et suivre la production ; faire tourner les machines |
| Contrôle qualité | Contrôleur qualité | Contrôler et trier : conforme, à retoucher, rebut |
| Emballage | Emballeur | Mettre en carton, étiqueter et peser, monter et filmer la palette, l’envoyer au stock PF |
| Maintenance et stock PDR | Technicien de maintenance | Réparer les pannes, faire le préventif, gérer les pièces de rechange |
| Logistique & Transport | Chauffeur livreur, magasinier, chauffeur client (externe) | Préparer les expéditions, charger les camions (les siens et ceux des clients venus au quai), livrer le client |
| Aucun bloc (à distance) | Joueur | Piloter l’usine depuis sa tablette : commandes clients, achats de MP, lancement des ordres de fabrication |

## 3. Les assets à créer

Liste minimale, à cocher au fur et à mesure. « Réutilisé » signale un asset déjà créé pour un autre bloc : il n’y a qu’un modèle à faire.

### Quai de déchargement

- [ ] Quai avec porte sectionnelle
- [ ] Niveleur de quai (rampe)
- [ ] Camion fournisseur
- [ ] Palette Europe avec sa charge de MP
- [ ] Transpalette manuel
- [ ] Zone de dépose (marquage au sol)
- [ ] Personnage : chauffeur fournisseur
- [ ] Personnage : réceptionnaire

### Bureau de réception

- [ ] Bureau et chaise
- [ ] Ordinateur
- [ ] Lecteur code-barres
- [ ] Imprimante d’étiquettes
- [ ] Balance au sol
- [ ] Zone de quarantaine (marquage rouge)
- [ ] Bon de livraison (document)
- [ ] Personnage : réceptionnaire (réutilisé du quai)

### Stock

**Commun aux 3 stocks**

- [ ] Rack à palettes (un module, répété)
- [ ] Étagère à bacs
- [ ] Bac plastique
- [ ] Chariot élévateur
- [ ] Borne de recharge
- [ ] Panneau de zone (MP, semi-finis, PF)
- [ ] Personnage : magasinier-cariste

**Stock de MP**

- [ ] Palette de matière première (réutilisée du quai)

**Stock de produits semi-finis**

- [ ] Bac ou chariot de pièces semi-finies

**Stock de produits finis**

- [ ] Palette de produits finis filmée

### Chaîne de production

- [ ] Machine : un modèle par opération (ex. M1 à M4)
- [ ] Voyant d’état sur chaque machine (colonne lumineuse)
- [ ] Table d’attente entre deux machines
- [ ] Convoyeur ou chariot de transfert
- [ ] Établi pour les postes manuels
- [ ] Pièce en cours de fabrication
- [ ] Tableau de ligne (OF, cadence, arrêts)
- [ ] Bac à déchets
- [ ] Personnage : chef de ligne
- [ ] Personnage : opérateur de machine
- [ ] Coin méthodes : bureau, chaise et ordinateur (réutilisés du bureau de réception)
- [ ] Tableau de planning
- [ ] Armoire à dossiers (gammes, nomenclatures)
- [ ] Personnage : responsable de production

### Contrôle qualité

- [ ] Table de contrôle
- [ ] Instruments de mesure (pied à coulisse, mètre)
- [ ] Banc d’essai
- [ ] Zone « conforme » (marquage vert)
- [ ] Zone « à retoucher » (marquage orange)
- [ ] Bac à rebut
- [ ] Ordinateur de saisie (réutilisé du bureau de réception)
- [ ] Personnage : contrôleur qualité

### Emballage

- [ ] Table d’emballage
- [ ] Carton (fermé et ouvert) et ruban adhésif
- [ ] Imprimante d’étiquettes (réutilisée du bureau de réception)
- [ ] Balance de table
- [ ] Filmeuse de palettes
- [ ] Palette de produits finis filmée (même modèle que le stock PF)
- [ ] Personnage : emballeur

### Maintenance et stock PDR

- [ ] Établi avec étau
- [ ] Servante d’outils (chariot à tiroirs)
- [ ] Armoire à pièces de rechange
- [ ] Pièce de rechange (modèle générique)
- [ ] Kit de consignation (cadenas)
- [ ] Tableau des interventions
- [ ] Personnage : technicien de maintenance

### Logistique & Transport

- [ ] Camion de livraison client
- [ ] Zone de préparation des expéditions (marquage au sol)
- [ ] Transpalette (réutilisé du quai)
- [ ] Palette de produits finis (réutilisée du stock PF)
- [ ] Personnage : chauffeur livreur
- [ ] Personnage : magasinier
- [ ] Personnage : chauffeur client (variante du chauffeur fournisseur)
- [ ] Quai d’expédition (réutilisé du quai de déchargement)
- [ ] Camion d’un client venu charger (variante du camion de livraison)

### Commun à toute l’usine

- [ ] Bâtiment : sol, murs, toit
- [ ] Porte d’accès piétons
- [ ] Marquage des allées (engins, piétons)
- [ ] Panneau de signalisation de chaque bloc
- [ ] Extincteur
- [ ] Modèle de personnage de base, décliné en tenue par rôle
- [ ] Personnage : joueur, avec sa tablette

## 4. Paramètres et fonctionnement

Toutes les valeurs sont des **valeurs de départ**, à remplacer selon le produit et le scénario. Le monde reste le même ; c’est le scénario qui règle les chiffres.

### 4.1 Règles générales

- Toutes les lignes fabriquent le même produit.
- Dans une ligne, les machines sont en série : chaque machine dépend de la précédente. Les lignes sont en parallèle : elles ne dépendent pas les unes des autres.
- Chaque agent a un état : disponible, occupé, en déplacement, en pause, absent.
- Horloge : journée de 8 h simulées, accélérable de ×1 à ×60, avec pause. Tous les temps des machines sont en minutes simulées.
- Les alertes (stock bas, livraison non conforme, panne, lot bloqué) arrivent sur la tablette du joueur.

### 4.2 Fournisseurs (variables du scénario)

Rôle : fournir la MP quand le joueur la commande. Dans le monde 3D, on ne voit que leur camion.

Paramètres (par fournisseur ; le monde peut en contenir plusieurs, comparés sur la tablette)

- Prix unitaire par article
- Délai de livraison : 3 jours
- Fiabilité du délai : 95 % des livraisons à l’heure
- Taux de livraisons non conformes : 2 %
- Quantité minimum de commande : 1 palette
- Créneau de livraison : 8 h – 10 h
- Camion : 4 à 6 palettes
- Stock du fournisseur : illimité par défaut (option : stock limité)

Fonctionnement

- Le fournisseur reçoit la commande du joueur, prépare les palettes et envoie le camion avec le bon de livraison.
- Le chauffeur arrive au quai de déchargement, attend si le quai est occupé, puis repart une fois le camion vide.

### 4.3 Quai de déchargement

Rôle : recevoir les camions des fournisseurs et décharger la MP.

Paramètres

- Quai : 1 camion à la fois
- Zone de dépose : 6 palettes
- Transpalette : 2 000 kg max
- Temps de déchargement : 2 min / palette

Fonctionnement

- Le réceptionnaire ouvre le quai et décharge le camion sur la zone de dépose.
- Un camion qui arrive quand le quai est occupé attend son tour.

### 4.4 Bureau de réception

Rôle : contrôler la livraison, l’enregistrer et l’envoyer au stock MP.

Paramètres

- Zone de quarantaine : 2 palettes
- Temps de contrôle : 5 min / palette

Fonctionnement

- Compter et comparer au bon de commande.
- Conforme → étiqueter → envoyer au stock MP.
- Non conforme → quarantaine → alerte sur la tablette du joueur, réclamation au fournisseur.
- Enregistrer l’entrée dans le système.

### 4.5 Stock (MP, semi-finis, PF)

Rôle : garder la matière et les produits, les sortir dans l’ordre d’arrivée (FIFO), préparer les kits des ordres de fabrication (OF).

Paramètres (identiques pour les 3 parties, par article)

- Stock initial
- Stock minimum (stock de sécurité)
- Point de commande : niveau qui déclenche une commande (MP) ou un OF (PF)
- Quantité commandée
- Capacité maximum : MP 24 emplacements, PF 20 palettes, semi-finis à régler par le scénario

Équipement

- Chariot élévateur : 1 200 kg, batterie 8 h, recharge 6 h
- Étagère à bacs (petites pièces), zone de préparation des kits

Fonctionnement

- Ranger les palettes reçues (MP depuis la réception, PF depuis l’emballage).
- Préparer le kit d’un OF : quantité de nomenclature × taille du lot, et le livrer à la ligne.
- Recevoir et rendre à la ligne les pièces semi-finies quand une ligne les met en attente.
- Sortir les palettes PF pour la logistique & transport.
- Faire l’inventaire.
- Stock sous le point de commande → alerte sur la tablette du joueur.

### 4.6 Chaîne de production

Rôle : définir comment le produit se fabrique, puis transformer la MP en produits sur N lignes en parallèle.

Paramètres de la chaîne

- Nombre de lignes : N (1 à 3), toutes identiques
- Une ligne = machines en série + tables d’attente entre machines + transfert (chariot ou convoyeur) + opérateurs
- Responsable de production : 1 ; chef de ligne : 1 pour toutes les lignes ; opérateurs : 1 par machine par défaut

Paramètres de chaque machine

| Paramètre | Unité | Ce que c’est |
| --- | --- | --- |
| Identifiant | — | Ligne + rang, ex. L1-M3 |
| Opération | — | Ce que fait la machine |
| Temps de cycle | min / produit | Temps pour traiter 1 produit |
| Vitesse | produits / h | 60 ÷ temps de cycle |
| Temps de fonctionnement | min | Temps de marche avant une pause planifiée |
| Temps d’arrêt | min | Durée de la pause planifiée |
| MTBF | h | Temps moyen de marche entre deux pannes |
| MTTR | h | Temps moyen de réparation d’une panne |
| Temps de réglage | min | Arrêt à chaque changement de lot |
| Durée de vie de l’outil | produits | Après ce nombre, l’outil doit être changé |
| Taux de défaut | % | Part des produits mauvais en sortie |
| Capacité de la table d’attente | produits | Place en sortie avant la machine suivante |
| Temps de transfert | min | Temps pour aller à la machine suivante |
| Opérateurs | nombre | Opérateurs nécessaires |
| État | — | Arrêt, marche, pause, réglage, panne, attente de matière, sortie pleine |

Exemple d’une ligne de 4 machines

| Machine | Cycle | Vitesse | Fonctionnement / arrêt | MTBF / MTTR | Réglage | Défaut | Table d’attente |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | 2 min | 30 / h | 110 / 10 min | 40 h / 1 h | 10 min | 2 % | 10 |
| M2 | 1,5 min | 40 / h | 110 / 10 min | 80 h / 0,5 h | 5 min | 1 % | 10 |
| M3 (goulot) | 3 min | 20 / h | 110 / 10 min | 60 h / 1 h | 0 min | 3 % | 10 |
| M4 | 1 min | 60 / h | 110 / 10 min | 100 h / 0,5 h | 5 min | 2 % | 10 |

Taux de production

- Disponibilité d’une machine = fonctionnement ÷ (fonctionnement + arrêt)
- Débit réel d’une machine = vitesse × disponibilité × (1 − taux de défaut)
- Débit d’une ligne = débit de la machine la plus lente (le goulot)
- Débit de l’usine = somme des débits des lignes
- Taux de production = produits bons réalisés ÷ produits prévus

Exemple : M3 est le goulot à 20 / h. Disponibilité = 110 ÷ 120 = 92 %. Débit réel = 20 × 0,92 × 0,97 ≈ 17,8 produits / h par ligne. Avec 3 lignes : environ 53 produits / h, soit environ 430 par journée de 8 h. Taux de production de la ligne = 17,8 ÷ 20 ≈ 89 %.

Flux dans une ligne

- Le flux avance à la vitesse du goulot : les machines plus rapides attendent.
- Table d’attente pleine → la machine d’avant s’arrête. Table vide → la machine d’après attend.
- Temps de traversée d’un produit (sans attente) = somme des temps de cycle + somme des temps de transfert. Exemple : 2 + 1,5 + 3 + 1 = 7,5 min, plus 4 transferts de 0,5 min = 9,5 min.
- Temps pour un lot de 20 ≈ temps du premier produit + 19 × cycle du goulot = 9,5 + 19 × 3 ≈ 67 min.
- Si une ligne tombe en panne, les autres continuent : avec 3 lignes, l’usine passe de 60 à 40 produits / h. Si M3 tombe en panne, sa ligne entière s’arrête.

Méthodes de production (nomenclature, gamme, temps)

La chaîne définit elle-même comment le produit se fabrique. Ces données alimentent aussi le stock (kits) et la tablette du joueur.

Nomenclature : matière pour 1 produit fini

| Article | Type | Quantité pour 1 PF | Unité |
| --- | --- | --- | --- |
| {MP 1} | Matière première | {…} | {pièce, kg, m…} |
| {MP 2} | Matière première | {…} | {…} |
| {Composant} | Composant (vis, pièce achetée…) | {…} | {…} |
| {Emballage} | Emballage | {…} | {…} |

- Matière pour un lot = quantité pour 1 PF × nombre de produits du lot
- Surplus pour le rebut : × (1 + taux de rebut)
- Gamme : ordre des opérations et machine de chaque opération
- Temps : temps de cycle, de réglage et de transfert de chaque machine (tableau ci-dessus)

Fonctionnement

- Chef de ligne : lancer l’OF reçu du joueur sur une ligne, affecter les opérateurs, remplacer un absent, suivre la cadence et les arrêts, appeler la maintenance.
- Opérateur : démarrer et arrêter sa machine, charger la matière et décharger le produit, régler la machine au changement de lot, changer l’outil usé, prendre sa pause, signaler une panne.
- Responsable de production : tenir à jour la nomenclature, les gammes et les temps. Une modification (nouveau produit, nouveau temps) change les kits préparés au stock et le débit de la chaîne.

### 4.7 Contrôle qualité

Rôle : vérifier chaque produit en sortie de ligne et le trier.

Paramètres

- Temps de contrôle : 1 min / produit
- Fréquence : 100 % ou 1 produit sur N
- Seuil de blocage d’un lot : 15 % de rebut

Fonctionnement

- Conforme → emballage.
- Défaut récupérable → retour à la ligne (retouche).
- Défaut grave → rebut.
- Trop de rebut → lot bloqué, chef de ligne prévenu, alerte sur la tablette du joueur.

### 4.8 Emballage

Rôle : mettre les produits conformes en colis puis en palettes.

Paramètres

- Produits par colis : 1
- Colis par palette : 6
- Temps d’emballage : 2 min / colis
- Temps de filmage : 5 min / palette

Fonctionnement

- Mettre le produit en carton et fermer, étiqueter et peser le colis.
- Monter la palette, la filmer et l’envoyer au stock PF.

### 4.9 Maintenance et stock PDR

Rôle : réparer les machines en panne et changer les pièces usées avant la panne.

Paramètres

- Temps de déplacement jusqu’à la machine : 3 min
- Durée de réparation : MTTR de la machine (section 4.6)
- Par pièce de rechange : stock, stock minimum, délai de réapprovisionnement

Fonctionnement

- Recevoir une demande d’intervention, aller à la machine et la mettre en sécurité (consignation).
- Réparer, en sortant la pièce du stock PDR si besoin, puis remettre la machine en marche.
- Faire la maintenance préventive aux dates prévues.
- Pièce sous le stock minimum → commande.
- Le technicien ne répare qu’une panne à la fois.

### 4.10 Logistique & Transport

Rôle : préparer les expéditions et faire partir les produits finis chez les clients.

Paramètres

- Quai d’expédition : 1 camion à la fois
- Temps de chargement : 2 min / palette
- Capacité d’un camion de livraison : nombre de palettes, à régler par le scénario
- Nombre de camions de l’usine : à régler par le scénario
- Mode de livraison par client : livré par l’usine, ou enlevé par le client au quai

Fonctionnement

- Le magasinier prépare la commande à partir du stock PF sur la zone de préparation.
- Livraison par l’usine : le chauffeur livreur charge le camion de l’usine et livre le client.
- Enlèvement : le chauffeur client vient au quai d’expédition, attend s’il est occupé, puis repart chargé.

### 4.11 Clients (variables du scénario)

Rôle : commander et recevoir les produits finis. Dans le monde 3D, on ne voit que leur camion.

Paramètres

- Demande moyenne : 100 produits / jour
- Variabilité de la demande : ± 10 %
- Délai promis : 5 jours
- Mode de livraison : livré par l’usine ou enlèvement au quai

Fonctionnement

- Le client passe une commande, qui arrive sur la tablette du joueur.
- La commande est livrée par l’usine ou enlevée par le chauffeur du client.

### 4.12 Joueur et sa tablette

Rôle : piloter l’usine à distance. Il remplace l’ancien département de pilotage.

Paramètres

- Lancement des OF : à la commande client, ou quand le stock PF passe sous le minimum
- Taille d’un lot (OF) : 20 produits
- Journée de travail : 8 h

Fonctionnement (depuis la tablette)

- Recevoir les commandes clients.
- Créer et lancer les OF, choisir la ligne, changer les priorités (commande urgente).
- Comparer les fournisseurs (prix, délai, fiabilité) et commander la MP.
- Recevoir les alertes : stock bas, livraison non conforme, panne, lot bloqué.
- Suivre les indicateurs.
- Toucher un bloc dans le monde ouvre son interface, avec ses indicateurs et ses décisions.

### 4.13 Produit fini

Paramètres

- Code et nom du produit
- Dimensions et poids
- Taille d’un lot (OF)
- Conditionnement : produits par colis, colis par palette

États (chacun a un aspect différent dans le monde 3D : matière brute, pièce en cours, produit fini, carton, palette)

- En cours (sur la ligne) → à contrôler → conforme / à retoucher / rebut → emballé → en stock PF → expédié

### 4.14 Les interactions

Interactions externes

| De → vers | Ce qui passe | Agents | Déclencheur |
| --- | --- | --- | --- |
| Joueur → Fournisseur | Commande de MP | Joueur → fournisseur | Stock MP sous le point de commande |
| Fournisseur → Quai de déchargement | Palettes de MP + bon de livraison | Chauffeur fournisseur → réceptionnaire | Fin du délai de livraison |
| Bureau de réception → Fournisseur | Réclamation | Réceptionnaire → fournisseur | Livraison non conforme |
| Client → Joueur | Commande de PF | Client → joueur | Besoin du client |
| Logistique & Transport → Client | Palettes de PF + bon de livraison | Chauffeur livreur ou chauffeur client | Commande prête |

Interactions internes

| De → vers | Ce qui passe | Agents | Déclencheur |
| --- | --- | --- | --- |
| Quai de déchargement → Bureau de réception | Palettes déchargées | Réceptionnaire | Camion vidé |
| Bureau de réception → Stock MP | Palettes contrôlées | Réceptionnaire → magasinier-cariste | Contrôle OK |
| Joueur → Chaîne de production | Ordre de fabrication (OF) | Joueur → chef de ligne | Commande client ou stock PF bas |
| Joueur → Stock MP | Demande de kit pour l’OF | Joueur → magasinier-cariste | OF lancé |
| Chaîne de production → Stock | Nomenclature (contenu des kits) | Responsable de production → magasinier-cariste | Nouveau produit ou modification |
| Stock MP → Chaîne de production | Kit de matière | Magasinier-cariste → opérateur M1 | Kit prêt |
| Machine → machine suivante | Produit en cours | Opérateur → opérateur | Fin du cycle |
| Chaîne ↔ Stock semi-finis | Pièces semi-finies | Opérateur ↔ magasinier-cariste | Mise en attente ou reprise |
| Chaîne de production → Contrôle qualité | Lot terminé | Opérateur dernière machine → contrôleur | Fin du lot |
| Contrôle qualité → Chaîne de production | Produits à retoucher | Contrôleur → chef de ligne | Défaut récupérable |
| Contrôle qualité → Emballage | Produits conformes | Contrôleur → emballeur | Contrôle OK |
| Emballage → Stock PF | Palettes filmées | Emballeur → magasinier-cariste | Palette complète |
| Stock PF → Logistique & Transport | Palettes à expédier | Magasinier-cariste → magasinier | Commande à préparer |
| Chaîne de production → Maintenance | Demande d’intervention | Opérateur → technicien | Panne ou outil usé |
| Maintenance → Chaîne de production | Machine réparée | Technicien → opérateur | Fin de réparation |
| Stock, réception, contrôle, maintenance → Joueur | Alertes | Tous → joueur (tablette) | Stock bas, non-conformité, panne, lot bloqué |

Ressources partagées (sources d’attente) : le quai de déchargement, le quai d’expédition, le chariot élévateur, le technicien (une seule panne à la fois), le chef de ligne.
