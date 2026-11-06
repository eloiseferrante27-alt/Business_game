"""Moteur des business games simulés (docs/decisions/0006), sur le principe du jeu de référence : chaque semaine,
les joueurs agissent par modules (commandes, plan de production, entretien, contrôle, prix, transport,
découvert), puis la semaine est simulée : livraisons fournisseurs selon leur délai et leur fiabilité, usure et
pannes des lignes, production limitée par la capacité, le TRS et les composants, défauts, demande de l'enseigne,
livraisons (OTIF), coûts et trésorerie. Un module que le formateur n'a pas choisi tourne en pilote automatique.

Les aléas sont tirés une semaine à l'avance et annoncés : les agents préviennent les joueurs, qui peuvent anticiper.
Fonctions pures et déterministes (le hasard dépend de la graine de la spec et du numéro de semaine) : l'API lit
lobbies.state, appelle le moteur sous verrou de ligne et enregistre le nouvel état.
"""

import copy
import math
import random
from typing import Any

CONTROL_RATES = {"0": 0.0, "50": 0.5, "100": 1.0}
PRICE_LEVELS = {"0.9": 0.9, "1.0": 1.0, "1.1": 1.1}
OVERDRAFTS = {"0": 0, "20000": 20000, "50000": 50000}
COVERAGE_WEEKS = 2  # pilote automatique : stock visé en fin de semaine, en semaines de demande
LEVEL_LABELS = {"aucune": "aucun entretien", "preventive": "entretien préventif", "renforcee": "entretien renforcé"}
TRANSPORT_LABELS = {"economique": "groupage", "standard": "messagerie", "express": "express"}


class GameRuleError(ValueError):
    """Action refusée par les règles ; le message est affichable au joueur."""


def money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ") + " €"


def initial_state(spec: dict[str, Any]) -> dict[str, Any]:
    if spec.get("factory"):
        return factory_game.initial_state(spec)
    active = {m["id"] for m in spec["modules"]}
    standard = _standard_offers(spec)
    pending = []
    for index, component in enumerate(spec["components"], start=1):  # commandes déjà passées avant la partie
        offer = standard[component["id"]]
        quantity = max(offer["min_order"], math.ceil(component["usage"] / 50) * 50)
        pending.append(_order(f"cmd{index}", offer, quantity, offer["unit_cost"], week=0, arrival=2))
    return {
        "status": "waiting",
        "week": 1,
        "cash": spec["economy"]["initial_cash"],
        "stocks": {p["id"]: p["initial_stock"] for p in spec["products"]},
        "components": {c["id"]: c["initial_stock"] for c in spec["components"]},
        "lines": {line["id"]: {"trs": line["trs"], "down": False} for line in spec["lines"]},
        "settings": {
            "plan": {
                line["id"]: min(line["capacity"], _product(spec, line["product_id"])["demand"])
                for line in spec["lines"]
            },
            "maintenance": {line["id"]: "preventive" for line in spec["lines"]},
            "control": "50",
            "transport": "standard",
            "price": {p["id"]: "1.0" for p in spec["products"]},
            "overdraft": "0" if "finance" in active else None,
        },
        "pending": pending,
        "order_seq": len(pending),
        "cost_index": 1.0,
        "event": None,
        "history": [],
        "log": [],
        "last": None,
    }


