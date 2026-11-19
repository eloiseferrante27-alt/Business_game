# factory.design, respect des consignes - b1-brief-en-fin - 2026-11-19

Modèle : qwen2.5:3b - prompt v4 - 10 conceptions - garde-fou coupé

- Respect : 33/50 (niveau 6/10, ton 9/10, aleas 6/10, secteur 8/10, unmet 4/10)
- Latence : médiane 5013.5 ms, max 12331 ms ; chargement du modèle 241 ms au total
- Tokens par conception : entrée médiane 1198, sortie médiane 214
- Replis : 0 ; essais > 1 : 1
- Ollama /api/ps après la série : [{"name": "qwen2.5:3b", "size": 2331886223, "size_vram": 2331886223, "context_length": 6144}]

| Jeu | niveau | ton | aleas | secteur | unmet | Total | ms | Essais | Niveau | Ton | Aléas (niveau, plan) | unmet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J01 | ok | ok | ok | ok | ok | 5/5 | 3783 | 1 | decouverte | mixte | aucun (4 sem.) - | - |
| J02 | ok | ok | ok | ok | NON | 4/5 | 4988 | 1 | expert | exigeant | frequents (12 sem.) s2:retard_transport,s3:hausse_matieres,s4:commande_exceptionnelle | aucun équipement spécifique à l'usine de production automobile n'est spécifié dans le catalogue |
| J03 | NON | ok | NON | ok | ok | 3/5 | 5039 | 1 | decouverte | mixte | aucun (10 sem.) - | - |
| J04 | NON | ok | ok | NON | NON | 2/5 | 12331 | 2 | expert | exigeant | rares (10 sem.) - | ne pas simuler les aléas liés aux étudiants en licence |
| J05 | ok | ok | ok | ok | NON | 4/5 | 5975 | 1 | decouverte | mixte | rares (12 sem.) s2:retard_transport,s4:hausse_matieres,s6:commande_exceptionnelle | aucun équipement en acier non défectueux |
| J06 | ok | ok | NON | ok | ok | 4/5 | 4030 | 1 | expert | exigeant | aucun (10 sem.) - | - |
| J07 | NON | NON | NON | ok | NON | 1/5 | 1313 | 1 | decouverte | mixte | aucun (10 sem.) - | aucun équipement spécifique |
| J08 | NON | ok | NON | ok | ok | 3/5 | 2856 | 1 | expert | exigeant | aucun (12 sem.) - | - |
| J09 | ok | ok | ok | ok | NON | 4/5 | 9141 | 1 | expert | exigeant | rares (5 sem.) - | usine chargée à  ouch  ouch  ouch  ouch  ouch  ouch  ouch  ouch  ouch  ouch  ouch  ouch  ouch  ouch  ouch  ouc |
| J10 | ok | ok | ok | NON | NON | 3/5 | 8739 | 1 | expert | exigeant | rares (4 sem.) - | - |
