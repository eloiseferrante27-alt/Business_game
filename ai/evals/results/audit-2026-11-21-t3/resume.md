# Audit des jeux IA - 2026-11-21

Modèle : qwen2.5:3b

| Id | Secteur | Niveau | Sem. | Modules | Repli | Essais | unmet | Échecs auto | OTIF pilote | ms | Tokens | Échecs avant (19/11) | Niveau / ton demandés | Niveau / ton obtenus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J01 | industrie | decouverte | 4 | pilotage,production,maintenance | non | 1 | - | - | 100.0 | 3910 | 1445 | - | libre / libre | decouverte / mixte |
| J02 | automobile | expert | 12 | pilotage,production,maintenance | non | 1 | - | - | 100.0 | 4424 | 1488 | C9 | expert / libre | expert / exigeant |
| J03 | industrie | equilibre | 12 | pilotage,production,maintenance | non | 1 | - | - | 100.0 | 4601 | 1462 | C1 | libre / libre | equilibre / mixte |
| J04 | industrie | decouverte | 12 | production,maintenance | non | 1 | - | - | 100.0 | 3859 | 1434 | C1 | libre / libre | decouverte / mixte |
| J05 | automobile | decouverte | 12 | pilotage | non | 1 | - | - | 100.0 | 4297 | 1481 | C1 | decouverte / libre | decouverte / mixte |
| J06 | industrie | expert | 12 | pilotage,production,maintenance | non | 1 | - | - | 100.0 | 4324 | 1423 | - | libre / exigeant | expert / exigeant |
| J07 | industrie | equilibre | 12 | pilotage,production,maintenance | non | 1 | - | - | 100.0 | 2416 | 3055 | C1 | libre / libre | equilibre / bienveillant |
| J08 | automobile | expert | 12 | pilotage,production,maintenance | non | 1 | - | - | 100.0 | 3185 | 1571 | C9 | libre / libre | expert / exigeant |
| J09 | industrie | expert | 5 | pilotage,production,maintenance | non | 1 | Le marketing n'est pas simulé dans cette usine. | - | 100.0 | 4738 | 1421 | C9 | expert / libre | expert / exigeant |
| J10 | industrie | expert | 12 | pilotage,production,maintenance | non | 1 | Les cibles chiffrées de la demande sont fixées par le pack, pas par la demande. | - | 100.0 | 4431 | 1450 | - | libre / libre | expert / exigeant |

Latence (ms) : médiane 4310, max 4738 ; tokens : médiane 1456, max 3055
