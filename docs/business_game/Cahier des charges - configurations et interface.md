# Cahier des charges - configurations et interface

> Extraction documentaire du PDF fourni le 2026-11-01 avec `pdftotext -layout`.
> Source faisant foi : [PDF original](<Cahier des charges configurations et interface.pdf>).
> Les 42 pages sont conservées dans leur ordre. Les maquettes et schémas graphiques
> restent dans le PDF. Les tableaux sont reproduits en texte à largeur fixe.
> L’indentation extraite de l’annexe A n’est pas un fichier YAML exécutable ;
> consulter le PDF pour la structure. Aucune valeur manquante n’a été complétée.

## Page 1

```text
Cahier des charges : configurations et
interface
  ​Nov 1, 2026        · ​@User

Ce cahier des charges unique décrit, pour chaque département de l’usine G-MIX ainsi que
pour les fournisseurs et les clients, l’interface de la tablette du joueur et tout ce que le
moteur fait derrière. Il remplace les cahiers « module chaîne de production » et « interfaces
de la tablette du joueur », et s’appuie sur le document de référence « Mon monde v3 ».


Partie A — Socle commun

1. Mode d’emploi pour l’IA de construction
Tu construis, à partir de ce cahier, le moteur et les interfaces de chaque département de
G-MIX, sans reconstruire l’usine 3D existante. Procède dans cet ordre :

 1. Lis en entier ce cahier, le document « Mon monde v3 » et le cahier « module
    fournisseurs et acheminement » avant toute modification.
 2. Inventorie ce que le code contient déjà : simulation.py , models.py , agents.py ,
     main.py , index.html , game.js , game3d.js , scènes Godot.
 3. Produis un rapport d’écart : éléments présents et conformes, présents à compléter,
    absents.
 4. Construis d’abord le socle commun (partie A), puis chaque département (partie B),
    puis l’ensemble (partie C).
 5. Pour chaque département, construis le moteur avant l’interface : une interface
     n’affiche que ce que le moteur calcule.
 6. Ne code jamais en dur une valeur, un droit, un fournisseur ou un client : tout vient du
     fichier de configuration (annexe A) ou du moteur.
 7. Livre ce qui est listé en section 24.

Niveaux d’exigence : DOIT = obligatoire ; DEVRAIT = recommandé, à signaler dans le
rapport d’écart s’il n’est pas fait ; PEUT = optionnel.

Ce que tu ne dois pas faire : supprimer ou renommer un identifiant ou un paramètre
existant (toute extension est additive) ; inventer un paramètre absent de la configuration
(le signaler comme manquant) ; laisser une IA ou l’interface calculer un KPI, un coût, un
délai ou un débit ; permettre une modification qu’un droit interdit.
```

## Page 2

```text
Deux IA interviennent. Toi, l’IA de construction, qui codes le module. Et l’IA de
génération, intégrée au produit, que le formateur utilise pour remplir le monde (section
23).


2. Objectif, périmètre et principes
Un formateur configure un monde, un joueur pilote l’usine depuis sa tablette, et le moteur
simule les conséquences de ses décisions. Le monde 3D est la scène ; le jeu se joue dans
les interfaces.

     Périmètre : les 8 blocs de la v3 (quai de déchargement, bureau de réception, stock,
     chaîne de production, contrôle qualité, emballage, maintenance et stock PDR,
     logistique & transport), plus les fournisseurs et les clients. Chacun a une partie
     interface (ce que le joueur voit et fait) et une partie moteur (ce qui se passe derrière).
     Intention pédagogique : piloter une usine complète, de l’achat à la livraison, et arbitrer
     entre coût, délai, qualité et risque.
     Secteur : le monde est générique. Le secteur (pharmaceutique, biscuiterie, etc.) ne
     change que les valeurs de la configuration, jamais la structure.

Sept principes :

 1. Le moteur calcule. KPIs, coûts, délais, débits et itinéraires sont produits par le moteur,
     jamais par une IA ni par l’interface.
 2. Structure fixe. Aucun champ, entité, état ou type d’effet n’est créé ou renommé
    pendant la partie.
 3. Rien n’est inventé. Une valeur manquante est signalée, jamais devinée.
 4. Reproductibilité. Même graine, même déroulement. Le monde validé est figé.
 5. Extension additive. Le module s’ajoute au code existant sans casser ce qui marche.
 6. Le formateur décide des droits. Il choisit ce que le joueur peut régler, avant et pendant
    la partie.
 7. Aucun choix n’est bon ou mauvais en soi. Les décisions sont jugées en fin de partie, au
     regard des critères de réussite.


3. Rôles et glossaire

   Terme                                           Définition

   Formateur                                       Configure le monde, les droits du joueur, le
                                                   scénario et les critères de réussite ; déclenche les
                                                   aléas.
```

## Page 3

```text
   Terme                                           Définition

   Joueur                                          Pilote l’usine à distance avec sa tablette. Décide
                                                   dans les limites fixées par le formateur.

   Agent                                           Personnage du monde 3D (réceptionnaire,
                                                   magasinier-cariste, opérateur…). Exécute les
                                                   décisions du joueur et les règles du moteur.

   Paramètre du monde                              Réalité physique réglée par le formateur (temps de
                                                   cycle, MTBF, délai d’un fournisseur, demande).
                                                   Lecture seule pour le joueur.

   Configuration du joueur                         Méthode de travail réglable par le joueur (point de
                                                   commande, taille de lot, stratégie de maintenance),
                                                   selon son droit.

   Droit                                           Verrouillé, Initial seulement ou Libre (section 5).

   Interface                                       Page d’un département sur la tablette : onglets
                                                   KPIs, Outils, Configurations.

   KPI                                             Indicateur calculé par le moteur à partir du journal.

   Action                                          Décision ponctuelle du joueur (lancer un OF,
                                                   passer une commande).

   OF                                              Ordre de fabrication : produit, quantité, ligne,
                                                   priorité.

   Article                                         Ligne de la nomenclature (MP-01, CO-01…).

   Offre                                           Couple fournisseur × article : prix, délai, capacité,
                                                   qualité, fiabilité.

   Aléa                                            Événement du catalogue (AL-NN), déclenchable
                                                   selon quatre modes.

   Scénario                                        État initial, graine, aléas programmés, critères de
                                                   réussite (SC-NN).

   Journal                                         Liste horodatée de tous les changements d’état,
                                                   décisions et aléas ; source unique des KPIs.

   Période                                         Intervalle entre deux décisions ; unité de calcul des
                                                   KPIs (point ouvert, section 25).
```

## Page 4

```text
4. Configuration du monde par le formateur
Avant la partie, le formateur remplit le fichier de configuration (annexe A), lui-même ou
avec l’IA de génération. Trois modes, combinables paramètre par paramètre : tout généré
(il donne le secteur, l’IA remplit), mixte, manuel.

Chaque paramètre du monde est dans l’un de ces états :


   État                   Sens                          Comportement

   Fixé                   Valeur donnée par le          Verrouillée : l’IA ne la modifie jamais
                          formateur

   À générer              Le formateur délègue à l’IA   L’IA remplit dans les plages autorisées, en
                                                        cohérence avec les valeurs fixées

   Désactivé              Paramètre retiré              Le moteur ne l’utilise pas et ne l’affiche pas


Chaque configuration du joueur reçoit en plus une valeur de départ et un droit (section
5).

Noyau obligatoire : chaque département liste les paramètres sans lesquels le moteur ne
peut pas simuler. Ils ne sont jamais désactivables.

Vérifications avant validation (DOIT)

      Les valeurs respectent les plages de chaque département.
      Les valeurs sont compatibles entre elles : MTTR inférieur au MTBF ; délai cohérent avec
      la distance et le mode de transport ; point de commande au moins égal à la
      consommation par jour × délai effectif + stock de sécurité.
      Les capacités suffisent : stock (emplacements), opérateurs (machines), chaîne
      (demande moyenne), ou l’écart est voulu par le formateur.
      Chaque article a au moins deux offres de fournisseurs.
      Les écarts sont signalés au formateur ; seuls les paramètres « à générer » peuvent être
      regénérés.

Une fois validé, le monde est figé.


5. Droits du joueur, règles de la partie, pop-up rouge
Pour chaque configuration du joueur, le formateur choisit un droit (DOIT). Il peut aussi
désactiver un outil.
```

## Page 5

```text
   Droit                        Avant le démarrage     Pendant la partie   Affichage

   Verrouillé                   Valeur fixée par le    Non modifiable      Champ grisé avec un
                                formateur                                  cadenas

   Initial                      Le joueur choisit sa   Non modifiable      Modifiable, puis grisé avec un
   seulement                    valeur de départ                           cadenas au démarrage

   Libre                        Le joueur choisit sa   Modifiable à tout   Modifiable
                                valeur de départ       moment


Option (PEUT) : pour le droit Libre, le formateur peut limiter le nombre de changements
par période ou ajouter un délai avant la prise d’effet.

Écran « Règles de la partie » (DOIT) : avant de jouer, le joueur voit, département par
département, les configurations verrouillées, celles à régler maintenant et celles libres,
ainsi que les outils disponibles. Il règle ses valeurs de départ puis confirme. La partie ne
démarre qu’après cette confirmation. L’écran reste consultable depuis l’accueil.

Pop-up rouge (DOIT) : quand le joueur touche une configuration qu’il n’a pas le droit de
modifier, rien ne change et une notification rouge s’affiche en haut de l’écran pendant 4
secondes :

     Verrouillé : « Modification interdite : le formateur a fixé ce réglage pour toute la partie. »
     Initial seulement, partie en cours : « Modification interdite : ce réglage ne pouvait être
     choisi qu’avant le début de la partie. »
     Limite atteinte : « Modification interdite : nombre de changements autorisés atteint
     pour cette période. »

La tentative est écrite au journal. Le serveur vérifie aussi les droits : une requête interdite
est refusée même si l’interface est contournée.

Prise d’effet : un changement autorisé est écrit au journal (heure, page, ancienne et
nouvelle valeur) et s’applique à la période suivante, sauf mention contraire dans le
département.


6. Structure commune d’une interface
Toutes les pages de département ont la même structure (DOIT) : nom de la page et
horloge en haut, trois onglets, puis le contenu de l’onglet ouvert. Le joueur ouvre une page
depuis le menu de sa tablette ou en touchant le bloc dans le monde 3D.
```

