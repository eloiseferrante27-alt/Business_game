"""Moteur de simulation du monde v3.

Une semaine suit le chemin de la matière, bloc par bloc :
quai de déchargement → bureau de réception → stock MP → chaîne de production
(passage par le stock de semi-finis) → contrôle qualité → emballage → stock PF
→ logistique & transport.

Le joueur n'a pas de bureau : il agit depuis sa tablette (achats de MP, OF, maintenance)
et consulte les commandes clients. Toutes les valeurs viennent du scénario.
"""

import math
import random
from functools import wraps
from threading import RLock

from .agents import CustomerAgent, MarketAgent, SupplierAgent
from .database import load_runtime, load_snapshot, save_snapshot
from .engine.journal import Journal
from .models import (
    SCHEMA_VERSION,
    Agent,
    Block,
    DecisionsRequest,
    GameState,
    KPIs,
    Machine,
    ManufacturingOrder,
    NewGameRequest,
    ProductionLine,
    PurchaseOrder,
    StockItem,
    Supplier,
    SupplierQuote,
    Truck,
)
from .scenario import load_scenario

SEED = 42
PURCHASABLE = {"MP", "PDR"}


def synchronized(function):
    @wraps(function)
    def guarded(self, *args, **kwargs):
        with self.lock:
            return function(self, *args, **kwargs)
    return guarded


