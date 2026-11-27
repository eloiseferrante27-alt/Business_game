# factory.design, respect des consignes - a-3b-v3 - 2026-11-19

Modèle : qwen2.5:3b - prompt v3 - 10 conceptions - garde-fou coupé

- Respect : 30/50 (niveau 5/10, ton 7/10, aleas 8/10, secteur 9/10, unmet 1/10)
- Latence : médiane 3926.5 ms, max 8368 ms ; chargement du modèle 119 ms au total
- Tokens par conception : entrée médiane 1194, sortie médiane 226
- Replis : 0 ; essais > 1 : 0
- Ollama /api/ps après la série : [{"name": "qwen2.5:3b", "size": 2331886223, "size_vram": 2331886223, "context_length": 6144}]

| Jeu | niveau | ton | aleas | secteur | unmet | Total | ms | Essais | Niveau | Ton | Aléas (niveau, plan) | unmet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J01 | NON | NON | ok | ok | NON | 2/5 | 3057 | 1 | expert | exigeant | aucun (4 sem.) - | aucun produit non conforme |
| J02 | ok | ok | NON | ok | NON | 3/5 | 3754 | 1 | expert | exigeant | rares (12 sem.) s2:retard_transport,s4:hausse_matieres,s6:commande_exceptionnelle | aucun équipement spécifique à l'industrie automobile |
| J03 | NON | ok | ok | ok | NON | 3/5 | 4414 | 1 | expert | exigeant | rares (12 sem.) s2:retard_transport,s3:hausse_matieres,s4:commande_exceptionnelle | aucun aléa |
| J04 | NON | ok | ok | ok | ok | 4/5 | 3509 | 1 | expert | exigeant | rares (12 sem.) - | - |
| J05 | ok | NON | ok | ok | NON | 3/5 | 3966 | 1 | decouverte | exigeant | rares (5 sem.) s2:retard_transport,s3:hausse_matieres,s4:creux_de_demande | pas de fournisseur spécialisé dans l'automobile |
| J06 | ok | ok | ok | ok | NON | 4/5 | 3887 | 1 | expert | exigeant | frequents (12 sem.) s2:retard_transport,s4:hausse_matieres,s6:commande_exceptionnelle | l'usine ne sait pas simuler les perturbations des fournisseurs |
| J07 | NON | NON | ok | ok | NON | 2/5 | 1876 | 1 | expert | exigeant | rares (12 sem.) s2:retard_transport,s3:hausse_matieres,s4:commande_exceptionnelle | la formation ne peut pas être intégralement réalisée sans un atelier de soudure d'équipements en acier |
| J08 | NON | ok | NON | ok | NON | 2/5 | 4504 | 1 | expert | exigeant | rares (12 sem.) s2:retard_transport,s4:hausse_matieres,s6:commande_exceptionnelle | aucun des secteurs de l'industrie automobile ne peut être complètement reproduit dans une usine de soudures en |
| J09 | ok | ok | ok | ok | NON | 4/5 | 4989 | 1 | expert | exigeant | rares (5 sem.) - | aucun aléa |
| J10 | ok | ok | ok | NON | NON | 3/5 | 8368 | 1 | expert | exigeant | frequents (12 sem.) s2:retard_transport,s3:hausse_matieres,s4:commande_exceptionnelle | usine chargée à  ubs  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough  ough |