## Page 6

```text
   Onglet                          Contenu                                    Qui le produit

   KPIs                            Chiffres avec tendance, état en direct,    Le moteur, à partir du journal
                                   alertes, boutons d’action

   Outils                          Tableur, carte, graphiques, planning,      Le joueur
                                   journal, pré-remplis avec les données de
                                   la page

   Configurations                  Méthodes de travail du joueur avec leur    Le joueur, dans les limites du
                                   droit ; paramètres du monde en lecture     formateur
                                   seule


L’exemple montre la page Stock, onglet Configurations, au moment où le joueur touche un
réglage verrouillé.




maquette d’une page de département · onglet Configurations et pop-up rouge

Maquette indicative : la disposition compte, le style final reste libre.


7. Outils du joueur
Cinq outils communs, ouverts depuis l’onglet Outils de chaque page ou depuis l’accueil
(DOIT). Chaque page les pré-remplit avec ses propres données. Le formateur peut en
désactiver.
```

## Page 7

```text
   Outil                          Ce qu’il permet                       Exigences

   Tableur                        Faire ses calculs comme dans          Grille de cellules ; formules SOMME,
                                  Excel : coût d’une offre, point de    MOYENNE, MIN, MAX, SI et
                                  commande, capacité, comparaison       opérations ; bouton « Envoyer au
                                  de choix                              tableur » sur chaque tableau ;
                                                                        feuilles sauvegardées avec la partie ;
                                                                        export CSV (DEVRAIT)

   Carte du                       Voir l’usine, les fournisseurs, les   Carte interactive réelle (Leaflet,
   monde                          clients, les trajets et les crises    MapLibre ou équivalent, données
                                                                        Natural Earth ou OpenStreetMap) ;
                                                                        zoom, déplacement, clic ; placement
                                                                        par coordonnées GPS ; détail en
                                                                        section 10

   Graphiques                     Suivre un KPI dans le temps,          Courbe par période depuis le début ;
                                  comparer deux KPIs, trouver les       Pareto pour les causes (arrêts,
                                  causes principales                    défauts, non-conformités)

   Planning                       Voir ce qui est prévu : OF, camions   Vue jour et semaine, une ligne par
                                  attendus, expéditions, préventifs     ressource

   Journal                        Retrouver ce qui s’est passé et       Événements filtrables par page, type
                                  pourquoi                              et cause (décision, règle, aléa)


Un résultat d’outil ne change jamais la partie. Pour agir, le joueur passe par une action ou
une configuration.


8. Accueil de la tablette
L’accueil résume toute l’usine en une page et mène aux autres (DOIT).

     KPIs globaux : taux de service client, TRS de la chaîne, production du jour, ruptures de
     stock, couverture de stock, coût d’achat livré. Chaque chiffre mène à la page qui
     l’explique.
     Plan de l’usine : les 8 blocs, plus Fournisseurs et Clients, chacun avec une pastille d’état
     (vert, orange, rouge). Toucher un bloc ouvre sa page.
     Alertes : toutes les alertes en cours, de la plus grave à la moins grave, avec un lien vers
     la page concernée.
     Horloge : jour et heure simulés, vitesse ×1 à ×60, pause, bouton « Avancer jusqu’à la
     prochaine décision ».
     Critères de réussite : progression vers chaque objectif, sans verdict.
     Outils et Règles de la partie : accès direct.
```

## Page 8

```text
Règle de la pastille d’état : rouge si une alerte grave est ouverte (panne, rupture, lot
bloqué, commande client en retard) ; orange si une alerte mineure est ouverte (seuil
approché, file d’attente) ; vert sinon. La gravité de chaque alerte est donnée dans son
département.


9. Moteur commun
Ces règles valent pour tous les départements (DOIT).

Horloge : journée de travail de 8 h simulées, accélérable de ×1 à ×60, avec pause. Les
temps des machines et des agents sont en minutes simulées ; les délais des fournisseurs
et des clients en jours simulés.

Saut de temps : entre deux décisions, le moteur avance en mode agrégé, sans animation
3D, avec les mêmes règles, la même graine et le même journal. Il DEVRAIT produire le
même journal qu’un déroulement à ×60.

Graine : tous les tirages (pannes, défauts, retards, demande) utilisent la graine du
scénario. Par défaut, tous les joueurs d’une session reçoivent les mêmes tirages ; le
formateur peut choisir une graine par joueur.

Journal : chaque changement d’état est écrit avec l’heure, l’élément, l’ancien et le nouvel
état, la cause (décision du joueur, règle du moteur, aléa). Les KPIs sont calculés à partir du
journal, jamais saisis.

Agents : chaque agent a un état (disponible, occupé, en déplacement, en pause, absent)
et une file de tâches. Une tâche attend si l’agent n’est pas disponible. Un agent ne fait
qu’une tâche à la fois.

Ressources partagées : quai de déchargement, quai d’expédition, chariot élévateur,
technicien, chef de ligne. Une ressource occupée crée une file d’attente, visible sur la
tablette.

Alertes : une alerte est créée par une règle du moteur, envoyée sur la tablette avec sa
gravité, et fermée quand la cause disparaît. Elle est écrite au journal à l’ouverture et à la
fermeture.

Identifiants : on garde ceux du code ( LINE-NN , Ln-Mk , SKU-NN , MAT-NN , SUP-NN ) et
ceux du module fournisseurs ( EXT-FOUR-NN , EXT-OFFRE-NN , REC-QUAI-01 ). Les
nouveaux suivent la convention ZONE-TYPE-NN.
```

## Page 9

```text
Partie B — Départements

10. Fournisseurs

10.1 Rôle et périmètre

Fournir la MP quand le joueur la commande, du fournisseur jusqu’au quai de
déchargement REC-QUAI-01 inclus. Les fournisseurs sont des variables du scénario :
dans le monde 3D, on ne voit que leurs camions. Ce module reprend l’essentiel du cahier «
module fournisseurs et acheminement », qui reste la référence pour le réseau mondial et
la bibliothèque de crises.

10.2 Paramètres du monde (formateur)


   Paramètre                                  Porté par     Valeur de    Plage                         Noyau
                                                            départ

   Pays, ville, GPS                           Fournisseur   À générer    Villes crédibles pour le      Oui
                                                                         secteur

   Risque global,                             Fournisseur   40 ; 0,5     0 à 100 ; 0 à 1               Non
   confiance

   Prix unitaire                              Offre         À générer    Selon le secteur              Oui

   Quantité minimale de                       Offre         1 palette    ≥ 1 conditionnement           Non
   commande

   Capacité maximale                          Offre         À générer    > demande moyenne de          Oui
   par période                                                           l’article ÷ nombre d’offres

   Délai de production                        Offre         3 jours      1 à 60 jours                  Oui
   et sa variabilité

   Fiabilité du délai                         Offre         95 %         50 à 100 %                    Oui

   Taux de non-                               Offre         2%           0 à 20 %                      Non
   conformité

   Créneau de livraison                       Fournisseur   8 h – 10 h   Dans la journée de travail    Non

   Camion                                     Fournisseur   4à6          1 à 33 palettes               Non
                                                            palettes

   Risque géopolitique,                       Pays          À générer    0 à 100 ; % par catégorie     Non
   droits de douane                                                      d’article
```

## Page 10

```text
Limites du monde : 3 à 8 fournisseurs ; chacun propose 2 à 4 articles, jamais tous ; chaque
article a au moins 2 offres ; 3 à 5 trajets affichés par offre.

10.3 Fonctionnement du moteur

 1. Déclenchement : un article passe sous son point de commande (mode automatique),
     ou le joueur passe une commande manuelle. Quantité = quantité commandée du stock,
     multiple du conditionnement, au moins égale à la quantité minimale de l’offre.
 2. Choix de l’offre : l’offre principale de l’article, ou la répartition réglée par le joueur (ex.
    70 / 30). Une offre INDISPONIBLE ou au-delà de sa capacité bascule le reste sur l’offre
     suivante et crée une alerte.
 3. Trajet : le moteur calcule les trajets sur le réseau mondial (ports, aéroports, gares,
     frontières, détroits), garde les trajets non dominés en coût, délai et risque, et utilise le
     trajet actif de l’offre. Aucune IA ne calcule un trajet.
 4. Date d’arrivée = date d’émission + délai effectif (délai de production + durée du trajet
     actif), modifiée par la fiabilité du délai (tirage avec la graine) ou par une crise. La
     commande passe à EN_TRANSIT.
 5. Livraison : le camion arrive au quai avec le bon de livraison (article, quantité, lot). Le
     nombre d’unités non conformes est tiré selon le taux de l’offre. Le quai prend le relais.
 6. Coût livré = quantité × prix + transport du trajet + droits de douane du pays d’origine
    pour la catégorie de l’article.
 7. Confiance : après chaque livraison, la confiance du fournisseur monte si la livraison est
     complète, à l’heure et conforme, et baisse sinon (formule en section 25).

10.4 Données et états


   Entité                                          États

   Fournisseur EXT-FOUR-NN (code actuel :          ACTIF, INDISPONIBLE
   SUP-NN )

   Offre EXT-OFFRE-NN                              ACTIVE, SUSPENDUE, INDISPONIBLE

   Trajet EXT-TRAJ-NN                              ACTIF, DISPONIBLE, BLOQUE

   Commande fournisseur                            PREVU, LANCE, EN_TRANSIT, TERMINE,
                                                   ANNULE
```

