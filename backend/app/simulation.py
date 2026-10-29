import random

from .agents import GMSClientAgent, MarketAgent, SupplierAgent
from .database import load_snapshot, save_snapshot
from .models import DecisionsRequest, GameState, KPIs, Machine, MaterialStock, NewGameRequest, ProductionLine, Stock, Supplier


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


def _line_machines(line_number: int, availability: float) -> list[Machine]:
    operations = [
        ("Préparation", 2.0, 2.0, 40, 1.0),
        ("Assemblage", 1.5, 1.0, 80, .5),
        ("Finition", 3.0, 3.0, 60, 1.0),
        ("Vérification", 1.0, 2.0, 100, .5),
    ]
    return [
        Machine(id=f"L{line_number}-M{index}", operation=operation, cycle_minutes=cycle,
                availability=availability, defect_rate=defect, mtbf_hours=mtbf, mttr_hours=mttr)
        for index, (operation, cycle, defect, mtbf, mttr) in enumerate(operations, start=1)
    ]


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
                product_sku=f"SKU-{i:02d}", weekly_capacity=800, efficiency=85.0, base_efficiency=85.0,
                machines=_line_machines(i, 85.0),
            )
            for i in range(1, 5)
        ]
        self.state = GameState(
            current_week=1,
            kpis=KPIs(otif=94.0, trs=85.0, stock_value=0, stockouts=0),
            suppliers=suppliers,
            stocks=stocks,
            production_lines=lines,
            raw_materials=[
                MaterialStock(sku=f"MAT-{i:02d}", name=f"Composant · {item[0]}", quantity=1200,
                              safety_stock=300, unit_value=round(item[3] * .28, 2))
                for i, item in enumerate(PRODUCT_CATALOG, start=1)
            ] + [MaterialStock(sku="MAT-PDR", name="Pièces de rechange", quantity=3, safety_stock=2, unit_value=24)],
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
            migrated_lines = False
            for index, line in enumerate(self.state.production_lines, start=1):
                if not line.machines:
                    line.machines = _line_machines(index, line.efficiency)
                    line.base_efficiency = line.efficiency
                    migrated_lines = True
            if migrated_lines:
                self._save()
            self._enrich_seed_data()
        else:
            self._save()

    def _save(self) -> None:
        save_snapshot(self.state.model_dump(), self.pending_orders)

    def clear_catalog(self) -> GameState:
        self.state = GameState(current_week=1, started=False, kpis=KPIs(otif=0, trs=0, stock_value=0, stockouts=0), suppliers=[], stocks=[], production_lines=[], raw_materials=[], spare_parts=0)
        self.pending_orders = []
        self._save()
        return self.state

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
            "facile": {"stock": 700, "efficiency": 90.0, "reliability": 98.0, "otif": 97.0, "capacity": 900},
            "normal": {"stock": 500, "efficiency": 85.0, "reliability": 92.0, "otif": 94.0, "capacity": 800},
            "difficile": {"stock": 300, "efficiency": 72.0, "reliability": 78.0, "otif": 82.0, "capacity": 600},
        }
        profile = profiles[setup.difficulty]
        product_skus = {item.name.strip(): f"SKU-{i:02d}" for i, item in enumerate(setup.products, start=1)}
        if any(item.product_name.strip() not in product_skus for item in setup.materials):
            raise ValueError("Chaque matière doit être liée au nom exact d’un produit fini.")
        if set(item.product_name.strip() for item in setup.materials) != set(product_skus):
            raise ValueError("Ajoute au moins une matière associée à chaque produit fini.")
        suppliers = [
            Supplier(
                id=f"SUP-{i:02d}", name=item.name.strip(),
                lead_time_weeks=item.lead_time_weeks,
                reliability=item.reliability, unit_cost=item.unit_cost,
                specialty=item.specialty.strip(), region=item.region.strip(),
            )
            for i, item in enumerate(setup.suppliers, start=1)
        ]
        stocks = [
            Stock(sku=f"SKU-{i:02d}", name=item.name.strip(), category=item.category.strip(), unit=item.unit.strip(), quantity=item.quantity, safety_stock=item.safety_stock, unit_value=item.unit_value, demand_per_week=item.demand_per_week, weekly_capacity=item.weekly_capacity)
            for i, item in enumerate(setup.products, start=1)
        ]
        lines = [
            ProductionLine(id=f"LINE-{i:02d}", name=f"Ligne {LINE_NAMES[(i - 1) % len(LINE_NAMES)]}", product_sku=f"SKU-{i:02d}", weekly_capacity=stocks[i - 1].weekly_capacity, efficiency=profile["efficiency"], base_efficiency=profile["efficiency"], machines=_line_machines(i, profile["efficiency"]))
            for i in range(1, len(stocks) + 1)
        ]
        self.state = GameState(
            current_week=1,
            company_name=setup.company_name.strip(),
            difficulty=setup.difficulty,
            started=True,
            kpis=KPIs(otif=profile["otif"], trs=profile["efficiency"], stock_value=0, stockouts=0),
            suppliers=suppliers, stocks=stocks, production_lines=lines,
            raw_materials=[MaterialStock(sku=f"MAT-{i:02d}", name=item.name.strip(), quantity=item.quantity, safety_stock=item.safety_stock, unit_value=item.unit_value, unit=item.unit.strip(), product_sku=product_skus[item.product_name.strip()]) for i, item in enumerate(setup.materials, start=1)],
            production_orders=[], pending_orders=[], purchase_orders=[], last_week={}, maintenance_queue=[], spare_parts=3,
        )
        self.pending_orders = []
        self.rng = random.Random(42)
        self._refresh_stock_kpis()
        self._save()
        return self.state

    def submit_decisions(self, decisions: DecisionsRequest) -> int:
        suppliers = {supplier.id: supplier for supplier in self.state.suppliers}
        stock_skus = {stock.sku for stock in self.state.raw_materials}
        for order in decisions.orders:
            if order.supplier_id not in suppliers:
                raise ValueError(f"Fournisseur inconnu : {order.supplier_id}")
            if order.sku not in stock_skus:
                raise ValueError(f"Matière première inconnue : {order.sku}")
        known_products = {stock.sku for stock in self.state.stocks}
        for order in decisions.production_orders:
            if order.sku not in known_products:
                raise ValueError(f"Produit inconnu : {order.sku}")
        known_lines = {line.id for line in self.state.production_lines}
        for line_id in decisions.maintenance_line_ids:
            if line_id not in known_lines:
                raise ValueError(f"Ligne inconnue : {line_id}")
            line = next(item for item in self.state.production_lines if item.id == line_id)
            if line.operational:
                raise ValueError(f"La ligne {line.name} n’a pas besoin d’intervention.")

        for order in decisions.orders:
            supplier = suppliers[order.supplier_id]
            self.pending_orders.append({
                "supplier_id": order.supplier_id,
                "sku": order.sku,
                "quantity": order.quantity,
                "arrival_week": self.state.current_week + supplier.lead_time_weeks,
            })
        for order in decisions.production_orders:
            self.state.production_orders.append(order.model_dump())
        self.state.maintenance_queue = list(dict.fromkeys([*self.state.maintenance_queue, *decisions.maintenance_line_ids]))
        self.state.pending_orders = [dict(order) for order in self.pending_orders]
        self.state.purchase_orders = [dict(order) for order in self.pending_orders]
        self._save()
        return len(decisions.orders)

    def next_turn(self) -> GameState:
        """Fait avancer une semaine et exécute les trois agents backend."""
        self.state.current_week += 1
        event = self.market_agent.generate_event(self.rng)
        self.state.events = [event.description] if event else []
        self.market_agent.apply_cost_impact(self.state.raw_materials, event)

        repair_queue = []
        technician_used = False
        for line_id in self.state.maintenance_queue:
            line = next((item for item in self.state.production_lines if item.id == line_id), None)
            if line is None:
                continue
            if self.state.spare_parts <= 0 or technician_used:
                repair_queue.append(line_id)
                continue
            for machine in line.machines:
                if machine.state == "panne":
                    machine.state = "maintenance"
                    machine.availability = max(machine.availability, line.base_efficiency)
                    machine.state = "marche"
            line.efficiency = line.base_efficiency
            line.operational = True
            self.state.spare_parts -= 1
            technician_used = True
            parts_stock = next((item for item in self.state.raw_materials if item.sku == "MAT-PDR"), None)
            if parts_stock and parts_stock.quantity > 0:
                parts_stock.quantity -= 1
        self.state.maintenance_queue = repair_queue

        delivered, self.pending_orders = self.supplier_agent.process_orders(
            self.pending_orders,
            self.state.suppliers,
            self.state.current_week,
            self.rng,
            delay_risk=event.delivery_delay_risk if event else 0.0,
        )
        materials_by_sku = {stock.sku: stock for stock in self.state.raw_materials}
        for order in delivered:
            if str(order["sku"]) in materials_by_sku:
                materials_by_sku[str(order["sku"])].quantity += int(order["quantity"])
                if str(order["sku"]) == "MAT-PDR":
                    self.state.spare_parts += int(order["quantity"])
        received_rejections = sum(int(order.get("nonconforming", 0)) for order in delivered)
        if received_rejections:
            self.state.events.append(f"Réception : {received_rejections} unité(s) non conformes mises en quarantaine.")

        materials_by_product = {item.product_sku: item for item in self.state.raw_materials if item.product_sku}
        lines_by_product: dict[str, list[ProductionLine]] = {}
        for line in self.state.production_lines:
            lines_by_product.setdefault(line.product_sku, []).append(line)
        total_good = 0
        total_scrap = 0
        total_reworked = 0
        queued: dict[str, dict[str, int]] = {}
        for order in self.state.production_orders:
            sku = str(order["sku"])
            queued.setdefault(sku, {"quantity": 0, "line_count": 1})
            queued[sku]["quantity"] += int(order["quantity"])
            queued[sku]["line_count"] = max(queued[sku]["line_count"], int(order.get("line_count", 1)))
        for sku, order in queued.items():
            material = materials_by_product.get(sku)
            lines = lines_by_product.get(sku, [])
            if material is None or not lines:
                continue
            active_lines = max(1, min(3, order["line_count"]))
            running_lines = [line for line in lines if line.operational]
            capacity = sum(
                min(line.weekly_capacity, int(8 * 60 * 5 / max(machine.cycle_minutes for machine in line.machines)))
                * line.efficiency / 100
                for line in running_lines
            ) * active_lines
            made = min(order["quantity"], int(capacity), material.quantity)
            if made <= 0:
                continue
            defect_rate = sum(machine.defect_rate for line in running_lines for machine in line.machines) / max(1, sum(len(line.machines) for line in running_lines))
            defective = min(made, int(made * defect_rate / 100))
            reworked = int(defective * .65)
            recovered = int(reworked * .75)
            scrap = defective - recovered
            material.quantity -= made
            good = made - scrap
            next(stock for stock in self.state.stocks if stock.sku == sku).quantity += good
            total_good += good
            total_scrap += scrap
            total_reworked += reworked
            for line in running_lines:
                for machine in line.machines:
                    machine.produced_since_tool_change += made
                    if machine.produced_since_tool_change >= machine.tool_life_units:
                        machine.state = "maintenance"
                        machine.produced_since_tool_change = 0
                        machine.state = "marche"
                    elif self.rng.random() > machine.mtbf_hours / (machine.mtbf_hours + 5):
                        machine.state = "panne"
                        machine.availability = max(20, machine.availability - machine.mttr_hours * 10)
                        line.operational = False
                        line.efficiency = 0
                        self.state.events.append(f"Panne sur {line.name}, machine {machine.id} : intervention maintenance nécessaire.")
                        break
        self.state.production_orders = []
        self.state.kpis.produced = total_good
        self.state.kpis.quality_rate = round(100 * total_good / max(1, total_good + total_scrap), 1)

        inventory_before_delivery = sum(stock.quantity for stock in self.state.stocks)
        self.state.kpis.otif, self.state.kpis.stockouts = self.gms_agent.serve(
            self.state.stocks,
            demand_multiplier=5 * (event.demand_multiplier if event else 1.0) * self.rng.uniform(.9, 1.1),
        )
        self.state.kpis.delivered = inventory_before_delivery - sum(stock.quantity for stock in self.state.stocks)
        self.state.kpis.trs = round(
            sum(line.efficiency for line in self.state.production_lines)
            / len(self.state.production_lines),
            2,
        )
        self.state.pending_orders = [dict(order) for order in self.pending_orders]
        self.state.purchase_orders = [dict(order) for order in self.pending_orders]
        self.state.last_week = {
            "produced": total_good,
            "quality_losses": total_scrap,
            "reworked": total_reworked,
            "delivered": self.state.kpis.delivered,
            "received_orders": len(delivered),
            "quarantined": received_rejections,
        }
        self._refresh_stock_kpis()
        self._save()
        return self.state

    def _refresh_stock_kpis(self) -> None:
        self.state.kpis.stock_value = round(
            sum(stock.quantity * stock.unit_value for stock in self.state.stocks)
            + sum(stock.quantity * stock.unit_value for stock in self.state.raw_materials), 2
        )


simulation = SimulationEngine()






