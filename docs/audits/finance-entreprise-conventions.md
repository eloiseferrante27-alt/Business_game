# Finance d'entreprise : conventions de calcul du module finance (D1, ADR 0013)

Décision de game-designer, 2026-11-24, avant D2. Elle tranche le § 9 de `docs/decisions/0013-annexe-contrats.md`
(base des jours, HT ou TTC, taux hebdomadaire des prêts) et relit le corpus `knowledge/finance-entreprise/`.
Statut : décidé, non signé (la signature vient en D3, `liste-a-signer.md`).

## 1. Base des jours : jours calendaires (7 par semaine), soit une base 365

**Règle.** `CA_jour = CA cumulé / (7 x semaines écoulées)`, `achats_jour` idem ; `dso`, `dpo` et `wcr_days` en jours
calendaires. Pénalités de retard : `montant x taux annuel x jours de retard / 365` (annexe § 4.3, inchangé).

**Pourquoi.**
- La loi compte les délais en jours calendaires à partir de la facture : Code de commerce L441-10, I (Légifrance,
  version du 26/04/2019, lue le 2026-11-24) ; l'Observatoire des délais de paiement (ODP) le rappelle : « Celle-ci
  dispose en effet des délais en jours calendaires qui courent à partir de la date d'émission de la facture »
  (rapport annuel 2025, annexe 2, p. 62). Les délais du jeu (`customer_terms_days`, `supplier_terms_days`) sont ces
  délais légaux : le DSO doit se lire dans la même unité pour que le joueur compare « 30 jours accordés » et
  « DSO 34 jours ».
- La Banque de France et l'Insee multiplient par 360 (ODP 2025, annexe 2, p. 61 et 62 ; formules Insee p. 64). C'est
  une convention d'agrégat comptable annuel, sans objet dans un jeu qui compte des semaines.

**Base 365 des pénalités : réserve levée sur le principe, maintenue sur le diviseur** (revue du 2026-11-27).
- Principe sourcé : intérêts simples, comptés par jour, à un taux annuel. Directive 2011/7/UE du 16/02/2011 (JO UE
  L 48 du 23/02/2011), que L441-10 transpose, considérant 15 : « Il convient que les intérêts légaux exigibles en cas
  de retard de paiement soient calculés quotidiennement en tant qu'intérêts simples » ; art. 2, 6) : « "intérêts
  légaux pour retard de paiement", les intérêts simples pour retard de paiement, dont le taux est égal à la somme du
  taux de référence et de huit points de pourcentage au moins ». Texte lu le 2026-11-27 sur
  http://publications.europa.eu/resource/celex/32011L0007 (Office des publications de l'UE, version FR).