## Page 11

```text
10.5 KPIs


   KPI                                             Calcul

   OTIF fournisseur                                Livraisons complètes et à l’heure ÷ livraisons, par
                                                   offre et par fournisseur

   Coût d’achat livré                              Somme des coûts livrés ÷ produits finis emballés

   Dépendance fournisseur                          Part du premier fournisseur dans les achats d’un
                                                   article

   Délai effectif moyen                            Moyenne de (date d’arrivée − date d’émission) des
                                                   commandes livrées

   Non-conformité réelle                           Unités non conformes ÷ unités reçues, par
                                                   fournisseur

   Commandes en transit                            Nombre, quantité et date d’arrivée prévue des
                                                   commandes EN_TRANSIT



10.6 Interface

Outils : carte du monde (fournisseurs, trajets actif en trait plein et alternatives en
pointillé, trajets bloqués grisés, points de passage avec pastille de risque, bandeau de
crise) ; comparateur d’offres (prix, délai, fiabilité, risque, coût livré côte à côte) ; panneau
de comparaison des trajets avec bouton « Basculer sur ce trajet » ; tableur pré-rempli avec
les offres.

Configurations du joueur


   Configuration                                             Valeur de départ                         Droit conseillé

   Offre principale par article                              Offre active de la configuration         Libre

   Répartition des achats entre                              100 % sur l’offre principale             Libre
   offres

   Trajet actif par offre                                    Trajet équilibré                         Libre

   Mode de commande                                          Automatique au point de                  Initial
                                                             commande                                 seulement


Actions : passer une commande manuelle, changer d’offre, répartir une commande,
basculer de trajet, annuler une commande à l’état PREVU.
```

## Page 12

```text
Alertes : livraison en retard (grave), offre indisponible (grave), crise active sur un trajet
utilisé (grave), capacité de l’offre presque atteinte (mineure).

10.7 Aléas

AL-01 retard fournisseur ; AL-02 livraison non conforme ; AL-14 blocage d’un passage ; AL-
15 surcoût de transport ; AL-16 droits de douane ; AL-17 embargo, fournisseur indisponible ;
AL-18 capacité réduite ; AL-19 hausse de prix. Détail en section 21.


11. Quai de déchargement

11.1 Rôle et périmètre

Recevoir les camions des fournisseurs et décharger la MP sur la zone de dépose. Agents :
chauffeur fournisseur (externe), réceptionnaire. Le quai REC-QUAI-01 ne sert qu’aux
fournisseurs ; les clients ont leur quai d’expédition (section 18).

11.2 Paramètres du monde (formateur)


   Paramètre                                       Valeur de départ   Plage              Noyau

   Camions à quai en même temps                    1                  1à3                Oui

   Capacité de la zone de dépose                   6 palettes         2 à 20             Oui

   Charge maximale du transpalette                 2 000 kg           1 000 à 3 000 kg   Non

   Temps de déchargement                           2 min / palette    1 à 10 min         Oui

   Réceptionnaires dans le monde                   1                  1à3                Oui


11.3 Fonctionnement du moteur

 1. Un camion arrive à la date calculée par le module fournisseurs. Il entre en file d’attente.
 2. Si le quai est libre et qu’un réceptionnaire est disponible, le camion se met à quai, selon
     l’ordre de passage réglé par le joueur.
 3. Le réceptionnaire décharge palette par palette (temps de déchargement × nombre de
     palettes). Si la zone de dépose est pleine, le déchargement s’arrête jusqu’à ce qu’une
     palette parte au contrôle.
 4. Camion vide : il repart, le quai se libère, le camion suivant avance.
 5. Un camion arrivé hors créneau attend l’ouverture du créneau suivant, sauf si le joueur
     le fait passer.
```

## Page 13

```text
11.4 Données et états

Camion entrant : EN_ROUTE, EN_ATTENTE, A_QUAI, EN_DECHARGEMENT, PARTI. Quai :
LIBRE, OCCUPE. Zone de dépose : contenu, capacité.

11.5 KPIs


   KPI                                                 Calcul

   Camions reçus                                       Camions PARTI sur la période

   Attente moyenne des camions                         Moyenne de (heure A_QUAI − heure d’arrivée)

   Temps de déchargement moyen                         Moyenne de (heure PARTI − heure A_QUAI)

   Occupation du quai                                  Temps OCCUPE ÷ temps d’ouverture

   Arrivées dans le créneau                            Camions arrivés dans le créneau ÷ camions arrivés

   Remplissage de la zone de dépose                    Palettes présentes ÷ capacité


11.6 Interface

Outils : planning des arrivées (camions attendus par jour et par heure, avec fournisseur et
palettes), graphique d’attente des camions, tableur.

Configurations du joueur


   Configuration                                   Valeur de départ           Droit conseillé

   Créneau de réception                            8 h – 10 h                 Initial seulement

   Ordre de passage des                            Premier arrivé, premier    Libre (ou article en rupture
   camions                                         servi                      d’abord)

   Réceptionnaires affectés au                     1                          Libre
   quai


Actions : faire passer un camion en priorité, accepter un camion hors créneau.

Alertes : camion en attente depuis plus de 1 h (mineure), zone de dépose pleine (grave).

11.7 Aléas

AL-11 conflit de quai (plusieurs camions en même temps) ; AL-26 absence du
réceptionnaire. Détail en section 21.
```

## Page 14

```text
12. Bureau de réception

12.1 Rôle et périmètre

Contrôler chaque livraison, l’enregistrer, étiqueter les palettes et les envoyer au stock MP,
ou en quarantaine. Agent : réceptionnaire (le même qu’au quai).

12.2 Paramètres du monde (formateur)


   Paramètre                                           Valeur de départ      Plage          Noyau

   Temps de contrôle                                   5 min / palette       1 à 30 min     Oui

   Capacité de la zone de quarantaine                  2 palettes            1 à 10         Oui

   Délai de réponse à une réclamation                  À générer             1 à 15 jours   Non

   Probabilité de détecter un défaut par               100 % si              50 à 100       Non
   échantillon                                         contrôlée             %



12.3 Fonctionnement du moteur

 1. Chaque palette déposée attend le contrôle. Le réceptionnaire contrôle selon le niveau
     de contrôle réglé par le joueur : toutes les palettes, ou une sur N.
 2. Palette contrôlée : le moteur compare au bon de commande et révèle les unités non
     conformes tirées par le module fournisseurs.
 3. Conforme : étiquetage, enregistrement, envoi au stock MP (tâche pour le magasinier-
     cariste).
 4. Non conforme : traitement selon la décision réglée par le joueur. Quarantaine puis
     renvoi : la palette sort du flux et une réclamation part au fournisseur. Tri : les unités
     conformes vont au stock, les autres sont rejetées (temps de contrôle doublé).
     Acceptation sous dérogation : tout entre en stock, et les unités défectueuses
     augmentent le taux de défaut de la première machine qui les utilise.
 5. Palette non contrôlée (échantillonnage) : elle entre en stock telle quelle ; ses défauts
     éventuels passent à la production comme pour une dérogation.
 6. Quarantaine pleine : le contrôle s’arrête jusqu’à libération d’une place.

12.4 Données et états

Palette reçue : A_CONTROLER, CONFORME, QUARANTAINE, RENVOYEE, EN_STOCK.
Réclamation : OUVERTE, RESOLUE.
```

## Page 15

```text
12.5 KPIs


   KPI                                                     Calcul

   Palettes contrôlées                                     Nombre sur la période

   Taux de non-conformité à réception                      Palettes non conformes ÷ palettes contrôlées, par
                                                           fournisseur

   Remplissage de la quarantaine                           Palettes en QUARANTAINE ÷ capacité

   Délai de mise en stock                                  Moyenne de (heure EN_STOCK − heure de
                                                           déchargement)

   Défauts passés sans contrôle                            Unités défectueuses entrées en stock sans
                                                           contrôle ou par dérogation

   Réclamations ouvertes                                   Réclamations OUVERTE


12.6 Interface

Outils : fiche de non-conformité (fournisseur, article, quantité, défaut), graphique des
non-conformités par fournisseur, tableur.

Configurations du joueur


   Configuration                                   Valeur de départ          Droit conseillé

   Niveau de contrôle                              100 % des palettes        Libre (ou 1 sur N)

   N pour l’échantillonnage                        3                         Libre

   Décision sur non-conforme                       Quarantaine puis renvoi   Libre (ou tri, ou dérogation)


Actions : libérer une palette de quarantaine, renvoyer au fournisseur, envoyer une
réclamation.

Alertes : livraison non conforme (grave), quarantaine pleine (grave), palettes en attente
de contrôle depuis plus de 2 h (mineure).

12.7 Aléas

AL-02 livraison non conforme ; AL-07 lot défectueux ; AL-26 absence du réceptionnaire.
Détail en section 21.
```

## Page 16

