import random

from .agents import GMSClientAgent, MarketAgent, SupplierAgent
from .database import load_snapshot, save_snapshot
from .models import DecisionsRequest, GameState, KPIs, NewGameRequest, ProductionLine, Stock, Supplier


SUPPLIER_CATALOG = [
    ("Cartonnerie du Rhône", "Emballages carton", "Lyon", 2, 96.0, 0.42),
    ("PolyNord Matières", "Polymères recyclés", "Lille", 3, 91.0, 1.18),
    ("Ingrédients de Loire", "Composants alimentaires", "Tours", 2, 94.0, 0.86),
    ("Acier & Alliages Ouest", "Métaux et pièces", "Nantes", 4, 88.0, 2.75),
    ("Emballages ÉcoSud", "Emballages durables", "Toulouse", 2, 93.0, 0.64),
    ("Résines Atlantique", "Résines techniques", "Bordeaux", 3, 89.0, 1.36),
    ("Transport Horizon", "Transport amont", "Le Havre", 2, 95.0, 0.72),
    ("Palettes du Centre", "Palettes et supports", "Clermont-Ferrand", 1, 97.0, 0.55),
    ("Colorants de France", "Pigments et colorants", "Rouen", 3, 90.0, 0.94),
    ("Minéraux Saône", "Charges minérales", "Dijon", 4, 86.0, 0.68),
    ("Films Techniques", "Films de protection", "Strasbourg", 3, 92.0, 0.78),
    ("Maintenance Pro", "Pièces de maintenance", "Lyon", 1, 98.0, 3.20),
    ("Énergie Verte Services", "Électricité renouvelable", "Montpellier", 1, 99.0, 0.31),
    ("Logistique Express", "Transport et affrètement", "Marseille", 2, 87.0, 1.05),
]
PRODUCT_CATALOG = [
    ("Gourde isotherme", "Accessoire nomade", "pièce", 13.0, 140),
    ("Boîte hermétique", "Rangement cuisine", "pièce", 10.0, 100),
    ("Organiseur modulaire", "Rangement maison", "pièce", 16.0, 120),
    ("Lampe atelier LED", "Éclairage", "pièce", 22.0, 90),
]
LINE_NAMES = ["Conditionnement", "Assemblage", "Moulage", "Contrôle qualité"]


