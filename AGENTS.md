# AGENTS.md — G-MIX Business Game

Shared instructions for every AI coding agent working on this repo (Codex, Kimi, Claude).
**Read this whole file before touching any code. Update the "Task board" and "Handoff log" sections before you finish.**

---

## 1. What G-MIX is

G-MIX is a pedagogical business game: a trainer configures a world, a player runs a factory remotely from a **tablet**, and the engine simulates the consequences of the player's decisions.

- The **3D world is only the stage**. The game is played in the **tablet interfaces**: one page per department, each with three tabs: **KPIs**, **Outils** (tools), **Configurations**.
- The player has no office and no "Pilotage" department. They act only from the tablet.
- Suppliers and clients are **scenario variables**; in 3D you only see their trucks.
- The world must stay **modular**: changing the configuration file changes the world without touching code.

## 2. Reference documents (source of truth)

Put these in `docs/` (ask the human if they are missing — do not guess their content):

| File | Role |
|---|---|
| `docs/Mon monde v3 - blocs, agents et assets.md` | **Single reference** for the world: 8 blocks, agents, assets, parameters. v1 and v2 are dropped — ignore them. |
| `docs/Cahier des charges - configurations et interface.md` | **The spec you are implementing.** Engine + tablet interface for every department, rights system, tools, hazards (aléas), config file (Annexe A), deliverables (§24). |

If code and these docs disagree, **the docs win**. If the docs are silent or contradictory, do not invent: write the question in the Handoff log and in the gap report.

## 3. Current code (as of 2026-11-01)

```
backend/app/main.py        FastAPI: /, /health, /api/state, /api/new-game, /api/decisions, /api/next-turn
backend/app/simulation.py  SimulationEngine — advances WEEK by week; catalogs are HARD-CODED (SUPPLIER_CATALOG, PRODUCT_CATALOG, LINE_NAMES)
backend/app/models.py      Pydantic: KPIs, Supplier, Stock (PF), MaterialStock (MP), Machine, ProductionLine, GameState, requests
backend/app/agents.py      SupplierAgent, MarketAgent (2 random events), GMSClientAgent (client demand, OTIF)
backend/app/database.py    SQLite snapshot save/load → backend/data/gmix.db
backend/app/static/        game3d.html / game3d.js (three.js 3D world), index.html / game.js (2D), CSS
godot/                     Godot scenes/scripts (NPCs) — do not modify unless a task says so
COMMENT_JOUER.md           How the current version is played
```

Known gaps vs. the spec (to confirm in the gap report):
- Time unit is **weeks**; the spec wants an 8 h simulated day with ×1–×60 speed (open point §25 — see Decisions below).
- 4 lines × 4 different products; v3 says N identical lines making one product. Structure must accept both (`lignes_identiques` in config).
- No config file, no event journal, no rights (Verrouillé / Initial / Libre), no tablet pages, KPIs computed ad hoc instead of from a journal.
- Only 2 random events; the spec has a catalogue AL-01…AL-34 with 4 trigger modes.

## 4. Non-negotiable rules (from the spec, §1–§2)

1. **The engine computes.** KPIs, costs, lead times, throughput, routes: engine only. Never in the UI, never by an AI.
2. **Nothing hard-coded.** Values, rights, suppliers, clients, prices, delays come from the config file (Annexe A) or the engine.
3. **Additive only.** Never delete or rename an existing identifier, field, endpoint or parameter. Extend. Keep IDs `LINE-NN`, `Ln-Mk`, `SKU-NN`, `MAT-NN`, `SUP-NN`; new IDs follow `ZONE-TYPE-NN` (`EXT-FOUR-NN`, `EXT-OFFRE-NN`, `EXT-CLI-NN`, `REC-QUAI-01`…).
4. **Never invent** a parameter, state or value missing from the docs — flag it.
5. **Reproducible.** Every random draw uses the scenario seed (`random.Random(seed)`), never the global `random`.
6. **Everything goes through the journal.** Every state change = one journal entry (time, element, old state, new state, cause: `decision | regle | alea`). KPIs are computed from the journal.
7. **Rights are enforced on the server**, not only in the UI. Forbidden requests are rejected and logged.
8. **Engine before interface** for each department.
9. The current game must keep running after your change (`/api/state`, `/api/next-turn` still work).

## 5. Target structure (create additively)

