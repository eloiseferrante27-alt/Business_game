# Jeux conçus par l'IA, relus (exigence n° 1)
Troisième et dernier tour. Pack usine (sha256 3b51658fb7987152d38937c298dc1335f31c178dd7e9d5a328e1dab6b79c8ffe, copie
de travail non commitée du 21/11 11:20, avant la génération de 11:29-11:32) · prompt factory.design v5 · modèle
qwen2.5:3b · résultats du 21/11/2026 (ai/evals/results/audit-2026-11-21-t3/) · protocole :
docs/audits/protocole-jeux-ia.md (version 1). Tours précédents : 19/11 (fiches J0x.md, 10 refusés) et 21/11 matin
(fiches J0x-t2.md, 5 à corriger, 5 refusés).

**État au 21/11/2026 : audit de l'exactitude clos.** J05, J08 et J09 conformes et signés par Romain (21/11/2026) ;
les 7 autres sont exacts, respect de la demande à améliorer (repris en tranche T9 de l'ADR 0013). Voir « Clôture ».

| Id | Titre | Secteur | Niveau | Semaines | Aléas | Verdict t3 | Reste à faire | Fiche |
|---|---|---|---|---|---|---|---|---|
| J01 | Métallerie du Val · Équipement en acier | industrie | découverte | 4 | aucun (forcé s2) | exact, demande à améliorer (T9) | D19 (moteur-jeu, en cours) | jeux-ia/J01-t3.md |
| J02 | Équipements Véloce · Équipement automobile | automobile | expert | 12 | rares, plan s2-s4 | exact, demande à améliorer (T9) | D14 : « beaucoup d'aléas » → rares (ia-runtime) | jeux-ia/J02-t3.md |
| J03 | Soudures de l'Estuaire · Équipement en acier | industrie | équilibré | 12 | rares, 1 tiré | exact, demande à améliorer (T9) | D14 : 8 réglages découverte (ia-runtime) | jeux-ia/J03-t3.md |
| J04 | Ateliers Métal Loire · Équipement en acier | industrie | découverte | 12 | rares (forcé s2) | exact, demande à améliorer (T9) | D17 reporté en T3 ; D14 (ia-runtime) | jeux-ia/J04-t3.md |
| J05 | Mécasoud Est · Équipement automobile | automobile | découverte | 12 | rares, plan s2-s6, 1 tiré | **conforme** | rien | jeux-ia/J05-t3.md |
| J06 | Métallerie du Val · Équipement en acier | industrie | expert | 12 | rares, 4 tirés | exact, demande à améliorer (T9) | D14 : « fréquents » → rares (ia-runtime) | jeux-ia/J06-t3.md |
| J07 | Soudures de l'Estuaire · Équipement en acier | industrie | équilibré | 12 | = J03 | exact, demande à améliorer (T9) | hérité de J03 ; régénération juste | jeux-ia/J07-t3.md |
| J08 | Équipements Véloce · Équipement automobile | automobile | expert | 12 | rares, plan s10 | **conforme** | rien | jeux-ia/J08-t3.md |
| J09 | Ateliers Métal Loire · Équipement en acier | industrie | expert | 5 | rares, 1 tiré | **conforme** | rien | jeux-ia/J09-t3.md |
| J10 | Mécanique du Bocage · Équipement en acier | industrie | expert | 12 | rares, 2 tirés | exact, demande à améliorer (T9) | C6 : secteur automobile (ia-runtime) | jeux-ia/J10-t3.md |

## Régénération (J07, J08) : défaut écarté
Comparaison clé par clé avec les jeux d'origine **du même tour** (J07 contre J03 t3, J08 contre J02 t3), `params` de
design.json et spec.json aplatis :
- J07 : seule `agent_tone` change (mixte → bienveillant), clé de `FACTORY_SECTIONS["personnages"]` (spec.py l. 924) ;
  46 chemins de spec diffèrent, tous `agents[i].personality.*` ou `params.agent_tone`. `options.lines` 3 = J03 t3.
- J08 : changent `tunings` et `event_plan`, clés de `FACTORY_SECTIONS["objectifs"]` (l. 923) ; `difficulty` expert et
  `events` rares, rendus au modèle, restent ; 36 chemins de spec diffèrent, tous dérivés du MTBF × 1,5 et du plan.
  `mtbf_factor` découverte suit la note (« pannes rares ») : J02 t3 n'a aucun réglage, rien n'a fui par `current`.
- `network.fournisseur_standard` manque aussi dans J02 t3 et J03 t3 : depuis D9 (c), le pack n'offre que `proche`
  (usine.yaml l. 131), la conception ne le choisit plus et le jeu prend le défaut `proche`. L'écart n'apparaît que
  face au t2. Ni `_keep` ni `current` n'est en cause ; aucun défaut pour ia-runtime ou pipeline-kafka.

## Textes nouveaux relus
- D16 corrigé, juste dans les 10 jeux : « X palettes sur 24 places, Y libres une fois comptées les Z en commande »,
  Y = 24 − X − Z vérifié partout. Tournure lourde quand Z = 0 (« les 0 en commande ») : remarque, non exigée.
- D7 corrigé (« 142 300 € », « 206 600 € »… dans la règle `objectifs`) ; D13 corrigé (« le module pilotage », J05) ;
  D15 corrigé (« 8,40 €/u. », « 7,50 €/u. », « 6,60 €/u. », J05).
- Bilan du préventif : justes à l'usure chiffrée (J03, J04, J05, J07 : évitées × 275 €) et à la forme 1 (J02, J06,
  J08, J09, J10 : « ne les évite pas », 0 €). **D19** au cas « hasard » (J01) : voir ci-dessous.
