# factory.design - 2026-11-06

Modèle : qwen2.5:3b - prompt v3 - 15 appels (15 cas)

- Valides du premier coup : 11/15 ; après réparation : 1 ; replis : 3/15
- Attentes satisfaites : 13/15
- Latence (appels au modèle) : médiane 4694 ms, max 13062 ms
- Tokens par appel : entrée médiane 1168, sortie médiane 220

| Cas | Attente | Repli | Essais | ms | Raisons |
|---|---|---|---|---|---|
| D01 | oui | non | 1 | 3750 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 12, "events": "rares", "tunings": {}, "event_plan": []} |
| D02 | oui | oui | 3 | 13062 | tentative 1 : params : Value error, plan d'aléas : retard_transport ne touche aucun module joué; plan d'aléas : hausse_matieres ne touche aucun module joué; pla |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "equilibre", "weeks": 6, "events": "rares", "tunings": {}, "event_plan": []} |
| D03 | oui | non | 1 | 5179 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "decouverte", "weeks": 12, "events": "frequents", "tunings": {}, "event_plan": [{"week": 2, "event_id": "retard_transport"}, {"week": 4, "event_id": "hausse_matieres"}, {"week": 6, "event_id": "commande_except |
| D04 | oui | non | 1 | 4570 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 12, "events": "rares", "tunings": {}, "event_plan": []} |
| D05 | oui | non | 1 | 4408 |  |
|  | params | | | | {"theme": "automobile", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 12, "events": "rares", "tunings": {"mtbf_factor": "decouverte"}, "event_plan": []} |
| D06 | NON | non | 1 | 4694 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 12, "events": "rares", "tunings": {}, "event_plan": []} |
| D07 | oui | non | 1 | 4815 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 4, "events": "rares", "tunings": {"mtbf_factor": "decouverte", "mp_stock_days": "decouverte", "pf_stock_days": "decouverte"}, "event_plan": []} |
| D08 | oui | non | 2 | 9712 | tentative 1 : params : Value error, plan d'aléas : retard_transport ne touche aucun module joué; plan d'aléas : hausse_matieres ne touche aucun module joué |
|  | params | | | | {"theme": "industrie", "modules": ["production"], "difficulty": "decouverte", "weeks": 10, "events": "rares", "tunings": {}, "event_plan": []} |
| D09 | NON | non | 1 | 6206 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 4, "events": "frequents", "tunings": {"mtbf_factor": "decouverte"}, "event_plan": [{"week": 2, "event_id": "retard_transport"}, {"week": 3, "event_id": "hausse_matieres"}, {"week": 4, "event |
| D10 | oui | oui | 0 | 0 | brief écarté : tentative d'injection détectée, paramètres par défaut |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "equilibre", "weeks": 6, "events": "rares", "tunings": {}, "event_plan": []} |
| D11 | oui | oui | 0 | 0 | brief écarté : tentative d'injection détectée, paramètres par défaut |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "equilibre", "weeks": 6, "events": "rares", "tunings": {}, "event_plan": []} |
| D12 | oui | non | 1 | 6178 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 12, "events": "rares", "tunings": {"mtbf_factor": "decouverte", "promised_days": "decouverte", "reliability_shift": "decouverte", "mp_stock_days": "decouverte", "pf_stock_days": "decouverte" |
| R01 | oui | non | 1 | 4684 |  |
|  | params | | | | {"theme": "automobile", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 6, "events": "rares", "tunings": {}, "event_plan": [{"week": 2, "event_id": "retard_transport"}, {"week": 4, "event_id": "hausse_matieres"}, {"week": 6, "event_id": "vague_de_chaleur"}]} |
| R02 | oui | non | 1 | 4563 |  |
|  | params | | | | {"theme": "automobile", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 6, "events": "rares", "tunings": {"mtbf_factor": "decouverte"}, "event_plan": [{"week": 2, "event_id": "retard_transport"}, {"week": 3, "event_id": "hausse_matieres"}, {"week": 4, "event_id |
| R03 | oui | non | 1 | 3468 | consigne écartée : tentative d'injection détectée |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 6, "events": "rares", "tunings": {"mtbf_factor": "decouverte"}, "event_plan": []} |