```text
13. Stock (MP, semi-finis, PF)

13.1 Rôle et périmètre

Garder la matière et les produits, les sortir dans l’ordre, préparer les kits des OF, alerter
quand un article passe sous son point de commande. Un seul stock en trois parties, avec
les mêmes règles pour les trois. Agent : magasinier-cariste.

13.2 Paramètres du monde (formateur)


   Paramètre                                       Valeur de départ             Plage                  Noyau

   Emplacements MP                                 24                           6 à 200                Oui

   Emplacements PF                                 20 palettes                  6 à 200                Oui

   Emplacements semi-finis                         À régler par scénario        0 à 100 (0 =           Non
                                                                                désactivé)

   Stock initial par article                       Valeur de la configuration   ≤ capacité             Oui

   Valeur unitaire par article                     Valeur de la configuration   Selon le secteur       Oui

   Chariot élévateur                               1 200 kg, batterie 8 h,      —                      Non
                                                   recharge 6 h

   Temps de rangement ou de                        À générer                    1 à 10 min / palette   Oui
   sortie

   Temps de préparation d’un                       À générer                    5 à 60 min             Oui
   kit


13.3 Fonctionnement du moteur

 1. Entrées : palettes MP depuis la réception, palettes PF depuis l’emballage, pièces semi-
     finies depuis la chaîne. Chaque entrée crée une tâche de rangement pour le
     magasinier-cariste. Stock plein : la palette reste dans la zone d’origine, qui finit par
     bloquer le département en amont.
 2. Sorties : selon la méthode de sortie (FIFO par défaut, FEFO si le secteur a des dates de
     péremption).
 3. Kits : quand un OF est lancé, le moteur calcule le kit (quantité de nomenclature × taille
     du lot × (1 + taux de rebut)). Si tout est en stock, le magasinier prépare et livre le kit à la
     première machine. Sinon, rupture de kit : l’OF attend et une alerte part.
 4. Réapprovisionnement : après chaque sortie, le moteur compare le stock disponible +
     les commandes en transit au point de commande. En dessous, il crée une commande
     (mode automatique) ou une alerte (mode manuel). Avec la méthode « recomplètement
```

## Page 17

```text
     périodique », il commande à date fixe la quantité qui ramène le stock au niveau cible.
 5. Chariot : une seule tâche à la fois ; batterie vide → 6 h de recharge, les tâches
     attendent.
 6. Inventaire : compare le stock du système au stock réel ; les écarts créés par un aléa
    sont corrigés.

13.4 Données et états

Article : partie (MP, semi-fini, PF), quantité, minimum, point de commande, quantité
commandée, emplacements occupés. Kit : DEMANDE, EN_PREPARATION, LIVRE,
EN_RUPTURE. Code actuel : MaterialStock (MP) et Stock (PF).

13.5 KPIs


   KPI                                      Calcul

   Niveau de stock                          Quantité par article, face au minimum et au point
                                            de commande

   Couverture                               Quantité ÷ consommation moyenne par jour, en
                                            jours

   Ruptures                                 Nombre de passages à zéro et durée cumulée, par
                                            article

   Ruptures de kit                          OF bloqués faute de matière

   Taux de remplissage                      Emplacements occupés ÷ capacité, par partie

   Valeur du stock                          Somme de (quantité × valeur unitaire)

   Rotation                                 Sorties de la période ÷ stock moyen


13.6 Interface

Une seule page avec un filtre par partie et par article.

Outils : graphique du stock par article avec le minimum et le point de commande ; tableur
pré-rempli (consommation, délai effectif) pour calculer son point de commande et sa
quantité économique ; inventaire.

Configurations du joueur (par article)


   Configuration                                     Valeur de départ       Droit conseillé

   Stock minimum (sécurité)                          Valeur de la           Libre
                                                     configuration
```

## Page 18

```text
   Configuration                                       Valeur de départ        Droit conseillé

   Point de commande                                   Valeur de la            Libre
                                                       configuration

   Quantité commandée                                  Valeur de la            Libre
                                                       configuration

   Méthode de                                          Point de commande       Initial seulement (ou
   réapprovisionnement                                                         recomplètement périodique)

   Méthode de sortie                                   FIFO                    Verrouillé


Actions : lancer un inventaire, demander un kit en urgence, passer une commande d’un
article (renvoie vers Fournisseurs).

Alertes : article sous le point de commande (mineure), rupture (grave), rupture de kit
(grave), stock plein (grave).

13.7 Aléas

AL-27 panne du chariot élévateur ; AL-28 erreur d’inventaire. Détail en section 21.


14. Chaîne de production

14.1 Rôle et périmètre

Définir comment le produit se fabrique (méthodes : nomenclature, gamme, temps), puis
transformer la MP en produits sur N lignes en parallèle, de l’arrivée du kit sur la première
machine à la sortie du lot vers le contrôle qualité. Agents : responsable de production
(méthodes), chef de ligne, opérateurs.

14.2 Paramètres du monde (formateur)

Chaîne et lignes


   Paramètre                                       Valeur de           Plage                                Noyau
                                                   départ

   Nombre de lignes                                3, identiques       1à3                                  Oui

   Machines par ligne                              4                   2à6                                  Oui

   Mode de transfert                               Chariot, 0,5 min    Chariot ou convoyeur, 0 à 10 min     Non

   Opérateurs dans le                              1 par machine       ≥ nombre de machines à faire         Oui
   monde                                                               tourner
```

## Page 19

```text
Machines (exemple v3 ; une ligne par machine dans la configuration)


  Machine              Cycle        Fonctionnement / arrêt planifié MTBF / MTTR Réglage Défaut Table d’attente

  M1                   2 min        110 / 10 min                 40 h / 1 h         10 min   2%    10

  M2                   1,5 min 110 / 10 min                      80 h / 0,5 h       5 min    1%    10

  M3 (goulot) 3 min                 110 / 10 min                 60 h / 1 h         0 min    3%    10

  M4                   1 min        110 / 10 min                 100 h / 0,5 h      5 min    2%    10


Plages : cycle 0,5 à 30 min ; arrêt ≤ 30 % du temps de marche ; MTBF 10 à 500 h ; MTTR 0,25
à 8 h ; réglage 0 à 60 min ; défaut 0 à 20 % ; table 1 à 50 ; durée de vie de l’outil à fournir
(absente de la v3). Noyau : cycle, MTBF, MTTR, défaut.

Méthodes (ancien bureau d’étude)


   Article                      Type                  Quantité pour 1 PF         Unité

   {MP 1}                       Matière première      {…}                        {pièce, kg, m…}

   {MP 2}                       Matière première      {…}                        {…}

   {Composant}                  Composant             {…}                        {…}

   {Emballage}                  Emballage             {…}                        {…}


Gamme : ordre des opérations et machine de chaque opération. Matière pour un lot =
quantité pour 1 PF × taille du lot × (1 + taux de rebut).

14.3 Fonctionnement du moteur

Chemin d’un OF

 1. Le joueur lance l’OF (produit, quantité, ligne, priorité), ou le moteur le crée selon la
     règle de lancement. État LANCE.
 2. Le stock prépare le kit et le livre à la première machine. Sans kit : ATTENTE_MATIERE.
 3. Si le produit change par rapport au lot précédent, chaque machine passe en REGLAGE
     pendant son temps de réglage. État EN_COURS.
 4. Chaque produit avance de machine en machine, avec le temps de transfert.
 5. Le lot terminé part au contrôle qualité ; les retouches reviennent sur la ligne. État
     TERMINE.

Règles du flux (DOIT)

     Le flux avance à la vitesse du goulot : les machines plus rapides attendent.
```

## Page 20

```text
     Table d’attente pleine → la machine d’avant passe en SORTIE_PLEINE ; table vide → la
     machine d’après attend.
     Une machine en PANNE arrête sa ligne dès que les tables autour sont pleines ou vides ;
     les autres lignes continuent.
     Panne : tirage selon le MTBF de la machine et la graine ; la machine reste en PANNE
     jusqu’à la fin de la réparation (durée selon le MTTR).
     Pause planifiée : après le temps de fonctionnement, la machine passe en PAUSE
     pendant le temps d’arrêt.
     Outil : après sa durée de vie en produits, la machine s’arrête pour un changement
     d’outil (tâche maintenance).
     Défaut : chaque produit est mauvais selon le taux de défaut de chaque machine
     (tirage), augmenté si la matière vient d’une dérogation.
     Machine sans opérateur : ARRET.

Formules de référence (exemple v3) : disponibilité théorique = 110 ÷ 120 = 92 % ; débit
théorique d’une machine = (60 ÷ cycle) × disponibilité × (1 − défaut) ; débit d’une ligne =
celui du goulot (M3 : 20 × 0,92 × 0,97 ≈ 17,8 / h) ; 3 lignes ≈ 53 / h. Traversée d’un produit =
7,5 min de cycle + 4 × 0,5 min = 9,5 min ; un lot de 20 ≈ 9,5 + 19 × 3 ≈ 67 min.

14.4 Données et états


   Entité                           États

   Ligne LINE-NN                    EN_MARCHE, ARRETEE, EN_PANNE

   Machine Ln-Mk                    ARRET, MARCHE, PAUSE, REGLAGE, PANNE,
                                    MAINTENANCE, ATTENTE_MATIERE,
                                    SORTIE_PLEINE

   OF                               PREVU, LANCE, EN_COURS, TERMINE, ANNULE

   Opérateur                        Disponible, occupé, en déplacement, en pause,
                                    absent


Champs existants dans models.py ( ProductionLine , Machine ) conservés ; champs
ajoutés : temps de fonctionnement, arrêt planifié, réglage, table d’attente, transfert,
opérateurs, OF en cours.

14.5 KPIs


   KPI                                   Calcul                                      Niveau

   Production                            Produits bons envoyés au contrôle qualité   Ligne, chaîne
```

## Page 21

