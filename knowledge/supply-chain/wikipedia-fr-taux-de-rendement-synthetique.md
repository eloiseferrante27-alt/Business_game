# Taux de rendement synthétique

> Source : Wikipédia (fr), « Taux de rendement synthétique », révision 234398211 : https://fr.wikipedia.org/wiki/Taux_de_rendement_synth%C3%A9tique?oldid=234398211
> Licence : CC BY-SA 4.0 (attribution : contributeurs de Wikipédia). Texte brut converti (API extraits), consulté le 2026-11-21.
> Note : la page renvoie à la norme NF E60-182 (payante) sans la reproduire et dit que la prise en compte des pauses varie selon les organisations.

Le taux de rendement synthétique (ou TRS) est un indicateur destiné à suivre le taux d'utilisation de machines.
Il est défini par la formule :

TRS = Production réelle / production maximum théorique
La définition du TRS est un standard propre à chaque organisation qui le définit. Ainsi, pour une situation donnée, le TRS calculé sera différent selon les organisations qui le calculent.
Le TRS décompose et met en évidence les pertes de production en différentes catégories sur lesquelles un plan d'action est mis en place.
Ainsi, on retrouve trois taux dans le calcul théorique du TRS : 

le taux de disponibilité (notamment influencé par les pannes et les changements d'outils). Celui-ci se définit comme un rapport entre le "temps disponible" et le "temps utile" ou "temps de production" (ou tout autre terme équivalent). Ce taux est un de ceux qui font l'objet des plus grandes divergences entre les organisations (voir le paragraphe qui y est consacré).
le taux de performance (notamment influencé par les micro-arrêts et les baisses de cadences)
le taux de qualité (notamment influencé par les défauts et les pertes aux redémarrages)
Le TRS correspond à la multiplication de ces trois taux. Chacun des trois taux étant compris entre 0 et 100 %, le TRS doit donc être compris entre 0 et 100 %.
Plus un indice de TRS est proche de 100 %, meilleure est l'efficacité de la ligne.
Pratiquement, le TRS est souvent calculé comme le rapport entre le nombre de pièces bonnes produites pendant une certaine période et le nombre de pièces théoriquement produites durant la même période.
On peut améliorer un TRS en utilisant différentes méthodes (SMED, TPM, 5S, autoqualité, démarche ergonomique, déploiement d'un système ...).
Les systèmes SCADA sont de plus en plus utilisés à des fins de calcul de TRS. La mise en place de ce type de système est facilitée par l’interopérabilité des équipements via des standards comme l'OPC UA.

== Formulation ==
On définit :

Ri = Temps d’arrêt = Date de réparation – Date d’apparition d’une panne causant l'arrêt du système.
R = Temps d’arrêt total = ∑Ri
E = Temps requis
A = temps d'ouverture : temps théorique de fonctionnement maximum.
Temps brut de fonctionnement : B = A – R
Temps net de fonctionnement : C = B - pertes de performances (différence entre cadence théorique et cadence réelle due aux arrêts mineurs)
D = temps utile (qui produit que des ensembles bons)
D = C - pertes de qualité : non qualité pendant le fonctionnement, réglages, essais, démarrage...
Taux de fonctionnement brut : Tb = (A-R) / A = B/A
Taux de performance : Tf = C/B
Taux de qualité : Tq = D/C
Le TRS est le seul indicateur qui tient compte de tous les paramètres qui affectent la productivité d'un système. Il dépend des trois qui le composent, si l’un des trois se dégrade le TRS chute.

Taux de Rendement Synthétique (TRS) : TRS = D/A = Tb x Tf x Tq = B/A x C/B x D/C
Cette décomposition permet d’identifier plus facilement quel facteur (disponibilité, performance ou qualité) influe le plus sur la baisse du TRS.

== Discussions sur le taux de disponibilité ==
Il existe de nombreuses variantes concernant la mesure des temps d'ouverture et les différents arrêts.
Ainsi:

Certaines organisations considèrent que le temps utile est mesuré à partir du moment où l'équipement a lancé tous ses processus de démarrage, est équipé, à la bonne température, etc. D'autres organisations, considérant que les temps de démarrage et mise en condition sont des gaspillages à chasser, considèrent le temps d'ouverture comme commençant dès que l'équipement est sous tension, voire dès le début de la période de mesure, même si aucune personne n'est présente et que l'équipement n'est pas encore mis en marche (certaines organisations considèrent que attendre un opérateur pour commencer est une source d'inefficacité).
Concernant les arrêts, de nombreuses variantes existent. Par exemple, si un opérateur doit arrêter l'équipement pour une pause réglementaire, selon les organisations, c'est considéré comme un arrêt (à éviter) ou une réduction du temps d'ouverture. Autrement dit, avec cette vision, l'équipement n'est pas censé produire à ce moment.
Une autre variante peut concerner les pertes de temps causées par des produits défectueux. Certaines méthodes enlèvent le temps passé à produire un produit défectueux, et réduisent ainsi le temps utile. D'autres méthodes conservent le temps utile, et réduisent le taux de produits bons.
Une autre variante concerne les arrêts causés par des facteurs externes, typiquement un manque de produits en entrée ou une saturation des équipements en sortie. Certaines analyses considèrent que c'est une réduction du temps d'ouverture, et que l'équipement n'est pas remis en cause dans sa capacité. D'autres points de vue gardent le temps d'ouverture inchangé, et considèrent des arrêts réduisant le TRS.
Une autre variante concerne les arrêts pour des préventifs des équipements. Ces divergences d’interprétation expliquent pourquoi deux usines similaires peuvent obtenir des valeurs de TRS différentes, malgré des conditions de production comparables.

== Application (exemple) ==
Nous partons d'une hypothèse d'un taux de fonctionnement brut Tb situé entre 90 et 98 %, un taux de performance Tf généralement aux alentours de 95 %, et un TRS à obtenir > 85 % (ce qui semble modeste).
Puisque TRS = Tb x Tf x Tq, il faut un taux de qualité tq de 99 %, autrement dit, il faut atteindre un niveau d'excellence !
Il est fréquent qu'avant une démarche TPM, le TRS initial soit de l'ordre de 50 % seulement. Le remonter à 70 % représente déjà un gain très significatif. Le suivi du TRS permet d'avoir une vue synthétique, et l'examen de ses composantes permet de déterminer quel levier activer pour l'améliorer.
Un atelier travaille en équipe de journée pendant 8 heures soit 480 minutes. L'ouverture machine constatée est de 440 minutes. Les arrêts machine d'un total de 40 minutes sont ventilés comme suit :

Changement de série = 20 minutes
Panne = 15 minutes
Réglages = 5 minutes
Le temps de cycle théorique est de 120 pièces / heure mais la mesure d'un temps de cycle réel donne une cadence de 100 pièces / heure seulement.
Quantité réalisée : 600 pièces / jour
Quantité rejetée : 18 pièces, 12 étant récupérables, 6 irrécupérables.

=== Taux de fonctionnement brut ===
Il représente les pertes liées au non fonctionnement de la machine
Tb = [(480-40) / 480] = 0,916 = 91,6 %

=== Taux de performance ===
Il représente les pertes dues à un fonctionnement non optimal de la machine
Une cadence de 100 pièces par heure équivaut à 0,6 minute par pièce.
C'est le temps net de fonctionnement, soit le temps utile à fabriquer des pièces bonnes.
C = B - perte de performance=temps de cycle réel * nombre de pièces.
Tf = C/B = (0,6 minute/pièce x 600 pièces) / (480-40) = 0,818 = 81,8 %
Rendement vitesse = 100/120 ≈ 0,833 = 83,3 % 
(quotient entre le temps de cycle théorique et réel, ou entre les cadences théoriques et réelles)

=== Taux de qualité ===
Il représente les pertes dues à de mauvaises fabrications
Taux de qualité Tq= (600-18) / 600 = 0,97 = 97 %

=== Taux de rendement synthétique ===
Le TRS est le produit de ces indicateurs, soit 72,5 %.

=== Taux de rendement global ===
Le taux de rendement global est défini comme le rapport du temps utile par le temps d'ouverture, autrement dit comme le TRS multiplié par le taux de charge. Il est plus "sévère" et de nombreuses organisations continuent à appeler TRS ce qui est en fait le TRG.

== Notes et références ==

=== Articles connexes ===
Taux de rendement global
Industrie

=== Liens externes ===
Définition et exemples de calcul du TRS
Norme NF E60-182 sur le site de l'AFNOR
L'indicateur TRS dans le logiciel MES
Site permettant le calcul en ligne du TRS
Autres documentations sur le TRS
Calcul TRS Norme NF E60-182
 Portail de l'industrie   Portail du management