```
config/world.yaml                 The Annexe A config file (one file = one world)
backend/app/engine/
    __init__.py
    config.py        load + validate world.yaml (§4 checks), states fixe / a_generer / desactive
    clock.py         simulated clock, pause, speed, time-jump (same seed ⇒ same journal)
    journal.py       append-only event journal + query helpers
    rights.py        verrouille / initial / libre, change limits, refusal messages (§5)
    alerts.py        open/close alerts, severity grave/mineure, status colour per block
    kpis.py          KPI functions reading ONLY the journal
    hazards.py       AL-xx catalogue, 4 trigger modes (manual, fixed time, condition, random)
    departments/
        suppliers.py  unloading_dock.py  reception.py  stock.py  production.py
        quality.py    packing.py  maintenance.py  logistics.py  clients.py
backend/app/api_tablet.py         new FastAPI router: /api/v2/... (keep old endpoints)
backend/app/static/tablet/        tablet UI: home, rules screen, 10 department pages, 5 tools
tests/                            pytest — every engine module gets tests
```

One department = one engine file + one UI page. **Only edit the files of the task you claimed**, plus shared files listed in the task.

## 6. Workflow between agents

- **Branches:** start from `contribution_amine`. One branch per task: `codex/T03-journal`, `kimi/T12-stock-ui`, `claude/...`. Open a PR into `contribution_amine`. Never push to `main`.
- **Claim before working:** set yourself as owner and status `in progress` in the Task board, commit that first.
- **Small PRs:** one task per PR, with tests. Run `pytest` before pushing.
- **Shared core files** (`engine/journal.py`, `engine/config.py`, `engine/rights.py`, `models.py`): change only within the task that owns them, or note the change clearly in the Handoff log so others can rebase.
- **When done:** set status `done`, write a Handoff log entry (what you did, what's left, open questions).
- **Stuck on a decision only the human can make:** status `blocked`, explain in the Handoff log, move to another task.
- Review: Amine (human) merges. Claude may be asked to review PRs against the spec.

## 7. Decisions already made

- v3 is the single reference; v1/v2 dropped.
- The cahier des charges replaces the older "module chaîne de production" and "interfaces de la tablette" docs.
- The tablet is the only player interface; touching a block in 3D opens its page.
- **Pending (human must decide — see T00):** time unit (proposed default: 8 h simulated day, period = 1 day), spreadsheet library vs home-made, map library (Leaflet suggested).

## 8. Task board

Status: `todo` · `in progress` · `blocked` · `review` · `done`. Owner is a suggestion — change it when you claim a task.

| ID | Task | Depends on | Suggested owner | Status |
|---|---|---|---|---|
| GAME-01 | User-requested playable game integration: live tablet API, real decisions, server refusals, event history, legacy compatibility and 3D tablet navigation | T06 | Codex | done |
| UI-01 | User-requested playable tablet: game interface, ten department pages, actual engine data/actions, responsive tools and 3D navigation | T06 | Kimi | done |
| T00 | Human decisions: time unit/period, spreadsheet lib, map lib (§25) | — | Amine | todo |
| T01 | **Gap report** (Livrable 1): inventory current code vs spec, list present / to complete / missing, map AL-03…AL-13 → `docs/rapport-ecart.md` | — | Codex | in progress |
| T02 | `config/world.yaml` from Annexe A + `engine/config.py` loader & §4 validations (MTTR<MTBF, reorder point, ≥2 offers per article, capacities) | T01 | Codex | todo |
| T03 | `engine/journal.py` + `engine/clock.py` (8 h day, ×1–×60, pause, time-jump, seed) | T00 | Codex | todo |
| T04 | `engine/rights.py` + server checks + refusal logging; `engine/alerts.py` | T02, T03 | Codex | todo |
| T05 | `engine/kpis.py` skeleton + `/api/v2` router (state, page data, set config, actions) | T03 | Codex | todo |
| T06 | Tablet shell: home page (§8), common page layout with 3 tabs (§6), red pop-up (4 s), "Règles de la partie" screen (§5) | T05 (can mock API first) | Kimi | done |
| T07 | Tools: spreadsheet, world map, charts (curve + Pareto), planning, journal viewer (§7) | T06 | Kimi | todo |
| T10 | Engine: Suppliers (§10) | T02–T05 | Codex | todo |
| T11 | Engine: Unloading dock (§11) + Reception (§12) | T10 | Codex | todo |
| T12 | Engine: Stock MP/semi/PF + kits + reorder (§13) | T03–T05 | Codex | todo |
| T13 | Engine: Production chain — machines, OF, bottleneck, buffers, breakdowns (§14) | T12 | Codex | todo |
| T14 | Engine: Quality (§15) + Packing (§16) | T13 | Codex | todo |
| T15 | Engine: Maintenance & PDR (§17) | T13 | Codex | todo |
| T16 | Engine: Logistics (§18) + Clients (§19) | T12 | Codex | todo |
| T20–T29 | UI page for each department (KPIs / Outils / Configurations / actions / alerts), one task per department, after its engine task | matching T1x + T06 | Kimi | todo |
| T30 | Hazards catalogue AL-01…AL-34 + 4 trigger modes (§21) | T10–T16 | Codex | todo |
| T31 | Interactions & chain effects (§20) end-to-end test | T10–T16 | Codex | todo |
| T32 | 3 demo scenarios (§24 Livrable 5) + success criteria display (§22) | T30, T31 | Codex + Kimi | todo |
| T33 | Hook 3D world: click on a block opens its tablet page; trucks for suppliers/clients | T06 | Kimi | todo |

## 9. Handoff log

Newest first. Format: `YYYY-MM-DD · agent · task · what changed · what's left · questions`.

- 2026-11-01 · Codex + Kimi Pro · GAME-01 · Connected the tablet to real engine data and purchase/OF/maintenance decisions, server configuration refusal logging, journal replay and corrected customer OTIF/history, SQLite journal/RNG persistence, confirmed startup rules, eight visible factory blocks and direct 3D tablet navigation. Integrated Kimi UI-01, enabled supplier comparison and per-game spreadsheet storage, fixed stale iframe reopening and truck refresh after tablet turns. Shared core ownership: added engine/journal.py, engine/kpis.py, engine/tablet.py and modified simulation.py, database.py, main.py; T03/T05 must rebase on this base. Existing IDs/endpoints and saved game preserved; root server restarted. Verified 24 game pytest tests / 58 full installed-project tests and 18 Node tests (including four bridge regression tests); original Kimi fixture browser checks passed at 1024/768 px. Final integrated browser preview denied by browser access policy, so final installation was checked via API/static HTTP and tests. · Full Annex A world loader, Initial/Libre rights, 8 h clock, geographic routes, Pareto, complete hazards/scenarios and success criteria remain in their original tasks; see docs/jeu-live.md and COMMENT_JOUER.md. · T00 time unit/library decisions and T01 source gaps remain open; no guessed defaults added.

- 2026-11-01 · Kimi · UI-01 · Replaced the production mock shell with the live `/api/v2/tablet` client: playable ten-page tablet, eight-block factory plan plus partners, real purchase/production/maintenance forms, engine supplier comparison, filtered server tables, explicit confirmed new game, period simulation, accessible modal, 4 s refusal feedback and 3D navigation. Added five non-mutating tools, safe local spreadsheet persistence/CSV export and `tablet_live_api.test.js`. Verified 14 Node tests, 12 pytest tests, JS syntax and headless Chrome flows at 1024/768 px. · Codex must expose the agreed v2 snapshot/new-game/next-turn/actions/configuration endpoints; unsupported actions stay disabled. Charts require numeric `history`; Pareto aggregation and geographic routes remain server-data gaps. `mock-api.js` is retained only for legacy tests and is not loaded by production; existing `test_tablet_shell.py` tests still pass and need no change yet. · No new questions.
- 2026-11-01 · Kimi · T06 · Added `/tablet` with the home dashboard, 10 department shells and three tabs, startup rules/rights screen, five tool entry points, clock controls, and exact 4 s red refusal pop-up. Added an isolated mock API plus Python/JS tests; existing game endpoints remain available. Verified with 12 pytest tests, 5 Node tests, and headless Chrome flows at 1440/1024/768 px. · T05 must replace `backend/app/static/tablet/mock-api.js` with `/api/v2`; T07 implements the tool workspaces; T04/T05 own real server-side rights and journaling. · No new questions.
- 2026-11-01 · Claude · setup · Wrote this AGENTS.md from the v3 doc, the cahier des charges and a read of the current backend. No code changed yet. · Next: T00 (Amine) and T01 (gap report). · Questions: see §7 "Pending".
