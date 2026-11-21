# Jeux conçus par l'IA, relus (exigence n° 1)
Second tour. Pack usine (sha256 9df8e8894be4b069c2d50d9314dd67cc3d3a36a5f73c6c1c2e2988c5055f1a8e, copie de travail
non commitée du 21/11 09:42, avant la génération de 09:46) · prompt factory.design v4 · modèle qwen2.5:3b · résultats
du 21/11/2026 (ai/evals/results/audit-2026-11-21/) · protocole : docs/audits/protocole-jeux-ia.md (version 1).
Premier tour (19/11, pack 5202967e…, prompt v3) : 10 refusés ; fiches docs/audits/jeux-ia/J01.md à J10.md.

**État : rien à signer.** 0 conforme, 5 à corriger, 5 refusés. Aucun jeu n'est « conforme » : D16, un texte du moteur
commun à tous les jeux, doit d'abord être corrigé. J01 n'attend que D16 et D7 (moteur-jeu) : c'est le premier
signable, après correction et relance avec la même graine.

| Id | Titre | Secteur | Niveau | Semaines | Aléas | Verdict | Fiche |
|---|---|---|---|---|---|---|---|
| J01 | Métallerie du Val · Équipement en acier | industrie | découverte | 4 | aucun (forcé s2) | à corriger (moteur-jeu) | jeux-ia/J01-t2.md |
| J02 | Équipements Véloce · Équipement automobile | automobile | expert | 12 | rares, aucun tiré | refusé (C9) | jeux-ia/J02-t2.md |
| J03 | Soudures de l'Estuaire · Équipement en acier | industrie | équilibré | 12 | rares, 1 tiré | à corriger (ia-runtime, moteur-jeu) | jeux-ia/J03-t2.md |
| J04 | Ateliers Métal Loire · Équipement en acier | industrie | découverte | 12 | rares, aucun tiré (forcé s2) | à corriger (ia-runtime, game-designer, moteur-jeu) | jeux-ia/J04-t2.md |
| J05 | Mécasoud Est · Équipement automobile | automobile | découverte | 10 | rares, 1 tiré | à corriger (ia-runtime, moteur-jeu) | jeux-ia/J05-t2.md |
| J06 | Métallerie du Val · Équipement en acier | industrie | expert | 12 | rares, 4 tirés | à corriger (ia-runtime, moteur-jeu) | jeux-ia/J06-t2.md |
| J07 | Soudures de l'Estuaire · Équipement en acier | industrie | équilibré | 12 | = J03 | refusé (C4, C8) | jeux-ia/J07-t2.md |
| J08 | Équipements Véloce · Équipement automobile | automobile | expert | 12 | = J02 | refusé (C8, C9) | jeux-ia/J08-t2.md |
| J09 | Ateliers Métal Loire · Équipement en acier | industrie | expert | 5 | rares, 1 tiré | refusé (C4, C9) | jeux-ia/J09-t2.md |
| J10 | Mécanique du Bocage · Équipement en acier | industrie | expert | 12 | rares, 2 tirés | refusé (C4) | jeux-ia/J10-t2.md |

## C1 tranché : les sommes non exposées sont justes
Les 5 « non trouvés » (J03, J04, J05, J07) sont calculés par le moteur (factory_game.py l. 251-281 et 700-716) et
recalculés ici à partir de debrief-pilote.json : pannes attendues au goulot = heures de marche ÷ MTBF du jeu ; évitées
= attendues − observées, au dixième ; coût évité = évitées × (MTTR 1 h × 75 €/h + 200 € de dégâts). J03 et J07 :
11,3 × 275 = 3 107,5 → « environ 3 108 € » ; J04 : 10,7 × 275 = 2 942,5 → « 2 942 € » (arrondi au pair) ; J05 :
19,2 × 275 = 5 280 € ; « 2,6 attendue(s) » = 3 × 0,867. Les deux coûts sont des calibrages listés dans « Non sourcé »
(`maintenance.cout_reparation_h`, `maintenance.cout_degats_panne`). C1 n'est bloquant pour aucun jeu.