- L441-10, II (Code de commerce, rédaction de l'ordonnance n° 2019-359, lu le 2026-11-27 sur
  https://codes.droit.org/payloads/Code%20de%20commerce.xml, reprise Légifrance du 2026-11-26, LEGIARTI000038414392)
  fixe le taux (« taux d'intérêt appliqué par la Banque centrale européenne à son opération de refinancement la plus
  récente majoré de 10 points de pourcentage », plancher « trois fois le taux d'intérêt légal ») mais aucun diviseur.
  service-public.gouv.fr F23211 (vérifié le 07/08/2026) dit seulement : « Les pénalités de retard sont une sanction
  pécuniaire qui s'applique pour chaque jour de retard de paiement ».
- Diviseur 365 : aucun texte français officiel trouvé qui le fixe pour les pénalités. Seul appui public : le guichet
  luxembourgeois (droit luxembourgeois, page du 06/01/2026), « (Montant dû x taux d'intérêt légal x nombre de jours de
  retard) / (365 x 100) », https://guichet.public.lu/fr/entreprises/gestion-juridique-comptabilite/facturation/encaissement/interets-retard.html.
  En droit français, l'année vaut 365 jours dans l'annexe à l'art. R314-3 du Code de la consommation (TAEG, § 3), par
  analogie seulement. Le jeu n'a pas d'année bissextile : 365 reste une convention, présentée comme telle.
- Sites essayés sans formule officielle : entreprendre.service-public.gouv.fr F23211 ; economie.gouv.fr (fiche DGCCRF
  du 23/12/2025, avis CEPC n° 13-07 : PDF refusé, HTTP 403) ; brochure DGCCRF « délais de paiement » (DREETS
  Nouvelle-Aquitaine, sans formule) ; Your Europe (calculateur sans méthode écrite) ; BOFiP (intérêt de retard
  fiscal, autre régime). Bpifrance Création donne « / 365 » mais n'est pas retenue (site d'information, non normatif).
- Débrief : « Les pénalités sont des intérêts simples comptés par jour (directive 2011/7/UE) ; le jeu divise le taux
  annuel par 365, l'usage courant. »

**Écart avec la convention officielle.** À encours égal, DSO Banque de France = DSO du jeu x 360/365, soit 1,4 % de
moins (42 jours BdF valent 42,6 jours calendaires). Présentation au joueur :
- libellé de l'indicateur : « DSO (jours calendaires) » ;
- débrief, une phrase : « La Banque de France compte sur 360 jours : son DSO est 1,4 % plus court que le nôtre pour
  la même situation, un écart négligeable devant le plafond légal de 60 jours. »
- Les moyennes nationales (ODP 2025, p. 7 et 9 : 50 jours d'achats pour les fournisseurs, environ 42 jours de CA pour
  les clients hors microentreprises en 2024) se citent comme ordre de grandeur, jamais comme cible exacte : ce sont
  des moyennes non pondérées d'encours de fin d'exercice, sensibles à la saisonnalité (p. 62).

## 2. Assiette : hors taxe partout, sans TVA

**Règle.** Le jeu n'a pas de TVA : créances, dettes, CA et achats sont tous hors taxe. `dso` = créances HT / CA HT
par jour ; `dpo` = dettes de matières HT / achats de matières HT par jour.

**Pourquoi c'est conforme.** La Banque de France rapporte des créances TTC à un CA TTC (ODP 2025, annexe 2, p. 61 :
créances clients rapportées « au chiffre d'affaires toutes charges comprises (TTC), le résultat étant ensuite multiplié
par 360 ») ; les créances du bilan sont TTC (PCG, comptes 411 et 401, fiche `pcg-2014-03-clients-fournisseurs-banques.md`).
Avec un taux de TVA unique t, le facteur (1 + t) est au numérateur et au dénominateur : le ratio HT/HT du jeu est
égal au ratio TTC/TTC officiel. Ce qui serait faux, c'est de mélanger (créances TTC sur CA HT : DSO gonflé de 20 % à
t = 20 %) ; c'est une leçon de débrief possible.

**Écarts à dire au joueur (débrief, au besoin).**
- DPO : la Banque de France prend « les achats et autres charges externes (TTC) » (p. 62) ; le jeu ne prend que les
  achats de matières, seuls payés à terme (annexe § 4.3, étape 1). Libellé : « DPO (jours d'achats de matières) ».
- Pénalités et commission d'affacturage : en réalité calculées sur le TTC (fiche BdF 422 : commission « du montant TTC
  des factures cédées ») ; dans le jeu, sur le HT. Le taux est juste, la base est sans TVA.

## 3. Taux hebdomadaire des prêts : proportionnel, `rate_week = rate_year / 52`

**Règle.** Inchangée (annexe § 4.3, étape 4). `rate_year` est le **taux nominal annuel du contrat** ; les intérêts de la
semaine valent `capital x rate_year / 52`. Même convention pour `economy.interest_rate_week` (agios).