class SimulationEngine:
    """État de partie chargé depuis SQLite et sauvegardé après chaque action."""

    def __init__(self) -> None:
        suppliers = [
            Supplier(id=f"SUP-{i:02d}", name=item[0], specialty=item[1], region=item[2], lead_time_weeks=item[3], reliability=item[4], unit_cost=item[5])
            for i, item in enumerate(SUPPLIER_CATALOG, start=1)
        ]
        stocks = [
            Stock(
                sku=f"SKU-{i:02d}", name=item[0], category=item[1], unit=item[2],
                quantity=[680, 520, 440, 360][i - 1], safety_stock=item[4], unit_value=item[3],
            )
            for i, item in enumerate(PRODUCT_CATALOG, start=1)
        ]
        lines = [
            ProductionLine(
                id=f"LINE-{i:02d}", name=f"Ligne {LINE_NAMES[i - 1]}",
                product_sku=f"SKU-{i:02d}", weekly_capacity=300, efficiency=85.0,
            )
            for i in range(1, 5)
        ]
        self.state = GameState(
            current_week=1,
            kpis=KPIs(otif=94.0, trs=85.0, stock_value=0, stockouts=0),
            suppliers=suppliers,
            stocks=stocks,
            production_lines=lines,
        )
        self.pending_orders: list[dict[str, object]] = []
        self.supplier_agent = SupplierAgent()
        self.market_agent = MarketAgent()
        self.gms_agent = GMSClientAgent()
        self.rng = random.Random(42)
        self._refresh_stock_kpis()
        snapshot = load_snapshot()
        if snapshot:
            saved_state, self.pending_orders = snapshot
            if "started" not in saved_state:
                saved_state["started"] = True
            self.state = GameState.model_validate(saved_state)
            self._enrich_seed_data()
        else:
            self._save()

    def _save(self) -> None:
        save_snapshot(self.state.model_dump(), self.pending_orders)

    def _enrich_seed_data(self) -> None:
        changed = False
        suppliers = []
        for supplier in self.state.suppliers:
            index = int(supplier.id.rsplit("-", 1)[-1]) - 1 if supplier.id.startswith("SUP-") else -1
            if 0 <= index < len(SUPPLIER_CATALOG):
                item = SUPPLIER_CATALOG[index]
                updates = {}
                if supplier.name.startswith("Fournisseur "):
                    updates["name"] = item[0]
                if supplier.specialty == "Fournisseur généraliste":
                    updates["specialty"] = item[1]
                if supplier.region == "France":
                    updates["region"] = item[2]
                if updates:
                    supplier = supplier.model_copy(update=updates)
                    changed = True
            suppliers.append(supplier)
        self.state.suppliers = suppliers
        stocks = []
        for stock in self.state.stocks:
            index = int(stock.sku.rsplit("-", 1)[-1]) - 1 if stock.sku.startswith("SKU-") else -1
            if 0 <= index < len(PRODUCT_CATALOG):
                item = PRODUCT_CATALOG[index]
                updates = {}
                generic_name = stock.name.startswith("Produit ")
                if generic_name:
                    updates["name"] = item[0]
                if stock.category == "Produit fini":
                    updates["category"] = item[1]
                if stock.unit == "pièce":
                    updates["unit"] = item[2]
                if generic_name:
                    updates["unit_value"] = item[3]
                if updates:
                    stock = stock.model_copy(update=updates)
                    changed = True
            stocks.append(stock)
        self.state.stocks = stocks
        for index, line in enumerate(self.state.production_lines[:len(LINE_NAMES)]):
            if line.name.startswith("Ligne "):
                self.state.production_lines[index] = line.model_copy(update={"name": f"Ligne {LINE_NAMES[index]}"})
                changed = True
        if changed:
            self._refresh_stock_kpis()
            self._save()

    def new_game(self, setup: NewGameRequest) -> GameState:
        """Reset the simulation using the selected company profile and difficulty."""
        profiles = {
            "facile": {"stock": 700, "efficiency": 90.0, "reliability": 98.0, "otif": 97.0, "capacity": 340},
            "normal": {"stock": 500, "efficiency": 85.0, "reliability": 92.0, "otif": 94.0, "capacity": 300},
            "difficile": {"stock": 300, "efficiency": 72.0, "reliability": 78.0, "otif": 82.0, "capacity": 250},
        }
        profile = profiles[setup.difficulty]
        suppliers = [
            Supplier(
                id=f"SUP-{i:02d}", name=item[0], specialty=item[1], region=item[2],
                lead_time_weeks=item[3],
                reliability=max(45.0, min(100.0, item[4] + profile["reliability"] - 92.0)),
                unit_cost=item[5],
            )
            for i, item in enumerate(SUPPLIER_CATALOG, start=1)
        ]
        suppliers.extend(
            Supplier(
                id=f"SUP-{i:02d}", name=item.name.strip(),
                lead_time_weeks=item.lead_time_weeks,
                reliability=item.reliability, unit_cost=item.unit_cost,
                specialty=item.specialty.strip(), region=item.region.strip(),
            )
            for i, item in enumerate(setup.additional_suppliers, start=15)
        )
        stocks = [
            Stock(sku=f"SKU-{i:02d}", name=item[0], category=item[1], unit=item[2], quantity=max(item[4], int(profile["stock"] * (1.0 + (i - 2) * 0.08))), safety_stock=item[4], unit_value=item[3])
            for i, item in enumerate(PRODUCT_CATALOG, start=1)
        ]
        lines = [
            ProductionLine(id=f"LINE-{i:02d}", name=f"Ligne {LINE_NAMES[i - 1]}", product_sku=f"SKU-{i:02d}", weekly_capacity=profile["capacity"], efficiency=profile["efficiency"])
            for i in range(1, 5)
        ]
        self.state = GameState(
            current_week=1,
            company_name=setup.company_name.strip(),
            difficulty=setup.difficulty,
            started=True,
            kpis=KPIs(otif=profile["otif"], trs=profile["efficiency"], stock_value=0, stockouts=0),
            suppliers=suppliers, stocks=stocks, production_lines=lines,
        )
        self.pending_orders = []
        self.rng = random.Random(42)
        self._refresh_stock_kpis()
        self._save()
        return self.state

    def submit_decisions(self, decisions: DecisionsRequest) -> int:
        suppliers = {supplier.id: supplier for supplier in self.state.suppliers}
        stock_skus = {stock.sku for stock in self.state.stocks}
        for order in decisions.orders:
            if order.supplier_id not in suppliers:
                raise ValueError(f"Fournisseur inconnu : {order.supplier_id}")
            if order.sku not in stock_skus:
                raise ValueError(f"Référence inconnue : {order.sku}")

        for order in decisions.orders:
            supplier = suppliers[order.supplier_id]
            self.pending_orders.append({
                "supplier_id": order.supplier_id,
                "sku": order.sku,
                "quantity": order.quantity,
                "arrival_week": self.state.current_week + supplier.lead_time_weeks,
            })
        self._save()
        return len(decisions.orders)

    def next_turn(self) -> GameState:
        """Fait avancer une semaine et exécute les trois agents backend."""
        self.state.current_week += 1
        event = self.market_agent.generate_event(self.rng)
        self.state.events = [event.description] if event else []
        self.market_agent.apply_cost_impact(self.state.stocks, event)

        delivered, self.pending_orders = self.supplier_agent.process_orders(
            self.pending_orders,
            self.state.suppliers,
            self.state.current_week,
            self.rng,
            delay_risk=event.delivery_delay_risk if event else 0.0,
        )
        stocks_by_sku = {stock.sku: stock for stock in self.state.stocks}
        for order in delivered:
            stocks_by_sku[str(order["sku"])].quantity += int(order["quantity"])

        line_by_sku = {line.product_sku: line for line in self.state.production_lines}
        for stock in self.state.stocks:
            line = line_by_sku[stock.sku]
            produced = int(line.weekly_capacity * line.efficiency / 100)
            stock.quantity += produced

        self.state.kpis.otif, self.state.kpis.stockouts = self.gms_agent.serve(
            self.state.stocks,
            demand_multiplier=event.demand_multiplier if event else 1.0,
        )
        self.state.kpis.trs = round(
            sum(line.efficiency for line in self.state.production_lines)
            / len(self.state.production_lines),
            2,
        )
        self._refresh_stock_kpis()
        self._save()
        return self.state

    def _refresh_stock_kpis(self) -> None:
        self.state.kpis.stock_value = round(
            sum(stock.quantity * stock.unit_value for stock in self.state.stocks), 2
        )


simulation = SimulationEngine()






