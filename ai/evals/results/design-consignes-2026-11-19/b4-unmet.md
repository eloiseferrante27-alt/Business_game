# factory.design, respect des consignes - b4-unmet - 2026-11-19

Modèle : qwen2.5:3b - prompt v4 - 10 conceptions - garde-fou coupé

- Respect : 41/50 (niveau 9/10, ton 9/10, aleas 8/10, secteur 9/10, unmet 6/10)
- Latence : médiane 4080.0 ms, max 7449 ms ; chargement du modèle 150 ms au total
- Tokens par conception : entrée médiane 1240, sortie médiane 188
- Replis : 0 ; essais > 1 : 0
- Ollama /api/ps après la série : [{"name": "qwen2.5:3b", "size": 2331886223, "size_vram": 2331886223, "context_length": 6144}]

| Jeu | niveau | ton | aleas | secteur | unmet | Total | ms | Essais | Niveau | Ton | Aléas (niveau, plan) | unmet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J01 | ok | ok | ok | ok | ok | 5/5 | 3648 | 1 | decouverte | mixte | aucun (4 sem.) - | - |
| J02 | ok | ok | NON | ok | NON | 3/5 | 4001 | 1 | expert | exigeant | rares (12 sem.) s2:retard_transport,s3:hausse_matieres,s4:commande_exceptionnelle | maintenance |
| J03 | ok | ok | ok | ok | ok | 5/5 | 4159 | 1 | equilibre | mixte | rares (12 sem.) - | - |
| J04 | ok | ok | ok | ok | ok | 5/5 | 3804 | 1 | decouverte | mixte | rares (12 sem.) - | - |
| J05 | ok | ok | ok | ok | ok | 5/5 | 4217 | 1 | decouverte | mixte | rares (12 sem.) - | - |
| J06 | ok | ok | NON | ok | ok | 4/5 | 4409 | 1 | expert | exigeant | aucun (12 sem.) - | - |
| J07 | ok | NON | ok | ok | NON | 3/5 | 1262 | 1 | equilibre | mixte | rares (12 sem.) - | maintenance |
| J08 | NON | ok | ok | ok | ok | 4/5 | 3374 | 1 | expert | exigeant | rares (12 sem.) s11:vague_de_chaleur,s12:hausse_matieres | - |
| J09 | ok | ok | ok | ok | NON | 4/5 | 5479 | 1 | expert | exigeant | rares (5 sem.) - | - |
| J10 | ok | ok | ok | NON | NON | 3/5 | 7449 | 1 | expert | mixte | rares (12 sem.) s2:retard_transport,s3:hausse_matieres,s4:commande_exceptionnelle | - |
