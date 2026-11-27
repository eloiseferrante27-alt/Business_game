# Évaluation de l'équipe d'agents

Savoir, sur des mesures, si l'équipe travaille bien et à quel coût, puis la corriger par petites propositions prouvées.

| Question | Réponse |
|---|---|
| Quand | À la demande de l'utilisateur, ou en fin de gros chantier (au moins trois agents impliqués). Jamais en continu. |
| Comment | `.\scripts\team.ps1 -Report [-Since AAAA-MM-JJ] [-Session <id>]` (80 lignes au plus ; seules les éditions Edit, Write et NotebookEdit sont vues), puis l'agent `coach-equipe`, qui ne lit aucun transcript brut. |
| Détail d'un run | `.\scripts\team.ps1 -Run <agentId>` ; sa section « Erreurs d'outil » liste une erreur par ligne (outil + 120 premiers caractères, masqués). `-Json` ajoute par run la clé `tool_error_details`. Attention : un « PowerShell : Exit code 1 » est souvent du stderr de Docker, pas un échec de code. |
| Où lire | `docs/equipe/retro-AAAA-MM-JJ.md` : indicateurs, trois problèmes prouvés au plus, une proposition chacun. |
| Propriété | `.claude/ownership.json`, contrôlé par `.\scripts\team.ps1 -CheckOwners`. |

- **Rien n'est appliqué sans l'accord de l'utilisateur.** Après accord, `documentaliste` applique et note la décision (appliquée ou rejetée) dans la rétro.
- Le processus est jugé, pas le produit (ergonomie et justesse pédagogique : utilisateur et `game-designer`).
- Aucun garde-fou (porte qualité, interdictions de .claude/settings.json, secrets, volumes Docker) n'est affaibli sans décision explicite de l'utilisateur.