**Pourquoi.** Code de la consommation, art. R314-2, texte français officiel (réserve levée le 2026-11-27 ; la version
du 2026-11-24 venait d'une traduction). Rédaction du décret n° 2016-884 du 29 juin 2016 (JO du 30/06/2016),
LEGIARTI000032807606, en vigueur ; lu sur https://codes.droit.org/payloads/Code%20de%20la%20consommation.xml (reprise
des données Légifrance par droit.org, mise à jour du code du 2026-11-20). Extraits exacts :
> « Pour les opérations de crédit destinées à financer les besoins d'une activité professionnelle ou destinées à des
> personnes morales de droit public, le taux effectif global est un taux annuel, proportionnel au taux de période, à
> terme échu et exprimé pour cent unités monétaires. Le taux de période et la durée de la période doivent être
> expressément communiqués à l'emprunteur. »
> « Lorsque la périodicité des versements est irrégulière, la période unitaire est celle qui correspond au plus petit
> intervalle séparant deux versements. Le plus petit intervalle de calcul ne peut cependant être inférieur à un mois. »
> « Lorsque les versements sont effectués avec une fréquence autre qu'annuelle, le taux effectif global est obtenu en
> multipliant le taux de période par le rapport entre la durée de l'année civile et celle de la période unitaire. Le
> rapport est calculé, le cas échéant, avec une précision d'au moins une décimale. »

La convention proportionnelle est donc celle du crédit aux entreprises en France. Le taux actuariel
(1 + i)^(1/52) - 1 est celui du TAEG des consommateurs (art. R314-3) et des statistiques de la Banque de France.
Nuance : R314-2 règle l'expression du TEG, pas le calcul des intérêts ; son calcul ne descend pas sous le mois. Le jeu
n'affiche pas de TEG : il applique un **taux nominal** proportionnel à des intérêts payés chaque semaine, ce que la
règle ne contredit pas. Ne pas écrire au joueur « TEG hebdomadaire ».
Nombre de semaines : le rapport de R314-2 pour une semaine serait 365/7 = 52,1 (une décimale) ; le jeu prend 52,
valeur que l'annexe à l'art. R314-3 retient pour le TAEG : « Une année compte 365 jours, ou, pour les années
bissextiles, 366 jours, 52 semaines ou 12 mois normalisés » (même source, LEGIARTI000053516619, décret n° 2026-105).
Écart relatif 0,27 % (à 4 % : 0,0769 % contre 0,0767 % par semaine), négligeable.

**Calibrage (D2).** Les taux Banque de France sont des taux actuariels annualisés (TESE, méthodologie du 05/07/2017,
fiche `taux-credits-entreprises-bdf-stat-info-2026-09.md`). Dans le pack, convertir puis arrondir au centième :
`rate_year = 52 x ((1 + TESE)^(1/52) - 1)`. Exemples, juillet 2026 : trésorerie échéancée 3,90 % -> 3,83 % ;
équipement 3,79 % -> 3,72 % ; découverts 5,07 % -> 4,95 %. Sans conversion, 3,90 % pris tel quel en nominal ferait
3,98 % actuariel (+0,08 point). Provenance dans le pack : « BdF, Stat Info sept. 2026, taux de juillet 2026, converti
en nominal proportionnel ».

**Présentation au joueur.** Offre : « taux nominal annuel 3,83 % (intérêts payés chaque semaine) ». Débrief :
« Les banques annoncent aux entreprises un taux proportionnel (taux de la période x nombre de périodes) ; la Banque
de France publie des taux actuariels. 3,90 % actuariel = 3,83 % nominal payé chaque semaine. »

## 4. VAN : formule confirmée, source à renforcer

La formule de l'annexe § 4.4 est juste : 100 000 €, 30 000 €/an, 5 ans, 8 % -> facteur d'annuité
(1 - 1,08^-5) / 0,08 = 3,99271 ; VAN = -100 000 + 119 781,30 = **19 781,30 €** (recalculé). Sources plus solides que
Wikipédia, à donner à rag-knowledge :
1. Vernimmen, *Finance d'entreprise* (Dalloz, éditions annuelles), chapitre sur la valeur actuelle nette : ouvrage de
   référence, déjà cité par la fiche BdF 422. Édition, chapitre et page à relever sur l'exemplaire (à vérifier).
2. Office québécois de la langue française, Grand dictionnaire terminologique, fiche « valeur actualisée nette »
   (source : ICCA, *Dictionnaire de la comptabilité et de la gestion financière*, 2006) :
   https://vitrinelinguistique.oqlf.gouv.qc.ca/fiche-gdt/fiche/503681/valeur-actualisee-nette (définition et taux
   d'actualisation fondé sur le coût pondéré du capital ; pas de formule).
