# factory.design, respect des consignes - b6-final-3b - 2026-11-19

Modèle : qwen2.5:3b - prompt v4 - 10 conceptions - garde-fou actif

- Respect : 42/50 (niveau 9/10, ton 9/10, aleas 8/10, secteur 9/10, unmet 7/10)
- Latence : médiane 5265.5 ms, max 7334 ms ; chargement du modèle 212 ms au total
- Tokens par conception : entrée médiane 1197, sortie médiane 192
- Replis : 0 ; essais > 1 : 0
- Ollama /api/ps après la série : [{"name": "qwen2.5:3b", "size": 2331886223, "size_vram": 2331886223, "context_length": 6144}]

| Jeu | niveau | ton | aleas | secteur | unmet | Total | ms | Essais | Niveau | Ton | Aléas (niveau, plan) | unmet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J01 | ok | ok | ok | ok | ok | 5/5 | 5136 | 1 | decouverte | mixte | aucun (4 sem.) - | - |
| J02 | ok | ok | NON | ok | ok | 4/5 | 5067 | 1 | expert | exigeant | rares (12 sem.) s2:retard_transport,s3:hausse_matieres,s4:lot_mp_non_conforme | - |
| J03 | ok | ok | ok | ok | ok | 5/5 | 5389 | 1 | equilibre | mixte | rares (12 sem.) - | - |
| J04 | ok | ok | ok | ok | ok | 5/5 | 5142 | 1 | decouverte | mixte | rares (12 sem.) - | - |
| J05 | ok | ok | ok | ok | ok | 5/5 | 6514 | 1 | decouverte | mixte | rares (12 sem.) - | - |
| J06 | ok | ok | ok | ok | ok | 5/5 | 6706 | 1 | expert | exigeant | frequents (12 sem.) s2:retard_transport,s3:hausse_matieres,s4:commande_exceptionnelle | - |
| J07 | ok | NON | ok | ok | NON | 3/5 | 1922 | 1 | equilibre | mixte | rares (12 sem.) - | maintenance |
| J08 | NON | ok | NON | ok | ok | 3/5 | 3786 | 1 | expert | exigeant | rares (12 sem.) - | - |
| J09 | ok | ok | ok | ok | NON | 4/5 | 7169 | 1 | expert | exigeant | rares (5 sem.) - | - |
| J10 | ok | ok | ok | NON | NON | 3/5 | 7334 | 1 | expert | mixte | rares (12 sem.) - | - |
