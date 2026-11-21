# Audit des jeux IA - 2026-11-21

Modèle : qwen2.5:3b

| Id | Secteur | Niveau | Sem. | Modules | Repli | Essais | unmet | Échecs auto | OTIF pilote | ms | Tokens | Échecs avant (19/11) | Niveau / ton demandés | Niveau / ton obtenus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J01 | industrie | decouverte | 4 | pilotage,production,maintenance | non | 1 | - | - | 100.0 | 3506 | 1432 | C1, C2, C9 | libre / libre | decouverte / mixte |
| J02 | automobile | expert | 12 | pilotage,production,maintenance | non | 1 | - | C9 | 100.0 | 3845 | 1422 | C1, C2 | expert / libre | expert / exigeant |
| J03 | industrie | equilibre | 12 | pilotage,production,maintenance | non | 1 | - | C1 | 100.0 | 4976 | 1448 | C2 | libre / libre | equilibre / mixte |
| J04 | industrie | decouverte | 12 | production,maintenance | non | 1 | - | C1 | 100.0 | 4409 | 1446 | C1, C2 | libre / libre | decouverte / mixte |
| J05 | automobile | decouverte | 10 | pilotage | non | 1 | - | C1 | 100.0 | 3872 | 1416 | C2, C9 | decouverte / libre | decouverte / mixte |
| J06 | industrie | expert | 12 | pilotage,production,maintenance | non | 1 | - | - | 100.0 | 3271 | 1412 | C1, C2, C9 | libre / exigeant | expert / exigeant |
| J07 | industrie | equilibre | 12 | pilotage,production,maintenance | non | 1 | maintenance | C1 | 100.0 | 1402 | 1458 | C2 | libre / libre | equilibre / mixte |
| J08 | automobile | expert | 12 | pilotage,production,maintenance | non | 1 | - | C9 | 100.0 | 2403 | 1456 | C1, C2 | libre / libre | expert / exigeant |
| J09 | industrie | expert | 5 | pilotage,production,maintenance | non | 1 | - | C9 | 100.0 | 3938 | 1409 | C1, C2, C9 | expert / libre | expert / exigeant |
| J10 | industrie | expert | 12 | pilotage,production,maintenance | non | 1 | - | - | 100.0 | 4324 | 1442 | C1, C2, C9 | libre / libre | expert / mixte |

Latence (ms) : médiane 3858, max 4976 ; tokens : médiane 1437, max 1458
