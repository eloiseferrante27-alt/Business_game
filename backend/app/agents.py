"""Agents externes du monde : fournisseurs, marché et clients.
Dans le monde 3D, on ne voit que leurs camions."""

from dataclasses import dataclass
import random

from .models import CustomerOrder, PurchaseOrder, Supplier


@dataclass(frozen=True)
class MarketEvent:
    code: str
    description: str
    delivery_delay_risk: float = 0.0
    cost_multiplier: float = 1.0
    demand_multiplier: float = 1.0


@dataclass
class Delivery:
    order: PurchaseOrder
    good_quantity: int
    nonconforming: int


class SupplierAgent:
    """Livre les commandes échues selon la fiabilité et le taux de non-conformité de chaque fournisseur."""

    def process_orders(
        self,
        orders: list[PurchaseOrder],
        suppliers: list[Supplier],
        current_week: int,
        rng: random.Random,
        delay_risk: float = 0.0,
    ) -> tuple[list[Delivery], list[PurchaseOrder], list[PurchaseOrder]]:
        """Renvoie (livraisons, commandes encore en attente, commandes retardées cette semaine)."""
        supplier_by_id = {supplier.id: supplier for supplier in suppliers}
        delivered: list[Delivery] = []
        pending: list[PurchaseOrder] = []
        delayed: list[PurchaseOrder] = []
        for order in orders:
            if order.arrival_week > current_week:
                pending.append(order)
                continue
            supplier = supplier_by_id.get(order.supplier_id)
            reliability = supplier.reliability if supplier else 90.0
            if rng.random() <= (reliability / 100) * (1 - delay_risk):
                rate = (supplier.nonconformity_rate if supplier else 2.0) / 100
                rejected = int(order.quantity * rate)
                delivered.append(Delivery(order=order, good_quantity=order.quantity - rejected, nonconforming=rejected))
            else:
                late = order.model_copy(update={"arrival_week": current_week + 1})
                pending.append(late)
                delayed.append(late)
        return delivered, pending, delayed


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
                description="Hausse des matières premières : prix fournisseurs en hausse de 10 %",
                cost_multiplier=1.10,
            )
        return None

    def apply_cost_impact(self, suppliers: list[Supplier], event: MarketEvent | None) -> None:
        if event is None or event.cost_multiplier == 1.0:
            return
        for supplier in suppliers:
            supplier.prices = {sku: round(price * event.cost_multiplier, 2) for sku, price in supplier.prices.items()}


class CustomerAgent:
    """Les clients passent des commandes ; une part vient enlever au quai d'expédition avec son camion."""

    def generate_orders(
        self,
        config: dict,
        current_week: int,
        rng: random.Random,
        demand_multiplier: float,
        next_id,
    ) -> list[CustomerOrder]:
        orders: list[CustomerOrder] = []
        names = config.get("names") or ["Client"]
        per_product = max(1, int(config.get("orders_per_product_per_week", 1)))
        variability = float(config.get("demand_variability", 0.1))
        lead = int(config.get("promised_lead_weeks", 1))
        pickup_share = float(config.get("pickup_share", 0.0))
        for sku, mean in config.get("weekly_demand", {}).items():
            total = round(mean * demand_multiplier * rng.uniform(1 - variability, 1 + variability))
            if total <= 0:
                continue
            base = total // per_product
            for index in range(per_product):
                quantity = base + (total - base * per_product if index == per_product - 1 else 0)
                if quantity <= 0:
                    continue
                orders.append(CustomerOrder(
                    id=next_id("CC"),
                    customer=rng.choice(names),
                    sku=sku,
                    quantity=quantity,
                    week_placed=current_week,
                    due_week=current_week + lead,
                    mode="enlèvement" if rng.random() < pickup_share else "livraison",
                ))
        return orders