- J10 au niveau expert sans niveau demandé : cohérent (98 % d'OTIF visés, défi exigeant) ; seul le secteur est faux.

## Défauts restants
| N° | Critère | Défaut, preuve | Jeux | Propriétaire | Bloquant |
|---|---|---|---|---|---|
| D19 | C4 | « l'écart reste dans les variations du hasard : on ne peut pas dire combien le préventif en a évité » puis « réparations et dégâts évités : environ 0 € » : la somme chiffre à 0 ce qui est déclaré inconnu (factory_game.py l. 273-277 et 703-704). Écrire « non chiffrables (écart dans les variations du hasard) » quand aucun groupe n'est chiffré et qu'un goulot à usure a eu du préventif ; garder 0 € à la forme 1 | J01 | moteur-jeu (correction en cours) | oui pour J01 |
| D14 (reste) | C10 | « beaucoup d'aléas » (J02) et « aléas fréquents » (J06) → `rares` alors que le pack a `frequents` ; « niveau moyen » → 8 réglages découverte (J03, donc J07) ; brief préventif sans `mtbf_factor` plus sévère (J04) | J02, J03, J04, J06, J07 | ia-runtime | non bloquant, correction exigée |
| C6 | C6 | « équipementier automobile » → thème industrie | J10 | ia-runtime | non bloquant, correction exigée |
| D17 (fond) | C9, C10 | Passif de J04 à 0,1 point de TRS du pilote ; la garde est codée en avertissement (generation.py l. 243-247). Critère « pannes évitées au goulot » à coder (spécification ci-dessous) | J04 | moteur-jeu ; game-designer (valeurs) | non bloquant à la graine 404 ; reporté en T3 |
| D8 | outil | Coïncidences prises pour des origines dans l'outil C1 (non revu au t3) | 10 | ia-runtime | non |

Corrigés et vérifiés au t3 : D6 (J07, J09, J10), D7, D9 (c) et (d), D13, D15, D16, D18, D14 en partie (J01, J05, J10 :
réglages ; J07, J08 : la régénération suit la note), garde D17. Plus tôt : D1 à D5, D10 à D12.

Remarques non exigées : unmet de J10 ambigu (« la demande » = celle du formateur) ; J02, graine 202 : 17 pannes pour
33,1 attendues à la forme 1, tirage extrême (27 à 37 sur les graines 5 à 11, moteur calé).

## D17 : critère à confier à moteur-jeu (spécification, inchangée)
Si `maintenance` est joué et la forme du goulot > 1 : critère « pannes évitées au goulot » = (attendues − observées) ÷
attendues (calcul déjà fait au bilan, factory_game.py l. 251-281) ; cible 50 %, partiel 25 % (indicatifs, à calibrer).
J04, graine 404 : (11,7 − 1) ÷ 11,7 = 91 % ; passif sans préventif : environ 0 (à mesurer). Source : forme de Weibull
> 1 = taux de panne croissant avec l'âge (nist-sematech-weibull l. 77-78) ; à forme 1, pas de critère.

## Écart au protocole, accepté par game-designer
§ 4 demande `seed + 1000` pour les jeux refusés au t2 (J02, J07 à J10) ; le t3 a gardé les graines d'origine. Accepté
pour C9 : les corrections D9 ont été mesurées sur les graines 5 à 8 (208 parties, 21/11). Non couvert pour D6 (unmet) :
la tenue sur d'autres graines du modèle reste à vérifier (ia-runtime, eval_design_consignes).

## Clôture (décision de l'utilisateur, 21/11/2026)
L'audit de l'exactitude (exigence n° 1) est clos.
- Signés : J05, J08 et J09, conformes au troisième tour (fiches jeux-ia/J05-t3.md, J08-t3.md, J09-t3.md).
- J01, J02, J03, J04, J06, J07 et J10 : **exacts, respect de la demande à améliorer**. Leurs écarts portent sur le
  respect des consignes, pas sur l'exactitude : aléas « fréquents » rendus « rares » (J02, J06) ; « niveau moyen »
  rendu en découverte (J03, J07) ; J04 sans `mtbf_factor` plus sévère ; J10 dans le mauvais secteur. Repris en
  tranche T9 de l'ADR 0013, avec un nouvel audit.
- D17 (critère « pannes évitées au goulot ») : reporté en tranche T3. D19 (J01) : correction en cours (moteur-jeu).
- Écart au protocole accepté (section ci-dessus) : les graines `seed + 1000` n'ont pas été appliquées.

## Condition de validité
1. La signature porte sur le pack (sha256 3b51658f… ci-dessus), le prompt v5 et le code du commit qui suit cette
   décision. Hash de ce commit : `ffed981ac042657a69e56258d7c24920481263ad` (poussé le 24/11/2026, plage
   2920a79..ffed981). Toute modification après ce commit de `ai/packs/usine.yaml`, de `ai/simulation.yaml` ou du
   code de génération et du moteur (`backend/gmix/game/`) rend un nouvel audit nécessaire avant de réutiliser
   cette signature.
2. Une correction du prompt (D14, C6) crée la v6 et rouvre la relecture de **tous** les jeux, J05, J08 et J09
   compris (§ 6) : ce sera le nouvel audit de T9.
3. Relances en T9 : J01, J02, J03, J04, J06, J10 même entrée et même graine ; J07 régénéré depuis le nouveau J03 ;
   J08 régénéré depuis le nouveau J02 si le prompt change.

## Signatures (jeux conformes)
| Id | Verdict | Relu le | Version | Signé par | Date |
|---|---|---|---|---|---|
| J05 | conforme | 21/11/2026 | pack 3b51658f…, prompt v5, qwen2.5:3b, graine 505 | Romain | 21/11/2026 |
| J08 | conforme | 21/11/2026 | pack 3b51658f…, prompt v5, qwen2.5:3b, graines 808 / 202 | Romain | 21/11/2026 |
| J09 | conforme | 21/11/2026 | pack 3b51658f…, prompt v5, qwen2.5:3b, graine 909 | Romain | 21/11/2026 |

Limites connues : ni les répliques libres des agents (`npc.dialogue`, non produites), ni le rendu Godot (les lignes
« OTIF moyen >= 95.0 » de textes.md viennent de l'outil d'audit, eval_audit_games.py l. 90), ni d'autres graines que
celles citées.

Je certifie avoir pris connaissance des jeux signés ci-dessus et de leurs fiches.
Nom : Romain  Date : 21/11/2026  Signature : signé par Romain, le 21/11/2026 (« Je signe les 3 »)

Relu par game-designer le 21/11/2026, sur les résultats du 21/11/2026 (troisième tour ; premier tour : 19/11/2026).