## Défauts : état au 21/11
Corrigés (vérifiés dans les 10 jeux) : D1 (règle camion sans citation), D2 (délai et fiabilité = fiche stock de
sécurité l. 6), D3 (« délai + 1 jour de révision + 2 jours de sécurité » = mp_safety_days 2), D4 (pitch par fragments
du profil appliqué), D5 (« Les 3 lignes ont été arrêtées 661 minutes au total »), D10 (TRS hors pauses, cible 80 % :
J05 à 80,6 %), D11 (OTIF, TRS, PF, MP expliqués), D12 (bienveillant vouvoie), nuance RCM (« pas forcément liées »).

| N° | Critère | Défaut restant, preuve | Jeux | Propriétaire | Bloquant |
|---|---|---|---|---|---|
| D9 (c) | C9 | Fournisseur standard à distance `national` (délai 4 j) en expert à 3 lignes : 9 à 11 jours-ligne sans matière pour 7,5 de partiel (graines 202, 5, 6, 8 ; 1 à la graine 7), contre 0 à 3 en `proche`. Valeurs : `network.sites.fournisseur_standard.distances` (pack l. 128) avec `difficulties.expert.mp_stock_days` 2,5 ; calibrage du 19/11 fait en `proche` seulement | J02, J08 | game-designer (+ moteur-jeu : trace) | oui |
| D9 (d) | C9 | Marge expert à une ligne : `criteria.stockouts.margin.expert` 5 ÷ `margin_lines` 2 = 2,5 ; J09 perd 3 jours-ligne (280 min sur 3 matins, camion entre 8 h et 10 h) ; graines 5 à 8 : 0 à 1 | J09 | game-designer | oui |
| D6 | C4 (f) | unmet faux ou muet : « maintenance » (J07, module joué) ; rien sur le marketing digital (J09) ni sur les cibles de 98 % et 20 000 € (J10) | J07, J09, J10 | ia-runtime | oui |
| D14 | C8, C10 | Régénération sans effet : spec de J07 = J03, de J08 = J02 (même sha256), notes non suivies (ton bienveillant ; indulgent, aléas en fin de partie). Réglages contraires au brief ou qui défont le niveau : J02 (pannes fréquentes → mtbf découverte), J03 (8 clés en découverte), J05 (« en douceur » → mtbf expert sur un module non joué ; directrice demandée, absente), J06 et J02 (« fréquents », « beaucoup d'aléas » → rares), J04 (brief préventif, MTBF × 1,5 : le préventif ne se voit pas). Le choix du niveau suit désormais le brief (J01, J03, J05) | J02 à J08 | ia-runtime | C8 oui (J07, J08) ; C10 non |
| D16 | C4 (lu) | « Magasin : 5 palettes sur 24 places, 3 libres. » (J05) : « libres » = capacité − stock − en commande (factory_game.py l. 772-782), mais les palettes en commande ne sont pas citées quand le stock dépasse le point de commande : 19 places sont libres au moment dit. Aussi J06, J09, J10 ; gabarit commun. Texte proposé : « …, 3 libres une fois reçues les 16 palettes en commande » | tous (vu : J05, J06, J09, J10) | moteur-jeu | non, mais à corriger avant signature |
| D7 | écriture | Règle `objectifs` : « trésorerie finale d'au moins 142300 € » (les briefings disent bien « 142 300 € ») | 10 | moteur-jeu | non |
| D13 | C5 | « votre équipe assure les modules pilotage » pour un seul module | J05 | moteur-jeu | non |
| D15 | C6 | Offres rapide 8,4 €/u. et standard 7,5 €/u. affichées « 8 €/u. » toutes deux | J05 | moteur-jeu | non |
| D17 | C9, C10 | Joueur passif de J04 (production et maintenance, pilotage automatique) : TRS 79,9 % pour 80 % (partiel), 675 € de moins que le pilote ; C9 tient à 0,1 point. À mesurer sur les graines 5 à 8 | J04 | game-designer | non |
| D18 | vue formateur | Note `values.pilotage.objectif_trs` : « 78 % reste la cible » alors que `targets.trs` vaut 80 | 10 (« Non sourcé ») | game-designer | non |
| D8 | outil | L'outil C1 prend encore des coïncidences pour des origines (« 1.2 » → `spec.world.objects[39].position[1]`, J01) | 10 | ia-runtime | non |

## Corrections du pack à faire par game-designer, par priorité (non faites dans cette mission)
1. D9 (c) : retirer `national` de `network.sites.fournisseur_standard.distances` (l. 128, garder `[proche]`), ou, si le
   choix doit rester, le réserver aux niveaux découverte et équilibré (règle de génération à spécifier pour moteur-jeu).
   Variantes mesurées le 21/11 sur J02 en national (graines 202, 5 à 8), sans succès : `cover_extra_days` 2,
   marge 6, commande initiale de deux camions, stock de départ de 3,5 j ; 3 j donne 6 partout mais une rupture
   certaine (arrivée au jour 3, stock vide) et 3 jours-ligne à une ligne (J09, graines 5 et 8). Demander à moteur-jeu
   une trace jour par jour de J02, graine 5.
2. D9 (d) : `criteria.stockouts.margin.expert` 5 → 6 (partiel : 3 jours-ligne à une ligne, 9 à trois). Mesuré : J09
   graine 909 passe en partiel ; J06, J10 et J02 en proche ne changent pas. Mettre à jour la note (« 0 à 3 à une
   ligne, graine 909 »). Autre voie : seuil partiel arrondi à l'entier supérieur (règle `apply_rules`, moteur-jeu).
3. Notes `criteria.stockouts` et `stock_mp.commande_initiale` : écrire que le calibrage ne vaut que pour le standard
   `proche`, avec la mesure en national ci-dessus.
4. D18 : réduire la note `pilotage.objectif_trs` à la cible actuelle (80 %, mesures du 19/11) et retirer l'historique
   de la cible de 78 %.
5. D17 : mesurer le joueur passif de J04 (graines 5 à 8). S'il atteint 80 %, exiger pour un jeu sans pilotage un
   réglage de pannes qui rende le préventif visible (consigne pour ia-runtime, `tunables.mtbf_factor.teaches`).

## Hors pack (propriétaires)
- ia-runtime : D6, D14 (régénération à refuser ou relancer si la section reste identique malgré une note ; réglages
  à choisir seulement si leurs `teaches` touchent le brief ; direction quand le brief la demande ; secteur de J10),
  D8.
- moteur-jeu : D16 (priorité : il bloque la signature de J01), D7, D13, D15, trace de D9 (c).
- Après corrections : relancer J01, J03 à J06 avec la même entrée et la même graine ; J02, J07, J08, J09, J10 avec
  `seed + 1000` (protocole § 4), puis relire en entier.

## À vérifier (rien n'est tranché par supposition)
- D9 (c) : cause des ruptures en national hors semaine 1 (graine 5) ; un seul camion par jour, quai ou chariot.
- D17 : passif de J04 sur d'autres graines.
- Le rendu des critères dans Godot : les lignes « OTIF moyen >= 95.0 (partiel 90.0) » de textes.md viennent de
  l'outil d'audit (eval_audit_games.py l. 90), pas d'un texte du jeu ; non relu à l'écran.

Défauts trouvés et corrigés : D1 à D5, D10 à D12 (pack et moteur, copie de travail non commitée au 21/11).
Limites connues : ni les répliques libres des agents (`npc.dialogue`, non produites), ni le rendu Godot, ni d'autres
graines que celles citées.

Je certifie avoir pris connaissance de ces 10 jeux et de leurs fiches.
Nom : ____________  Date : ____________  Signature : ____________

Relu par game-designer le 21/11/2026, sur les résultats du 21/11/2026 (premier tour : 19/11/2026).