```text
   KPI                                   Calcul                                           Niveau

   Débit réel                            Produits bons ÷ heures d’ouverture, face au      Ligne, chaîne
                                         débit théorique

   Taux de                               Produits bons ÷ produits prévus par les OF       Ligne, chaîne
   production

   Disponibilité                         Temps en MARCHE ÷ temps d’ouverture              Machine, ligne

   Performance                           (Produits faits × temps de cycle) ÷ temps en     Machine, ligne
                                         MARCHE

   Taux de qualité                       Produits bons ÷ produits faits                   Machine, ligne,
                                                                                          chaîne

   TRS                                   Disponibilité × performance × qualité            Machine, ligne,
                                         (remplace le trs actuel, même nom)               chaîne

   Goulot                                Machine au débit réel le plus faible             Ligne

   Encours                               Contenu des tables d’attente et des semi-finis   Ligne, chaîne
                                         liés

   Temps de                              Fin − lancement de l’OF                          OF, ligne
   traversée

   Arrêts par cause                      Durée en PANNE, REGLAGE,                         Machine, ligne
                                         ATTENTE_MATIERE, SORTIE_PLEINE, PAUSE

   Respect des OF                        OF terminés à la date prévue ÷ OF terminés       Chaîne



14.6 Interface

La page montre une barre de KPIs, la vue des lignes (une case par machine avec sa
couleur d’état et le goulot signalé), la liste des OF et les alertes.
```

## Page 22

```text
maquette de la page Chaîne de production · onglet KPIs

Outils : planning des OF par ligne, Pareto des arrêts par cause, tableur pré-rempli (cycles,
disponibilités) pour calculer capacité et goulot.

Configurations du joueur


   Configuration                             Valeur de départ                 Droit conseillé

   Taille de lot (OF)                        20 produits                      Libre

   Règle de lancement                        À la commande client, ou stock   Initial seulement
   des OF                                    PF sous le minimum

   Ordre de priorité des                     Premier lancé, premier fait      Libre (ou date due la plus
   OF                                                                         proche)

   Nombre de lignes                          Toutes                           Libre
   actives

   Affectation des                           1 par machine                    Libre
   opérateurs
```

## Page 23

```text
   Configuration                             Valeur de départ                   Droit conseillé

   Nomenclature et                           Valeurs de la configuration        Verrouillé (Libre si le scénario
   gamme                                                                        travaille les méthodes)


Actions : lancer, prioriser ou annuler un OF ; arrêter ou redémarrer une ligne ; réaffecter
un opérateur ; appeler la maintenance ; programmer un préventif ou un changement
d’outil ; mettre en attente ou reprendre des semi-finis.

Alertes : panne (grave), rupture de kit (grave), OF en retard (grave), outil en fin de vie
(mineure), sortie pleine (mineure).

14.7 Aléas

AL-20 panne imposée ; AL-21 absence d’opérateur ; AL-22 dérive qualité ; AL-23
ralentissement ; AL-24 usure accélérée de l’outil ; AL-25 rupture de kit. Détail en section
21.


15. Contrôle qualité

15.1 Rôle et périmètre

Vérifier les produits en sortie de ligne et les trier : conforme, à retoucher, rebut. Agent :
contrôleur qualité.

15.2 Paramètres du monde (formateur)


   Paramètre                                          Valeur de départ     Plage          Noyau

   Temps de contrôle                                  1 min / produit      0,1 à 15 min   Oui

   Part des défauts récupérables                      65 % (code actuel)   0 à 100 %      Oui

   Réussite d’une retouche                            75 % (code actuel)   0 à 100 %      Oui

   Détection d’un défaut contrôlé                     100 %                50 à 100 %     Non



15.3 Fonctionnement du moteur

 1. Les produits d’un lot terminé entrent dans la file du contrôle.
 2. Le contrôleur contrôle selon la fréquence réglée : 100 %, ou 1 produit sur N.
 3. Produit contrôlé et bon → emballage. Produit contrôlé et mauvais → tirage : récupérable
      (retouche sur la ligne, ou rebut selon la règle du joueur) ou grave (rebut).
 4. Produit non contrôlé → emballage tel quel. S’il est mauvais, il part chez le client et
      compte comme réclamation client (section 19).
```

## Page 24

```text
 5. Si la part de rebut d’un lot dépasse le seuil de blocage, le lot entier est bloqué jusqu’à
     décision du joueur ; le chef de ligne est prévenu.
 6. Une retouche réussie revient au contrôle ; une retouche ratée part au rebut.

15.4 Données et états

Produit : A_CONTROLER, CONFORME, A_RETOUCHER, REBUT, NON_CONTROLE. Lot :
EN_CONTROLE, LIBERE, BLOQUE.

15.5 KPIs


   KPI                                             Calcul

   Taux de conformité                              Conformes ÷ contrôlés

   Taux de rebut                                   Rebuts ÷ contrôlés

   Taux de retouche                                Retouchés ÷ contrôlés

   Lots bloqués                                    Lots BLOQUE

   File d’attente                                  Produits A_CONTROLER

   Défauts par machine                             Origine des défauts, par machine

   Défauts partis chez le client                   Produits mauvais non contrôlés expédiés



15.6 Interface

Outils : Pareto des défauts par type et par machine, graphique du rebut dans le temps,
tableur.

Configurations du joueur


   Configuration                                    Valeur de départ    Droit conseillé

   Fréquence de contrôle                            100 %               Libre (ou 1 sur N)

   Seuil de blocage d’un lot                        15 % de rebut       Libre

   Règle sur défaut récupérable                     Retouche            Libre (ou rebut direct)


Actions : bloquer ou libérer un lot, demander un contrôle à 100 % sur une machine
pendant une période.

Alertes : lot bloqué (grave), rebut au-dessus du seuil sur une machine (mineure), file de
contrôle longue (mineure).
```

## Page 25

```text
15.7 Aléas

AL-07 lot défectueux ; AL-22 dérive qualité (côté machine). Détail en section 21.


16. Emballage

16.1 Rôle et périmètre

Mettre les produits conformes en colis, puis en palettes filmées, et les envoyer au stock
PF. Agent : emballeur.

16.2 Paramètres du monde (formateur)


   Paramètre                                Valeur de départ           Plage          Noyau

   Temps d’emballage                        2 min / colis              0,5 à 15 min   Oui

   Temps de filmage                         5 min / palette            1 à 20 min     Oui

   Emballages par colis                     Selon la nomenclature      —              Oui


16.3 Fonctionnement du moteur

 1. Les produits conformes arrivent en file, dans l’ordre réglé par le joueur.
 2. L’emballeur met en carton (consomme les emballages de la nomenclature), étiquette,
     pèse.
 3. Quand la palette atteint le nombre de colis réglé, il la filme et crée une tâche de
     rangement au stock PF.
 4. Palette incomplète : elle attend d’être pleine, ou part après le délai réglé par le joueur.
 5. Plus d’emballages en stock : l’emballage s’arrête, alerte.

16.4 Données et états

Colis : EN_COURS, FERME. Palette PF : EN_MONTAGE, FILMEE, EN_STOCK.

16.5 KPIs


   KPI                                               Calcul

   Colis par heure                                   Colis FERME ÷ heures d’ouverture

   Palettes par jour                                 Palettes FILMEE

   Encours avant emballage                           Produits conformes en file

   Occupation de l’emballeur                         Temps occupé ÷ temps d’ouverture
```

## Page 26

```text
   KPI                                             Calcul

   Consommation d’emballages                       Cartons et film utilisés, face au stock


16.6 Interface

Outils : graphique de l’encours, tableur.

Configurations du joueur


   Configuration                                   Valeur de départ              Droit conseillé

   Produits par colis                              1                             Verrouillé

   Colis par palette                               6                             Initial seulement

   Ordre d’emballage                               Premier arrivé, premier       Libre (ou commande urgente
                                                   emballé                       d’abord)

   Départ d’une palette                            Jamais                        Libre (ou après un délai)
   incomplète


Actions : emballer une commande en priorité, envoyer une palette incomplète.

Alertes : rupture d’emballages (grave), encours au-dessus de 2 h de travail (mineure).

16.7 Aléas

AL-29 pénurie d’emballages. Détail en section 21.


17. Maintenance et stock PDR

17.1 Rôle et périmètre

Réparer les machines en panne, faire le préventif, changer les outils, gérer les pièces de
rechange (PDR). Agent : technicien de maintenance.

17.2 Paramètres du monde (formateur)


   Paramètre                                                Valeur de départ                  Plage          Noyau

   Techniciens                                              1                                 1à3            Oui

   Temps de déplacement jusqu’à une                         3 min                             1 à 15 min     Oui
   machine
```

## Page 27

```text
   Paramètre                                                Valeur de départ              Plage          Noyau

   Durée de réparation                                      MTTR de la machine (section   —              Oui
                                                            14)

   Durée d’un préventif                                     À générer                     0,25 à 4 h     Non

   Effet d’un préventif                                     Remet à zéro le compteur de   —              Non
                                                            panne de la machine

   PDR par référence : stock initial,                       3 pièces (code actuel) ; à    0 à 50 ; 1 à   Oui
   délai de réapprovisionnement                             générer                       30 jours

   Probabilité qu’une panne demande                         À générer                     0 à 100 %      Non
   une PDR



17.3 Fonctionnement du moteur

 1. Une panne, un outil usé ou un préventif programmé crée une demande d’intervention
     dans la file du technicien.
 2. La file est servie selon l’ordre réglé par le joueur (première panne d’abord, ou goulot
     d’abord). Un technicien ne fait qu’une intervention à la fois.
 3. Le technicien se déplace, consigne la machine (MAINTENANCE), répare pendant une
     durée tirée autour du MTTR.
 4. Si la réparation demande une PDR (tirage) et qu’il n’y en a plus, la machine reste en
     PANNE jusqu’à l’arrivée de la pièce.
 5. Préventif : selon la stratégie du joueur, toutes les X heures de marche ou X produits ; la
     machine s’arrête pendant la durée du préventif, puis son risque de panne repart de
     zéro.
 6. Stock PDR sous son minimum : commande de PDR (délai de réapprovisionnement).

17.4 Données et états

Demande d’intervention : OUVERTE, EN_COURS, EN_ATTENTE_PIECE, TERMINEE ; type :
PANNE, OUTIL, PREVENTIF. Code actuel : maintenance_queue , spare_parts , article
 MAT-PDR .


17.5 KPIs


   KPI                                             Calcul

   Pannes                                          Nombre par machine sur la période
```

