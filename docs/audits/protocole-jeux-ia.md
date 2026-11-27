# Protocole de relecture de 10 jeux conçus par l'IA (pack usine)

Propriétaire : game-designer. Exécution : ia-runtime. Version 1 du 19/11/2026.
Critère visé : « 10 jeux conçus, relus et signés » (ADR 0010 §6, étape 8 ; ADR 0012, décision 4 ; exigence n° 1).

Chaîne relue : `design_factory` (tâche `factory.design`, prompt v3, backend/gmix/llm/factory_design.py), puis
`generation.generate` (vers `factory_generation.generate_factory`), puis `engine` (`start`, `advance`, `force_event`,
`public_state`, `debrief`). Données : ai/packs/usine.yaml ; corpus : knowledge/supply-chain (SOURCES.md).

Ce que la conception choisit : seulement des paramètres `GameParams` dans les listes du pack (secteur, modules,
difficulté, réglages, aléas, plan d'aléas, ton, agent en plus, réseau, lignes). Tous les textes vus par le joueur
viennent du pack ou du moteur, sauf `unmet` (demandes non couvertes, écrites par le modèle). La relecture porte
donc sur deux choses : les choix du modèle sont-ils justes pour le brief, et le jeu assemblé dit-il vrai ?

## 1. Les 10 jeux

Graine : la même sert au modèle (`seed` de `design_factory`) et au jeu (`GameParams.seed`). Régénération (J07,
J08) : comme le worker (`workers/generation.py`, `_keep`), `keep` = paramètres du jeu d'origine moins les clés de
`FACTORY_SECTIONS[section]`, graine du jeu comprise (elle ne change pas) ; la graine indiquée est celle du modèle.

| Id | Secteur attendu | Durée | Niveau | Aléas | Imposé (`fixed`) | Risque visé |
|---|---|---|---|---|---|---|
| J01 | industrie | 4 (court) | découverte | aucun | weeks, events | jeu sans aléa ; aléa forcé par le formateur |
| J02 | automobile | 12 (long) | expert | fréquents | theme, difficulty, weeks | partie longue, fournisseurs peu fiables |
| J03 | industrie | libre | équilibré | rares | company_name, products | nom imposé repris tel quel |
| J04 | libre | libre | libre | libre | modules sans pilotage | cas D02 : aléa sur un module non joué |
| J05 | automobile | libre | découverte | libre | theme, modules = pilotage, difficulty | aléas machines exclus |
| J06 | industrie | libre (long attendu) | équilibré | fréquents | options.lines = 3, agent_tone | trois lignes, ton exigeant |
| J07 | = J03 | = J03 | = J03 | = J03 | régénération « personnages » + note | consigne libre, reste intact |
| J08 | = J02 | = J02 | à revoir | à revoir | régénération « objectifs » + note | aléas en fin de partie, plus indulgent |
| J09 | industrie | 5 (court) | expert | libre | difficulty, weeks | demande hors périmètre : `unmet` |
| J10 | automobile | libre | libre | libre | company_name, products | brief chiffré : aucun chiffre repris |

Entrées exécutables (une ligne JSON par jeu, à copier dans un fichier d'entrées d'ia-runtime ; `regen.from` :
jeu dont on reprend les paramètres finaux) :

```jsonl
{"id": "J01", "seed": 101, "brief": "Séance découverte pour des lycéens en forum des métiers : une PME qui soude des équipements en acier pour un distributeur de bricolage, sans mauvaise surprise.", "fixed": {"weeks": 4, "events": "aucun"}}
{"id": "J02", "seed": 202, "brief": "Des managers d'un sous-traitant automobile veulent un défi dur sur l'approvisionnement : fournisseurs peu fiables, stocks bas, pannes fréquentes et beaucoup d'aléas.", "fixed": {"theme": "automobile", "difficulty": "expert", "weeks": 12}}
{"id": "J03", "seed": 303, "brief": "Former des BTS au goulot d'étranglement dans un atelier de soudure d'équipements en acier, avec un niveau moyen et quelques aléas.", "fixed": {"company_name": "Soudures de l'Estuaire", "products": 1}}
{"id": "J04", "seed": 404, "brief": "Des étudiants en licence doivent comprendre la maintenance préventive et pourquoi les pannes arrêtent les lignes ; les achats ne sont pas le sujet.", "fixed": {"modules": ["production", "maintenance"]}}
{"id": "J05", "seed": 505, "brief": "Premier cours d'approvisionnement chez un sous-traitant automobile : point de commande et choix du fournisseur, en douceur, avec la directrice du site pour guider.", "fixed": {"theme": "automobile", "modules": ["pilotage"], "difficulty": "decouverte"}}
{"id": "J06", "seed": 606, "brief": "Cours de gestion des stocks en master : le stock de sécurité face à une demande qui varie beaucoup, aléas fréquents, une partie longue sur une grande usine.", "fixed": {"options": {"lines": 3}, "agent_tone": "exigeant"}}
{"id": "J07", "seed": 707, "brief": "Former des BTS au goulot d'étranglement dans un atelier de soudure d'équipements en acier, avec un niveau moyen et quelques aléas.", "regen": {"from": "J03", "section": "personnages", "note": "Des collègues plus bienveillants, qui encouragent les débutants."}}
{"id": "J08", "seed": 808, "brief": "Des managers d'un sous-traitant automobile veulent un défi dur sur l'approvisionnement : fournisseurs peu fiables, stocks bas, pannes fréquentes et beaucoup d'aléas.", "regen": {"from": "J02", "section": "objectifs", "note": "Plus indulgent : des pannes rares, et des aléas seulement dans les dernières semaines."}}
{"id": "J09", "seed": 909, "brief": "Jeu court pour des ingénieurs : une usine d'équipements en acier, avec en plus un module de marketing digital et des campagnes sur les réseaux sociaux.", "fixed": {"difficulty": "expert", "weeks": 5}}
{"id": "J10", "seed": 1010, "brief": "Trois lignes de production chez un équipementier automobile, un objectif de 98 % de livraisons à l'heure et 20 000 euros de trésorerie à la fin.", "fixed": {"company_name": "Mécanique du Bocage", "products": 1}}
```

Noms d'entreprise imposés : fictifs, choisis pour le test. `products` vaut 1 (seule valeur du pack usine,
`limits.products: [1, 1, 1]`) ; une autre valeur doit être refusée par `DesignRequest` (contrôle à part, hors des 10).

