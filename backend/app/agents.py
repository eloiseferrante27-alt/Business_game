from dataclasses import dataclass
import random

from .models import Stock, Supplier


@dataclass(frozen=True)
class MarketEvent:
    code: str
    description: str
    delivery_delay_risk: float = 0.0
    cost_multiplier: float = 1.0
    demand_multiplier: float = 1.0


class SupplierAgent:
    """Livre les commandes échues selon la fiabilité des fournisseurs."""

    def process_orders(
        self,
        orders: list[dict[str, object]],
        suppliers: list[Supplier],
        current_week: int,
        rng: random.Random,
        delay_risk: float = 0.0,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        supplier_by_id = {supplier.id: supplier for supplier in suppliers}
        delivered: list[dict[str, object]] = []
        pending: list[dict[str, object]] = []

        for order in orders:
            if int(order["arrival_week"]) > current_week:
                pending.append(order)
                continue

            supplier = supplier_by_id[str(order["supplier_id"])]
            delivery_probability = (supplier.reliability / 100) * (1 - delay_risk)
            if rng.random() <= delivery_probability:
                received_order = dict(order)
                rejected = int(int(order["quantity"]) * .02)
                received_order["quantity"] = int(order["quantity"]) - rejected
                received_order["nonconforming"] = rejected
                delivered.append(received_order)
            else:
                delayed_order = dict(order)
                delayed_order["arrival_week"] = current_week + 1
                pending.append(delayed_order)

        return delivered, pending


class MarketAgent:
    """Génère des aléas de marché simulés, sans source de données externe."""

    def generate_event(self, rng: random.Random) -> MarketEvent | None:
        roll = rng.random()
        if roll < 0.08:
            return MarketEvent(
                code="red_sea_disruption",
                description="Perturbation en mer Rouge : retards fournisseurs possibles",
                delivery_delay_risk=0.25,
                demand_multiplier=1.05,
            )
        if roll < 0.16:
            return MarketEvent(
                code="materials_price_hike",
                description="Hausse des matières premières : coûts en hausse de 10 %",
                cost_multiplier=1.10,
            )
        return None

    def apply_cost_impact(self, stocks: list[Stock], event: MarketEvent | None) -> None:
        if event is None or event.cost_multiplier == 1.0:
            return
        for stock in stocks:
            stock.unit_value = round(stock.unit_value * event.cost_multiplier, 2)


class GMSClientAgent:
    """Représente la demande hebdomadaire et calcule le service client."""

    def serve(self, stocks: list[Stock], demand_multiplier: float = 1.0) -> tuple[float, int]:
        total_demand = 0
        total_served = 0
        stockouts = 0
        for stock in stocks:
            demand = round(stock.demand_per_week * demand_multiplier)
            served = min(stock.quantity, demand)
            stock.quantity -= served
            total_demand += demand
            total_served += served
            if served < demand:
                stockouts += 1
        otif = 100.0 if total_demand == 0 else 100 * total_served / total_demand
        return round(otif, 2), stockouts
