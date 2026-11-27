# factory.design, respect des consignes - b2-guidage - 2026-11-19

Modèle : qwen2.5:3b - prompt v4 - 10 conceptions - garde-fou coupé

- Respect : 39/50 (niveau 9/10, ton 9/10, aleas 7/10, secteur 8/10, unmet 6/10)
- Latence : médiane 4802.0 ms, max 9554 ms ; chargement du modèle 156 ms au total
- Tokens par conception : entrée médiane 1287, sortie médiane 200
- Replis : 0 ; essais > 1 : 0
- Ollama /api/ps après la série : [{"name": "qwen2.5:3b", "size": 2331886223, "size_vram": 2331886223, "context_length": 6144}]

| Jeu | niveau | ton | aleas | secteur | unmet | Total | ms | Essais | Niveau | Ton | Aléas (niveau, plan) | unmet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J01 | ok | ok | ok | ok | ok | 5/5 | 4342 | 1 | decouverte | mixte | aucun (4 sem.) - | - |
| J02 | ok | ok | NON | ok | NON | 3/5 | 5052 | 1 | expert | exigeant | rares (12 sem.) s2:retard_transport,s4:hausse_matieres,s6:commande_exceptionnelle | marketing department |
| J03 | ok | ok | ok | ok | ok | 5/5 | 5257 | 1 | equilibre | mixte | rares (10 sem.) - | - |
| J04 | ok | ok | ok | ok | ok | 5/5 | 5736 | 1 | decouverte | mixte | rares (12 sem.) - | - |
| J05 | ok | ok | ok | ok | ok | 5/5 | 4142 | 1 | decouverte | mixte | rares (12 sem.) - | - |
| J06 | ok | ok | NON | NON | ok | 3/5 | 4552 | 1 | expert | exigeant | rares (4 sem.) - | - |
| J07 | ok | NON | ok | ok | NON | 3/5 | 1178 | 1 | equilibre | mixte | rares (10 sem.) - | marketing department |
| J08 | NON | ok | NON | ok | NON | 2/5 | 4546 | 1 | expert | exigeant | rares (12 sem.) s2:retard_transport,s4:hausse_matieres,s6:commande_exceptionnelle | marketing department |
| J09 | ok | ok | ok | ok | ok | 5/5 | 9554 | 1 | expert | exigeant | frequents (5 sem.) s2:retard_transport,s3:hausse_matieres,s4:creux_de_demande | marketing digital / campagnes réseaux sociaux |
| J10 | ok | ok | ok | NON | NON | 3/5 | 6719 | 1 | expert | mixte | rares (12 sem.) s2:retard_transport,s3:hausse_matieres,s4:commande_exceptionnelle | - |