## 2. Exécution (ia-runtime)

Pour chaque entrée, dans cet ordre (fermer Godot avant : GPU) :

1. Conception : `design_factory(llm, brief, seed=seed, pack_id="usine", keep=fixed)` ; régénération :
   `keep` = `spec["params"]` du jeu `from` moins `FACTORY_SECTIONS[section]`, `note=note`. Repli (`fallback`
   vrai) : relancer avec `seed + 100`, deux fois au plus, et noter chaque essai ; trois replis = jeu refusé.
2. Jeu : `spec = generate(GameParams(**design.params))` ; revue comme le worker : `autopilot_check(spec)`,
   `unsourced(spec)`.
3. Semaine 1 : `state = engine.start(spec, engine.initial_state(spec))`, puis `engine.public_state(spec, state)`.
4. Semaine avec aléa : rejouer en pilote automatique (`advance(..., autopilot_all=True)`) et prendre la première
   vue dont `event` n'est pas vide. Aucune (J01, ou pas de tirage) : depuis la semaine 2,
   `engine.force_event(spec, state, <premier id de spec["events"]>)`, puis la vue (`forced: true`).
5. Pilote automatique : partie complète (`advance(..., autopilot_all=True)` jusqu'à `finished`), puis
   `engine.debrief(spec, state)`.
6. Joueur passif : partie complète avec `held_roles` = tous les rôles de la spec et aucune action, puis les
   `criteria` de `engine.debrief`.

Fichiers, dans `ai/evals/results/jeux-ia-<AAAA-MM-JJ>/<Id>/` :

| Fichier | Contenu |
|---|---|
| `entree.json` | la ligne d'entrée ; pour J07 et J08, le `keep` réellement envoyé |
| `design.json` | `FactoryDesign` complet : params, fallback, reasons, attempts, unmet, model, prompt_version, tokens, duration_ms, brief_sha256 ; essais en repli compris |
| `spec.json` | la spec validée, telle que stockée |
| `textes.md` | les textes tels que le joueur les lit, dans l'ordre de l'écran : `meta.title`, `meta.pitch` ; `game_rules[]` (texte et citation) ; `criteria[]` ; modules (titre, description, `autopilot`) ; agents (nom, métier, caractère, personnalité, tâches) ; notions (titre, texte, citation) ; aléas (titre, description, modules) ; tutoriel ; libellés des offres et des lignes ; `unmet` ; `unsourced` (vue formateur) |
| `briefings-s1.json` | semaine, `event`, `briefings` (faits, `urgent`, `line` par agent), `alerts` |
| `briefings-alea.json` | idem pour la semaine avec aléa, plus `forced` |
| `debrief-pilote.json` | sortie complète de `engine.debrief` (kpis, history, lessons, notions, events, criteria, unsourced) |
| `criteres-passif.json` | `criteria` du joueur passif |
| `controles.json` | contrôles automatiques C3, C5, C7, C8 et pré-appariement C1 (ci-dessous) |

Plus un `index.md` : une ligne par jeu (id, secteur, produit, niveau, semaines, modules, repli, essais, durée,
`playable`, nombre de contrôles automatiques en échec). Répliques d'agents (`npc.dialogue`, outil d'eval_dialogue) :
facultatives ; si elles sont produites (une par agent, semaine 1, message « Où en est-on ? »), elles entrent dans C3.