3. France Stratégie et DG Trésor, *Guide de l'évaluation socioéconomique des investissements publics*, complément
   opérationnel E « Règles de décision à partir de la VAN socioéconomique » (2017) : formules d'actualisation et règle
   « VAN positive », mais pour l'investissement public ; à citer comme appui, pas comme définition de la VAN financière.

## 5. Relecture des fiches prioritaires (corrections pour rag-knowledge)

Vérifié sur la source : L441-10 et D441-5 (Légifrance), ODP 2025 (p. 7, 9, 18, 61, 62, 64), fiche BdF 422 (PDF
05/2022). Les chiffres recopiés sont justes. Corrections :

| Fiche | Phrase | Correction |
|---|---|---|
| `odp-2025-dso-dpo.md` l. 12 | « (annexe 1, page 62) » | « (annexe 2, page 62) » : la phrase sur les jours calendaires est en annexe 2. |
| `code-commerce-l441-10-d441-5-delais-paiement.md` l. 3 et 27 | « Observatoire des délais de paiement, rapport annuel 2025, annexe 1 » | « annexe 2, p. 62 ». |
| idem l. 12 | « version en vigueur depuis le 1er janvier 2024, ordonnance n° 2023-1210 » | Référence non retrouvée : vérifier la version de L441-11 sur Légifrance ou retirer la date. Délais sectoriels (transport 30 jours, agroalimentaire non périssable 60 jours) confirmés par la DGCCRF (fiche du 23/12/2025). |
| idem l. 30-31 | taux légal non lu | Ajouter, avec sa source : service-public.gouv.fr F23211 (vérifié le 07/08/2026) : plancher 3 x taux légal = 8,25 % ; taux par défaut BCE + 10 points = 12,15 % (1er semestre 2026, BCE 2,15 %) et 12,40 % (2e semestre, BCE 2,40 %). Semestre du taux légal à vérifier. |
| `taux-credits-entreprises-bdf-stat-info-2026-09.md` l. 38 | « La seule convention de taux annuel documentée ici est actuarielle » | Ajouter : pour le crédit professionnel, le TEG est proportionnel au taux de période (Code de la consommation, art. R314-2) ; le jeu suit cette convention (cette note, § 3). |
| `van-wikipedia-valeur-actuelle-nette.md` | source unique Wikipédia | Ajouter les sources du § 4 ; garder Wikipédia en appui seulement. |
| `affacturage-bdf-fiche-422.md` | - | Juste (85-95 %, 8-15 %, 0,2-2 % du TTC, indice + jusqu'à 2,5 %, 365 Md€ en 2021, LME 2009 vérifiés p. 1-4). |

Nouvelle fiche à créer : Code de la consommation, art. R314-2 (TEG des crédits professionnels, proportionnel), lien
Légifrance LEGIARTI000032807606, avec la ligne « > Source : Code de la consommation, art. R314-2 (décret n° 2016-884),
texte lu le 2026-11-27 sur codes.droit.org (reprise Légifrance) » et les trois extraits du § 3, mot pour mot.

Ajout à `code-commerce-l441-10-d441-5-delais-paiement.md` (rag-knowledge), avec sa source : « Les intérêts légaux pour
retard de paiement sont des intérêts simples calculés quotidiennement (directive 2011/7/UE, considérant 15 et art. 2,
6) ; L441-10 ne fixe pas le nombre de jours de l'année : le jeu prend 365 par convention. »

## 6. Texte de remplacement du § 9 de l'annexe (pour l'architecte)

> - Base des jours, assiette et taux des prêts : tranchés en D1 (`docs/audits/finance-entreprise-conventions.md`).
>   Jours calendaires (7 par semaine) comme L441-10 ; la BdF compte 360 jours (DSO 1,4 % plus court, dit au débrief).
>   Tout hors taxe : sans TVA, le ratio HT/HT égale le ratio TTC/TTC de la BdF. Taux proportionnel `rate_year / 52`,
>   convention du TEG des crédits professionnels (Code de la consommation, R314-2) ; `rate_year` est un taux nominal,
>   converti depuis le taux actuariel BdF dans le pack.