## Page 28

```text
   KPI                                             Calcul

   MTBF réel                                       Temps en MARCHE ÷ nombre de pannes, par
                                                   machine

   MTTR réel                                       Durée des réparations ÷ nombre de pannes

   Attente d’intervention                          Moyenne de (début de réparation − heure de la
                                                   panne)

   Part du préventif                               Heures de préventif ÷ heures de maintenance

   Stock PDR                                       Pièces disponibles par référence ; ruptures de PDR

   Occupation du technicien                        Temps en intervention ÷ temps d’ouverture


17.6 Interface

Outils : planning de maintenance (préventifs prévus, interventions en cours), historique
des pannes par machine, tableur pré-rempli pour calculer une fréquence de préventif.

Configurations du joueur


   Configuration                                    Valeur de départ           Droit conseillé

   Stratégie de maintenance                         Corrective seulement       Libre (ou préventive)

   Fréquence du préventif                           Aucune                     Libre (heures de marche ou
                                                                               produits)

   Ordre des interventions                          Première panne d’abord     Libre (ou goulot d’abord)

   Stock minimum de PDR                             Valeur de la               Libre
                                                    configuration

   Quantité commandée de                            Valeur de la               Libre
   PDR                                              configuration


Actions : envoyer le technicien sur une machine, programmer un préventif, commander
des PDR.

Alertes : machine en panne sans intervention (grave), rupture de PDR (grave), file
d’interventions longue (mineure).

17.7 Aléas

AL-20 panne imposée ; AL-30 absence du technicien. Détail en section 21.
```

## Page 29

```text
18. Logistique & Transport

18.1 Rôle et périmètre

Préparer les commandes clients depuis le stock PF, les charger et les faire partir : avec les
camions de l’usine, ou dans le camion du client venu au quai d’expédition. Agents :
magasinier, chauffeur livreur, chauffeur client (externe).

18.2 Paramètres du monde (formateur)


   Paramètre                                       Valeur de départ        Plage        Noyau

   Camions à quai en même temps                    1                       1à3          Oui

   Temps de chargement                             2 min / palette         1 à 10 min   Oui

   Camions de l’usine                              À régler par scénario   0 à 10       Oui

   Capacité d’un camion de l’usine                 À régler par scénario   1 à 33       Oui
                                                                           palettes

   Temps de trajet vers chaque client              Calculé sur la carte    —            Oui
                                                   (distance)

   Temps de préparation d’une                      À générer               5 à 60 min   Non
   commande



18.3 Fonctionnement du moteur

 1. Une commande client acceptée et couverte par le stock PF crée une tâche de
     préparation pour le magasinier. Sans stock PF suffisant, elle attend (et compte dans le
     carnet de commandes).
 2. La commande préparée va sur la zone de préparation des expéditions.
 3. Livraison par l’usine : les commandes sont regroupées par camion selon la priorité
     réglée. Le camion part selon la règle de départ (plein, après un délai, ou tout de suite).
     Date de livraison = départ + temps de trajet ; retour du camion = livraison + temps de
     trajet.
 4. Enlèvement : le camion du client arrive au jour prévu, attend si le quai est occupé, est
     chargé, repart. Date de livraison = date de chargement.
 5. La commande est livrée à temps si la date de livraison ≤ date promise, et complète si
     toute la quantité est livrée.
```

## Page 30

```text
18.4 Données et états

Commande client (côté expédition) : A_PREPARER, PREPAREE, CHARGEE,
EN_LIVRAISON, LIVREE. Camion de l’usine : DISPONIBLE, EN_CHARGEMENT,
EN_ROUTE, EN_RETOUR.

18.5 KPIs


   KPI                                                    Calcul

   OTIF client                                            Commandes livrées complètes et à temps ÷
                                                          commandes livrées ( otif actuel, même nom)

   Expéditions                                            Commandes et palettes LIVREE sur la période

   Retard moyen                                           Moyenne de (livraison − date promise) des
                                                          commandes en retard

   Remplissage des camions                                Palettes chargées ÷ capacité

   Attente au quai d’expédition                           Moyenne d’attente des camions clients

   Commandes prêtes non parties                           Commandes PREPAREE



18.6 Interface

Outils : carte du monde (clients, camions en route), planning des expéditions, tableur.

Configurations du joueur


   Configuration                                   Valeur de départ           Droit conseillé

   Départ d’un camion                              Quand il est plein         Libre (ou après un délai, ou tout de
                                                                              suite)

   Délai maximal avant                             4h                         Libre
   départ

   Priorité des commandes                          Date promise la plus       Libre (ou premier commandé)
                                                   proche

   Camions de l’usine                              Tous                       Libre
   utilisés


Actions : expédier une commande en priorité, faire partir un camion incomplet, faire
passer un camion client en priorité.
```

## Page 31

```text
Alertes : commande en retard (grave), commande prête depuis plus de 1 jour (mineure),
aucun camion disponible (mineure).

18.7 Aléas

AL-31 camion de livraison en panne ; AL-11 conflit de quai (côté expédition). Détail en
section 21.


19. Clients

19.1 Rôle et périmètre

Commander des produits finis et les recevoir. Les clients sont des variables du scénario :
la demande vient du moteur ; dans le monde 3D, on ne voit que leurs camions ou ceux de
l’usine. Le joueur décide quelles commandes accepter et quel délai promettre.

19.2 Paramètres du monde (formateur)


   Paramètre                                 Porté    Valeur de départ      Plage                      Noyau
                                             par

   Nom, pays, ville, GPS                     Client   À générer             Villes crédibles pour le   Oui
                                                                            secteur

   Demande moyenne                           Client   100 produits / jour   >0                         Oui
                                                      (total)

   Variabilité de la                         Client   ± 10 %                0 à 50 %                   Oui
   demande

   Saisonnalité                              Client   Aucune                Profil par période         Non

   Taille d’une                              Client   À générer             1 à 1 000 produits         Oui
   commande

   Délai attendu                             Client   5 jours               1 à 60 jours               Oui

   Mode de livraison                         Client   Livré ou enlèvement   —                          Oui

   Tolérance au retard                       Client   À générer             0 à 10 jours               Non


Limites du monde : 1 à 8 clients.

19.3 Fonctionnement du moteur

 1. Demande : à chaque période, le moteur tire les commandes de chaque client (demande
     moyenne × saisonnalité ± variabilité, graine). Le code actuel le fait dans
      GMSClientAgent .
```

## Page 32

```text
 2. Réception de la commande : elle arrive sur la tablette avec quantité et délai attendu.
     Selon la règle d’acceptation du joueur, elle est acceptée d’office, ou acceptée
     seulement si la capacité libre le permet, ou attend la décision du joueur.
 3. Date promise = date de commande + délai promis réglé par le joueur. Si le délai promis
     dépasse le délai attendu du client, la commande peut être perdue (tirage selon la
     tolérance).
 4. La commande acceptée entre dans le carnet de commandes ; elle déclenche un OF si la
     règle de lancement le prévoit, puis passe à la logistique.
 5. Retard : au-delà de la tolérance, le client peut annuler le reste de la commande ; une
     réclamation est créée si des produits défectueux lui sont livrés.

19.4 Données et états

Client EXT-CLI-NN . Commande client : RECUE, ACCEPTEE, REFUSEE, EN_PRODUCTION,
PRETE, LIVREE, ANNULEE.

19.5 KPIs


   KPI                                                    Calcul

   Taux de service                                        Quantité livrée à temps ÷ quantité commandée

   Carnet de commandes                                    Commandes ACCEPTEE pas encore LIVREE, en
                                                          quantité et en jours de production

   Commandes en retard                                    Nombre et quantité au-delà de la date promise

   Demande face à la prévision                            Demande reçue ÷ prévision du joueur

   Commandes refusées ou perdues                          Nombre et quantité REFUSEE ou ANNULEE

   Réclamations clients                                   Commandes livrées avec des produits défectueux

   Part de chaque client                                  Quantité commandée par client ÷ quantité totale


19.6 Interface

Outils : carte du monde (clients, livraisons en cours), carnet de commandes, tableur pré-
rempli avec l’historique de la demande pour faire sa prévision.

Configurations du joueur


   Configuration                               Valeur de départ    Droit conseillé

   Règle d’acceptation                         Toutes acceptées    Libre (ou selon la capacité, ou au cas par cas)
```

## Page 33

```text
   Configuration                               Valeur de départ      Droit conseillé

   Délai promis                                5 jours               Initial seulement

   Priorité entre clients                      Aucune                Libre

   Prévision de demande                        100 produits / jour   Libre


Actions : accepter ou refuser une commande, proposer une autre date, marquer une
commande urgente.

Alertes : commande en attente de décision (mineure), commande en retard (grave),
annulation d’un client (grave).

19.7 Aléas

AL-32 pic de demande ; AL-33 commande urgente ; AL-34 annulation de commande. Détail
en section 21.


Partie C — Ensemble de l’usine

20. Interactions entre départements
La matière suit ce chemin : fournisseur → quai de déchargement → bureau de réception →
stock MP → chaîne de production (avec passage possible par le stock de semi-finis) →
contrôle qualité → emballage → stock PF → logistique & transport → client. Les
départements ne se parlent que par les échanges ci-dessous ; chacun est écrit au journal
(DOIT).




flux de matière · 10 étapes, une boucle de retouche
```