## 3. Grille de vérification

« Auto » : ia-runtime le calcule dans `controles.json` ; « Lu » : game-designer le vérifie à la lecture.
Bloquant : un échec rend le jeu refusé (§ 4).

| Id | Critère | Méthode | Bloquant |
|---|---|---|---|
| C1 | Chaque chiffre est traçable dans le pack ou dans simulation.yaml, ou calculé par le moteur | Auto : extraire tous les nombres de `textes.md`, des briefings, des alertes et des leçons ; chercher chacun, à la précision affichée (format français : « 20 000 », « 0,7 »), dans le pack aplati, la spec et l'état ; écrire le chemin trouvé ou « non trouvé ». Lu : chaque « non trouvé » ; une valeur `calibre` ou `exemple` doit figurer dans `unsourced` | oui si un chiffre reste sans origine |
| C2 | Chaque notion est reliée à une fiche source exacte | Auto : la citation de chaque notion, règle et alerte citée égale la ligne « > Source : » d'une fiche de knowledge/supply-chain déclarée dans SOURCES.md. Lu : le texte de la notion est dit par la fiche (ligne citée dans la fiche du jeu) | oui |
| C3 | Aucun nombre inventé dans les textes du modèle | Auto : `unmet` (et répliques s'il y en a) sans chiffre (`forbidden_in_text`) ni nombre en lettres (deux à mille, moitié, double, triple, pour cent). Lu : aucune quantité implicite (« la plupart », « deux fois plus ») présentée comme un fait | oui |
| C4 | Aucun fait qui contredit le moteur | Lu, sur les points connus : (a) l'usine livre en retard, elle ne perd pas de vente : aucun texte ne dit « vente perdue » ; (b) `meta.pitch` reprend `difficulties.<niveau>.detail` (charge, délai promis) : il doit rester vrai si `tunings` change `load` ou `promised_days` ; (c) l'alerte de trésorerie ne propose pas l'action `decouvert` (pas de module finance dans l'usine) et n'annonce aucun agio ; (d) l'alerte « Aléa annoncé pour la semaine qui vient » et le briefing « Cette semaine, … » visent la même semaine simulée ; (e) les cibles des `game_rules` égalent `targets` ; (f) `unmet` ne déclare pas absent ce que le jeu simule, ni l'inverse ; (g) la règle `pilote_automatique` décrit ce que fait le pilote du journal | oui |
| C5 | Vouvoiement et ton | Auto : aucun « tu, te, toi, ton, ta, tes » adressé au joueur dans les textes et briefings. Lu : registre professionnel ; préfixes des personnalités cohérents avec `agent_tone` ; sigles expliqués à leur première apparition (OTIF, TRS, MP, PF) | non |
| C6 | Cohérence secteur et produits | Lu : le secteur suit le brief ; produit, matière, fournisseurs et client viennent du même `themes.<secteur>` ; nom imposé repris à l'identique, sinon pris dans `companies` ; prix > coût de transformation + coût de la matière de l'offre standard ; aléa « Hausse de l'acier » cohérent avec la matière (toutes en acier au 19/11) | non |
| C7 | Les aléas touchent un module joué (cas D02) | Auto : chaque aléa de `spec.events` et de `params.event_plan` a au moins un module de `spec.modules` ; la semaine avec aléa, au moins un agent de module joué (ou fournisseur, direction) le reçoit dans ses faits ; aucun aléa planifié après la dernière semaine ; `events: aucun` implique un `event_plan` vide et aucun aléa tiré dans `history` (hors aléa forcé) | oui |
| C8 | Contraintes du formateur respectées | Auto : chaque clé de `fixed` (ou de `keep`) est identique dans `design.params` ; en régénération, seules les clés de la section changent, graine du jeu comprise. Lu : la `note` est suivie dans son esprit (J07 : ton bienveillant ; J08 : moins de pannes et aléas tardifs) | oui |
| C9 | Jouabilité | Auto : `autopilot_check.playable` vrai ; en découverte, tous les critères du pilote atteints ; en expert, au moins un partiel admis ; le joueur passif manque au moins un critère | oui si le pilote ou le passif ne suit pas la règle |
| C10 | Choix pédagogiques justes pour le brief | Lu : modules, niveau, aléas et réglages servent le sujet du brief ; chaque `tunings` enseigne une notion du brief (`tunables.*.teaches`) ; leçons du débrief reliées à un indicateur observé | non |

