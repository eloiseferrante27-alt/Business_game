# Intitulés de métiers ROME des rôles du pack usine

> Source : France Travail, ROME 4.0 version 62 (26M10, publiée le 19/10/2026), open data https://api.francetravail.fr/api-nomenclatureemploi/v1/open-data/json (fichiers unix_fiche_emploi_metier_v462, unix_referentiel_appellation_v462, unix_referentiel_code_rome_v462) ; fiches en ligne https://candidat.francetravail.fr/metierscope/fiche-metier/<code>. Consulté le 2026-11-27.
> Licence : données ouvertes France Travail (licence attachée aux fichiers ; Licence Ouverte non confirmée dans le texte) ; synthèse interne, appellations citées telles quelles.

## Correspondance rôle du jeu, code ROME, appellation

L'appellation est rattachée au code ROME dans la fiche métier (liste des appellations de la fiche). Le code OGR identifie l'appellation.

| Rôle du jeu | Code ROME (intitulé du code) | Appellation exacte | OGR |
|---|---|---|---|
| responsable_usine | H2510 (Directeur / Directrice de production industrielle) | Directeur / Directrice d'unité de production | 14436 |
| responsable_flux | H1403 (Gestionnaire de flux de production) | Gestionnaire de flux de production | 15331 |
| responsable_atelier | H2507 (Responsable de ligne de production industrielle) | Chef / Cheffe de fabrication | 12139 |
| responsable_production | H2507 | Responsable de production | 18813 |
| chef_de_ligne | H2507 | Chef / Cheffe de ligne de production | 12185 |
| responsable_maintenance | I1102 (Ingénieur / Ingénieure de maintenance industrielle) | Responsable de maintenance industrielle | 18789 |
| acheteur | M1101 (Acheteur / Acheteuse) | Acheteur approvisionneur / Acheteuse approvisionneuse | 10242 |
| ordonnanceur | H1403 | Gestionnaire d'ordonnancement | 15360 |
| technicien_methodes | H1404 (Technicien / Technicienne méthodes) | Préparateur / Préparatrice méthodes de travaux en maintenance industrielle | 18033 |
| chef_equipe_maintenance | I1326 (Responsable d'équipe maintenance) | Chef / Cheffe d'équipe de maintenance industrielle | 12418 |

## Missions citées

- Fiche I1326 : le responsable d'équipe maintenance « Planifie les interventions de maintenance préventive et corrective pour minimiser les arrêts de production » et gère une équipe de techniciens.
- Fiche H2507 (Responsable de ligne de production industrielle), mot pour mot : « Planifier des interventions de maintenance » (savoir-faire, enjeu « Prévention des risques », code OGR 122329) ; « Maintenance préventive et corrective » (savoirs, catégorie « Techniques professionnelles », code OGR 477228). Ni l'une ni l'autre n'est un savoir-faire de cœur de métier (champ coeur_metier vide).
- Fiche I1326 (Responsable d'équipe maintenance), compétences mot pour mot (open data v62, fichier fiche_emploi_metier) :
  - savoir-faire, « Prévention des risques » : « Planifier les opérations de maintenance des équipements » (OGR 125310, cœur de métier : Principale) ; « Planifier les interventions d'urgence » (OGR 484770) ;
  - savoir-faire, « Maintenance, Réparation » : « Réaliser ou superviser les interventions de maintenance préventive et corrective » (OGR 490295, cœur de métier : Principale) ; « Détecter l'origine d'une panne (sur place ou à distance) » (OGR 402115) ;
  - savoir-faire, « Management » : « Répartir la charge de travail et les tâches à effectuer entre les membres de l'équipe » (OGR 489488) ;
  - savoir-faire, « Gestion des stocks » : « Gérer les stocks de pièces de rechange » (OGR 483226) ;
  - savoirs, « Normes et procédés » : « Gestion de la maintenance » (OGR 109977) ;
  - appellation : « Dispatcheur / Dispatcheuse de techniciens de maintenance » (OGR 14497).
- Fiche H1404 (Technicien / Technicienne méthodes), compétences mot pour mot :
  - savoir-faire, « Maintenance, Réparation » : « Analyser un dysfonctionnement ou une non conformité » (OGR 123311, cœur de métier : Principale) ; « Réaliser une opération de maintenance » (OGR 300183) ;
  - savoir-faire, « Conseil, Transmission » : « Apporter un appui technique aux services qualité, maintenance, méthodes, recherche et développement » (OGR 121049) ;
  - savoirs, « Normes et procédés » : « Gestion de la maintenance » (OGR 109977).
- Constat : la fiche H1404 ne contient aucune compétence de planification (aucun savoir-faire dont le libellé contient « planifi »). La planification du préventif figure dans I1326 et H2507, pas dans H1404 : la répartition préventif / correctif entre deux rôles (méthodes et équipe de maintenance) n'est donc pas fondée par le ROME.

## Limites

- Le fichier du référentiel des appellations donne, pour certains OGR, un code parent différent (12139, 12185, 18813 et 14436 : H2502 ; 12418 : I1304), alors que les fiches métier listent ces appellations sous H2507, H2510 et I1326. Le code retenu ici est celui de la fiche métier ; l'écart est à garder en tête si on cite le code.
- Seules les appellations et la mission I1326 sont sourcées ; les missions des autres rôles ne sont pas reprises ici.