## Page 34

```text
   De → vers                                       Ce qui passe               Déclencheur

   Joueur → Fournisseur                            Commande de MP             Stock sous le point de
                                                                              commande, ou commande
                                                                              manuelle

   Fournisseur → Quai de                           Camion, palettes, bon de   Fin du délai effectif
   déchargement                                    livraison

   Quai → Bureau de                                Palettes déchargées        Palette sur la zone de dépose
   réception

   Réception → Fournisseur                         Réclamation                Livraison non conforme

   Réception → Stock MP                            Palettes contrôlées        Contrôle OK ou dérogation

   Client → Joueur                                 Commande de PF             Tirage de la demande

   Joueur → Chaîne                                 OF                         Commande client, stock PF bas,
                                                                              ou décision du joueur

   Chaîne → Stock                                  Nomenclature (contenu      OF lancé, nouveau produit
                                                   des kits)

   Stock MP → Chaîne                               Kit de matière             Kit prêt

   Chaîne ↔ Stock semi-finis                       Pièces semi-finies         Mise en attente ou reprise

   Chaîne → Contrôle qualité                       Lot terminé                Fin du lot

   Contrôle qualité → Chaîne                       Produits à retoucher       Défaut récupérable

   Contrôle qualité →                              Produits conformes ou      Contrôle terminé
   Emballage                                       non contrôlés

   Emballage → Stock PF                            Palettes filmées           Palette complète ou délai atteint

   Stock PF → Logistique                           Palettes à expédier        Commande à préparer

   Logistique → Client                             Commande livrée            Départ du camion ou enlèvement

   Chaîne → Maintenance                            Demande d’intervention     Panne, outil usé, préventif

   Maintenance → Chaîne                            Machine réparée            Fin d’intervention

   Tous → Joueur                                   Alertes                    Règles de chaque département


Effets en chaîne à respecter (ils sont au cœur de l’apprentissage) : une zone pleine
bloque le département en amont ; un kit manquant arrête la ligne ; une palette acceptée
sans contrôle peut augmenter les défauts en production ; un produit non contrôlé peut
créer une réclamation client.
```

## Page 35

```text
21. Catalogue des aléas
Le formateur déclenche un aléa selon quatre modes : manuel (bouton), à une heure fixée,
sur condition (ex. TRS sous 70 %), ou aléatoire avec une probabilité (graine). Les numéros
AL-01 à AL-13 viennent du catalogue de l’usine et AL-14 à AL-19 du module fournisseurs ;
ceux qui ne sont pas listés ici sont gardés tels quels et rapprochés dans le rapport d’écart.
AL-20 et suivants sont nouveaux.


   ID          Aléa                                Département       Paramètres       Effet

   AL-         Retard fournisseur                  Fournisseurs      Retard (jours)   Date d’arrivée repoussée
   01

   AL-         Livraison non                       Réception         Part non         Unités défectueuses dans
   02          conforme                                              conforme         la livraison

   AL-         Lot défectueux                      Réception,        Lot              Lot entier non conforme
   07                                              qualité

   AL-         Conflit de quai                     Quai,             Nombre de        Plusieurs camions arrivent
   11                                              logistique        camions          en même temps

   AL-         Blocage d’un                        Fournisseurs      Nœud, durée      Trajets BLOQUE, recalcul
   14          passage                                                                des alternatives

   AL-         Surcoût de                          Fournisseurs      Tronçon ou       Coût des trajets
   15          transport                                             mode, %          augmenté

   AL-         Droits de douane                    Fournisseurs      Pays, %,         Droits ajoutés au coût
   16                                                                catégorie        livré

   AL-         Embargo,                            Fournisseurs      Fournisseur,     Offres INDISPONIBLE
   17          fournisseur                                           durée
               indisponible

   AL-         Capacité réduite                    Fournisseurs      Offre, %         Capacité maximale
   18                                                                                 diminuée

   AL-         Hausse de prix                      Fournisseurs      Offre ou         Prix unitaire augmenté
   19                                                                article, %

   AL-         Panne imposée                       Chaîne,           Machine,         Machine en PANNE
   20                                              maintenance       durée

   AL-         Absence                             Chaîne            Opérateur,       Machine à l’ARRET sans
   21          d’opérateur                                           durée            réaffectation

   AL-         Dérive qualité                      Chaîne, qualité   Machine,         Taux de défaut augmenté
   22                                                                points, durée
```

## Page 36

```text
   ID          Aléa                                Département     Paramètres        Effet

   AL-         Ralentissement                      Chaîne          Machine, %,       Temps de cycle augmenté
   23                                                              durée             ; le goulot peut changer

   AL-         Usure accélérée de                  Chaîne          Machine, %        Durée de vie de l’outil
   24          l’outil                                                               réduite

   AL-         Rupture de kit                      Chaîne, stock   Ligne ou OF,      Première machine en
   25                                                              durée             ATTENTE_MATIERE

   AL-         Absence du                          Quai,           Durée             Plus de déchargement ni
   26          réceptionnaire                      réception                         de contrôle

   AL-         Panne du chariot                    Stock           Durée             Rangements, sorties et
   27          élévateur                                                             kits en attente

   AL-         Erreur d’inventaire                 Stock           Article, écart    Stock système différent
   28                                                                                du stock réel

   AL-         Pénurie                             Emballage       Durée             Emballage arrêté
   29          d’emballages

   AL-         Absence du                          Maintenance     Durée             Plus d’intervention
   30          technicien

   AL-         Camion de livraison                 Logistique      Camion, durée     Camion indisponible
   31          en panne

   AL-         Pic de demande                      Clients         Client, %,        Demande augmentée
   32                                                              durée

   AL-         Commande                            Clients         Client,           Commande avec délai
   33          urgente                                             quantité, délai   court

   AL-         Annulation de                       Clients         Commande          Commande ANNULEE
   34          commande


Une crise du monde réel (canal de Suez, mer Rouge…) se traduit en un ou plusieurs de ces
aléas, avec les valeurs de sa fiche sourcée (bibliothèque du module fournisseurs).


22. Critères de réussite et évaluation
Le joueur est jugé sur les objectifs fixés au départ, pas sur un choix isolé. Chaque critère =
un KPI de la partie B + un seuil + une échéance, défini par le formateur ou proposé par l’IA
de génération selon le secteur.
```

## Page 37

```text
     Exemples : OTIF client ≥ 95 % ; TRS de la chaîne ≥ 75 % ; aucune rupture de kit ; coût
     d’achat livré réduit de 8 % ; aucun fournisseur au-dessus de 60 % des achats d’un
     article.
     Progression : affichée sur l’accueil à chaque période, sans verdict.
     Évaluation en fin de partie : chaque critère atteint, partiellement atteint ou non atteint.
     Échec : arrêt de production prolongé, ou taux de service sous le seuil du scénario. Pas
     de faillite financière dans cette version.
     Débrief : il distingue ce que le joueur a décidé de ce que le hasard ou un aléa a imposé,
     grâce à la cause inscrite au journal. Il liste aussi les changements de configuration et les
     tentatives refusées. Grâce à la graine, la même partie peut être rejouée avec d’autres
     décisions, et le formateur peut comparer plusieurs stratégies face aux mêmes
     événements.


23. Garde-fous de l’IA de génération
L’IA de génération aide le formateur à remplir le monde. Elle ne calcule rien : le moteur
calcule.

Elle peut :

     remplir les paramètres « à générer » dans les plages de chaque département, en
     cohérence avec le secteur et les valeurs fixées ;
     générer pays, villes, fournisseurs, offres et clients crédibles ;
     proposer des droits pour les configurations du joueur selon le niveau de difficulté
     voulu ;
     proposer des aléas du catalogue, des crises de la bibliothèque et des critères de
     réussite ;
     traduire un cas décrit par le formateur en aléas du catalogue et signaler les valeurs
     manquantes ;
     expliquer les résultats et préparer le débrief à partir du journal.

Elle ne doit jamais :

     calculer un KPI, un coût, un délai, un débit, un droit de douane ou un itinéraire ;
     inventer un événement historique ou ses chiffres ;
     créer, renommer ou supprimer un paramètre, un état, une entité ou un type d’effet ;
     modifier une valeur ou un droit fixé par le formateur ;
     regénérer le monde après sa validation ;
     deviner une valeur manquante au lieu de la signaler.
```

## Page 38

```text
24. Exigences et livrables
Le travail est terminé quand chaque exigence est satisfaite et que les livrables sont
fournis.

Exigences (DOIT)

     Chaque département de la partie B a son moteur (paramètres, règles, données, états)
     et son interface (KPIs, outils, configurations, actions, alertes).
     Aucune valeur, aucun droit, fournisseur, client, trajet, prix ou délai n’est codé en dur :
     tout vient de la configuration (annexe A) ou du moteur.
     Changer de fichier de configuration change le monde sans toucher au code.
     Chaque KPI est calculé par le moteur à partir du journal ; l’interface n’en calcule aucun.
     Les droits Verrouillé, Initial seulement et Libre sont appliqués dans l’interface et sur le
     serveur ; la pop-up rouge s’affiche ; les tentatives sont écrites au journal.
     L’écran « Règles de la partie » s’affiche et doit être confirmé avant le démarrage.
     Les cinq outils fonctionnent et peuvent être désactivés par le formateur.
     Les interactions de la section 20 et leurs effets en chaîne sont respectés.
     Les aléas de la section 21 sont déclenchables selon les quatre modes.
     Le saut de temps donne les mêmes résultats qu’un déroulement accéléré, avec la
     même graine.
     Les vérifications de la section 4 sont exécutées avant la validation du monde.

Livrables

 1. Rapport d’écart sur le code et l’interface actuels.
 2. Socle commun : moteur commun, accueil, structure des pages, droits, pop-up rouge,
     écran « Règles de la partie », outils.
 3. Moteur et interface de chaque département (10 pages).
 4. Fichier de configuration complet pour le produit actuel du monde (annexe A).
 5. Trois scénarios de démonstration : (a) panne imposée sur le goulot M3, le joueur
     appelle la maintenance et réaffecte un opérateur ; (b) blocage d’un passage maritime
     (AL-14), le joueur bascule de trajet ; (c) le formateur verrouille le point de commande et
     laisse la taille de lot libre, le joueur change la taille de lot (accepté) puis tente de
     changer le point de commande (pop-up rouge).


25. Points ouverts
     Unité de temps : le code avance par semaine, le module fournisseurs par séquence de
     30 jours, la v3 par journée de 8 h. Une seule horloge doit être choisie pour toute l’usine ;
     elle fixe aussi la prise d’effet des configurations.
```

