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
from gmix.game.engine import GameRuleError, money, num
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
    fs = factory.initial_state(plant)
    f = spec["factory"]  # commandes déjà en route (règle n° 5a, une par matière), payées à la réception
    for first in ([f["initial_order"]] if f.get("initial_order") else []) + (f.get("initial_orders") or []):
        offer = next(o for o in spec["offers"] if o["id"] == first["offer_id"])
        factory.order_mp(plant, fs, offer, first["pallets"], day=first["arrival_day"] - offer["lead_time"])
    return {
        "status": "waiting", "week": 1, "cash": spec["economy"]["initial_cash"], "cost_index": 1.0, "event": None,
        "history": [], "log": [], "last": None, "fs": fs, "snap": None,
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


def _mp_by(plant: factory.Plant, fs: dict[str, Any], key: str) -> list[int]:
    """Matière par composant (`key` : units, staged, quarantine, reserved) ; l'agrégat à un produit et un client."""
    return fs["mp"]["by"][key] if plant.multi else [fs["mp"][key]]


def _pf_by(plant: factory.Plant, fs: dict[str, Any]) -> list[int]:
    return fs["pf"]["by"] if plant.multi else [fs["pf"]["units"]]


def _upp(plant: factory.Plant, component_id: str) -> int:
    return plant.upps[plant.p_of_comp[component_id]]


def _engaged(plant: factory.Plant, state: dict[str, Any]) -> float:
    """Matière en route, payée à la livraison."""
    return sum(po["pallets"] * _upp(plant, po["component_id"]) * po["unit_price"] for po in state["fs"]["pending"])


def _rack_pallets(plant: factory.Plant, fs: dict[str, Any]) -> int:
    """Places occupées au magasin matière : stock rangé, palettes en attente de place et commandes en route."""
    units, staged = _mp_by(plant, fs, "units"), _mp_by(plant, fs, "staged")
    stock = sum(-(-u // upp) + s for u, upp, s in zip(units, plant.upps, staged, strict=True))
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
    price = round(v["pallets"] * _upp(plant, offer["component_id"]) * offer["unit_cost"] * state["cost_index"], 2)
    due = round(_engaged(plant, state), 2)
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


def _delivery_text(lead_days: int) -> str:
    return "demain à 8 h" if lead_days == 1 else f"dans {lead_days} jours à 8 h"


def _h_spares(spec: dict[str, Any], state: dict[str, Any], v: dict[str, Any]) -> str:
    plant = factory.Plant(spec)
    if not plant.spares:
        raise GameRuleError("Cette usine n'a pas de stock de pièces de rechange à régler")
    cfg = {"cible": v["cible"], "pieces": int(v.get("pieces", 3))}
    state["fs"]["settings"]["spares"] = cfg
    sp = state["fs"]["spares"]
    target = factory.spares_target(plant, cfg)
    ordered = sum(max(0, target[t] - (sp["stock"][t] + sp["transit"][t] - len(sp["waiting"][t]))) for t in plant.types)
    label = {
        "aucune": "aucune machine",
        "goulot": f"goulots, {cfg['pieces']} par type",
        "toutes": f"toutes les machines, {cfg['pieces']} par type",
    }[cfg["cible"]]
    price = plant.spares["price"]
    when = _delivery_text(plant.spares["lead_days"])
    tail = f" ; {ordered} pièce(s) commandée(s), livrée(s) {when} ({money(ordered * price)})"
    return f"Pièces de rechange : {label}{tail if ordered else ' ; rien à commander'}."


# --- pilote automatique ---------------------------------------------------------------------------------------------


def _yields(plant: factory.Plant) -> list[float]:
    return [factory.trs_factors(plant, ln)["qualite"] for ln in range(plant.nl)]


def _daily_mp(plant: factory.Plant, p: int = 0) -> float:
    """Matière du produit p consommée par jour pour servir sa demande moyenne (ses clients), rebuts compris."""
    yields = [y for y, q in zip(_yields(plant), plant.line_prod, strict=True) if q == p]
    demand = sum(c["demand_per_day"] for c in plant.clients if c["p"] == p)
    return demand / (sum(yields) / len(yields)) * plant.per_units[p]


def _reorder_point(spec: dict[str, Any], plant: factory.Plant, offer: dict[str, Any]) -> int:
    """Point de commande en palettes = (délai L + période de revue R de 1 jour + stock de sécurité SS) x conso/jour
    / palette (wikipedia-en-safety-stock, § Inventory policy), de la matière de l'offre."""
    p = plant.p_of_comp[offer["component_id"]]
    days = offer["lead_time"] + 1 + spec["factory"].get("mp_safety_days", 1)
    return math.ceil(days * _daily_mp(plant, p) / plant.upps[p])


def _standard_offer(spec: dict[str, Any], component_id: str | None = None) -> dict[str, Any]:
    mine = [o for o in spec["offers"] if component_id in (None, o["component_id"])]
    offers = sorted(mine, key=lambda o: o["lead_time"])
    return next((o for o in offers if o["profile"] == "standard"), offers[len(offers) // 2])


def _truck(plant: factory.Plant, offer: dict[str, Any], reorder: int) -> int:
    """Camion d'une matière : à plusieurs produits, les racks sont communs, donc la part des lignes du produit
    moins le point de commande (au plus un camion de six) ; à un produit, le camion standard."""
    if plant.np == 1:
        return MAX_TRUCK_PALLETS
    share = plant.lg["mp_capacity_pallets"] * plant.line_prod.count(plant.p_of_comp[offer["component_id"]]) // plant.nl
    return max(offer["min_order"], min(MAX_TRUCK_PALLETS, share - reorder))


def _autopilot(
    spec: dict[str, Any], plant: factory.Plant, state: dict[str, Any], played: set[str]
) -> dict[str, Any] | None:
    """Une action que personne n'a jouée tourne seule (règle de la spec) ;
    `played` = actions jouées par un humain. Réglages
    posés ici ; les règles de pilotage (OF et matière) sont rendues au noyau, qui les applique CHAQUE jour simulé :
    - OF : position PF (stock + en-cours bon - commandes ouvertes) < `pf_min` -> campagne : OF sur chaque ligne
      jusqu'à `pf_max` (limité par le magasin PF) ;
    - MP : stock + palettes commandées <= (délai + revue 1 jour + stock de sécurité) jours de matière
      -> un camion standard
      de six palettes au plus, dans la limite du magasin et de la trésorerie."""
    settings = state["fs"]["settings"]
    if "preventif" not in played:
        settings["preventive"] = dict.fromkeys(plant.line_ids, "goulot")
    if "priorite_reparation" not in played:
        settings["priority"] = "arrivee"
    if plant.spares and "pieces_rechange" not in played:
        settings["spares"] = None  # S* du pilote
    if "proteger_goulot" not in played:
        settings["protect"] = dict.fromkeys(plant.line_ids, "aucune")
    if {"commander_mp", "lancer_of"} <= played:
        return None
    budget = state["cash"] - _engaged(plant, state)  # déjà engagé ; un budget commun, pris dans la première règle
    orders = [
        {"offer": offer, "reorder": (ro := _reorder_point(spec, plant, offer)), "truck": _truck(plant, offer, ro),
         "cost_index": state["cost_index"], "budget": budget}
        for offer in (_standard_offer(spec, c) for c in plant.comps)
    ]  # fmt: skip
    rules = {
        "order": orders if plant.multi else orders[0],
        "launch": {"pf_max": spec["factory"].get("pf_max") or plant.pf_min,
                   "yields": dict(zip(plant.line_ids, _yields(plant), strict=True))},
    }  # fmt: skip
    if "commander_mp" in played:  # une seule des deux actions de pilotage est jouée : l'autre garde sa règle
        del rules["order"]
    if "lancer_of" in played:
        del rules["launch"]
    return rules


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
    rows = _by_product(plant, report)
    price = {p["id"]: p["price"] for p in spec["products"]}
    revenue = sum(r["shipped"] * price[r["product_id"]] for r in rows)  # somme par produit (annexe 0013 §3 bis)
    staff = sum(m["operators"] for m in plant.machines) * plant.days * plant.mpd / 60 * plant.costs["operator_per_h"]
    relief = report["relief_min"] / 60 * plant.costs["operator_per_h"]
    costs = {"repair": report["costs"]["repair"], "preventive": report["costs"]["preventive"],
             "staff": staff, "relief": relief, "mp": report["costs"]["mp"]}  # fmt: skip
    if "spares" in report["costs"]:  # pièces : commande + possession (absent sans spares : coûts d'avant)
        costs["spares"] = report["costs"]["spares"]
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
        {"week": week, **kpis, "event": new["last"]["event"], "lost": lost, "returns": 0, "delays": len(delayed),
         "wear": _wear(plant, report, effects.get("mtbf", 1.0)), "preventive": len(report["preventive"]["done"]),
         "by_product": _week_products(spec, plant, new["fs"], rows)}
        | ({"spares": _week_spares(report["spares"])} if "spares" in report else {})
    )  # fmt: skip
    if week >= spec["meta"]["weeks"]:
        new["status"], new["event"] = "finished", None
    else:
        new["week"], new["event"] = week + 1, roll_event(spec, week + 1)
    return new


def _week_spares(sp: dict[str, Any]) -> dict[str, Any]:
    """Pièces de la semaine : utilisées, pannes en attente, minutes d'attente, achat et possession (€)."""
    return {"used": sp["used"], "missing": sp["missing"], "wait_min": round(sp["wait_min"]), "bought": sp["bought"],
            "purchase": round(sp["purchase"], 2), "holding": round(sp["holding"], 2)}  # fmt: skip


def _by_product(plant: factory.Plant, report: dict[str, Any]) -> list[dict[str, Any]]:
    """Expédié, palettes emballées, commandes échues et à l'heure du tour, par produit (un produit : le rapport)."""
    return report.get("by_product") or [
        {"product_id": plant.pids[0], "shipped": report["shipped"], "pallets": report["packed"]["pallets"],
         "due": report["orders"]["due"], "on_time": report["orders"]["on_time"]}
    ]  # fmt: skip


def _week_products(
    spec: dict[str, Any], plant: factory.Plant, fs: dict[str, Any], rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Ligne par produit de l'historique : stock PF en fin de tour, expédié et OTIF (0-100) de la semaine."""
    names, stock = {p["id"]: p["name"] for p in spec["products"]}, _pf_by(plant, fs)
    return [
        {"product_id": r["product_id"], "name": names[r["product_id"]], "quantity": stock[i],
         "pallets": -(-stock[i] // plant.pallet_pf), "shipped": r["shipped"],
         "otif": round(100 * r["on_time"] / r["due"], 1) if r["due"] else None}
        for i, r in enumerate(rows)
    ]  # fmt: skip


def _game_products(spec: dict[str, Any], state: dict[str, Any], plant: factory.Plant) -> list[dict[str, Any]]:
    """Table par produit de la partie : stock PF actuel, expédié cumulé, OTIF moyen des semaines (vue et débrief)."""
    weeks = [h["by_product"] for h in state["history"] if h.get("by_product")]
    now = _week_products(spec, plant, state["fs"], [
        {"product_id": pid, "shipped": 0, "due": 0, "on_time": 0} for pid in plant.pids
    ])  # fmt: skip
    for i, row in enumerate(now):
        otifs = [w[i]["otif"] for w in weeks if w[i]["otif"] is not None]
        row["shipped"] = sum(w[i]["shipped"] for w in weeks)
        row["otif"] = round(sum(otifs) / len(otifs), 1) if otifs else None
    return now


def _game_spares(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Débrief : pièces semaine par semaine et cumul (sans valeur du pilote : le bilan n'en compare aucune)."""
    weeks = [{"week": h["week"], **h["spares"]} for h in history if "spares" in h]
    keys = ("used", "missing", "wait_min", "bought", "purchase", "holding")
    return {"weeks": weeks, "total": {k: round(sum(w[k] for w in weeks), 2) for k in keys}}


def _wear(plant: factory.Plant, report: dict[str, Any], mtbf_factor: float) -> dict[str, Any]:
    """Par goulot : heures de marche, pannes attendues (heures de marche / MTBF) et observées, arrêt, préventifs."""
    out = {}
    for i in plant.bottleneck:
        mid, mc = plant.mids[i], plant.machines[i]
        r = report["machines"][mid]
        run_h = r["minutes"]["marche"] / 60
        out[mid] = {"run_h": round(run_h, 2), "expected": round(run_h / (mc["mtbf_h"] * mtbf_factor), 3),
                    "failures": r["failures"], "down_h": round(r["minutes"]["panne"] / 60, 2),
                    "preventive": report["preventive"]["done"].count(mid)}  # fmt: skip
    return out


def bottleneck_wear(spec: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    """Pannes des goulots sur la partie, regroupés par forme d'usure et par entretien (préventif fait ou non) :
    observées, attendues (fiche MTBF : heures de marche / MTBF), évitées (attendues - observées, affichées si
    >= 2 racine(attendues) : seuil de calibrage, sinon `avoided` vaut None), arrêt en heures."""
    plant, groups = factory.Plant(spec), {}
    for i in plant.bottleneck:
        mid, mc = plant.mids[i], plant.machines[i]
        ws = [h["wear"][mid] for h in state["history"] if mid in h.get("wear", {})]
        if not ws:
            continue
        prev = sum(w["preventive"] for w in ws)
        g = groups.setdefault((mc["weibull_shape"], prev > 0), {
            "names": [], "lines": 0, "shape": mc["weibull_shape"], "mttr_h": mc["mttr_h"], "failures": 0,
            "expected": 0.0, "down_h": 0.0, "preventive": 0, "with_preventive": prev > 0})  # fmt: skip
        g["names"] += [mc["name"]] if mc["name"] not in g["names"] else []
        g["lines"] += 1
        g["failures"] += sum(w["failures"] for w in ws)
        g["expected"] += sum(w["expected"] for w in ws)
        g["down_h"] += sum(w["down_h"] for w in ws)
        g["preventive"] += prev
    for g in groups.values():
        avoided = g["expected"] - g["failures"]
        g["avoided"] = round(avoided, 1) if avoided >= 2 * math.sqrt(g["expected"]) and avoided > 0 else None
        costs = spec["factory"]["costs"]
        counted = g["shape"] > 1 and g["with_preventive"] and g["avoided"] is not None
        per_failure = (
            g["mttr_h"] * costs["repair_per_h"]
            + costs.get("damage_per_failure", 0.0)
            + (spec["factory"].get("spares") or {}).get("price", 0.0)
        )  # pièce usée par la panne
        g["avoided_cost"] = g["avoided"] * per_failure if counted else None
        g["expected"], g["down_h"] = round(g["expected"], 1), round(g["down_h"], 1)
        g["expected_without_preventive"] = g["expected"]  # pannes attendues sans entretien, telles qu'affichées
        g["label"] = " / ".join(g["names"]) + (f" ({g['lines']} lignes)" if g["lines"] > 1 else "")
    return list(groups.values())


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
        # planifié : hors arrêts et pauses (convention du jeu, fiche wikipedia-fr-taux-de-rendement-synthetique l.48)
        planned_h = (T - b["arret"] - b["pause"]) / 60
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
    rec = report["reception"]
    delivered = rec["accepted"] + rec["quarantined"] if plant.multi else rec["pallets"] * plant.upp  # palettes mêlées
    edges = [["fournisseur", "reception", delivered], ["reception", "stock_mp", rec["accepted"]]]
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


_SP_STOCK_KEYS = ("stock", "transit", "target")


def _spare_stocks(plant: factory.Plant, fs: dict[str, Any]) -> list[dict[str, Any]]:
    """Stock de pièces par type de machine : en rayon, en route, visé, en attente (format des autres stocks)."""
    sp = fs["spares"]
    return [
        {"type": t, "name": " / ".join(dict.fromkeys(m["name"] for m, mt in zip(plant.machines, plant.mtype,
                                                                               strict=True) if mt == t)),
         "quantity": sp["stock"][t], "pending": sp["transit"][t], "target": sp["target"][t],
         "waiting": len(sp["waiting"][t])}
        for t in plant.types
    ]  # fmt: skip


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
    names = {c["id"]: c["name"] for c in spec["components"]}
    mp_stocks = [  # une entrée par matière
        {
            "component_id": cid,
            "name": names[cid],
            "quantity": units,
            "pallets": -(-units // upp),
            "capacity_pallets": plant.lg["mp_capacity_pallets"],
            "reorder_point": _reorder_point(spec, plant, _standard_offer(spec, cid)),
            "pending": sum(po["pallets"] for po in fs["pending"] if po["component_id"] == cid),
        }
        for cid, units, upp in zip(plant.comps, _mp_by(plant, fs, "units"), plant.upps, strict=True)
    ]  # fmt: skip
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
            "mp": mp_stocks,
            "pf": {
                "quantity": pf,
                "pallets": -(-pf // plant.pallet_pf),
                "capacity_pallets": plant.lg["pf_capacity_pallets"],
                "min": plant.pf_min,
            },
            "quarantine": fs["mp"]["quarantine"],
            **({"spares": _spare_stocks(plant, fs)} if plant.spares else {}),
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
                    "client_id": o.get("client_id", "c1"),
                    "product_id": o.get("product_id", plant.pids[0]),
                }
                for o in customer
            ],  # fmt: skip
        },
        "by_product": _game_products(spec, state, plant),
        **(
            {"spares_week": {k: v for k, v in snap["report"]["spares"].items() if k not in _SP_STOCK_KEYS}}
            if plant.spares and snap.get("report")
            else {}
        ),  # semaine passée : used, missing, wait_min, bought, ...
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


DAY_NAMES = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _waiting_spares(plant: factory.Plant, fs: dict[str, Any]) -> dict[str, tuple[str, int]]:
    """Machines qui attendent leur pièce : id -> (jour de livraison, stock visé de leur type). La k-ième machine en
    attente d'un type reçoit la k-ième livraison en route (événements `spare` gardés dans fs["events"])."""
    if not plant.spares:
        return {}
    sp, out = fs["spares"], {}
    for t, waiting in sp["waiting"].items():
        due = sorted(e[0] for e in fs["events"] if e[3] == "spare" and e[4] == t)
        for k, (_, i) in enumerate(waiting[: len(due)]):
            day = (fs["day"] + int(due[k] // plant.mpd)) % plant.days  # semaine de plant.days jours dès le lundi
            out[plant.mids[i]] = (DAY_NAMES[day], sp["target"][t])
    return out


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

    held = sum(m["pallets"] + m["pending"] for m in f["stocks"]["mp"])  # le magasin est commun à toutes les matières
    plant = factory.Plant(spec)
    for mp in f["stocks"]["mp"]:
        if mp["pallets"] + mp["pending"] < mp["reorder_point"]:
            offer = _standard_offer(spec, mp["component_id"])
            truck = _truck(plant, offer, mp["reorder_point"])
            pallets = min(truck, mp["capacity_pallets"] - held)
            order = (
                ("commander_mp", {"offer": offer["id"], "pallets": pallets}) if pallets >= offer["min_order"] else None
            )
            cid = mp["component_id"]
            emit("reorder", f"reorder:{cid}", mp, ref=f"mp:{cid}", action=order)
    snap = state.get("snap") or {}
    for lid, line in (((snap.get("report") or {}).get("lines")) or {}).items():
        if line["stockout_min"]:
            emit(
                "starved",
                f"starved:{lid}",
                {"line": _name(spec, lid), "stockout_min": round(line["stockout_min"])},
                ref=f"line:{lid}",
            )
    for m in f["machines"]:
        if m["state"] == "panne":
            emit(
                "breakdown_goulot" if m["bottleneck"] else "breakdown",
                f"breakdown:{m['id']}",
                {"machine": m["name"]},
                ref=f"machine:{m['id']}",
            )
    chosen = state["fs"]["settings"].get("spares")  # réglage du joueur (None : S* du pilote)
    for mid, (day, target) in _waiting_spares(plant, state["fs"]).items():
        name = next(m["name"] for m in f["machines"] if m["id"] == mid)
        kind = plant.mtype[plant.mids.index(mid)]
        keep = chosen and factory.spares_target(plant, chosen | {"pieces": 1})[kind] > 0  # sa cible couvre ce type
        emit(
            "spare_missing",
            f"spare_missing:{mid}",
            {"machine": name, "day": day},
            ref=f"machine:{mid}",
            action=("pieces_rechange", {"cible": chosen["cible"] if keep else "toutes", "pieces": target + 1})
            if target < 6
            else None,
        )
    threshold = tpl.get("trs_low", {}).get("threshold")
    for lid, line in (snap.get("lines") or {}).items():
        if threshold is not None and line["trs"] is not None and line["trs"] < threshold:
            emit(
                "trs_low", f"trs_low:{lid}", {"line": _name(spec, lid), "trs": f"{num(line['trs'])}"}, ref=f"line:{lid}"
            )
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
        "history": history, "by_product": _game_products(spec, state, factory.Plant(spec)),
        **({"spares": _game_spares(history)} if any("spares" in h for h in history) else {}),
        "lessons": _lessons(spec, state), "bottlenecks": bottleneck_wear(spec, state),
        "preventive": preventive_balance(spec, state),
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
        weeks = sum(1 for h in history if h["stockouts"])
        reorder = _reorder_point(spec, factory.Plant(spec), _standard_offer(spec, spec["components"][0]["id"]))
        lessons.append(
            f"{starved} jour(s)-ligne arrêté(s) faute de matière, sur {weeks} semaine(s). Repère : recommandez quand "
            "stock et palettes commandées passent sous le point de commande (consommation pendant le délai + stock "
            f"de sécurité) ; le pilote automatique de ce jeu le place à {reorder} palettes."
        )
    otif = engine._mean(history, "otif")
    if otif is not None and otif < targets["otif"]:
        late = sum(h["delays"] for h in history)
        both = sum(1 for h in history if h["delays"] and h["stockouts"])
        shared = f" ; {both} des semaines concernées ont aussi eu des lignes arrêtées faute de matière" if both else ""
        lessons.append(
            f"OTIF moyen de {num(otif)} % pour un objectif de {num(targets['otif'], 0)} % : "
            f"{late} commande(s) client en "
            f"retard{shared}. Une commande ne compte que si elle part complète au plus tard le jour promis."
        )
    trs = engine._mean(history, "trs")
    if trs is not None and trs < targets["trs"]:
        good = engine._mean(history, "good_share")
        plant = factory.Plant(spec)
        shapes = [plant.machines[i]["weibull_shape"] for i in plant.bottleneck]
        wear, random_ = all(k > 1 for k in shapes), all(k <= 1 for k in shapes)
        lessons.append(
            f"TRS moyen de {num(trs)} % pour un objectif de {num(targets['trs'], 0)} %"
            + (f", avec {num(good)} % de produits bons" if good is not None else "")
            + ". Le TRS d'une ligne se mesure sur son goulot : pannes, attentes, ralentissements et rebuts le font "
            "baisser."
            + (
                " Ici, le risque de panne croît avec l'âge de la machine et un préventif le remet à zéro."
                if wear
                else " Ici, les pannes du goulot arrivent au hasard : un préventif à date fixe ne les évite pas."
                if random_
                else ""
            )
        )
    if state["cash"] < targets["cash_final"]:
        previous = [spec["economy"]["initial_cash"]] + [h["cash"] for h in history[:-1]]
        down = sum(1 for h, before in zip(history, previous, strict=True) if h["cash"] < before)
        lessons.append(
            f"Trésorerie finale de {money(state['cash'])}, sous l'objectif de {money(targets['cash_final'])} ; elle "
            f"a baissé sur {down} semaine(s). Ici, chaque produit expédié est encaissé ; la matière reçue, les "
            "opérateurs, les réparations et le préventif sont payés."
        )
    if not lessons:
        lessons.append(
            "Objectifs atteints : aucune ligne arrêtée faute de matière, "
            + (f"OTIF moyen de {num(otif)} %, " if otif is not None else "")
            + (f"TRS moyen de {num(trs)} %, " if trs is not None else "")
            + f"trésorerie finale de {money(state['cash'])}."
        )
    return lessons + _wear_lessons(spec, state)


def _wear_lessons(spec: dict[str, Any], state: dict[str, Any]) -> list[str]:
    """Une leçon par goulot (usure avec préventif, usure sans préventif, hasard) et le bilan du préventif."""
    lessons = []
    for w in bottleneck_wear(spec, state):
        n, x, a, name = w["failures"], num(w["expected"]), w["avoided"], w["label"]
        f = f"{n} {'panne' if n <= 1 else 'pannes'}"
        if w["shape"] <= 1:
            lessons.append(
                f"{name} : {f} pour {x} attendues d'après son MTBF, {'avec' if w['with_preventive'] else 'sans'} "
                "préventif. Ses pannes arrivent au hasard, quel que soit son âge : l'entretien à date fixe ne les "
                "évite pas."
            )
        elif w["with_preventive"] and a is not None:
            lessons.append(
                f"{name} : {f} pour {x} attendues sans entretien d'après son MTBF ; le préventif en a évité environ "
                f"{num(a, 0)} ({num(a * w['mttr_h'], 0)} h d'arrêt). Son risque de panne croît avec l'âge et "
                "l'entretien le remet à zéro."
            )
        elif w["with_preventive"]:
            lessons.append(
                f"{name} : {f} pour {x} attendues sans entretien d'après son MTBF ; l'écart reste dans les "
                "variations du hasard : on ne peut pas dire combien le préventif en a évité."
            )
        else:
            lessons.append(
                f"{name} : {f} pour {x} attendues d'après son MTBF, sans préventif. Son risque croît avec l'âge : "
                "un entretien régulier en aurait évité une partie."
            )
    b = preventive_balance(spec, state)
    if b["done"]:
        lessons.append(
            f"Préventif : {money(b['cost'])} ; réparations et dégâts évités : "
            + (
                "non chiffrables (écart dans les variations du hasard)"
                if b["avoided_cost"] is None
                else f"environ {money(b['avoided_cost'])}"
            )
            + f" ; ventes perdues : {b['lost']} produit(s)."
        )
    return lessons


def preventive_balance(spec: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Bilan du préventif, valeurs avant arrondi (le texte arrondit à l'affichage)."""
    done = sum(h.get("preventive", 0) for h in state["history"])
    costs = [w["avoided_cost"] for w in bottleneck_wear(spec, state) if w["avoided_cost"] is not None]
    avoided = sum(costs) if costs else None  # None : pannes évitées non chiffrables (sous le seuil du hasard)
    return {
        "done": done, "cost": done * spec["factory"]["costs"]["preventive_per_intervention"],
        "avoided_cost": avoided,
        "lost": sum(h["lost"] for h in state["history"]),
    }  # fmt: skip


# --- informations essentielles des agents (briefings) ---------------------------------------------------------------

Fact = tuple[bool, str]


def _rep(state: dict[str, Any]) -> dict[str, Any] | None:
    return (state.get("snap") or {}).get("report")


def _facts_fournisseur(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    pending = state["fs"]["pending"]
    facts: list[Fact] = [
        (
            False,
            f"{len(pending)} commande(s) de matière en route, "
            f"soit {num(sum(p['pallets'] for p in pending), 0)} palettes.",
        )
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
            facts.append(
                (True, f"{num(r['quarantined'], 0)} produits de matière mis en quarantaine : palettes non conformes.")
            )
        facts.append((False, f"Semaine passée : {r['trucks']} camion(s) déchargé(s), {num(r['pallets'], 0)} palettes."))
        if rep["dock"]["wait_min"] > 30:
            facts.append((False, f"Les camions ont attendu un quai {num(rep['dock']['wait_min'], 0)} minutes en tout."))
    if due:
        facts.append((False, f"Prochaine livraison attendue dans {max(min(due), 0)} jour(s)."))
    return facts or [(False, "Aucun camion attendu pour l'instant.")]


def _facts_stock_mp(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    stocks = view["factory"]["stocks"]["mp"]  # une matière par produit (3 au plus)
    rep = _rep(state)
    facts: list[Fact] = []
    stopped = [line["stockout_min"] for line in rep["lines"].values() if line["stockout_min"]] if rep else []
    if stopped:  # somme sur les lignes : à dire comme un total, pas comme la durée d'une ligne
        total, n = num(sum(stopped), 0), len(rep["lines"])
        facts.append((True, f"Les {n} lignes ont été arrêtées {total} minutes au total faute de matière.")
                     if n > 1 else (True, f"La ligne a été arrêtée {total} minutes faute de matière."))  # fmt: skip
    pallets, pending = sum(m["pallets"] for m in stocks), sum(m["pending"] for m in stocks)
    left = stocks[0]["capacity_pallets"] - pallets - pending  # un magasin commun à toutes les matières
    for mp in stocks:
        if mp["pallets"] + mp["pending"] < mp["reorder_point"]:
            what = f"{mp['name']} : " if len(stocks) > 1 else ""
            stock = f"{what}{num(mp['pallets'], 0)} palettes en stock et {num(mp['pending'], 0)} en commande"
            facts.append(
                (True, f"{stock}, sous le point de commande de {num(mp['reorder_point'], 0)} : il faut commander.")
            )
    facts.append(
        (
            False,
            f"Magasin : {num(pallets, 0)} palettes sur {num(stocks[0]['capacity_pallets'], 0)} places, "
            f"{num(max(left, 0), 0)} libres une fois comptées les {num(pending, 0)} en commande.",
        )
    )
    if len(stocks) > 1:  # le stock de chaque matière, en palettes
        facts.append(
            (False, " ; ".join(f"{m['name']} : {num(m['pallets'], 0)} palettes en stock" for m in stocks) + ".")
        )
    return facts


def _facts_production(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    f = view["factory"]
    facts: list[Fact] = []
    for m in f["machines"]:
        if m["bottleneck"] and m["state"] == "panne":
            facts.append((True, f"Le goulot {m['name']} est en panne."))
    products = {p["id"]: p["name"] for p in spec["products"]}
    made = {ln["id"]: products[ln["product_id"]] for ln in spec["lines"]}
    for line in f["lines"]:
        if line["real_h"] is not None:
            slow = line["real_h"] < 0.9 * line["expected_h"]
            what = f"{line['name']} ({made[line['id']]})" if len(products) > 1 else line["name"]  # produit de la ligne
            facts.append(
                (
                    slow,
                    f"{what} : {num(line['real_h'])} bons par heure mesurés pour {num(line['expected_h'])} attendus.",
                )
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
    facts: list[Fact] = [
        (False, f"Semaine passée : {num(rep['controlled'], 0)} produits contrôlés, {num(scrap, 0)} rebuts.")
    ]
    if shares["measured"] is not None and shares["measured"] < shares["expected"] - 2:
        facts.insert(
            0, (True, f"Part de bons de {num(shares['measured'])} % pour {num(shares['expected'])} % attendus.")
        )
    return facts


def _facts_emballage(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    rep, plant_pallet = _rep(state), view["factory"]["stocks"]["pf"]
    facts: list[Fact] = []
    waiting = view["factory"]["products"]["conforme"]
    if waiting > 2 * spec["factory"]["logistics"]["units_per_case"] * spec["factory"]["logistics"]["cases_per_pallet"]:
        facts.append((True, f"{num(waiting, 0)} produits bons attendent d'être emballés."))
    if rep:
        facts.append(
            (
                False,
                f"Semaine passée : {num(rep['packed']['cases'], 0)} cartons "
                f"et {num(rep['packed']['pallets'], 0)} palettes.",
            )
        )
    facts.append(
        (
            False,
            f"Entrepôt PF : {num(plant_pallet['pallets'], 0)} palettes sur {num(plant_pallet['capacity_pallets'], 0)}.",
        )
    )
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
        facts.append(
            (worst["bottleneck"], f"{worst['name']} a perdu {num(worst['downtime_min'], 0)} minutes en panne.")
        )
    facts.append((False, f"Semaine passée : {total} panne(s) au total."))
    facts += [(False, f"{w['label']} : {w['failures']} panne(s) depuis le début, {num(w['expected'])} attendue(s) "
                      "sans entretien d'après son MTBF.") for w in bottleneck_wear(spec, state)]  # fmt: skip
    if rep["technician"]["waited"]:
        facts.append((False, f"{rep['technician']['waited']} panne(s) ont attendu le technicien."))
    if "spares" in rep:
        sp = rep["spares"]
        names = {s["type"]: s["name"] for s in f["stocks"]["spares"]}
        facts.append((False, "Pièces de rechange en stock : "
                      + " ; ".join(f"{names[t]} {n}" for t, n in sp["stock"].items()) + "."))  # fmt: skip
        if sp["missing"]:
            facts.append((True, f"{sp['missing']} panne(s) ont attendu une pièce, {num(sp['wait_min'], 0)} minutes "
                                "d'attente au total."))  # fmt: skip
    done, skipped = len(rep["preventive"]["done"]), len(rep["preventive"]["skipped"])
    facts.append((False, f"Préventif : {done} fait(s), {skipped} non fait(s)."))
    return facts


def _facts_pilotage(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    f, targets = view["factory"], spec["targets"]
    orders = f["orders"]["customer"]
    late = [o for o in orders if o["status"] == "en_retard"]
    open_ = [o for o in orders if o["status"] != "livree"]
    stock = f["stocks"]["pf"]
    facts: list[Fact] = [(bool(late), f"{len(open_)} commande(s) ouverte(s), dont {len(late)} en retard.")]
    prod_of_line = factory.Plant(spec).prod_of_line
    for p, row in enumerate(f["by_product"]):  # le minimum s'applique à chaque produit (pf_min commun)
        wip = sum(line["wip"] for line in f["lines"] if prod_of_line[line["id"]] == p)
        if row["quantity"] + wip < stock["min"]:
            what = "Stock fini" if len(f["by_product"]) == 1 else f"{row['name']} : stock fini"
            facts.append(
                (True, f"{what} et en-cours à {row['quantity'] + wip}, sous le minimum de {stock['min']} : "
                       "lancer des ordres.")
            )  # fmt: skip
    otif, trs = view["kpis"]["otif"], view["kpis"]["trs"]
    if otif is not None:
        facts.append(
            (
                False,
                f"OTIF à {num(otif, 0)} % (objectif {num(targets['otif'], 0)} %), "
                f"TRS à {num(trs, 0)} % (objectif {num(targets['trs'], 0)} %).",
            )
        )
    return facts


def _facts_entrepot_pf(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    stock, by_product = view["factory"]["stocks"]["pf"], view["factory"]["by_product"]
    late = sum(1 for o in view["factory"]["orders"]["customer"] if o["status"] == "en_retard")
    facts: list[Fact] = []
    if stock["pallets"] >= stock["capacity_pallets"]:
        facts.append((True, "L'entrepôt est plein : l'emballage ne peut plus ranger de palette."))
    if late:
        facts.append((True, f"{late} commande(s) en retard faute de stock complet."))
    facts.append((False, f"{stock['pallets']} palettes en stock sur {stock['capacity_pallets']} places."))
    if len(by_product) > 1:  # une palette ne porte qu'un produit
        facts.append((False, " ; ".join(f"{r['name']} : {r['pallets']} palettes" for r in by_product) + "."))
    return facts


def _facts_client(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[Fact]:
    otif, targets = view["kpis"]["otif"], spec["targets"]
    mine = [o for o in view["factory"]["orders"]["customer"] if o["client_id"] == "c1"]  # le PNJ parle de c1 seul
    open_ = [o for o in mine if o["status"] != "livree"]
    facts: list[Fact] = []
    multi = bool(spec["factory"].get("clients"))
    late = sum(1 for o in open_ if o["status"] == "en_retard")
    if multi and late:  # l'OTIF agrégé mêle les clients : le client ne cite que ses commandes
        facts.append((True, f"{late} de nos commande(s) sont en retard."))
    elif not multi and otif is not None and otif < targets["otif"]:
        facts.append(
            (
                True,
                f"Livraisons à l'heure et complètes : {num(otif, 0)} %, "
                f"sous l'objectif de {num(targets['otif'], 0)} %.",
            )
        )
    facts.append((False, f"{len(open_)} commande(s) attendue(s) chez nous."))
    return facts


engine._HANDLERS.update({
    ("pilotage", "lancer_of"): _h_launch, ("pilotage", "commander_mp"): _h_order,
    ("production", "proteger_goulot"): _h_protect, ("maintenance", "preventif"): _h_preventive,
    ("maintenance", "priorite_reparation"): _h_priority, ("maintenance", "pieces_rechange"): _h_spares,
})  # fmt: skip
engine._FACTS.update({
    "usine_fournisseur": _facts_fournisseur, "usine_reception": _facts_reception, "usine_stock_mp": _facts_stock_mp,
    "usine_production": _facts_production, "usine_qualite": _facts_qualite, "usine_emballage": _facts_emballage,
    "usine_maintenance": _facts_maintenance, "usine_pilotage": _facts_pilotage,
    "usine_entrepot_pf": _facts_entrepot_pf, "usine_client": _facts_client,
})  # fmt: skip
