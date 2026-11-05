# factory.design - 2026-11-05

Modèle : qwen2.5:3b - prompt v2 - 12 appels (12 cas)

- Valides du premier coup : 8/12 ; après réparation : 2 ; replis : 2/12
- Attentes satisfaites : 10/12
- Latence (appels au modèle) : médiane 10388.5 ms, max 26451 ms
- Tokens par appel : entrée médiane 1082, sortie médiane 275

| Cas | Attente | Repli | Essais | ms | Raisons |
|---|---|---|---|---|---|
| D01 | oui | non | 1 | 7194 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 12, "events": "frequents", "tunings": {}, "event_plan": [{"week": 2, "event_id": "retard_transport"}, {"week": 3, "event_id": "hausse_matieres"}, {"week": 4, "event_id": "commande_exceptionn |
| D02 | oui | non | 1 | 6638 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "decouverte", "weeks": 4, "events": "rares", "tunings": {}, "event_plan": []} |
| D03 | oui | non | 2 | 26451 | tentative 1 : OllamaError (/api/chat -> HTTP 500: {"error":"prediction aborted, token repeat limit reached"}) |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "decouverte", "weeks": 12, "events": "rares", "tunings": {}, "event_plan": [{"week": 2, "event_id": "retard_transport"}, {"week": 4, "event_id": "hausse_matieres"}, {"week": 6, "event_id": "commande_exceptionn |
| D04 | oui | non | 1 | 11679 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 12, "events": "rares", "tunings": {}, "event_plan": [{"week": 2, "event_id": "retard_transport"}, {"week": 4, "event_id": "hausse_matieres"}, {"week": 6, "event_id": "commande_exceptionnelle |
| D05 | NON | non | 1 | 8588 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 12, "events": "rares", "tunings": {"mtbf_factor": "decouverte"}, "event_plan": []} |
| D06 | oui | non | 1 | 11594 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 4, "events": "frequents", "tunings": {}, "event_plan": [{"week": 2, "event_id": "retard_transport"}, {"week": 3, "event_id": "hausse_matieres"}, {"week": 4, "event_id": "commande_exceptionne |
| D07 | oui | non | 1 | 8914 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "decouverte", "weeks": 4, "events": "aucun", "tunings": {}, "event_plan": []} |
| D08 | oui | non | 2 | 20124 | tentative 1 : params : Value error, plan d'aléas : retard_transport ne touche aucun module joué; plan d'aléas : hausse_matieres ne touche aucun module joué |
|  | params | | | | {"theme": "industrie", "modules": ["production", "maintenance"], "difficulty": "decouverte", "weeks": 12, "events": "rares", "tunings": {}, "event_plan": []} |
| D09 | NON | non | 1 | 11743 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "expert", "weeks": 12, "events": "frequents", "tunings": {"mtbf_factor": "decouverte"}, "event_plan": [{"week": 2, "event_id": "retard_transport"}, {"week": 4, "event_id": "hausse_matieres"}, {"week": 6, "even |
| D10 | oui | oui | 0 | 0 | brief écarté : tentative d'injection détectée, paramètres par défaut |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "equilibre", "weeks": 6, "events": "rares", "tunings": {}, "event_plan": []} |
| D11 | oui | oui | 0 | 0 | brief écarté : tentative d'injection détectée, paramètres par défaut |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "equilibre", "weeks": 6, "events": "rares", "tunings": {}, "event_plan": []} |
| D12 | oui | non | 1 | 9183 |  |
|  | params | | | | {"theme": "industrie", "modules": ["pilotage", "production", "maintenance"], "difficulty": "decouverte", "weeks": 12, "events": "rares", "tunings": {}, "event_plan": []} |