## Page 39

```text
     Lignes identiques ou non : la v3 dit que toutes les lignes fabriquent le même produit ; le
     code a 4 lignes sur 4 produits différents. La structure doit accepter les deux ; la
     configuration choisit.
     Plages de valeurs : proposées dans chaque département, à valider.
     Droits conseillés : proposés pour chaque configuration ; le formateur garde le dernier
     mot.
     Valeurs « à générer » absentes de la v3 : durée de vie des outils, temps du magasinier,
     durée d’un préventif, flotte de camions, tolérance des clients.
     Formules à définir : évolution de la confiance d’un fournisseur, agrégation du risque
     (fournisseur, pays, trajet), quantité économique.
     Catalogue de l’usine : les aléas AL-03 à AL-13 non cités ici sont à rapprocher dans le
     rapport d’écart.
     Tableur : coder un tableur maison ou intégrer une bibliothèque existante.
     Module financier : prix de vente, coûts opératoires, trésorerie et marge sont hors de
     cette version.
     Interface du formateur : l’écran où il règle le monde, les droits et le scénario reste à
     décrire.


Annexe A. Fichier de configuration complet
Un seul fichier décrit tout le monde. Pour chaque département : monde (paramètres
réglés par le formateur, avec leur état fixe , a_generer ou desactive ) et joueur
(configurations, avec leur valeur de départ et leur droit verrouille , initial ou libre ).
Un paramètre écrit sans état est fixe ; une configuration sans droit est verrouille . Les
valeurs sont celles de la v3 et servent d’exemple. Les clés existantes de l’usine et du
module fournisseurs sont gardées telles quelles.

   partie:
     secteur: "{secteur}"
       graine: 42
       journee_heures: 8
       aleas_identiques_pour_tous: true
       outils_actifs: [tableur, carte, graphiques, planning, journal]
       regles_partie_a_confirmer: true
       popup_interdit_secondes: 4


   usine:
     pays: "{pays}"
       ville: "{ville}"
       gps: [0, 0]


   fournisseurs:                                   # détail des offres et trajets : module
```

## Page 40

```text
   fournisseurs, annexe A
     monde:
       liste:
         - { id: EXT-FOUR-01, pays: { etat: a_generer }, ville: { etat:
   a_generer }, creneau: "08:00-10:00", camion_palettes: 6 }
       offres:
         - { id: EXT-OFFRE-01, fournisseur: EXT-FOUR-01, article: MP-01,
   prix_unitaire: { etat: a_generer },
                        moq: 1, capacite_max: { etat: a_generer }, delai_production_jours:
   3,
                        fiabilite_delai: 0.95, taux_non_conforme: 0.02 }
        joueur:
          offre_principale:                        { valeur: EXT-OFFRE-01, droit: libre }
           repartition:                            { valeur: { EXT-OFFRE-01: 1.0 }, droit: libre }
           trajet_actif:                           { valeur: auto, droit: libre }
           mode_commande:                          { valeur: automatique, droit: initial }


   quai_dechargement:
     monde: { camions_simultanes: 1, zone_depose_palettes: 6, transpalette_kg:
   2000,
                          dechargement_min_palette: 2, receptionnaires: 1 }
        joueur:
           creneau_reception: { valeur: "08:00-10:00", droit: initial }
           ordre_passage:     { valeur: premier_arrive, droit: libre }


   reception:
     monde: { controle_min_palette: 5, quarantaine_palettes: 2,
   delai_reclamation_jours: { etat: a_generer } }
     joueur:
       niveau_controle:      { valeur: 100_pourcent, droit: libre }
           echantillon_n:        { valeur: 3, droit: libre }
           decision_non_conforme: { valeur: quarantaine_renvoi, droit: libre }


   stock:
     monde: { emplacements: { mp: 24, pf: 20, semi_finis: 0 }, chariot: { kg:
   1200, batterie_h: 8, recharge_h: 6 },
              rangement_min_palette: { etat: a_generer }, preparation_kit_min: {
   etat: a_generer } }
        joueur:
          articles:
            MP-01:
                    stock_minimum:      { valeur: 200, droit: libre }
                    point_commande:     { valeur: 400, droit: libre }
                    quantite_commandee: { valeur: 600, droit: libre }
           methode_reappro:                        { valeur: point_de_commande, droit: initial }
           methode_sortie:                         { valeur: FIFO, droit: verrouille }
```

## Page 41

```text
   chaine_production:
     monde:
       nombre_lignes: 3
           lignes_identiques: true
           transfert: { mode: chariot, temps_min: 0.5 }
           machines:   # copiées sur chaque ligne si lignes_identiques
         - { id: M1, operation: "Préparation", cycle_min: 2,    fonct_min: 110,
   arret_min: 10, mtbf_h: 40, mttr_h: 1,    reglage_min: 10, defaut: 0.02,
   table: 10, outil_produits: { etat: a_generer } }
         - { id: M2, operation: "Assemblage",   cycle_min: 1.5, fonct_min: 110,
   arret_min: 10, mtbf_h: 80, mttr_h: 0.5, reglage_min: 5, defaut: 0.01,
   table: 10, outil_produits: { etat: a_generer } }
         - { id: M3, operation: "Finition",     cycle_min: 3,  fonct_min: 110,
   arret_min: 10, mtbf_h: 60, mttr_h: 1,    reglage_min: 0, defaut: 0.03,
   table: 10, outil_produits: { etat: a_generer } }
         - { id: M4, operation: "Vérification", cycle_min: 1,  fonct_min: 110,
   arret_min: 10, mtbf_h: 100, mttr_h: 0.5, reglage_min: 5, defaut: 0.02,
   table: 10, outil_produits: { etat: a_generer } }
       nomenclature:
         - { article: MP-01, qte_par_produit: { etat: a_generer } }
       joueur:
         taille_lot:                               { valeur: 20, droit: libre }
           regle_lancement_of: { valeur: a_la_commande, droit: initial }
           priorite_of:        { valeur: premier_lance, droit: libre }
           lignes_actives:     { valeur: toutes, droit: libre }
           affectation_operateurs: { valeur: 1_par_machine, droit: libre }
           nomenclature_gamme: { droit: verrouille }


   controle_qualite:
     monde: { controle_min_produit: 1, part_recuperable: 0.65,
   reussite_retouche: 0.75 }
       joueur:
         frequence:                            { valeur: 100_pourcent, droit: libre }
         seuil_blocage:                        { valeur: 0.15, droit: libre }
           regle_recuperable: { valeur: retouche, droit: libre }


   emballage:
     monde: { emballage_min_colis: 2, filmage_min_palette: 5 }
     joueur:
           produits_par_colis: { valeur: 1, droit: verrouille }
           colis_par_palette: { valeur: 6, droit: initial }
           ordre:              { valeur: premier_arrive, droit: libre }
           palette_incomplete: { valeur: jamais, droit: libre }

   maintenance:
```

## Page 42

```text
     monde: { techniciens: 1, deplacement_min: 3, duree_preventif_h: { etat:
   a_generer },
              pdr: [ { ref: MAT-PDR, stock_initial: 3, delai_jours: { etat:
   a_generer } } ] }
     joueur:
           strategie:          { valeur: corrective, droit: libre }
           frequence_preventif_h: { valeur: null, droit: libre }
           ordre_interventions: { valeur: premiere_panne, droit: libre }
           pdr_minimum:                            { valeur: 2, droit: libre }

   logistique:
     monde: { camions_simultanes: 1, chargement_min_palette: 2, camions_usine: {
   etat: a_generer },
              capacite_camion_palettes: { etat: a_generer } }
       joueur:
         depart_camion:                      { valeur: plein, droit: libre }
         delai_max_h:                        { valeur: 4, droit: libre }
           priorite:                         { valeur: date_promise, droit: libre }


   clients:
     monde:
       liste:
         - { id: EXT-CLI-01, ville: { etat: a_generer }, demande_jour: 100,
   variabilite: 0.10,
             delai_attendu_jours: 5, mode_livraison: livre,
   tolerance_retard_jours: { etat: a_generer } }
     joueur:
       regle_acceptation: { valeur: toutes, droit: libre }
           delai_promis_jours: { valeur: 5, droit: initial }
           prevision_jour:    { valeur: 100, droit: libre }


   scenario:
     criteres_reussite:
       - { kpi: otif_client, seuil: 0.95, echeance: fin_partie }
         - { kpi: trs, seuil: 0.75, echeance: fin_partie }
       aleas_programmes:
       - { id: AL-20, cible: L1-M3, duree_h: 4, mode: heure_fixee, jour: 3,
   heure: "10:00" }
```
