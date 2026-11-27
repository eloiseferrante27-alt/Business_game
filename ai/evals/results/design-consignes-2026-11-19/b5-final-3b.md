# factory.design, respect des consignes - b5-final-3b - 2026-11-19

Modèle : qwen2.5:3b - prompt v4 - 10 conceptions - garde-fou actif

- Respect : 39/50 (niveau 9/10, ton 9/10, aleas 7/10, secteur 9/10, unmet 5/10)
- Latence : médiane 6765.0 ms, max 8275 ms ; chargement du modèle 174 ms au total
- Tokens par conception : entrée médiane 1222, sortie médiane 210
- Replis : 0 ; essais > 1 : 0
- Ollama /api/ps après la série : [{"name": "qwen2.5:3b", "size": 2331886223, "size_vram": 2331886223, "context_length": 6144}]

| Jeu | niveau | ton | aleas | secteur | unmet | Total | ms | Essais | Niveau | Ton | Aléas (niveau, plan) | unmet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J01 | ok | ok | ok | ok | ok | 5/5 | 6457 | 1 | decouverte | mixte | aucun (4 sem.) - | - |
| J02 | ok | ok | NON | ok | NON | 3/5 | 7154 | 1 | expert | exigeant | rares (12 sem.) s2:retard_transport,s4:hausse_matieres,s6:lot_mp_non_conforme | maintenance |
| J03 | ok | ok | ok | ok | ok | 5/5 | 6960 | 1 | equilibre | mixte | rares (12 sem.) s2:retard_transport,s4:hausse_matieres,s6:commande_exceptionnelle | - |
| J04 | ok | ok | ok | ok | NON | 4/5 | 6827 | 1 | decouverte | mixte | rares (12 sem.) - | maintenance |
| J05 | ok | ok | ok | ok | ok | 5/5 | 5279 | 1 | decouverte | mixte | rares (8 sem.) - | - |
| J06 | ok | ok | NON | ok | ok | 4/5 | 6703 | 1 | expert | exigeant | rares (12 sem.) s2:retard_transport,s3:hausse_matieres,s4:commande_exceptionnelle | - |
| J07 | ok | NON | ok | ok | NON | 3/5 | 1531 | 1 | equilibre | mixte | rares (12 sem.) s2:retard_transport,s4:hausse_matieres,s6:commande_exceptionnelle | maintenance |
| J08 | NON | ok | NON | ok | ok | 3/5 | 5598 | 1 | expert | exigeant | frequents (12 sem.) s2:retard_transport,s5:hausse_matieres,s8:commande_exceptionnelle | - |
| J09 | ok | ok | ok | ok | NON | 4/5 | 8101 | 1 | expert | exigeant | rares (5 sem.) s2:retard_transport,s3:hausse_matieres,s4:commande_exceptionnelle | - |
| J10 | ok | ok | ok | NON | NON | 3/5 | 8275 | 1 | expert | mixte | rares (12 sem.) - | - |
