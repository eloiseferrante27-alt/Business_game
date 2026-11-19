# Audit des jeux IA - 2026-11-19

Modèle : qwen2.5:3b

| Id | Secteur | Niveau | Sem. | Modules | Repli | Essais | unmet | Échecs auto | OTIF pilote | ms | Tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| J01 | industrie | expert | 4 | pilotage,production,maintenance | non | 1 | aucun produit non conforme | C1, C2, C9 | 95.0 | 3417 | 1382 |
| J02 | automobile | expert | 12 | pilotage,production,maintenance | non | 1 | aucun équipement spécifique à l'industrie automobile | C1, C2 | 100.0 | 4729 | 1446 |
| J03 | industrie | expert | 12 | pilotage,production,maintenance | non | 1 | aucun aléa | C2 | 100.0 | 5226 | 1460 |
| J04 | industrie | expert | 12 | production,maintenance | non | 1 | - | C1, C2 | 100.0 | 3748 | 1365 |
| J05 | automobile | decouverte | 5 | pilotage | non | 1 | pas de fournisseur spécialisé dans l'automobile | C2, C9 | 100.0 | 5070 | 1446 |
| J06 | industrie | expert | 12 | pilotage,production,maintenance | non | 1 | l'usine ne sait pas simuler les perturbations des fournisseurs | C1, C2, C9 | 96.7 | 4476 | 1448 |
| J07 | industrie | expert | 12 | pilotage,production,maintenance | non | 1 | la formation ne peut pas être intégralement réalisée sans un atelier de soudure d'équipements en acier | C2 | 100.0 | 1901 | 1442 |
| J08 | automobile | expert | 12 | pilotage,production,maintenance | non | 1 | aucun des secteurs de l'industrie automobile ne peut être complètement reproduit dans une usine de soudures en acier | C1, C2 | 100.0 | 3971 | 1509 |
| J09 | industrie | expert | 5 | production,maintenance,pilotage | non | 1 | aucun aléa | C1, C2, C9 | 100.0 | 3771 | 1377 |
| J10 | industrie | expert | 12 | pilotage,production,maintenance | non | 1 | usine chargée à  ubs  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ou | C1, C2, C9 | 93.3 | 6092 | 1524 |

Latence (ms) : médiane 4224, max 6092 ; tokens : médiane 1446, max 1524