## 4. Verdicts

- **Conforme** : aucun critère bloquant en échec ; remarques non bloquantes écrites, sans correction exigée.
- **À corriger avec le propriétaire** : un critère non bloquant en échec, ou un défaut corrigeable dans les données ou
  le code. La fiche nomme le propriétaire : pack et simulation.yaml, game-designer ; prompt et `factory_design.py`,
  ia-runtime ; moteur et génération, moteur-jeu ; rendu à l'écran, godot-dev. Après correction, le jeu est relancé
  avec la même entrée et la même graine, puis relu.
- **Refusé** : un critère bloquant en échec, ou trois replis. Le défaut va au propriétaire ; le jeu est remplacé par
  la même entrée avec `seed + 1000` une fois la cause corrigée, et la nouvelle partie est relue entièrement.

Seuls des jeux « conforme » entrent dans la liste signée ; il en faut 10, un par entrée.

## 5. Fiche d'un jeu (`docs/audits/jeux-ia/<Id>.md`)

```markdown
# <Id> : <meta.title>
Entrée : graine <n> · fixed <…> · regen <section, note ou « aucune »> · essais <n> · repli <oui/non>
Jeu : secteur <…> · produit <…> · niveau <…> · <n> semaines · modules <…> · lignes <n> · aléas <niveau, plan>
Résultats : ai/evals/results/jeux-ia-<date>/<Id>/ · pilote OTIF <…> %, TRS <…> %, ruptures <…>, trésorerie <…> € · passif <critères manqués>

| Critère | Résultat | Preuve (fichier, ligne, fiche du corpus) | Propriétaire si écart |
|---|---|---|---|
| C1 … C10 | ok / écart / sans objet | | |

Écarts : <numéro, description, citation exacte du texte fautif, correction demandée>
À vérifier : <points sans certitude, jamais tranchés par supposition>
Verdict : conforme | à corriger (<propriétaire>) | refusé
Relu par game-designer le <date>, sur les résultats du <date>.
```

## 6. Liste finale à signer (`docs/audits/liste-jeux-ia.md`)

```markdown
# Jeux conçus par l'IA, relus (exigence n° 1)
Pack usine (sha256 <…>) · prompt factory.design v<n> · modèle <nom Ollama> · résultats du <date>

| Id | Titre | Secteur | Niveau | Semaines | Aléas | Verdict | Fiche |
|---|---|---|---|---|---|---|---|
| J01 | … | … | … | … | … | conforme | jeux-ia/J01.md |

Défauts trouvés et corrigés : <liste courte, propriétaire, commit>
Limites connues : <ce que la relecture ne couvre pas : répliques libres des agents, rendu Godot>

Je certifie avoir pris connaissance de ces 10 jeux et de leurs fiches.
Nom : ____________  Date : ____________  Signature : ____________
```

La signature vaut pour la version du pack, du prompt et du modèle indiquée : un changement de l'un d'eux rouvre
la relecture des jeux concernés.
