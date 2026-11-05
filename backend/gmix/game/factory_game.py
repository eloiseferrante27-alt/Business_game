"""Partie d'usine (docs/decisions/0007 et 0010) : la semaine jouée est un tour du noyau `factory` (cinq jours de
480 minutes, événements discrets) ; ce module y ajoute ce qu'une partie a de plus : trésorerie, aléas annoncés,
indicateurs, vue publique `public_state["factory"]`, bilan, pilote automatique et informations des agents.
Mêmes principes que le moteur de l'atelier : fonctions pures (état JSON en entrée, nouvel état en sortie), hasard
dérivé de la graine de la spec et du numéro de semaine, aucune entrée-sortie. `engine` aiguille ici dès que la spec
porte une section `factory` ; les handlers et les faits sont enregistrés dans les tables de `engine`."""

import copy
import math
import random
from typing import Any

from gmix.game import engine, factory
from gmix.game.engine import GameRuleError, money
from gmix.game.spec import COUNTERS, INDICATORS, load_pack

# Effets d'aléa que le noyau lit ; `cost` est une hausse durable des achats, gérée ici (refus de tout autre effet à la
# génération : un effet inconnu serait sans suite).
SIM_EFFECTS = frozenset({"mtbf", "delay_risk", "demand", "nonconform"})
EVENT_EFFECTS = SIM_EFFECTS | {"cost"}
LEVELS = {"aucune": "aucun entretien", "goulot": "le goulot", "toutes": "toutes les machines"}
FLOW_DEPARTMENTS = ("fournisseur", "reception", "stock_mp", "qualite", "emballage", "entrepot_pf", "client")
MAX_TRUCK_PALLETS = 6  # une commande d'achat est un camion (pack : camion_palettes)
KEPT_CLOSED = factory.KEPT_ORDERS


# --- état ----------------------------------------------------------------------------------------------------------


def initial_state(spec: dict[str, Any]) -> dict[str, Any]:
    plant = factory.Plant(spec)
    return {
        "status": "waiting", "week": 1, "cash": spec["economy"]["initial_cash"], "cost_index": 1.0, "event": None,
        "history": [], "log": [], "last": None, "fs": factory.initial_state(plant), "snap": None,
    }  # fmt: skip


def roll_event(spec: dict[str, Any], week: int) -> str | None:
    """Aléa de la semaine, tiré une semaine à l'avance ; le plan du formateur (`params.event_plan`) l'emporte."""
    for planned in spec["params"].get("event_plan") or []:
        if planned["week"] == week:
            return planned["event_id"]
    probability = spec["economy"]["events_probability"]
    rng = random.Random(spec["seed"] * 31 + week * 977)
    if week == 1 or probability <= 0 or rng.random() >= probability or not spec["events"]:
        return None
    pick = rng.random() * sum(e["weight"] for e in spec["events"])
    for event in spec["events"]:
        pick -= event["weight"]
        if pick <= 0:
            return event["id"]
    return spec["events"][-1]["id"]


# --- actions des joueurs --------------------------------------------------------------------------------------------


def _name(spec: dict[str, Any], line_id: str) -> str:
    return next(line["name"] for line in spec["lines"] if line["id"] == line_id)


