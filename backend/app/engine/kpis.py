"""Tablet service indicators derived only from append-only journal replay."""
from copy import deepcopy


def customer_indicators(journal):
    state, known_orders, history = {}, {}, {}
    current = {"otif": None, "service_rate": None}
    for event in journal.events:
        state = journal.apply(state, event)
        for order in state.get("customer_orders", []):
            known_orders[order["id"]] = dict(order)
        delivered = [order for order in known_orders.values() if order["status"] == "livrée"]
        on_time = [order for order in delivered if order.get("on_time")]
        demand = sum(order["quantity"] for order in known_orders.values())
        current = {
            "otif": round(100 * len(on_time) / len(delivered), 2) if delivered else None,
            "service_rate": round(100 * sum(order["quantity"] for order in on_time) / demand, 2) if demand else None,
        }
        if state.get("started"):
            period = event["time"]["period"]
            history[period] = dict(period=period, **{**deepcopy(state["kpis"]), **current})
    return {**current, "history": list(history.values())}