def start(spec: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    if state["status"] != "waiting":
        raise GameRuleError("La partie a déjà commencé")
    new = copy.deepcopy(state)
    new["status"] = "running"
    new["event"] = factory_game.roll_event(spec, 1) if spec.get("factory") else _roll_event(spec, 1)
    return new


def act(
    spec: dict[str, Any],
    state: dict[str, Any],
    module_id: str,
    action_id: str,
    values: dict[str, Any],
    *,
    actor: dict[str, Any],
    manager: bool,
    occupied_roles: set[str] | None = None,  # conservé pour les appelants ; le droit est celui du rôle (annexe 0010 §5)
) -> tuple[dict[str, Any], str]:
    """Action d'un joueur. Un non-gestionnaire n'agit que sur le module de son rôle ; le formateur agit partout (un
    module sans joueur tourne en pilote automatique, sauf la semaine où le formateur y a agi : voir `advance`)."""
    if state["status"] != "running":
        raise GameRuleError("La partie n'est pas en cours")
    module = next((m for m in spec["modules"] if m["id"] == module_id), None)
    action = next((a for a in module["actions"] if a["id"] == action_id), None) if module else None
    if module is None or action is None:
        raise GameRuleError("Action inconnue dans ce business game")
    role = next(r for r in spec["roles"] if r["id"] == module["role_id"])
    mine = actor.get("role") == role["id"]
    if not manager and not mine:
        if not actor.get("role"):
            raise GameRuleError("Choisissez un rôle")
        raise GameRuleError(f"Cette action revient au rôle « {role['title']} »")
    clean = _validate(spec, action, values)
    new = copy.deepcopy(state)
    summary = _HANDLERS[(module_id, action_id)](spec, new, clean)
    new["log"].append(
        {"week": new["week"], "kind": "decision", "module": module_id, "action": action_id,
         "user_id": actor.get("user_id"), "name": actor.get("name"), "by": "joueur" if mine else "formateur",
         "summary": summary, "ref": None}
    )  # fmt: skip
    return new, summary


def advance(
    spec: dict[str, Any], state: dict[str, Any], *, autopilot_all: bool = False, held_roles: set[str] | None = None
) -> dict[str, Any]:
    """Simule la semaine en cours, puis passe à la suivante (ou termine la partie après la dernière). `held_roles` :
    rôles tenus ; seuls leurs modules (et ceux où le formateur a agi cette semaine) sont joués, les autres passent en
    pilote automatique pour la semaine. `None` : tous les modules sont joués."""
    if state["status"] != "running":
        raise GameRuleError("La partie n'est pas en cours")
    played = played_modules(spec, state, autopilot_all, held_roles)
    entries = _week_entries(spec, state, played)
    if spec.get("factory"):
        new = factory_game.advance(spec, state, played)
    else:
        new = copy.deepcopy(state)
        week = new["week"]
        report = _simulate(spec, new, week, played)
        new["last"] = report
        new["history"].append(
            {"week": week, **report["kpis"], "event": report["event"], "lost": report["totals"]["lost"],
             "returns": report["totals"]["returns"], "delays": len(report["delayed"])}
        )  # fmt: skip
        if week >= spec["meta"]["weeks"]:
            new["status"], new["event"] = "finished", None
        else:
            new["week"], new["event"] = week + 1, _roll_event(spec, week + 1)
    new["log"] += entries
    return new


def played_modules(
    spec: dict[str, Any], state: dict[str, Any], autopilot_all: bool = False, held_roles: set[str] | None = None
) -> set[str]:
    """Modules joués cette semaine : tous (`held_roles` None), ceux des rôles tenus et ceux où une décision est au
    journal de la semaine (un module libre quitte le pilote automatique la semaine où le formateur y agit)."""
    if autopilot_all:
        return set()
    if held_roles is None:
        return {m["id"] for m in spec["modules"]}
    acted = {
        e["module"] for e in state["log"] if e["week"] == state["week"] and e.get("kind", "decision") == "decision"
    }
    return {m["id"] for m in spec["modules"] if m["role_id"] in held_roles or m["id"] in acted}


def _week_entries(spec: dict[str, Any], state: dict[str, Any], played: set[str]) -> list[dict[str, Any]]:
    """Journal de la semaine qui s'achève : un module en pilote automatique, l'aléa appliqué (sauf s'il est déjà
    écrit par `force_event`)."""
    week, entries = state["week"], []
    for module in spec["modules"]:
        if module["id"] not in played:
            entries.append(_entry(week, "auto", "moteur", f"Pilote automatique : {module['autopilot']}",
                                  module=module["id"]))  # fmt: skip
    event = _event(spec, state.get("event"))
    if event and not any(e["week"] == week and e.get("kind") == "alea" and e.get("ref") == event["id"]
                         for e in state["log"]):  # fmt: skip
        entries.append(_entry(week, "alea", "moteur", f"Aléa de la semaine : {event['title']}", ref=event["id"]))
    return entries


def _entry(week: int, kind: str, by: str, summary: str, *, module: str | None = None, ref: str | None = None) -> dict:
    return {"week": week, "kind": kind, "module": module, "action": None, "user_id": None, "name": None, "by": by,
            "summary": summary, "ref": ref}  # fmt: skip


def force_event(spec: dict[str, Any], state: dict[str, Any], event_id: str) -> dict[str, Any]:
    """Le formateur remplace l'aléa annoncé ; il s'applique à la prochaine avance."""
    if state["status"] != "running":
        raise GameRuleError("La partie n'est pas en cours")
    event = _event(spec, event_id)
    if event is None:
        raise GameRuleError("Aléa inconnu dans ce business game")
    new = copy.deepcopy(state)
    new["event"] = event_id
    new["log"].append(_entry(new["week"], "alea", "formateur", f"Aléa imposé par le formateur : {event['title']}",
                             ref=event_id))  # fmt: skip
    return new


def recent_log(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Quinze dernières décisions et aléas (le pilote automatique reste au débrief)."""
    return [full_entry(e) for e in state["log"] if e.get("kind") != "auto"][-15:]


def full_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Entrée de journal complète ; sans `kind` (anciennes parties) : une décision."""
    return {"kind": "decision", "module": None, "action": None, "user_id": None, "name": None, "by": "joueur",
            "ref": None} | entry  # fmt: skip


def public_state(spec: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Ce que voient tous les membres du lobby (rien n'est caché dans une simulation, hormis le hasard à venir)."""
    if spec.get("factory"):
        return factory_game.public_state(spec, state)
    week = state["week"]
    standard = _standard_offers(spec)
    pending_by_component: dict[str, int] = {}
    for order in state["pending"]:
        pending_by_component[order["component_id"]] = (
            pending_by_component.get(order["component_id"], 0) + order["quantity"]
        )
    event = _event(spec, state.get("event"))
    stocks = []
    for product in spec["products"]:
        level = state["settings"]["price"][product["id"]]
        forecast = _forecast(spec, product, week, level, event)
        quantity = state["stocks"][product["id"]]
        stocks.append(
            {"id": product["id"], "name": product["name"], "quantity": quantity,
             "safety_stock": product["safety_stock"], "forecast": forecast,
             "coverage_weeks": round(quantity / forecast, 1) if forecast else None,
             "price": round(product["price"] * PRICE_LEVELS[level], 2)}
        )  # fmt: skip
    components = []
    for component in spec["components"]:
        offer = standard[component["id"]]
        components.append(
            {"id": component["id"], "name": component["name"], "quantity": state["components"][component["id"]],
             "pending": pending_by_component.get(component["id"], 0), "usage": component["usage"],
             "reorder_point": component["usage"] * offer["lead_time"] + component["safety_stock"]}
        )  # fmt: skip
    lines = []
    for line in spec["lines"]:
        current = state["lines"][line["id"]]
        status = "arret" if current["down"] else "ok" if current["trs"] >= spec["targets"]["trs"] else "alerte"
        lines.append(
            {"id": line["id"], "name": line["name"], "trs": current["trs"], "down": current["down"], "status": status,
             "capacity": line["capacity"], "real_capacity": int(line["capacity"] * current["trs"] / 100),
             "plan": state["settings"]["plan"][line["id"]], "maintenance": state["settings"]["maintenance"][line["id"]]}
        )  # fmt: skip
    offers = {o["id"]: o for o in spec["offers"]}
    suppliers = {s["id"]: s["name"] for s in spec["suppliers"]}
    names = {c["id"]: c["name"] for c in spec["components"]}
    view = {
        "status": state["status"],
        "week": week,
        "weeks": spec["meta"]["weeks"],
        "cash": round(state["cash"]),
        "overdraft": state["settings"]["overdraft"],
        "kpis": _kpis(spec, state),
        "targets": spec["targets"],
        "history": state["history"],
        "stocks": stocks,
        "components": components,
        "lines": lines,
        "pending": [
            {
                "id": o["id"],
                "component_id": o["component_id"],
                "component": names[o["component_id"]],
                "supplier": suppliers[offers[o["offer_id"]]["supplier_id"]],
                "quantity": o["quantity"],
                "arrival_week": o["arrival_week"],
                "delays": o["delays"],
            }
            for o in sorted(state["pending"], key=lambda o: o["arrival_week"])
        ],
        "settings": state["settings"],
        "event": {k: event[k] for k in ("id", "title", "description")} if event else None,
        "last": state["last"],
        "log": recent_log(state),
    }
    view["briefings"] = _briefings(spec, state, view)
    view["alerts"] = _alerts(spec, state, view)
    return view


def debrief(spec: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    if spec.get("factory"):
        return factory_game.debrief(spec, state)
    history = state["history"]
    targets = spec["targets"]
    kpis = _kpis(spec, state)
    finals = [
        {"id": "otif", "name": "OTIF moyen", "unit": "%", "final": _mean(history, "otif"), "target": targets["otif"]},
        {"id": "trs", "name": "TRS moyen", "unit": "%", "final": _mean(history, "trs"), "target": targets["trs"]},
        {"id": "stockouts", "name": "Références en rupture (dernière semaine)", "unit": "",
         "final": history[-1]["stockouts"] if history else 0, "target": targets["stockouts"]},
        {"id": "cash", "name": "Trésorerie finale", "unit": "€", "final": kpis["cash"],
         "target": targets["cash_final"]},
    ]  # fmt: skip
    for item in finals:
        if item["final"] is None:
            item["met"] = None
        elif item["id"] == "stockouts":
            item["met"] = item["final"] <= item["target"]
        else:
            item["met"] = item["final"] >= item["target"]
    notion_ids = {n for m in spec["modules"] for n in m["notions"]} | {n for a in spec["agents"] for n in a["notions"]}
    events = {e["id"]: e["title"] for e in spec["events"]}
    return {
        "status": state["status"],
        "company": spec["meta"]["company"],
        "weeks_played": len(history),
        "kpis": finals,
        "history": history,
        "lessons": _lessons(spec, state),
        "notions": [n for n in spec["notions"] if n["id"] in notion_ids],
        "events": [{"week": h["week"], "title": events.get(h["event"], h["event"])} for h in history if h["event"]],
        "log": [full_entry(e) for e in state["log"]],
        "criteria": criteria_verdicts(spec, history, finals),
        "unsourced": _unsourced(spec),
    }


def _unsourced(spec: dict[str, Any]) -> list[dict[str, Any]]:
    from gmix.game.generation import unsourced  # import tardif : generation importe ce module

    return unsourced(spec)


# --- critères de réussite (annexe 0010 §3) ------------------------------------------------------------------------


def criteria_verdicts(spec: dict[str, Any], history: list[dict[str, Any]], finals: list[dict[str, Any]]) -> list[dict]:
    """Verdict de chaque critère : atteint, partiel, non atteint (ou sans objet), avec la pire semaine et son aléa.
    Sans `spec.criteria` (anciens jeux), les critères sont dérivés de `targets`, sans partiel."""
    by_id = {f["id"]: f for f in finals}
    criteria = spec.get("criteria") or [
        {"id": f["id"], "label": f["name"], "op": "<=" if f["id"] == "stockouts" else ">=", "target": f["target"],
         "partial": None}
        for f in finals if f["target"] is not None
    ]  # fmt: skip
    titles = {e["id"]: e["title"] for e in spec["events"]}
    out = []
    for c in criteria:
        item = by_id.get(c["id"])
        final = item["final"] if item else None
        if final is None:
            verdict = "sans_objet"
        elif item.get("failed"):  # ex. usine qui n'a rien produit : le critère est raté quel que soit le compte
            verdict = "non_atteint"
        elif (final >= c["target"]) if c["op"] == ">=" else (final <= c["target"]):
            verdict = "atteint"
        elif c.get("partial") is not None and ((final >= c["partial"]) if c["op"] == ">=" else (final <= c["partial"])):
            verdict = "partiel"
        else:
            verdict = "non_atteint"
        weeks = [h for h in history if h.get(c["id"]) is not None]
        worst = (min if c["op"] == ">=" else max)(weeks, key=lambda h: h[c["id"]], default=None)
        out.append({
            "id": c["id"], "label": c["label"], "unit": item["unit"] if item else "", "op": c["op"],
            "target": c["target"], "partial": c.get("partial"), "final": final, "verdict": verdict,
            "series": _series(spec, history, c["id"]),
            "worst_week": worst["week"] if worst else None,
            "event": titles.get(worst["event"], worst["event"]) if worst and worst.get("event") else None,
        })  # fmt: skip
    return out


def _series(spec: dict[str, Any], history: list[dict[str, Any]], key: str) -> list[float | None]:
    """Valeur du critère après chaque semaine, même formule que `final` sur les semaines 1 à w (annexe 0012 §2) :
    moyenne cumulée (otif, trs, good_share), somme cumulée (ruptures de l'usine), valeur de la semaine sinon."""
    if key in ("otif", "trs", "good_share"):
        return [_mean(history[: w + 1], key) for w in range(len(history))]
    if key == "stockouts" and spec.get("factory"):
        return [sum(h["stockouts"] for h in history[: w + 1]) for w in range(len(history))]
    return [h.get(key) for h in history]


# --- alertes (annexe 0010 §2) --------------------------------------------------------------------------------------

ALERTS_MAX = 8
ALERT_LEVELS = {"critical": 0, "warning": 1, "info": 2}
WEAR_TRS = 78  # TRS sous lequel une ligne risque la panne : seuil de la simulation elle-même (`_simulate`)


def alert(
    spec: dict[str, Any],
    alert_id: str,
    level: str,
    text: str,
    *,
    module_id: str | None = None,
    department_id: str | None = None,
    ref: str | None = None,
    action: tuple[str, dict] | None = None,
) -> dict:
    """Alerte du modèle `Alert`. Le département est celui du rôle du module sauf `department_id` ; l'action
    préremplie (action_id, valeurs) n'est gardée que si le module la déclare."""
    module = next((m for m in spec["modules"] if m["id"] == module_id), None)
    role = next((r for r in spec["roles"] if module and r["id"] == module["role_id"]), None)
    declared = bool(module and action and any(a["id"] == action[0] for a in module["actions"]))
    return {
        "id": alert_id, "level": level, "department_id": department_id or (role or {}).get("department_id"),
        "module_id": module_id if module else None, "text": text[:120], "ref": ref,
        "action": {"module_id": module_id, "action_id": action[0], "values": action[1]} if declared else None,
    }  # fmt: skip


def finish_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(alerts, key=lambda a: ALERT_LEVELS[a["level"]])[:ALERTS_MAX]  # tri stable


def common_alerts(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[dict[str, Any]]:
    """Trésorerie négative et aléa annoncé : les mêmes dans l'atelier et dans l'usine."""
    out = []
    if state["cash"] < 0:
        out.append(alert(spec, "cash:negative", "critical", f"Trésorerie négative : {money(state['cash'])}.",
                         module_id="finance", action=("decouvert", {"limit": "20000"})))  # fmt: skip
    if view["event"]:
        out.append(alert(spec, f"event:{view['event']['id']}", "info",
                         f"Aléa annoncé pour la semaine qui vient : {view['event']['title']}."))  # fmt: skip
    return out


def _alerts(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> list[dict[str, Any]]:
    """Alertes de l'atelier, calculées sur l'état courant (faits du moteur seulement)."""
    out = []
    standard = _standard_offers(spec)
    supply = next((m for m in spec["modules"] if m["id"] == "approvisionnement"), None)
    qty = next((f for a in (supply or {"actions": []})["actions"] if a["id"] == "commander" for f in a["fields"]
                if f["id"] == "quantity"), None)  # fmt: skip
    for c in view["components"]:
        if c["quantity"] + c["pending"] <= c["reorder_point"]:
            offer = standard[c["id"]]
            quantity = max(offer["min_order"], math.ceil(c["usage"] * 2 / 50) * 50)
            if qty and qty.get("max") is not None:
                quantity = min(quantity, int(qty["max"]))
            out.append(alert(spec, f"reorder:{c['id']}", "warning",
                             f"{c['name']} : {c['quantity']} en stock et {c['pending']} en route, "
                             f"point de commande {c['reorder_point']}.", module_id="approvisionnement",
                             ref=f"component:{c['id']}",
                             action=("commander", {"offer": offer["id"], "quantity": quantity})))  # fmt: skip
    for line in view["lines"]:
        if line["down"]:
            out.append(alert(spec, f"breakdown:{line['id']}", "critical", f"{line['name']} en panne.",
                             module_id="maintenance", ref=f"line:{line['id']}",
                             action=("entretenir", {"line": line["id"], "level": "renforcee"})))  # fmt: skip
        elif line["trs"] < WEAR_TRS:
            out.append(alert(spec, f"wear:{line['id']}", "warning",
                             f"{line['name']} : TRS à {line['trs']:g} %, sous le seuil de {WEAR_TRS} %.",
                             module_id="maintenance", ref=f"line:{line['id']}",
                             action=("entretenir", {"line": line["id"], "level": "renforcee"})))  # fmt: skip
    names = {item["id"]: item["name"] for item in view["lines"]}
    for lid, line in ((state["last"] or {}).get("lines") or {}).items():
        if line["starved"] and not line["down"]:
            out.append(alert(spec, f"starved:{lid}", "critical",
                             f"{names[lid]} : {line['produced']} produits sur {line['planned']} prévus.",
                             module_id="approvisionnement", ref=f"line:{lid}"))  # fmt: skip
    for order in view["pending"]:
        if order["delays"]:
            out.append(alert(spec, f"late:{order['id']}", "warning",
                             f"Commande {order['id']} ({order['component']}) en retard, "
                             f"arrivée semaine {order['arrival_week']}.",
                             module_id="approvisionnement", ref=f"component:{order['component_id']}"))  # fmt: skip
    return finish_alerts(out + common_alerts(spec, state, view))


# --- actions -----------------------------------------------------------------------------------------------


def _validate(spec: dict[str, Any], action: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    sources = {"offers": spec["offers"], "lines": spec["lines"], "products": spec["products"]}
    clean: dict[str, Any] = {}
    for field in action["fields"]:
        value = values.get(field["id"], field.get("default"))
        if value is None:
            raise GameRuleError(f"{field['label']} : valeur manquante")
        if field["type"] == "int":
            try:
                number = int(value)
            except (TypeError, ValueError):
                raise GameRuleError(f"{field['label']} : nombre entier attendu") from None
            if not field["min"] <= number <= field["max"]:
                raise GameRuleError(f"{field['label']} : entre {field['min']} et {field['max']}")
            clean[field["id"]] = number
        else:
            allowed = {item["id"] for item in (sources[field["source"]] if field.get("source") else field["options"])}
            if str(value) not in allowed:
                raise GameRuleError(f"{field['label']} : choix inconnu")
            clean[field["id"]] = str(value)
    return clean


def _order_components(spec: dict[str, Any], state: dict[str, Any], values: dict[str, Any]) -> str:
    offer = next(o for o in spec["offers"] if o["id"] == values["offer"])
    quantity = values["quantity"]
    supplier = next(s["name"] for s in spec["suppliers"] if s["id"] == offer["supplier_id"])
    component = next(c["name"] for c in spec["components"] if c["id"] == offer["component_id"])
    if quantity < offer["min_order"]:
        raise GameRuleError(f"{supplier} n'accepte pas moins de {offer['min_order']} unités par commande")
    unit_cost = round(offer["unit_cost"] * state["cost_index"], 2)
    cost = quantity * unit_cost
    if state["settings"]["overdraft"] is not None:
        committed = sum(o["quantity"] * o["unit_cost"] for o in state["pending"])
        available = state["cash"] + OVERDRAFTS[state["settings"]["overdraft"]] - committed
        if cost > available:
            raise GameRuleError(
                f"Trésorerie insuffisante : {money(max(0, available))} disponibles (découvert et commandes en cours "
                f"compris) pour une commande de {money(cost)}"
            )
    state["order_seq"] += 1
    arrival = state["week"] + offer["lead_time"]
    state["pending"].append(_order(f"cmd{state['order_seq']}", offer, quantity, unit_cost, state["week"], arrival))
    return f"Commande de {quantity} × {component} chez {supplier} : {money(cost)}, arrivée prévue semaine {arrival}"


def _plan_line(spec: dict[str, Any], state: dict[str, Any], values: dict[str, Any]) -> str:
    line = next(item for item in spec["lines"] if item["id"] == values["line"])
    quantity = min(values["quantity"], line["capacity"])
    state["settings"]["plan"][line["id"]] = quantity
    real = int(line["capacity"] * state["lines"][line["id"]]["trs"] / 100)
    return f"{line['name']} : {quantity} unités planifiées par semaine (capacité réelle actuelle {real})"


def _maintain_line(spec: dict[str, Any], state: dict[str, Any], values: dict[str, Any]) -> str:
    line = next(item for item in spec["lines"] if item["id"] == values["line"])
    state["settings"]["maintenance"][line["id"]] = values["level"]
    return f"{line['name']} : {LEVEL_LABELS[values['level']]}"


def _set_control(spec: dict[str, Any], state: dict[str, Any], values: dict[str, Any]) -> str:
    state["settings"]["control"] = values["rate"]
    return f"Contrôle avant expédition : {values['rate']} % des lots"


def _set_price(spec: dict[str, Any], state: dict[str, Any], values: dict[str, Any]) -> str:
    product = _product(spec, values["product"])
    state["settings"]["price"][product["id"]] = values["price"]
    price = product["price"] * PRICE_LEVELS[values["price"]]
    return f"{product['name']} : prix de vente {price:.2f} €".replace(".", ",")


def _set_transport(spec: dict[str, Any], state: dict[str, Any], values: dict[str, Any]) -> str:
    state["settings"]["transport"] = values["mode"]
    return f"Livraisons en {TRANSPORT_LABELS[values['mode']]}"


def _set_overdraft(spec: dict[str, Any], state: dict[str, Any], values: dict[str, Any]) -> str:
    state["settings"]["overdraft"] = values["limit"]
    return f"Découvert autorisé : {money(OVERDRAFTS[values['limit']])}"


_HANDLERS = {
    ("approvisionnement", "commander"): _order_components,
    ("production", "planifier"): _plan_line,
    ("maintenance", "entretenir"): _maintain_line,
    ("qualite", "controler"): _set_control,
    ("commercial", "fixer_prix"): _set_price,
    ("transport", "choisir_mode"): _set_transport,
    ("finance", "decouvert"): _set_overdraft,
}


# --- simulation d'une semaine --------------------------------------------------------------------------------


def _simulate(spec: dict[str, Any], state: dict[str, Any], week: int, active: set[str]) -> dict[str, Any]:
    economy = spec["economy"]
    rng = random.Random(spec["seed"] * 7919 + week * 104729)
    products = {p["id"]: p for p in spec["products"]}
    offers = {o["id"]: o for o in spec["offers"]}
    event = _event(spec, state["event"])
    effects = event["effects"] if event else {}
    report: dict[str, Any] = {"week": week, "event": event["id"] if event else None, "auto": [], "deliveries": [],
                              "delayed": [], "lines": {}, "sales": {}}  # fmt: skip
    _autopilot(spec, state, week, active, report, event)
    if "cost" in effects:  # hausse durable : s'applique aux commandes passées à partir de maintenant
        state["cost_index"] = round(state["cost_index"] * effects["cost"], 4)

    purchases = 0.0
    still = []
    for order in state["pending"]:
        if order["arrival_week"] > week:
            still.append(order)
            continue
        offer = offers[order["offer_id"]]
        if rng.random() < offer["reliability"] / 100 * (1 - effects.get("delay_risk", 0)):
            state["components"][order["component_id"]] += order["quantity"]
            purchases += order["quantity"] * order["unit_cost"]
            report["deliveries"].append(
                {"order": order["id"], "component_id": order["component_id"], "quantity": order["quantity"]}
            )
        else:
            still.append({**order, "arrival_week": week + 1, "delays": order["delays"] + 1})
            report["delayed"].append(
                {"order": order["id"], "component_id": order["component_id"], "quantity": order["quantity"]}
            )
    state["pending"] = still

    worn = (
        min(spec["lines"], key=lambda line: state["lines"][line["id"]]["trs"])["id"]
        if effects.get("breakdown")
        else None
    )
    maintenance_cost = 0.0
    for line in spec["lines"]:
        current = state["lines"][line["id"]]
        level = state["settings"]["maintenance"][line["id"]]
        current["trs"] = round(min(96.0, max(50.0, current["trs"] + economy["trs_drift"][level])), 1)
        maintenance_cost += (
            line["capacity"] * products[line["product_id"]]["unit_cost"] * economy["maintenance_rate"][level]
        )
        current["down"] = line["id"] == worn or rng.random() < max(0.0, (WEAR_TRS - current["trs"]) / 100)

    defect_rate = economy["defect_rate"] + effects.get("defects", 0)
    control = CONTROL_RATES[state["settings"]["control"]]
    production_cost = control_cost = 0.0
    escaped: dict[str, float] = {}
    for line in spec["lines"]:
        current = state["lines"][line["id"]]
        product = products[line["product_id"]]
        capacity = int(line["capacity"] * current["trs"] / 100 * (0.4 if current["down"] else 1))
        planned = int(state["settings"]["plan"][line["id"]])
        produced = min(planned, capacity, state["components"][product["component_id"]])
        state["components"][product["component_id"]] -= produced
        defects = produced * defect_rate
        caught = round(defects * control)
        escaped[product["id"]] = defects - caught
        state["stocks"][product["id"]] += produced - caught
        production_cost += produced * product["unit_cost"]
        control_cost += produced * control * product["unit_cost"] * economy["control_cost_rate"]
        report["lines"][line["id"]] = {
            "planned": planned, "capacity": capacity, "produced": produced, "scrapped": caught,
            "starved": produced < min(planned, capacity), "down": current["down"],
        }  # fmt: skip

    mode = economy["transport"][state["settings"]["transport"]]
    on_time = max(0.5, min(1.0, mode["on_time"] + effects.get("on_time", 0)))
    revenue = transport_cost = 0.0
    demand_total = served_total = good_total = lost_total = returns_total = stockouts = 0
    for product in spec["products"]:
        level = state["settings"]["price"][product["id"]]
        demand = _demand(spec, product, week, level, effects, rng)
        served = min(state["stocks"][product["id"]], demand)
        state["stocks"][product["id"]] -= served
        returns = min(served, round(escaped.get(product["id"], 0)))
        price = product["price"] * PRICE_LEVELS[level]
        revenue += (served - returns) * price
        transport_cost += served * price * mode["cost_rate"]
        stockouts += demand > served
        demand_total += demand
        served_total += served
        good_total += served - returns
        lost_total += demand - served
        returns_total += returns
        report["sales"][product["id"]] = {
            "demand": demand,
            "served": served,
            "lost": demand - served,
            "returns": returns,
        }

    holding = _stock_value(spec, state) * economy["holding_rate_week"]
    interest = -state["cash"] * economy["interest_rate_week"] if state["cash"] < 0 else 0.0
    costs = {
        "achats": purchases, "production": production_cost, "maintenance": maintenance_cost, "controle": control_cost,
        "transport": transport_cost, "possession": holding, "interets": interest,
    }  # fmt: skip
    state["cash"] = round(state["cash"] + revenue - sum(costs.values()), 2)
    effective = [
        state["lines"][line["id"]]["trs"] * (0.4 if state["lines"][line["id"]]["down"] else 1) for line in spec["lines"]
    ]
    report["costs"] = {key: round(value) for key, value in costs.items()}
    report["revenue"] = round(revenue)
    report["on_time"] = round(on_time * 100, 1)
    report["totals"] = {"demand": demand_total, "served": served_total, "lost": lost_total, "returns": returns_total}
    report["kpis"] = {
        **_kpis(spec, state),
        "otif": round(100 * good_total / demand_total * on_time, 1) if demand_total else 100.0,
        "service": round(100 * served_total / demand_total, 1) if demand_total else 100.0,
        "trs": round(sum(effective) / len(effective), 1),
        "stockouts": stockouts,
        "margin": round(revenue - sum(costs.values())),
    }
    return report


def _autopilot(
    spec: dict[str, Any], state: dict[str, Any], week: int, active: set[str], report: dict[str, Any], event: dict | None
) -> None:
    """Règles simples des modules sans pilote : point de commande, plan visant deux semaines de couverture,
    entretien préventif, contrôle d'un lot sur deux, prix catalogue, messagerie standard."""
    settings = state["settings"]
    if "approvisionnement" not in active:
        standard = _standard_offers(spec)
        for component in spec["components"]:
            offer = standard[component["id"]]
            pending = sum(o["quantity"] for o in state["pending"] if o["component_id"] == component["id"])
            reorder_point = component["usage"] * offer["lead_time"] + component["safety_stock"]
            if state["components"][component["id"]] + pending < reorder_point + component["usage"]:
                quantity = max(offer["min_order"], math.ceil(component["usage"] * 2 / 50) * 50)
                state["order_seq"] += 1
                unit_cost = round(offer["unit_cost"] * state["cost_index"], 2)
                order = _order(f"cmd{state['order_seq']}", offer, quantity, unit_cost, week, week + offer["lead_time"])
                state["pending"].append(order)
                report["auto"].append({"module": "approvisionnement", "order": order["id"], "quantity": quantity})
    if "production" not in active:
        for line in spec["lines"]:
            product = _product(spec, line["product_id"])
            forecast = _forecast(spec, product, week, settings["price"][product["id"]], event)
            wanted = forecast + COVERAGE_WEEKS * product["demand"] - state["stocks"][product["id"]]
            settings["plan"][line["id"]] = max(0, min(line["capacity"], math.ceil(wanted / 10) * 10))
    if "maintenance" not in active:
        settings["maintenance"] = {line["id"]: "preventive" for line in spec["lines"]}
    if "qualite" not in active:
        settings["control"] = "50"
    if "commercial" not in active:
        settings["price"] = {p["id"]: "1.0" for p in spec["products"]}
    if "transport" not in active:
        settings["transport"] = "standard"
    if "finance" not in active:
        settings["overdraft"] = None


# --- outils -------------------------------------------------------------------------------------------------


def _order(order_id: str, offer: dict, quantity: int, unit_cost: float, week: int, arrival: int) -> dict[str, Any]:
    return {"id": order_id, "offer_id": offer["id"], "supplier_id": offer["supplier_id"],
            "component_id": offer["component_id"], "quantity": quantity, "unit_cost": unit_cost,
            "ordered_week": week, "arrival_week": arrival, "delays": 0}  # fmt: skip


def _product(spec: dict[str, Any], product_id: str) -> dict[str, Any]:
    return next(p for p in spec["products"] if p["id"] == product_id)


def _standard_offers(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Offre de référence de chaque composant (profil standard, sinon la première) : point de commande, pilote."""
    chosen: dict[str, dict[str, Any]] = {}
    for offer in spec["offers"]:
        if offer["component_id"] not in chosen or offer["profile"] == "standard":
            chosen[offer["component_id"]] = offer
    return chosen


def _event(spec: dict[str, Any], event_id: str | None) -> dict[str, Any] | None:
    return next((e for e in spec["events"] if e["id"] == event_id), None) if event_id else None


def _roll_event(spec: dict[str, Any], week: int) -> str | None:
    """Aléa de la semaine, tiré une semaine à l'avance pour être annoncé ; aucun la première semaine."""
    probability = spec["economy"]["events_probability"]
    rng = random.Random(spec["seed"] * 31 + week * 977)
    if week == 1 or probability <= 0 or rng.random() >= probability:
        return None
    total = sum(e["weight"] for e in spec["events"])
    pick = rng.random() * total
    for event in spec["events"]:
        pick -= event["weight"]
        if pick <= 0:
            return event["id"]
    return spec["events"][-1]["id"]


def _season(spec: dict[str, Any], product: dict[str, Any], week: int) -> float:
    index = next(i for i, p in enumerate(spec["products"]) if p["id"] == product["id"])
    return 1 + 0.10 * math.sin(2 * math.pi * (week + 1.5 * index) / 6)


def _forecast(spec: dict[str, Any], product: dict[str, Any], week: int, level: str, event: dict | None) -> int:
    """Demande attendue (sans le bruit) : saison, aléa annoncé, effet du prix."""
    effect = (event or {}).get("effects", {}).get("demand", 1.0)
    price_effect = PRICE_LEVELS[level] ** -spec["economy"]["price_elasticity"]
    return round(product["demand"] * _season(spec, product, week) * effect * price_effect)


def _demand(spec: dict[str, Any], product: dict, week: int, level: str, effects: dict, rng: random.Random) -> int:
    noise = spec["economy"]["demand_noise"]
    price_effect = PRICE_LEVELS[level] ** -spec["economy"]["price_elasticity"]
    base = product["demand"] * _season(spec, product, week) * effects.get("demand", 1.0) * price_effect
    return max(0, round(base * (1 + rng.uniform(-noise, noise))))


def _stock_value(spec: dict[str, Any], state: dict[str, Any]) -> float:
    """Stock valorisé au coût : composant + transformation pour les produits finis, prix d'achat pour les composants."""
    components = {c["id"]: c for c in spec["components"]}
    finished = sum(
        state["stocks"][p["id"]] * (p["unit_cost"] + components[p["component_id"]]["unit_cost"])
        for p in spec["products"]
    )
    return finished + sum(state["components"][c["id"]] * c["unit_cost"] for c in spec["components"])


def _kpis(spec: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Indicateurs de stock du moment ; ceux d'une semaine jouée (OTIF, service, ruptures, marge) s'y ajoutent."""
    weekly = sum(p["demand"] for p in spec["products"])
    finished = sum(state["stocks"].values())
    last = state["history"][-1] if state["history"] else {}
    return {
        "otif": last.get("otif"),
        "service": last.get("service"),
        "trs": round(sum(line["trs"] for line in state["lines"].values()) / len(state["lines"]), 1),
        "stockouts": last.get("stockouts", 0),
        "stock_value": round(_stock_value(spec, state)),
        "coverage_days": round(finished / weekly * 7, 1) if weekly else 0.0,
        "cash": round(state["cash"]),
        "margin": last.get("margin"),
    }


def _mean(history: list[dict[str, Any]], key: str) -> float | None:
    values = [h[key] for h in history if h.get(key) is not None]
    return round(sum(values) / len(values), 1) if values else None


def _lessons(spec: dict[str, Any], state: dict[str, Any]) -> list[str]:
    history = state["history"]
    if not history:
        return ["La partie n'a pas été jouée."]
    targets, eco = spec["targets"], spec["economy"]
    lessons = []
    rupture_weeks = sum(1 for h in history if h["stockouts"])
    lost = sum(h["lost"] for h in history)
    if rupture_weeks:
        lessons.append(
            f"Ruptures sur {rupture_weeks} semaine(s), {lost} vente(s) perdue(s) : dans ce jeu, la demande non servie "
            "ne se reporte pas. Une ligne produit au plus le minimum de son plan, de sa capacité et des composants en "
            "stock ; repère pour vos commandes : recommandez quand stock et commandes en cours passent sous le point "
            "de commande (consommation pendant le délai + stock de sécurité)."
        )
    else:
        lessons.append("Aucune rupture : chaque semaine, chaque produit a servi toute sa demande.")
    trs = _mean(history, "trs")
    if trs is not None and trs < targets["trs"]:
        drift = eco["trs_drift"]
        lessons.append(
            f"TRS moyen de {trs} % pour un objectif de {targets['trs']:.0f} %. Dans ce jeu, la capacité d'une ligne "
            f"suit son TRS ; sans entretien, il perd {-drift['aucune']:g} point(s) par semaine (préventif : "
            f"{drift['preventive']:+g}, renforcé : {drift['renforcee']:+g}), et sous {WEAR_TRS} % la ligne risque "
            "la panne."
        )
    returns = sum(h["returns"] for h in history)
    if returns:
        lessons.append(
            f"{returns} produit(s) défectueux livré(s) puis retourné(s) : ils ne sont pas payés et sortent de "
            "l'OTIF. Le contrôle avant expédition arrête 0, 50 ou 100 % des défauts selon son niveau, contre un coût "
            "par unité contrôlée."
        )
    delays = sum(h["delays"] for h in history)
    if delays:
        lessons.append(
            f"{delays} report(s) d'une semaine sur des livraisons de composants : chaque commande arrive à la date "
            "prévue avec une probabilité égale à la fiabilité de l'offre choisie, moins l'effet d'un aléa. Repère : "
            "des délais aléatoires demandent de commander plus tôt et de garder plus de stock de sécurité."
        )
    if state["cash"] < targets["cash_final"]:
        negative = sum(1 for h in history if (h.get("margin") or 0) < 0)
        lessons.append(
            f"Trésorerie finale de {money(state['cash'])}, sous l'objectif de {money(targets['cash_final'])} ; la "
            f"marge de la semaine a été négative {negative} fois. Chaque semaine, le jeu facture aussi la possession "
            "du stock, en part de sa valeur."
        )
    if all(h["otif"] >= targets["otif"] for h in history):
        low = min(h["otif"] for h in history)
        lessons.append(
            f"OTIF d'au moins {targets['otif']:.0f} % chaque semaine (plus bas : {low:g} %) : la part livrée à "
            "l'heure et complète est restée au niveau visé."
        )
    return lessons


# --- informations essentielles des agents -------------------------------------------------------------------


def _briefings(spec: dict[str, Any], state: dict[str, Any], view: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Ce que chaque agent sait et doit transmettre : [(urgent, fait)] selon son module ou son rôle. Ces faits
    alimentent l'alerte au-dessus de sa tête, sa réplique spontanée et le prompt de ses dialogues."""
    event = view["event"]
    event_modules = set(next((e["modules"] for e in spec["events"] if event and e["id"] == event["id"]), []))
    briefings = {}
    for agent in spec["agents"]:
        facts = _FACTS[agent.get("facts") or agent["module_id"] or agent["kind"]](spec, state, view)
        if event and (agent["module_id"] in event_modules or agent["kind"] in ("fournisseur", "direction")):
            what = event["description"][:1].lower() + event["description"][1:]
            facts.insert(0, (True, f"Cette semaine, {event['title'].lower()} : {what}"))
        urgent = [text for flag, text in facts if flag]
        briefings[agent["id"]] = {
            "facts": [text for _, text in facts][:5],
            "urgent": bool(urgent),
            "line": f"{agent['personality']['prefix']} {urgent[0]}" if urgent else None,
        }
    return briefings


def _facts_supply(spec: dict, state: dict, view: dict) -> list[tuple[bool, str]]:
    facts: list[tuple[bool, str]] = []
    for c in view["components"]:
        if c["quantity"] + c["pending"] < c["reorder_point"]:
            stock = f"{c['quantity']} en stock et {c['pending']} en commande"
            text = f"{c['name']} : {stock}, sous le point de commande de {c['reorder_point']}, il faut commander."
            facts.append((True, text))
    for o in view["pending"]:
        if o["delays"]:
            text = f"La commande de {o['component']} chez {o['supplier']} a {o['delays']} semaine(s) de retard."
            facts.append((True, text))
        elif o["arrival_week"] == view["week"]:
            text = f"Livraison attendue cette semaine : {o['quantity']} {o['component']} de {o['supplier']}."
            facts.append((False, text))
    if not any(flag for flag, _ in facts):
        facts.append((False, "Tous les composants sont au-dessus de leur point de commande."))
    return facts


def _facts_production(spec: dict, state: dict, view: dict) -> list[tuple[bool, str]]:
    facts: list[tuple[bool, str]] = []
    components = {c["id"]: c for c in view["components"]}
    stocks = {s["id"]: s for s in view["stocks"]}
    for line_spec, line in zip(spec["lines"], view["lines"], strict=True):  # la vue suit l'ordre des lignes de la spec
        product = _product(spec, line_spec["product_id"])
        c, s = components[product["component_id"]], stocks[product["id"]]
        incoming = sum(
            o["quantity"] for o in view["pending"] if o["component_id"] == c["id"] and o["arrival_week"] <= view["week"]
        )
        if c["quantity"] + incoming < min(line["plan"], line["real_capacity"]):
            short = f"{c['quantity']} {c['name']} en stock et {incoming} attendus pour {line['plan']} unités prévues"
            facts.append((True, f"{line['name']} : {short}, la ligne va s'arrêter."))
        if s["coverage_weeks"] is not None and s["coverage_weeks"] < 1:
            text = f"{s['name']} : moins d'une semaine de stock ({s['quantity']} pour {s['forecast']} attendues)."
            facts.append((True, text))
        elif s["coverage_weeks"] is not None and s["coverage_weeks"] > 4:
            facts.append((False, f"{s['name']} : {s['coverage_weeks']} semaines de stock, on surproduit."))
    if not facts:
        plan = sum(line["plan"] for line in view["lines"])
        facts.append((False, f"Les lignes tournent normalement : {plan} unités planifiées cette semaine."))
    return facts


def _facts_maintenance(spec: dict, state: dict, view: dict) -> list[tuple[bool, str]]:
    worst = min(view["lines"], key=lambda line: line["trs"])
    level = LEVEL_LABELS[worst["maintenance"]]
    facts = [(worst["trs"] < spec["targets"]["trs"], f"{worst['name']} est à {worst['trs']:.0f} % de TRS ({level}).")]
    down = [line["name"] for line in view["lines"] if line["down"]]
    return facts + [(True, f"{name} est tombée en panne la semaine dernière.") for name in down]


def _facts_quality(spec: dict, state: dict, view: dict) -> list[tuple[bool, str]]:
    control = state["settings"]["control"]
    if not state["last"]:
        return [(False, f"Contrôle avant expédition réglé à {control} % des lots.")]
    returns = sum(s["returns"] for s in state["last"]["sales"].values())
    text = f"{returns} produits défectueux revenus des magasins la semaine dernière, contrôle à {control} %."
    return [(returns > 0, text)]


def _facts_sales(spec: dict, state: dict, view: dict) -> list[tuple[bool, str]]:
    forecast = sum(s["forecast"] for s in view["stocks"])
    facts = [(False, f"Demande attendue cette semaine : {forecast} unités, tous produits confondus.")]
    last = state["last"]
    for product in spec["products"]:
        lost = last["sales"][product["id"]]["lost"] if last else 0
        if lost:
            facts.insert(0, (True, f"{lost} {product['name']} non livrés la semaine dernière faute de stock."))
    return facts


def _facts_transport(spec: dict, state: dict, view: dict) -> list[tuple[bool, str]]:
    mode = state["settings"]["transport"]
    rate = spec["economy"]["transport"][mode]["on_time"] * 100
    otif = view["kpis"]["otif"]
    facts = [(False, f"Livraisons en {TRANSPORT_LABELS[mode]} : {rate:.0f} % à l'heure.")]
    if otif is not None:
        target = spec["targets"]["otif"]
        facts.insert(
            0, (otif < target, f"OTIF de la semaine dernière : {otif:.0f} % pour un objectif de {target:.0f} %.")
        )
    return facts


def _facts_finance(spec: dict, state: dict, view: dict) -> list[tuple[bool, str]]:
    kpis = view["kpis"]
    text = f"Trésorerie : {money(view['cash'])}, stock immobilisé : {money(kpis['stock_value'])}."
    facts = [(view["cash"] < 0, text)]
    if kpis["margin"] is not None:
        facts.append((kpis["margin"] < 0, f"Résultat de la semaine dernière : {money(kpis['margin'])}."))
    return facts


def _facts_client(spec: dict, state: dict, view: dict) -> list[tuple[bool, str]]:
    otif = view["kpis"]["otif"]
    if otif is None:
        expected = sum(s["forecast"] for s in view["stocks"])
        return [(False, f"{spec['meta']['client']} attend {expected} unités cette semaine.")]
    if otif < spec["targets"]["otif"]:
        return [(True, f"OTIF de {otif:.0f} % la semaine dernière : nos rayons ont manqué de vos produits.")]
    return [(False, f"OTIF de {otif:.0f} % : livraisons satisfaisantes, continuez.")]


def _facts_supplier(spec: dict, state: dict, view: dict) -> list[tuple[bool, str]]:
    late = [o for o in view["pending"] if o["delays"]]
    facts = [(True, f"Désolé, la commande de {o['component']} a pris du retard.") for o in late]
    if state["cost_index"] > 1:
        facts.append((False, f"Nos prix ont augmenté de {round((state['cost_index'] - 1) * 100)} % depuis le début."))
    return facts or [(False, "Livraisons dans les délais habituels.")]


def _facts_direction(spec: dict, state: dict, view: dict) -> list[tuple[bool, str]]:
    remaining = spec["meta"]["weeks"] - view["week"] + 1
    targets = spec["targets"]
    cash = money(targets["cash_final"])
    goals = f"OTIF {targets['otif']:.0f} %, TRS {targets['trs']:.0f} %, trésorerie d'au moins {cash}"
    facts = [(False, f"Il reste {remaining} semaine(s) ; objectifs : {goals}.")]
    otif = view["kpis"]["otif"]
    if otif is not None and otif < targets["otif"]:
        facts.insert(0, (True, f"OTIF à {otif:.0f} % : c'est la priorité."))
    return facts


_FACTS = {
    "approvisionnement": _facts_supply,
    "production": _facts_production,
    "maintenance": _facts_maintenance,
    "qualite": _facts_quality,
    "commercial": _facts_sales,
    "transport": _facts_transport,
    "finance": _facts_finance,
    "client": _facts_client,
    "fournisseur": _facts_supplier,
    "direction": _facts_direction,
}


from gmix.game import factory_game  # noqa: E402,F401  (enregistre les handlers et les faits de l'usine)