class SimulationEngine:
    """État de partie chargé depuis SQLite et sauvegardé après chaque action."""

    def __init__(self, persist: bool = True) -> None:
        self.persist = persist
        self.lock = RLock()
        self.rng = random.Random(SEED)
        self.journal = Journal()
        self._journal_saved = 0
        self.generation = 0
        self.supplier_agent = SupplierAgent()
        self.market_agent = MarketAgent()
        self.customer_agent = CustomerAgent()
        self.state = self._build_state(NewGameRequest(company_name="G-mix"), started=False)
        saved = load_snapshot(SCHEMA_VERSION) if persist else None
        runtime = load_runtime() if persist else None
        if saved:
            self.state = GameState.model_validate(saved)
            if runtime:
                def tuples(value):
                    return tuple(tuples(item) for item in value) if isinstance(value, list) else value
                self.rng.setstate(tuples(runtime["rng_state"]))
                self.generation = runtime["generation"]
                self.journal = Journal(runtime["events"])
                self._journal_saved = len(self.journal.events)
            # Upgrade an existing compatible snapshot without discarding its state.
            if not self.journal.events or self.journal.state != self.state.model_dump(mode="json"):
                self._save()
        else:
            if runtime:
                self.generation = runtime["generation"] + 1
            self._save()

    # ------------------------------------------------------------------ outils

    @property
    def scenario(self) -> dict:
        return load_scenario(self.state.scenario_id)

    def _save(self, cause="regle", *, new_game=False) -> None:
        if new_game:
            self.generation += 1
            self.journal = Journal()
            self._journal_saved = 0
        self.journal.capture(self.state.model_dump(mode="json"), cause)
        if self.persist:
            save_snapshot(self.state.model_dump(mode="json"), events=self.journal.events[self._journal_saved:],
                          generation=self.generation, rng_state=self.rng.getstate())
        self._journal_saved = len(self.journal.events)

    def _next_id(self, prefix: str) -> str:
        value = self.state.next_id
        self.state.next_id += 1
        return f"{prefix}-{value:04d}"

    def stock(self, sku: str) -> StockItem | None:
        return next((item for item in self.state.stocks if item.sku == sku), None)

    def stocks_by_category(self, category: str) -> list[StockItem]:
        return [item for item in self.state.stocks if item.category == category]

    def _product(self, sku: str) -> dict:
        return next(item for item in self.scenario["products"] if item["sku"] == sku)

    # ------------------------------------------------------------ construction

    def _build_state(self, setup: NewGameRequest, started: bool) -> GameState:
        scenario = load_scenario(setup.scenario_id)
        profile = scenario["difficulty_profiles"][setup.difficulty]

        suppliers = [
            Supplier(
                id=item["id"], name=item["name"], specialty=item.get("specialty", ""), region=item.get("region", ""),
                lead_time_weeks=item["lead_time_weeks"],
                reliability=max(45.0, min(100.0, item["reliability"] + profile["reliability_delta"])),
                nonconformity_rate=item.get("nonconformity_rate", 2.0),
                prices=dict(item["prices"]),
            )
            for item in scenario["suppliers"]
        ]
        mp_skus = [item["sku"] for item in scenario["stock_items"] if item["category"] == "MP"]
        start = len(suppliers) + 1
        for index, extra in enumerate(setup.additional_suppliers, start=start):
            suppliers.append(Supplier(
                id=f"SUP-{index:02d}", name=extra.name.strip(), lead_time_weeks=extra.lead_time_weeks,
                reliability=extra.reliability, specialty=extra.specialty.strip(), region=extra.region.strip(),
                prices={sku: extra.unit_cost for sku in mp_skus},
            ))

        stocks = []
        for item in scenario["stock_items"]:
            multiplier = 1.0 if item["category"] == "PDR" else profile["stock_multiplier"]
            quantity = min(item["capacity_max"], round(item["initial"] * multiplier))
            stocks.append(StockItem(**{**item, "initial": quantity, "quantity": quantity}))

        routing = scenario["routing"]
        products = {item["sku"]: item for item in scenario["products"]}
        lines = []
        for number, line in enumerate(scenario["lines"], start=1):
            machines = [
                Machine(
                    id=f"L{number}-M{rank}", operation=machine["operation"], cycle_minutes=machine["cycle_minutes"],
                    availability=profile["efficiency"], defect_rate=machine["defect_rate"],
                    mtbf_hours=machine["mtbf_hours"], mttr_hours=machine["mttr_hours"],
                )
                for rank, machine in enumerate(routing["machines"], start=1)
            ]
            lines.append(ProductionLine(
                id=line["id"], name=line["name"], product_sku=line["product_sku"],
                semi_finished_sku=products[line["product_sku"]]["semi_finished_sku"],
                semi_finished_after=routing["semi_finished_after_machine"],
                weekly_capacity=profile["capacity"], efficiency=profile["efficiency"],
                base_efficiency=profile["efficiency"], machines=machines,
            ))

        state = GameState(
            scenario_id=setup.scenario_id,
            current_week=1,
            company_name=setup.company_name.strip(),
            difficulty=setup.difficulty,
            started=started,
            kpis=KPIs(otif=profile["otif"], trs=profile["efficiency"], stock_value=0, stockouts=0),
            suppliers=suppliers,
            stocks=stocks,
            production_lines=lines,
            blocks=[Block(**block) for block in scenario["blocks"]],
            agents=[Agent(**agent) for agent in scenario["agents"]],
        )
        self.state = state
        self._refresh_kpis()
        self._refresh_alerts()
        return state

    @synchronized
    def new_game(self, setup: NewGameRequest) -> GameState:
        """Reset the simulation using the selected scenario, company profile and difficulty."""
        self._build_state(setup, started=True)
        self.rng = random.Random(SEED)
        self._save("decision", new_game=True)
        return self.state

    # ---------------------------------------------------------------- tablette

    @synchronized
    def quotes(self, sku: str, quantity: int) -> list[SupplierQuote]:
        """Comparateur de la tablette : coût et risque de chaque fournisseur pour une MP."""
        item = self.stock(sku)
        if item is None or item.category not in PURCHASABLE:
            raise ValueError(f"Référence non achetable : {sku}")
        quotes = []
        for supplier in self.state.suppliers:
            if not supplier.active or sku not in supplier.prices:
                continue
            price = supplier.prices[sku]
            quotes.append(SupplierQuote(
                supplier_id=supplier.id, supplier_name=supplier.name, sku=sku,
                unit_price=price, total_cost=round(price * quantity, 2),
                lead_time_weeks=supplier.lead_time_weeks,
                expected_arrival_week=self.state.current_week + supplier.lead_time_weeks,
                reliability=supplier.reliability, nonconformity_rate=supplier.nonconformity_rate,
                expected_good_quantity=quantity - int(quantity * supplier.nonconformity_rate / 100),
            ))
        return sorted(quotes, key=lambda quote: quote.total_cost)

    @synchronized
    def submit_decisions(self, decisions: DecisionsRequest) -> int:
        suppliers = {supplier.id: supplier for supplier in self.state.suppliers}
        for order in decisions.orders:
            supplier = suppliers.get(order.supplier_id)
            if supplier is None:
                raise ValueError(f"Fournisseur inconnu : {order.supplier_id}")
            item = self.stock(order.sku)
            if item is None or item.category not in PURCHASABLE:
                raise ValueError(f"Matière première inconnue : {order.sku}")
            if order.sku not in supplier.prices:
                raise ValueError(f"{supplier.name} ne vend pas {item.name}.")
        for order in decisions.production_orders:
            item = self.stock(order.sku)
            if item is None or item.category != "PF":
                raise ValueError(f"Produit inconnu : {order.sku}")
        lines = {line.id: line for line in self.state.production_lines}
        for line_id in decisions.maintenance_line_ids:
            if line_id not in lines:
                raise ValueError(f"Ligne inconnue : {line_id}")
            if lines[line_id].operational:
                raise ValueError(f"La ligne {lines[line_id].name} n’a pas besoin d’intervention.")

        for order in decisions.orders:
            supplier = suppliers[order.supplier_id]
            price = supplier.prices[order.sku]
            self.state.purchase_orders.append(PurchaseOrder(
                id=self._next_id("ACH"), supplier_id=supplier.id, sku=order.sku, quantity=order.quantity,
                unit_price=price, week_ordered=self.state.current_week,
                arrival_week=self.state.current_week + supplier.lead_time_weeks,
            ))
            self.state.kpis.purchases_cost = round(self.state.kpis.purchases_cost + price * order.quantity, 2)
        for order in decisions.production_orders:
            self.state.production_orders.append(ManufacturingOrder(
                id=self._next_id("OF"), sku=order.sku, quantity=order.quantity, week_launched=self.state.current_week,
            ))
        self.state.maintenance_queue = list(dict.fromkeys([*self.state.maintenance_queue, *decisions.maintenance_line_ids]))
        self._refresh_alerts()
        self._save("decision")
        return len(decisions.orders)

    # ----------------------------------------------------------------- semaine

    @synchronized
    def next_turn(self) -> GameState:
        """Fait avancer une semaine en traversant les blocs dans l'ordre du flux."""
        state = self.state
        state.current_week += 1
        state.trucks = []
        purchases_cost = state.kpis.purchases_cost
        state.events = []
        self.journal.capture(state.model_dump(mode="json"), "regle")
        event = self.market_agent.generate_event(self.rng)
        state.events = [event.description] if event else []
        if event:
            self.journal.note(state.current_week, "EXT-MARCHE-01", event.description, cause="alea", department="fournisseurs")
        self.market_agent.apply_cost_impact(state.suppliers, event)
        self.journal.capture(state.model_dump(mode="json"), "alea" if event else "regle")
        busy: set[str] = set()

        repaired = self._block_maintenance(busy)
        received = self._block_dock_and_reception(event, busy)
        production = self._block_production(busy)
        packed = self._block_packaging(busy)
        logistics = self._block_logistics(event, busy)

        for agent in state.agents:
            agent.state = "occupé" if agent.role in busy else "disponible"

        state.kpis.produced = production["conform"]
        state.kpis.quality_rate = round(
            100 * production["conform"] / max(1, production["conform"] + production["scrap"]), 1
        ) if production["checked"] else 100.0
        state.kpis.delivered = logistics["delivered_units"]
        if logistics["closed"]:
            state.kpis.otif = round(100 * logistics["on_time"] / logistics["closed"], 2)
        state.kpis.trs = round(sum(line.efficiency for line in state.production_lines) / len(state.production_lines), 2)
        state.last_week = {
            "received_orders": received["orders"],
            "received_units": received["units"],
            "quarantined": received["quarantined"],
            "semi_finished": production["semi_finished"],
            "produced": production["conform"],
            "reworked": production["reworked"],
            "quality_losses": production["scrap"],
            "packed": packed["units"],
            "pallets": packed["pallets"],
            "delivered": logistics["delivered_units"],
            "customer_orders_delivered": logistics["delivered_orders"],
            "customer_orders_late": logistics["late"],
            "customer_orders_cancelled": logistics["cancelled"],
            "repairs": repaired,
            "purchases_cost": purchases_cost,
        }
        state.kpis.purchases_cost = 0
        self._refresh_kpis()
        self._refresh_alerts()
        self._save()
        return state

    def _block_maintenance(self, busy: set[str]) -> int:
        """Maintenance et stock PDR : une réparation consomme une pièce de rechange."""
        state = self.state
        parts = self.stock("MAT-PDR")
        capacity = int(self.scenario.get("maintenance", {}).get("repairs_per_week", 1))
        remaining = []
        repaired = 0
        for line_id in state.maintenance_queue:
            line = next((item for item in state.production_lines if item.id == line_id), None)
            if line is None or line.operational:
                continue
            if repaired >= capacity or parts is None or parts.quantity <= 0:
                remaining.append(line_id)
                continue
            for machine in line.machines:
                if machine.state == "panne":
                    machine.availability = max(machine.availability, line.base_efficiency)
                    machine.state = "marche"
            line.efficiency = line.base_efficiency
            line.operational = True
            parts.quantity -= 1
            repaired += 1
            busy.add("technicien_maintenance")
            state.events.append(f"Maintenance : {line.name} réparée (1 pièce de rechange utilisée).")
        if remaining and (parts is None or parts.quantity <= 0):
            state.events.append("Maintenance bloquée : stock PDR vide.")
        state.maintenance_queue = remaining
        return repaired

    def _block_dock_and_reception(self, event, busy: set[str]) -> dict[str, int]:
        """Quai de déchargement puis bureau de réception : contrôle, quarantaine, entrée en stock."""
        state = self.state
        deliveries, pending, delayed = self.supplier_agent.process_orders(
            state.purchase_orders, state.suppliers, state.current_week, self.rng,
            delay_risk=event.delivery_delay_risk if event else 0.0,
        )
        state.purchase_orders = pending
        suppliers = {supplier.id: supplier for supplier in state.suppliers}
        for order in delayed:
            message = f"Retard : la commande {order.id} de {suppliers[order.supplier_id].name} arrivera semaine {order.arrival_week}."
            state.events.append(message)
            self.journal.note(state.current_week, order.id, message, cause="alea", department="fournisseurs")
        if delayed:
            self.journal.capture(state.model_dump(mode="json"), "alea")
        units = quarantined = 0
        for delivery in deliveries:
            item = self.stock(delivery.order.sku)
            supplier = suppliers.get(delivery.order.supplier_id)
            state.trucks.append(Truck(
                id=self._next_id("CAM"), kind="fournisseur", block_id="quai_dechargement",
                label=supplier.name if supplier else "Fournisseur", sku=delivery.order.sku, quantity=delivery.order.quantity,
            ))
            if item is None:
                continue
            room = max(0, item.capacity_max - item.quantity)
            accepted = min(delivery.good_quantity, room)
            if accepted < delivery.good_quantity:
                state.events.append(f"Stock plein : {delivery.good_quantity - accepted} {item.unit}(s) de {item.name} refusé(s) à la réception.")
            item.quantity += accepted
            units += accepted
            quarantined += delivery.nonconforming
        if deliveries:
            busy.update({"chauffeur_fournisseur", "receptionnaire", "magasinier_cariste"})
        if quarantined:
            state.events.append(f"Réception : {quarantined} unité(s) non conformes mises en quarantaine.")
        return {"orders": len(deliveries), "units": units, "quarantined": quarantined}

    def _block_production(self, busy: set[str]) -> dict[str, int]:
        """Chaîne de production : MP → semi-finis (stock SF) → fin de ligne → contrôle qualité."""
        state = self.state
        minutes = self.scenario.get("work_minutes_per_week", 2400)
        quality = self.scenario.get("quality", {})
        totals = {"semi_finished": 0, "checked": 0, "conform": 0, "reworked": 0, "scrap": 0}

        for line in state.production_lines:
            orders = [order for order in state.production_orders if order.sku == line.product_sku and order.status != "terminé"]
            if not orders or not line.operational:
                continue
            split = line.semi_finished_after
            first, last = line.machines[:split], line.machines[split:]
            efficiency = line.efficiency / 100

            def capacity(machines: list[Machine]) -> int:
                if not machines:
                    return line.weekly_capacity
                return int(min(line.weekly_capacity, minutes / max(machine.cycle_minutes for machine in machines)) * efficiency)

            # Amont : kit de MP préparé par le magasinier-cariste, puis machines 1..split → stock SF.
            sf = self.stock(line.semi_finished_sku)
            bom = self._product(line.product_sku)["bom"]
            kit_limit = min((self.stock(sku).quantity // max(1, qty) for sku, qty in bom.items()), default=0)
            need_sf = sum(order.quantity - order.semi_finished_done for order in orders)
            made_sf = max(0, min(need_sf, capacity(first), kit_limit, sf.capacity_max - sf.quantity))
            for sku, qty in bom.items():
                self.stock(sku).quantity -= made_sf * qty
            sf.quantity += made_sf
            remaining = made_sf
            for order in orders:
                step = min(remaining, order.quantity - order.semi_finished_done)
                order.semi_finished_done += step
                remaining -= step
            if kit_limit < need_sf:
                state.events.append(f"Kit incomplet pour {line.name} : matière première insuffisante.")

            # Aval : stock SF → machines split+1..N → produits à contrôler.
            need_finish = sum(order.quantity - order.finished_done for order in orders)
            made = max(0, min(need_finish, capacity(last), sf.quantity))
            sf.quantity -= made
            remaining = made
            for order in orders:
                step = min(remaining, order.quantity - order.finished_done)
                order.finished_done += step
                order.semi_finished_done = max(order.semi_finished_done, order.finished_done)
                remaining -= step
                order.status = "terminé" if order.finished_done >= order.quantity else "en cours"

            # Contrôle qualité : conforme, à retoucher, rebut.
            defect_rate = 1 - math.prod(1 - machine.defect_rate / 100 for machine in line.machines)
            defective = min(made, int(made * defect_rate))
            reworked = int(defective * quality.get("rework_share", 0.65))
            recovered = int(reworked * quality.get("rework_recovery", 0.75))
            scrap = defective - recovered
            conform = made - scrap
            state.packing_queue[line.product_sku] = state.packing_queue.get(line.product_sku, 0) + conform
            totals["semi_finished"] += made_sf
            totals["checked"] += made
            totals["conform"] += conform
            totals["reworked"] += reworked
            totals["scrap"] += scrap
            if made_sf or made:
                busy.update({"magasinier_cariste", "chef_de_ligne", "operateur_machine"})
            if made:
                busy.add("controleur_qualite")

            # Usure des outils et pannes : probabilité = part bloquante × heures de marche ÷ MTBF.
            blocking_share = self.scenario["routing"].get("blocking_breakdown_share", 0.1)
            for rank, machine in enumerate(line.machines, start=1):
                volume = made_sf if rank <= split else made
                if volume <= 0:
                    continue
                machine.produced_since_tool_change += volume
                if machine.produced_since_tool_change >= machine.tool_life_units:
                    machine.produced_since_tool_change = 0
                    state.events.append(f"Outil changé sur {machine.id}.")
                elif self.rng.random() < blocking_share * (volume * machine.cycle_minutes / 60) / machine.mtbf_hours:
                    self.journal.capture(state.model_dump(mode="json"), "regle")
                    machine.state = "panne"
                    machine.availability = max(20, machine.availability - machine.mttr_hours * 10)
                    line.operational = False
                    line.efficiency = 0
                    message = f"Panne sur {line.name}, machine {machine.id} : intervention maintenance nécessaire."
                    state.events.append(message)
                    self.journal.note(state.current_week, machine.id, message, cause="alea", department="maintenance")
                    self.journal.capture(state.model_dump(mode="json"), "alea")
                    break

        state.production_orders = [order for order in state.production_orders if order.status != "terminé"]
        return totals

    def _block_packaging(self, busy: set[str]) -> dict[str, int]:
        """Emballage : mise en carton, palette filmée, envoi au stock PF."""
        state = self.state
        config = self.scenario["packaging"]
        minutes = self.scenario.get("work_minutes_per_week", 2400)
        per_box = config["products_per_box"]
        box_minutes = config["minutes_per_box"] + config["minutes_per_pallet_wrap"] / config["boxes_per_pallet"]
        boxes_left = int(minutes / box_minutes)
        cartons = self.stock(config["box_sku"])
        packed_units = boxes_used = 0
        for sku in sorted(state.packing_queue):
            waiting = state.packing_queue[sku]
            pf = self.stock(sku)
            if waiting <= 0 or pf is None:
                continue
            boxes = min(boxes_left, cartons.quantity if cartons else boxes_left, math.ceil(waiting / per_box))
            units = min(waiting, boxes * per_box, pf.capacity_max - pf.quantity)
            if units <= 0:
                continue
            boxes = math.ceil(units / per_box)
            pf.quantity += units
            state.packing_queue[sku] = waiting - units
            boxes_left -= boxes
            boxes_used += boxes
            packed_units += units
            if cartons:
                cartons.quantity -= boxes
        waiting_total = sum(state.packing_queue.values())
        if waiting_total:
            state.events.append(f"Emballage : {waiting_total} produit(s) conformes en attente (capacité, cartons ou stock PF plein).")
        if packed_units:
            busy.add("emballeur")
        return {"units": packed_units, "pallets": math.ceil(boxes_used / config["boxes_per_pallet"]) if boxes_used else 0}

    def _block_logistics(self, event, busy: set[str]) -> dict[str, int]:
        """Logistique & transport : nouvelles commandes, chargement de nos camions et des camions clients."""
        state = self.state
        self.journal.capture(state.model_dump(mode="json"), "regle")
        new_orders = self.customer_agent.generate_orders(
            self.scenario["customers"], state.current_week, self.rng,
            demand_multiplier=event.demand_multiplier if event else 1.0,
            next_id=self._next_id,
        )
        state.customer_orders.extend(new_orders)
        for order in new_orders:
            self.journal.note(state.current_week, order.id, f"{order.customer} commande {order.quantity} unités de {order.sku}, échéance semaine {order.due_week}.",
                              cause="alea", department="clients")
        self.journal.capture(state.model_dump(mode="json"), "alea")
        transport = self.scenario["transport"]
        truck_capacity = transport["truck_capacity_units"]
        own_capacity = transport["own_trucks"] * truck_capacity
        delivered_units = delivered_orders = on_time = late = own_units = 0
        cancel_after = int(self.scenario["customers"].get("cancel_after_weeks_late", 0))
        cancelled = 0
        for order in sorted(state.customer_orders, key=lambda item: (item.due_week, item.id)):
            if order.status in ("livrée", "annulée"):
                continue
            if cancel_after and state.current_week - order.due_week > cancel_after:
                order.status = "annulée"
                cancelled += 1
                continue
            pf = self.stock(order.sku)
            can_ship = pf is not None and pf.quantity >= order.quantity
            if can_ship and order.mode == "livraison" and own_units + order.quantity > own_capacity:
                can_ship = False
            if can_ship:
                pf.quantity -= order.quantity
                order.status = "livrée"
                order.delivered_week = state.current_week
                order.on_time = state.current_week <= order.due_week
                delivered_units += order.quantity
                delivered_orders += 1
                on_time += int(order.on_time)
                if order.mode == "livraison":
                    own_units += order.quantity
                else:
                    state.trucks.append(Truck(
                        id=self._next_id("CAM"), kind="client", block_id="logistique_transport",
                        label=order.customer, sku=order.sku, quantity=order.quantity,
                    ))
            elif state.current_week >= order.due_week and order.status == "ouverte":
                order.status = "en retard"
                late += 1
        for _ in range(math.ceil(own_units / truck_capacity) if own_units else 0):
            state.trucks.append(Truck(
                id=self._next_id("CAM"), kind="livraison", block_id="logistique_transport",
                label="Camion de livraison", quantity=min(truck_capacity, own_units),
            ))
            own_units -= truck_capacity
        if delivered_orders:
            busy.update({"magasinier_logistique"})
        if any(truck.kind == "livraison" for truck in state.trucks):
            busy.add("chauffeur_livreur")
        if any(truck.kind == "client" for truck in state.trucks):
            busy.add("chauffeur_client")
        if late:
            state.events.append(f"Logistique : {late} commande(s) client en retard.")
        if cancelled:
            state.events.append(f"Logistique : {cancelled} commande(s) annulée(s) par le client après un retard trop long.")
        # On garde les commandes ouvertes et l'historique récent.
        state.customer_orders = [
            order for order in state.customer_orders
            if order.status in ("ouverte", "en retard")
            or (order.delivered_week or order.due_week) >= state.current_week - 2
        ]
        return {
            "delivered_units": delivered_units, "delivered_orders": delivered_orders,
            "on_time": on_time, "late": late, "cancelled": cancelled, "closed": delivered_orders + late,
        }

    # -------------------------------------------------------------- indicateurs

    def _refresh_kpis(self) -> None:
        state = self.state
        state.kpis.stock_value = round(sum(item.quantity * item.unit_value for item in state.stocks), 2)
        state.kpis.stockouts = sum(1 for item in self.stocks_by_category("PF") if item.quantity < item.minimum)

    def _refresh_alerts(self) -> None:
        """Alertes du stock affichées sur la tablette : le joueur décide, rien n'est commandé tout seul."""
        state = self.state
        on_order: dict[str, int] = {}
        for order in state.purchase_orders:
            on_order[order.sku] = on_order.get(order.sku, 0) + order.quantity
        in_production: dict[str, int] = {}
        for order in state.production_orders:
            in_production[order.sku] = in_production.get(order.sku, 0) + order.quantity - order.finished_done
        alerts = []
        for item in state.stocks:
            if item.category in PURCHASABLE:
                if item.quantity + on_order.get(item.sku, 0) <= item.reorder_point:
                    alerts.append(f"{item.name} : {item.quantity} en stock, sous le point de commande ({item.reorder_point}). Commander {item.reorder_qty}.")
            elif item.category == "PF":
                if item.quantity + in_production.get(item.sku, 0) <= item.reorder_point:
                    alerts.append(f"{item.name} : {item.quantity} en stock PF, sous le point de commande ({item.reorder_point}). Lancer un OF de {item.reorder_qty}.")
            elif item.category == "SF" and item.quantity < item.minimum:
                alerts.append(f"{item.name} : stock de semi-finis bas ({item.quantity}).")
        state.alerts = alerts


simulation = SimulationEngine()