def _rack_pallets(plant: factory.Plant, fs: dict[str, Any]) -> int:
    """Places occupées au magasin matière : stock rangé, palettes en attente de place et commandes en route."""
    stock = -(-fs["mp"]["units"] // plant.upp) + fs["mp"]["staged"]
    return stock + sum(po["pallets"] for po in fs["pending"])


def _h_launch(spec: dict[str, Any], state: dict[str, Any], v: dict[str, Any]) -> str:
    plant = factory.Plant(spec)
    of_id = factory.launch_of(plant, state["fs"], v["line"], v["lots"])
    units = v["lots"] * plant.lot_size
    return f"Ordre {of_id} lancé sur {_name(spec, v['line'])} : {v['lots']} lots, soit {units} produits à fabriquer."


def _h_order(spec: dict[str, Any], state: dict[str, Any], v: dict[str, Any]) -> str:
    plant = factory.Plant(spec)
    offer = next(o for o in spec["offers"] if o["id"] == v["offer"])
    if v["pallets"] < offer["min_order"]:
        raise GameRuleError(f"Ce fournisseur impose au moins {offer['min_order']} palettes par commande")
    price = round(v["pallets"] * plant.upp * offer["unit_cost"] * state["cost_index"], 2)
    due = round(sum(po["pallets"] * plant.upp * po["unit_price"] for po in state["fs"]["pending"]), 2)
    if price > state["cash"] - due:  # la matière en route sera payée à la livraison
        raise GameRuleError(
            f"Trésorerie insuffisante : la commande coûte {money(price)}, {money(state['cash'])} en caisse "
            f"dont {money(due)} déjà engagés sur les commandes en route"
        )
    free = plant.lg["mp_capacity_pallets"] - _rack_pallets(plant, state["fs"])
    if v["pallets"] > free:
        raise GameRuleError(f"Le magasin matière n'a que {max(free, 0)} place(s) libre(s) pour {v['pallets']} palettes")
    po_id = factory.order_mp(plant, state["fs"], offer, v["pallets"], state["cost_index"])
    return (
        f"Commande {po_id} : {v['pallets']} palettes, {money(price)} à payer à la livraison "
        f"(sous {offer['lead_time']} jour(s) ; les palettes refusées au contrôle ne sont pas facturées)."
    )


def _h_protect(spec: dict[str, Any], state: dict[str, Any], v: dict[str, Any]) -> str:
    plant = factory.Plant(spec)
    protect = state["fs"]["settings"]["protect"]
    name = _name(spec, v["line"])
    note = ""
    if v["mode"] == "releve_pauses":  # un seul chef de ligne : la relève ne couvre qu'une ligne à la fois
        others = [lid for lid, mode in protect.items() if mode == "releve_pauses" and lid != v["line"]]
        for lid in others:
            protect[lid] = "aucune"
        note = " La relève des autres lignes est retirée (un seul chef de ligne)." if others else ""
    if (
        v["mode"] == "tampon_avant"
        and plant.bottleneck[plant.line_ids.index(v["line"])] == plant.first[plant.line_ids.index(v["line"])]
    ):
        note = " Le goulot est la première machine : le tampon n'a pas d'effet."
    protect[v["line"]] = v["mode"]
    label = {"aucune": "aucune protection", "releve_pauses": "relève du goulot pendant les pauses",
             "tampon_avant": "tampon devant le goulot"}[v["mode"]]  # fmt: skip
    return f"{name} : {label}.{note}"


def _h_preventive(spec: dict[str, Any], state: dict[str, Any], v: dict[str, Any]) -> str:
    state["fs"]["settings"]["preventive"][v["line"]] = v["cible"]
    return f"{_name(spec, v['line'])} : préventif sur {LEVELS[v['cible']]} chaque semaine."


def _h_priority(spec: dict[str, Any], state: dict[str, Any], v: dict[str, Any]) -> str:
    state["fs"]["settings"]["priority"] = v["ordre"]
    return "Réparations : les goulots d'abord." if v["ordre"] == "goulot" else "Réparations : dans l'ordre d'arrivée."


# --- pilote automatique ---------------------------------------------------------------------------------------------


def _yields(plant: factory.Plant) -> list[float]:
    return [factory.trs_factors(plant, ln)["qualite"] for ln in range(plant.nl)]


def _daily_mp(plant: factory.Plant) -> float:
    """Matière consommée par jour pour servir la demande moyenne, rebuts compris."""
    return plant.cu["demand_per_day"] / (sum(_yields(plant)) / plant.nl) * plant.per_unit


def _reorder_point(spec: dict[str, Any], plant: factory.Plant, offer: dict[str, Any]) -> int:
    """Point de commande en palettes = (délai L + période de revue R de 1 jour + stock de sécurité SS) x conso/jour
    / palette (wikipedia-en-safety-stock, § Inventory policy)."""
    days = offer["lead_time"] + 1 + spec["factory"].get("mp_safety_days", 1)
    return math.ceil(days * _daily_mp(plant) / plant.upp)


def _standard_offer(spec: dict[str, Any]) -> dict[str, Any]:
    offers = sorted(spec["offers"], key=lambda o: o["lead_time"])
    return next((o for o in offers if o["profile"] == "standard"), offers[len(offers) // 2])


def _autopilot(
    spec: dict[str, Any], plant: factory.Plant, state: dict[str, Any], played: set[str]
) -> dict[str, Any] | None:
    """Un module que le formateur n'a pas choisi tourne seul (celui de la spec) ;
    `played` = modules joués par un humain. Réglages
    posés ici ; les règles de pilotage (OF et matière) sont rendues au noyau, qui les applique CHAQUE jour simulé :
    - OF : position PF (stock + en-cours bon - commandes ouvertes) < `pf_min` -> campagne : OF sur chaque ligne
      jusqu'à `pf_max` (limité par le magasin PF) ;
    - MP : stock + palettes commandées <= (délai + revue 1 jour + stock de sécurité) jours de matière
      -> un camion standard
      de six palettes au plus, dans la limite du magasin et de la trésorerie."""
    settings = state["fs"]["settings"]
    if "maintenance" not in played:
        settings["preventive"] = dict.fromkeys(plant.line_ids, "goulot")
        settings["priority"] = "arrivee"
    if "production" not in played:
        settings["protect"] = dict.fromkeys(plant.line_ids, "aucune")
    if "pilotage" in played:
        return None
    offer = _standard_offer(spec)
    reorder = _reorder_point(spec, plant, offer)
    return {
        "order": {"offer": offer, "reorder": reorder, "truck": MAX_TRUCK_PALLETS, "cost_index": state["cost_index"],
                  "budget": state["cash"] - sum(po["pallets"] * plant.upp * po["unit_price"]
                                                for po in state["fs"]["pending"])},  # déjà engagé
        "launch": {"pf_max": spec["factory"].get("pf_max") or plant.pf_min,
                   "yields": dict(zip(plant.line_ids, _yields(plant), strict=True))},
    }  # fmt: skip


# --- semaine -------------------------------------------------------------------------------------------------------


def advance(spec: dict[str, Any], state: dict[str, Any], played: set[str]) -> dict[str, Any]:
    if state["status"] != "running":
        raise GameRuleError("La partie n'est pas en cours")
    new = copy.deepcopy({k: v for k, v in state.items() if k != "last"}) | {
        "last": None
    }  # `last` est remplacé plus bas
    plant, week = factory.Plant(spec), new["week"]
    auto = _autopilot(spec, plant, new, played)
    event = engine._event(spec, new["event"])
    effects = dict(event["effects"]) if event else {}
    if "cost" in effects:  # hausse durable : s'applique aux commandes passées à partir de maintenant
        new["cost_index"] = round(new["cost_index"] * effects.pop("cost"), 4)
    day0 = new["fs"]["day"]
    new["fs"], timeline, report = factory.simulate(
        plant, new["fs"], week, {k: v for k, v in effects.items() if k in SIM_EFFECTS}, auto
    )
    snap = _snapshot(plant, new["fs"], timeline, report, new["snap"])
    revenue = report["shipped"] * spec["products"][0]["price"]
    staff = sum(m["operators"] for m in plant.machines) * plant.days * plant.mpd / 60 * plant.costs["operator_per_h"]
    relief = report["relief_min"] / 60 * plant.costs["operator_per_h"]
    costs = {"repair": report["costs"]["repair"], "preventive": report["costs"]["preventive"],
             "staff": staff, "relief": relief, "mp": report["costs"]["mp"]}  # fmt: skip
    new["cash"] = round(new["cash"] + revenue - sum(costs.values()), 2)
    snap["report"] = report
    previous = new["history"][-1]["otif"] if new["history"] else 100.0
    kpis = _week_kpis(plant, report, snap, new["cash"], previous)
    delayed = [
        o["id"] for o in new["fs"]["orders"] if day0 <= o["due_day"] < new["fs"]["day"] and o["on_time"] is not True
    ]
    kept = [o for o in new["fs"]["orders"] if o["due_day"] >= day0]  # shortcut: seulement les commandes gardées
    lost = sum(o["quantity"] for o in kept if o["id"] in delayed)
    new["snap"] = snap
    new["last"] = {
        "week": week, "kpis": kpis, "totals": {"demand": sum(o["quantity"] for o in kept), "served": report["shipped"],
                                              "lost": lost, "returns": 0},
        "delayed": delayed, "event": event["id"] if event else None, "revenue": round(revenue),
        "costs": {k: round(v) for k, v in costs.items()}, "timeline": timeline,
    }  # fmt: skip
    new["history"].append(
        {"week": week, **kpis, "event": new["last"]["event"], "lost": lost, "returns": 0, "delays": len(delayed)}
    )
    if week >= spec["meta"]["weeks"]:
        new["status"], new["event"] = "finished", None
    else:
        new["week"], new["event"] = week + 1, roll_event(spec, week + 1)
    return new


def _week_kpis(
    plant: factory.Plant, report: dict[str, Any], snap: dict[str, Any], cash: float, previous: float
) -> dict[str, Any]:
    trs = [m["trs"] for m in snap["lines"].values() if m["trs"] is not None]
    out = sum(line["out"] for line in report["lines"].values())
    good = sum(line["good"] for line in report["lines"].values())
    return {
        "otif": round(report["orders"]["otif"], 1) if report["orders"]["otif"] is not None else previous,
        "trs": round(sum(trs) / len(trs), 1) if trs else 0.0,
        "stockouts": sum(line["stockout_days"] for line in report["lines"].values()),
        "cash": round(cash),
        "good_share": round(100 * good / out, 1) if out else None,
    }


def _snapshot(
    plant: factory.Plant, fs: dict[str, Any], tl: dict[str, Any], report: dict[str, Any], prev: dict[str, Any] | None
) -> dict[str, Any]:
    """Ce que la vue publique garde de la chronologie (que les lobbies rangent à part) : états en fin de tour,
    mesures par machine et par ligne, flux, états des agents."""
    last = tl["frames"][-1]
    machines, T = {}, plant.T
    for i, mid in enumerate(plant.mids):
        r = report["machines"][mid]
        mins = r["minutes"]
        planned = T - mins["pause"]
        machines[mid] = {
            "state": tl["states"][last[1][i]], "buffer": last[2][i],
            "availability": round(100 * (planned - mins["panne"]) / planned, 1) if planned > 0 else None,
            "downtime_min": round(mins["panne"]), "produced": r["produced"], "defects": r["defects"],
            "failures": r["failures"], "age_h": round(r["age_min"] / 60, 1),
        }  # fmt: skip
    agents = dict(prev["agents"]) if prev else {}
    for _t, kind, subject, data in tl["events"]:
        if kind == "agent":
            agents[subject] = [data["state"], data["at"]]
    lines = {}
    for ln, lid in enumerate(plant.line_ids):
        r, b = report["lines"][lid], report["machines"][plant.mids[plant.bottleneck[ln]]]["minutes"]
        planned_h = (T - b["arret"]) / 60  # temps planifié : hors les moments où la ligne n'a rien à faire
        run_h = (T - b["arret"] - b["pause"] - b["panne"]) / 60
        th = r["theoretical_h"]
        ok = planned_h > 0 and r["out"] > 0
        lines[lid] = {
            "real_h": round(r["good"] / planned_h, 1) if planned_h > 0 else None,
            "trs": min(1.0, r["good"] / (th * planned_h)) * 100 if planned_h > 0 else None,
            "disponibilite": 100 * run_h / planned_h if planned_h > 0 else None,
            "performance": min(100.0, 100 * r["out"] / (th * run_h)) if run_h > 0 else None,
            "qualite": 100 * r["good"] / r["out"] if ok else None,
        }  # fmt: skip
    rec, upp = report["reception"], plant.upp
    edges = [["fournisseur", "reception", rec["pallets"] * upp], ["reception", "stock_mp", rec["accepted"]]]
    for ln, lid in enumerate(plant.line_ids):
        ms = plant.line_machines[ln]
        edges.append(["stock_mp", plant.mids[ms[0]], report["lines"][lid]["entered"]])
        edges += [[plant.mids[a], plant.mids[b], report["machines"][plant.mids[a]]["produced"]]
                  for a, b in zip(ms, ms[1:], strict=False)]  # fmt: skip
        edges.append([plant.mids[ms[-1]], "qualite", report["lines"][lid]["out"]])
    good = sum(r["good"] for r in report["lines"].values())
    packed = report["packed"]["pallets"] * plant.pallet_pf
    edges += [["qualite", "emballage", good], ["emballage", "entrepot_pf", packed]]
    edges.append(["entrepot_pf", "client", report["shipped"]])
    return {"machines": machines, "agents": agents, "counters": list(last[3]), "lines": lines, "edges": edges,
            "report": None}  # fmt: skip


# --- vue publique ---------------------------------------------------------------------------------------------------


def _blank_snap(plant: factory.Plant, fs: dict[str, Any]) -> dict[str, Any]:
    machines = {mid: {"state": "arret", "buffer": len(fs["tables"][i]), "availability": None, "downtime_min": 0,
                      "produced": 0, "defects": 0, "failures": 0, "age_h": 0.0}
                for i, mid in enumerate(plant.mids)}  # fmt: skip
    lines = dict.fromkeys(plant.line_ids, {"real_h": None, "trs": None, "disponibilite": None, "performance": None,
                                           "qualite": None})  # fmt: skip
    return {"machines": machines, "agents": {}, "counters": [fs["mp"]["units"], *[0] * 7, fs["pf"]["units"], 0][:9],
            "lines": lines, "edges": [], "report": None}  # fmt: skip


def _avg(values: list[float | None]) -> float | None:
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 1) if values else None


def _factory_view(spec: dict[str, Any], state: dict[str, Any], plant: factory.Plant) -> dict[str, Any]:
    fs = state["fs"]
    snap = state["snap"] or _blank_snap(plant, fs)
    ms = snap["machines"]
    protect = fs["settings"]["protect"]
    machines = []
    for i, m in enumerate(plant.machines):
        ln = plant.line_of[i]
        raised = (
            protect.get(m["line_id"]) == "tampon_avant" and plant.bottleneck[ln] == i + 1 and i + 1 != plant.first[ln]
        )
        machines.append({
            "id": m["id"], "line_id": m["line_id"], "rank": m["rank"], "name": m["name"],
            "bottleneck": plant.bottleneck[ln] == i, "rate_h": round(60 / m["cycle_min"], 1),
            "buffer_max": max(m["buffer"], plant.protect) if raised else m["buffer"], "tool_left": None, **ms[m["id"]],
        })  # fmt: skip
    ofs = fs["ofs"]
    yields = _yields(plant)
    lines = []
    for ln, lid in enumerate(plant.line_ids):
        mine = [of for of in ofs if of["line_id"] == lid]
        planned = sum(of["quantity"] for of in mine) * yields[ln]
        wip = sum(n for _, n in fs["pools"][ln]) + sum(
            len(fs["tables"][i]) + (fs["machines"][i]["cur"] is not None) for i in plant.line_machines[ln]
        )
        got = snap["lines"][lid]
        lines.append({
            "id": lid, "name": _name(spec, lid), "bottleneck_id": plant.mids[plant.bottleneck[ln]],
            "theoretical_h": round(factory.theoretical_h(plant, ln), 1),
            "expected_h": round(factory.expected_h(plant, ln), 1), "real_h": got["real_h"],
            "production_rate": round(min(100.0, 100 * sum(o["good"] for o in mine) / planned), 1) if planned else None,
            "wip": wip, "capacity": round(factory.theoretical_h(plant, ln) * plant.T / 60),
            "trs": None if got["trs"] is None else round(got["trs"], 1),
        })  # fmt: skip
    std = _standard_offer(spec)
    reorder = _reorder_point(spec, plant, std)
    component = next(c for c in spec["components"] if c["id"] == plant.component)
    pending = sum(po["pallets"] for po in fs["pending"])
    mp_units = fs["mp"]["units"]
    pf = fs["pf"]["units"]
    expected = [factory.trs_factors(plant, ln) for ln in range(plant.nl)]
    measured = [snap["lines"][lid] for lid in plant.line_ids]
    exp_trs = round(100 * sum(e["disponibilite"] * e["performance"] * e["qualite"] for e in expected) / plant.nl, 1)
    pct = lambda key: round(100 * sum(e[key] for e in expected) / plant.nl, 1)  # noqa: E731
    formulas = [
        {"id": "capacite_et_trs", "expected": exp_trs, "measured": _avg([m["trs"] for m in measured]), "unit": "%"},
        {"id": "capacite_et_trs.disponibilite", "expected": pct("disponibilite"),
         "measured": _avg([m["disponibilite"] for m in measured]), "unit": "%"},
        {"id": "capacite_et_trs.performance", "expected": pct("performance"),
         "measured": _avg([m["performance"] for m in measured]), "unit": "%"},
        {"id": "capacite_et_trs.qualite", "expected": pct("qualite"),
         "measured": _avg([m["qualite"] for m in measured]), "unit": "%"},
    ]  # fmt: skip
    nodes = [{"id": d["id"], "label": d["label"], "kind": "departement", "state": None,
              "count": sum(e[2] for e in snap["edges"] if e[1] == d["id"])}
             for d in spec["departments"] if d["id"] in FLOW_DEPARTMENTS]  # fmt: skip
    nodes += [{"id": m["id"], "label": m["name"], "kind": "machine", "state": ms[m["id"]]["state"],
               "count": ms[m["id"]]["produced"]} for m in machines]  # fmt: skip
    crew = {}
    for member in spec["factory"]["crew"]:
        if member["machine_id"]:
            st = ms[member["machine_id"]]["state"]
            crew[member["id"]] = {"state": _operator_state(st), "at": member["machine_id"]}
    agents = {a["id"]: {"state": "disponible", "at": a["department_id"]} for a in spec["agents"]}
    agents |= {c["id"]: {"state": "disponible", "at": c["department_id"]} for c in spec["factory"]["crew"]}
    agents |= {k: {"state": s, "at": at} for k, (s, at) in snap["agents"].items() if k in agents}
    agents |= crew
    customer = sorted(fs["orders"], key=lambda o: (o["shipped_day"] is not None, o["due_day"], o["id"]))
    return {
        "day": fs["day"],
        "machines": machines,
        "lines": lines,
        "stocks": {
            "mp": [
                {
                    "component_id": component["id"],
                    "name": component["name"],
                    "quantity": mp_units,
                    "pallets": -(-mp_units // plant.upp),
                    "capacity_pallets": plant.lg["mp_capacity_pallets"],
                    "reorder_point": reorder,
                    "pending": pending,
                }
            ],  # fmt: skip
            "pf": {
                "quantity": pf,
                "pallets": -(-pf // plant.pallet_pf),
                "capacity_pallets": plant.lg["pf_capacity_pallets"],
                "min": plant.pf_min,
            },
            "quarantine": fs["mp"]["quarantine"],
        },
        "orders": {
            "production": [
                {
                    "id": of["id"],
                    "line_id": of["line_id"],
                    "quantity": of["quantity"],
                    "done": of["out"],
                    "status": of["status"],
                }
                for of in ofs
            ],  # fmt: skip
            "customer": [
                {
                    "id": o["id"],
                    "quantity": o["quantity"],
                    "due_day": o["due_day"],
                    "shipped": o["quantity"] if o["shipped_day"] is not None else 0,
                    "status": o["status"],
                }
                for o in customer
            ],  # fmt: skip
        },
        "agents": agents,
        "products": dict(zip(COUNTERS[1:], snap["counters"][1:], strict=True)),
        "flow": {"nodes": nodes, "edges": [{"from": a, "to": b, "count": c} for a, b, c in snap["edges"]]},
        "formulas": formulas,
    }


def _operator_state(machine_state: str) -> str:
    if machine_state in ("marche", "reglage", "panne"):
        return "occupe"
    return "pause" if machine_state == "pause" else "disponible"


def public_state(spec: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Ce que voient tous les membres du lobby. Les racines de l'atelier (`stocks`, `components`, `lines`, `pending`)
    restent présentes et vides : tout le détail est dans `factory`."""
    plant = factory.Plant(spec)
    event = engine._event(spec, state.get("event"))
    last = state["last"]
    last_kpis = last["kpis"] if last else {}
    view = {
        "status": state["status"], "week": state["week"], "weeks": spec["meta"]["weeks"], "cash": round(state["cash"]),
        "overdraft": None,
        "kpis": {"otif": last_kpis.get("otif"), "trs": last_kpis.get("trs"), "cash": round(state["cash"]),
                 "good_share": last_kpis.get("good_share"), "stockouts": last_kpis.get("stockouts", 0)},
        "targets": spec["targets"], "history": state["history"],
        "stocks": [], "components": [], "lines": [], "pending": [], "settings": state["fs"]["settings"],
        "event": {k: event[k] for k in ("id", "title", "description")} if event else None,
        "last": {k: v for k, v in last.items() if k != "timeline"} if last else None,
        "log": engine.recent_log(state),
        "factory": _factory_view(spec, state, plant),
    }  # fmt: skip
    view["briefings"] = engine._briefings(spec, state, view)
    view["alerts"] = _alerts(spec, state, view)
    return view


def _alerts(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[dict[str, Any]]:
    """Alertes de l'usine (annexe 0010 §2) : celles du pack (`alerts:` : niveau, département, module, texte à
    {clés}), déclenchées par des faits du moteur. Une alerte absente du pack n'est pas émise."""
    tpl = {t["id"]: t for t in load_pack(spec["meta"]["pack"]).get("alerts", [])}
    f, out = view["factory"], []

    def emit(
        key: str,
        alert_id: str,
        ctx: dict[str, Any],
        *,
        level: str | None = None,
        ref: str | None = None,
        action: tuple[str, dict] | None = None,
    ) -> None:
        if key in tpl:
            t = tpl[key]
            out.append(engine.alert(spec, alert_id, level or t["level"], t["text"].format_map(ctx),
                                    module_id=t["module_id"], department_id=t["department_id"], ref=ref,
                                    action=action))  # fmt: skip

    mp = f["stocks"]["mp"][0]
    if mp["pallets"] + mp["pending"] < mp["reorder_point"]:
        offer = _standard_offer(spec)
        pallets = min(MAX_TRUCK_PALLETS, mp["capacity_pallets"] - mp["pallets"] - mp["pending"])
        order = ("commander_mp", {"offer": offer["id"], "pallets": pallets}) if pallets >= offer["min_order"] else None
        emit("reorder", "reorder:c1", mp, ref="mp:c1", action=order)
    snap = state.get("snap") or {}
    for lid, line in (((snap.get("report") or {}).get("lines")) or {}).items():
        if line["stockout_min"]:
            emit(
                "starved",
                f"starved:{lid}",
                {"line": _name(spec, lid), "stockout_min": round(line["stockout_min"])},
                ref=f"line:{lid}",
            )
    ordered = state["fs"]["settings"]["priority"] == "goulot"
    for m in f["machines"]:
        if m["state"] == "panne":
            emit(
                "breakdown",
                f"breakdown:{m['id']}",
                {"machine": m["name"]},
                level="critical" if m["bottleneck"] else "warning",
                ref=f"machine:{m['id']}",
                action=None if ordered else ("priorite_reparation", {"ordre": "goulot"}),
            )
            out[-1]["text"] = (f"{m['name']} en panne" + (" : c'est le goulot." if m["bottleneck"] else "."))[:120]
    threshold = tpl.get("trs_low", {}).get("threshold")
    for lid, line in (snap.get("lines") or {}).items():
        if threshold is not None and line["trs"] is not None and line["trs"] < threshold:
            emit("trs_low", f"trs_low:{lid}", {"line": _name(spec, lid), "trs": f"{line['trs']:g}"}, ref=f"line:{lid}")
    for oid in ((state["last"] or {}).get("delayed") or [])[:3]:
        emit("late", f"late:{oid}", {"order": oid}, ref="dock")
    return engine.finish_alerts(out + engine.common_alerts(spec, state, view))


# --- bilan ---------------------------------------------------------------------------------------------------------


def debrief(spec: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    history, targets = state["history"], spec["targets"]
    names = {"otif": ("OTIF moyen", "%"), "trs": ("TRS moyen", "%"),
             "stockouts": ("Jours-ligne arrêtés faute de matière (sur la partie)", ""),
             "cash": ("Trésorerie finale", "€"), "good_share": ("Part de bons (moyenne)", "%")}  # fmt: skip
    finals = []
    for key in INDICATORS["factory"]:
        if key == "stockouts":
            final = sum(h["stockouts"] for h in history)
        elif key == "cash":
            final = round(state["cash"])
        else:
            final = engine._mean(history, key)
        target = targets["cash_final"] if key == "cash" else None if key == "good_share" else targets[key]
        met = None if final is None or target is None else (final <= target if key == "stockouts" else final >= target)
        failed = key == "stockouts" and bool(history) and all(h["good_share"] is None for h in history)
        finals.append({"id": key, "name": names[key][0], "unit": names[key][1], "final": final, "target": target,
                       "met": False if failed else met, "failed": failed})  # fmt: skip
    notion_ids = {n for m in spec["modules"] for n in m["notions"]} | {n for a in spec["agents"] for n in a["notions"]}
    events = {e["id"]: e["title"] for e in spec["events"]}
    return {
        "status": state["status"], "company": spec["meta"]["company"], "weeks_played": len(history), "kpis": finals,
        "history": history, "lessons": _lessons(spec, state),
        "notions": [n for n in spec["notions"] if n["id"] in notion_ids],
        "events": [{"week": h["week"], "title": events.get(h["event"], h["event"])} for h in history if h["event"]],
        "log": [engine.full_entry(e) for e in state["log"]],
        "criteria": engine.criteria_verdicts(spec, history, finals), "unsourced": engine._unsourced(spec),
    }  # fmt: skip


def _lessons(spec: dict[str, Any], state: dict[str, Any]) -> list[str]:
    history, targets = state["history"], spec["targets"]
    if not history:
        return ["La partie n'a pas été jouée."]
    lessons = []
    starved = sum(h["stockouts"] for h in history)
    if starved:
        lessons.append(
            f"{starved} jour(s)-ligne arrêtés faute de matière : commander au point de commande (consommation "
            "pendant le délai du fournisseur, plus revue et stock de sécurité) les aurait évités."
        )
    otif = engine._mean(history, "otif")
    if otif is not None and otif < targets["otif"]:
        late = sum(h["delays"] for h in history)
        lessons.append(
            f"OTIF moyen de {otif} % pour un objectif de {targets['otif']:.0f} % : {late} commande(s) en retard. "
            "Lancer les ordres de fabrication assez tôt pour que le stock de produits finis couvre la demande."
        )
    trs = engine._mean(history, "trs")
    if trs is not None and trs < targets["trs"]:
        lessons.append(
            f"TRS moyen de {trs} % pour un objectif de {targets['trs']:.0f} % : pannes, pauses et rebuts réduisent la "
            "production du goulot ; protéger le goulot et faire du préventif la préserve."
        )
    if state["cash"] < targets["cash_final"]:
        lessons.append(
            f"Trésorerie finale de {money(state['cash'])} sous l'objectif de {money(targets['cash_final'])} : matière "
            "commandée en trop, pannes ou ventes manquées ont pesé."
        )
    if not lessons:
        lessons.append("Objectifs atteints : la matière, la fabrication et les livraisons sont restées alignées.")
    return lessons


# --- informations essentielles des agents (briefings) ---------------------------------------------------------------

Fact = tuple[bool, str]


def _rep(state: dict[str, Any]) -> dict[str, Any] | None:
    return (state.get("snap") or {}).get("report")


def _facts_fournisseur(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    pending = state["fs"]["pending"]
    facts: list[Fact] = [
        (False, f"{len(pending)} commande(s) de matière en route, soit {sum(p['pallets'] for p in pending)} palettes.")
    ]
    if state["cost_index"] > 1:
        facts.append((False, f"Nos prix ont augmenté de {round((state['cost_index'] - 1) * 100)} % depuis le début."))
    rep = _rep(state)
    if rep and rep["reception"]["quarantined"]:
        facts.append((False, "Des palettes ont été refusées au contrôle la semaine passée : réclamation à traiter."))
    return facts


def _facts_reception(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    rep = _rep(state)
    due = [p["due_day"] - state["fs"]["day"] for p in state["fs"]["pending"]]
    facts: list[Fact] = []
    if rep:
        r = rep["reception"]
        if r["quarantined"]:
            facts.append((True, f"{r['quarantined']} produits de matière mis en quarantaine : palettes non conformes."))
        facts.append((False, f"Semaine passée : {r['trucks']} camion(s) déchargé(s), {r['pallets']} palettes."))
        if rep["dock"]["wait_min"] > 30:
            facts.append((False, f"Les camions ont attendu un quai {round(rep['dock']['wait_min'])} minutes en tout."))
    if due:
        facts.append((False, f"Prochaine livraison attendue dans {max(min(due), 0)} jour(s)."))
    return facts or [(False, "Aucun camion attendu pour l'instant.")]


def _facts_stock_mp(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    mp = view["factory"]["stocks"]["mp"][0]
    rep = _rep(state)
    facts: list[Fact] = []
    stopped = sum(line["stockout_min"] for line in rep["lines"].values()) if rep else 0
    if stopped:
        facts.append((True, f"Une ligne s'est arrêtée {round(stopped)} minutes faute de matière."))
    left = mp["capacity_pallets"] - mp["pallets"] - mp["pending"]
    if mp["pallets"] + mp["pending"] < mp["reorder_point"]:
        stock = f"{mp['pallets']} palettes en stock et {mp['pending']} en commande"
        facts.append((True, f"{stock}, sous le point de commande de {mp['reorder_point']} : il faut commander."))
    facts.append(
        (False, f"Magasin : {mp['pallets']} palettes sur {mp['capacity_pallets']} places, {max(left, 0)} libres.")
    )
    return facts


def _facts_production(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    f = view["factory"]
    facts: list[Fact] = []
    for m in f["machines"]:
        if m["bottleneck"] and m["state"] == "panne":
            facts.append((True, f"Le goulot {m['name']} est en panne."))
    for line in f["lines"]:
        if line["real_h"] is not None:
            slow = line["real_h"] < 0.9 * line["expected_h"]
            facts.append(
                (slow, f"{line['name']} : {line['real_h']} bons par heure mesurés pour {line['expected_h']} attendus.")
            )
    open_of = [of for of in f["orders"]["production"] if of["status"] != "termine"]
    facts.append((False, f"{len(open_of)} ordre(s) de fabrication ouvert(s)."))
    return facts


def _facts_qualite(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    rep = _rep(state)
    if not rep:
        return [(False, "Aucun produit contrôlé pour l'instant.")]
    f = view["factory"]
    shares = next(x for x in f["formulas"] if x["id"] == "capacite_et_trs.qualite")
    scrap = sum(line["scrap"] for line in rep["lines"].values())
    facts: list[Fact] = [(False, f"Semaine passée : {rep['controlled']} produits contrôlés, {scrap} rebuts.")]
    if shares["measured"] is not None and shares["measured"] < shares["expected"] - 2:
        facts.insert(0, (True, f"Part de bons de {shares['measured']} % pour {shares['expected']} % attendus."))
    return facts


def _facts_emballage(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    rep, plant_pallet = _rep(state), view["factory"]["stocks"]["pf"]
    facts: list[Fact] = []
    waiting = view["factory"]["products"]["conforme"]
    if waiting > 2 * spec["factory"]["logistics"]["units_per_case"] * spec["factory"]["logistics"]["cases_per_pallet"]:
        facts.append((True, f"{waiting} produits bons attendent d'être emballés."))
    if rep:
        facts.append(
            (False, f"Semaine passée : {rep['packed']['cases']} cartons et {rep['packed']['pallets']} palettes.")
        )
    facts.append((False, f"Entrepôt PF : {plant_pallet['pallets']} palettes sur {plant_pallet['capacity_pallets']}."))
    return facts


def _facts_maintenance(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    rep = _rep(state)
    if not rep:
        return [(False, "Aucune panne depuis le début de la partie.")]
    f = view["factory"]
    worst = max(f["machines"], key=lambda m: (m["downtime_min"], m["id"]))
    facts: list[Fact] = []
    total = sum(m["failures"] for m in f["machines"])
    if worst["downtime_min"]:
        facts.append((worst["bottleneck"], f"{worst['name']} a perdu {worst['downtime_min']} minutes en panne."))
    facts.append((False, f"Semaine passée : {total} panne(s) au total."))
    if rep["technician"]["waited"]:
        facts.append((False, f"{rep['technician']['waited']} panne(s) ont attendu le technicien."))
    done, skipped = len(rep["preventive"]["done"]), len(rep["preventive"]["skipped"])
    facts.append((False, f"Préventif : {done} fait(s), {skipped} non fait(s)."))
    return facts


def _facts_pilotage(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    f, targets = view["factory"], spec["targets"]
    orders = f["orders"]["customer"]
    late = [o for o in orders if o["status"] == "en_retard"]
    open_ = [o for o in orders if o["status"] != "livree"]
    stock = f["stocks"]["pf"]
    wip = sum(line["wip"] for line in f["lines"])
    facts: list[Fact] = [(bool(late), f"{len(open_)} commande(s) ouverte(s), dont {len(late)} en retard.")]
    if stock["quantity"] + wip < stock["min"]:
        facts.append(
            (
                True,
                f"Stock fini et en-cours à {stock['quantity'] + wip}, sous le minimum de {stock['min']} : "
                "lancer des ordres.",
            )
        )
    otif, trs = view["kpis"]["otif"], view["kpis"]["trs"]
    if otif is not None:
        facts.append(
            (
                False,
                f"OTIF à {otif:.0f} % (objectif {targets['otif']:.0f} %), "
                f"TRS à {trs:.0f} % (objectif {targets['trs']:.0f} %).",
            )
        )
    return facts


def _facts_entrepot_pf(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    stock = view["factory"]["stocks"]["pf"]
    late = sum(1 for o in view["factory"]["orders"]["customer"] if o["status"] == "en_retard")
    facts: list[Fact] = []
    if stock["pallets"] >= stock["capacity_pallets"]:
        facts.append((True, "L'entrepôt est plein : l'emballage ne peut plus ranger de palette."))
    if late:
        facts.append((True, f"{late} commande(s) en retard faute de stock complet."))
    facts.append((False, f"{stock['pallets']} palettes en stock sur {stock['capacity_pallets']} places."))
    return facts


def _facts_client(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    otif, targets = view["kpis"]["otif"], spec["targets"]
    open_ = [o for o in view["factory"]["orders"]["customer"] if o["status"] != "livree"]
    facts: list[Fact] = []
    if otif is not None and otif < targets["otif"]:
        facts.append(
            (True, f"Livraisons à l'heure et complètes : {otif:.0f} %, sous l'objectif de {targets['otif']:.0f} %.")
        )
    facts.append((False, f"{len(open_)} commande(s) attendue(s) chez nous."))
    return facts


engine._HANDLERS.update({
    ("pilotage", "lancer_of"): _h_launch, ("pilotage", "commander_mp"): _h_order,
    ("production", "proteger_goulot"): _h_protect, ("maintenance", "preventif"): _h_preventive,
    ("maintenance", "priorite_reparation"): _h_priority,
})  # fmt: skip
engine._FACTS.update({
    "usine_fournisseur": _facts_fournisseur, "usine_reception": _facts_reception, "usine_stock_mp": _facts_stock_mp,
    "usine_production": _facts_production, "usine_qualite": _facts_qualite, "usine_emballage": _facts_emballage,
    "usine_maintenance": _facts_maintenance, "usine_pilotage": _facts_pilotage,
    "usine_entrepot_pf": _facts_entrepot_pf, "usine_client": _facts_client,
})  # fmt: skip
