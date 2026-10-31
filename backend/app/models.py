"""Modèles du monde v3 : un stock unique (MP, SF, PF + PDR), 9 blocs, agents par bloc,
commandes clients et camions. Les valeurs viennent du scénario (scenarios/*.json)."""

from typing import Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = 3

StockCategory = Literal["MP", "SF", "PF", "PDR"]
AgentState = Literal["disponible", "occupé", "en déplacement", "en pause", "absent"]


class KPIs(BaseModel):
    otif: float = Field(ge=0, le=100, description="Commandes livrées complètes et à l'heure (%)")
    trs: float = Field(ge=0, le=100, description="Taux de rendement synthétique (%)")
    stock_value: float = Field(ge=0, description="Valeur totale du stock (€)")
    stockouts: int = Field(ge=0, description="Nombre de références PF sous le stock minimum")
    produced: int = Field(default=0, ge=0, description="Produits conformes sortis du contrôle cette semaine")
    delivered: int = Field(default=0, ge=0, description="Produits expédiés cette semaine")
    quality_rate: float = Field(default=100, ge=0, le=100, description="Taux de conformité qualité (%)")
    purchases_cost: float = Field(default=0, ge=0, description="Coût des achats MP passés cette semaine (€)")


class StockItem(BaseModel):
    """Une référence du stock. MP, semi-finis et PF partagent les mêmes paramètres."""

    sku: str
    name: str
    category: StockCategory
    unit: str = "unité"
    unit_value: float = Field(ge=0, description="Valeur unitaire (€)")
    initial: int = Field(ge=0, description="Stock initial")
    minimum: int = Field(ge=0, description="Stock minimum (sécurité)")
    reorder_point: int = Field(ge=0, description="Point de commande")
    reorder_qty: int = Field(ge=0, description="Quantité commandée (ou lot conseillé pour un PF)")
    capacity_max: int = Field(gt=0, description="Capacité maximum")
    quantity: int = Field(ge=0)


class Supplier(BaseModel):
    id: str
    name: str
    lead_time_weeks: int = Field(ge=0)
    reliability: float = Field(ge=0, le=100, description="Livraisons à l'heure (%)")
    nonconformity_rate: float = Field(default=2.0, ge=0, le=100, description="Part livrée non conforme (%)")
    prices: dict[str, float] = Field(default_factory=dict, description="Prix unitaire par référence MP (€)")
    active: bool = True
    specialty: str = "Fournisseur généraliste"
    region: str = ""


class Machine(BaseModel):
    id: str
    operation: str
    cycle_minutes: float = Field(gt=0)
    availability: float = Field(default=92, ge=0, le=100)
    defect_rate: float = Field(default=2, ge=0, le=100)
    mtbf_hours: float = Field(default=60, gt=0)
    mttr_hours: float = Field(default=1, ge=0)
    tool_life_units: int = Field(default=5000, gt=0)
    produced_since_tool_change: int = Field(default=0, ge=0)
    state: Literal["marche", "arrêt", "panne", "maintenance"] = "marche"


class ProductionLine(BaseModel):
    id: str
    name: str
    product_sku: str
    semi_finished_sku: str
    semi_finished_after: int = Field(default=2, ge=1, description="Rang de la machine après laquelle le produit passe au stock SF")
    weekly_capacity: int = Field(gt=0)
    efficiency: float = Field(ge=0, le=100)
    base_efficiency: float = Field(default=85, ge=0, le=100)
    machines: list[Machine] = Field(default_factory=list)
    operational: bool = True


class Block(BaseModel):
    id: str
    name: str
    kind: str
    parts: list[str] = Field(default_factory=list)


class Agent(BaseModel):
    id: str
    name: str
    role: str
    role_label: str
    block_id: str
    also_in: list[str] = Field(default_factory=list)
    external: bool = False
    state: AgentState = "disponible"


class PurchaseOrder(BaseModel):
    id: str
    supplier_id: str
    sku: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    week_ordered: int
    arrival_week: int


class ManufacturingOrder(BaseModel):
    """Ordre de fabrication : passe par le stock SF puis par la fin de ligne."""

    id: str
    sku: str
    quantity: int = Field(gt=0)
    semi_finished_done: int = Field(default=0, ge=0)
    finished_done: int = Field(default=0, ge=0)
    week_launched: int
    status: Literal["lancé", "en cours", "terminé"] = "lancé"


class CustomerOrder(BaseModel):
    id: str
    customer: str
    sku: str
    quantity: int = Field(gt=0)
    week_placed: int
    due_week: int
    mode: Literal["livraison", "enlèvement"] = "livraison"
    status: Literal["ouverte", "en retard", "livrée", "annulée"] = "ouverte"
    delivered_week: int | None = None
    on_time: bool | None = None


class Truck(BaseModel):
    """Un passage de camion pendant la semaine : la seule trace visible des fournisseurs et clients."""

    id: str
    kind: Literal["fournisseur", "livraison", "client"]
    block_id: str
    label: str
    sku: str | None = None
    quantity: int = 0


class GameState(BaseModel):
    schema_version: int = SCHEMA_VERSION
    scenario_id: str = "default"
    current_week: int = Field(ge=1)
    company_name: str = "G-mix"
    difficulty: Literal["facile", "normal", "difficile"] = "normal"
    started: bool = False
    kpis: KPIs
    suppliers: list[Supplier]
    stocks: list[StockItem]
    production_lines: list[ProductionLine]
    blocks: list[Block] = Field(default_factory=list)
    agents: list[Agent] = Field(default_factory=list)
    purchase_orders: list[PurchaseOrder] = Field(default_factory=list)
    production_orders: list[ManufacturingOrder] = Field(default_factory=list)
    customer_orders: list[CustomerOrder] = Field(default_factory=list)
    trucks: list[Truck] = Field(default_factory=list)
    packing_queue: dict[str, int] = Field(default_factory=dict, description="Produits conformes en attente d'emballage")
    maintenance_queue: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    last_week: dict[str, int | float] = Field(default_factory=dict)
    next_id: int = 1


class SupplierOrder(BaseModel):
    supplier_id: str
    sku: str
    quantity: int = Field(gt=0)


class ProductionOrder(BaseModel):
    sku: str
    quantity: int = Field(gt=0, le=10000)


class DecisionsRequest(BaseModel):
    orders: list[SupplierOrder] = Field(default_factory=list)
    production_orders: list[ProductionOrder] = Field(default_factory=list)
    maintenance_line_ids: list[str] = Field(default_factory=list)


class NewSupplierRequest(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    lead_time_weeks: int = Field(ge=1, le=8)
    reliability: float = Field(ge=0, le=100)
    unit_cost: float = Field(ge=0, description="Prix proposé pour toutes les MP")
    specialty: str = Field(default="Fournisseur généraliste", max_length=50)
    region: str = Field(default="", max_length=50)


class NewGameRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=32)
    difficulty: Literal["facile", "normal", "difficile"] = "normal"
    scenario_id: str = Field(default="default", pattern=r"^[a-z0-9_-]{1,40}$")
    additional_suppliers: list[NewSupplierRequest] = Field(default_factory=list, max_length=20)


class SupplierQuote(BaseModel):
    """Une ligne du comparateur de la tablette."""

    supplier_id: str
    supplier_name: str
    sku: str
    unit_price: float
    total_cost: float
    lead_time_weeks: int
    expected_arrival_week: int
    reliability: float
    nonconformity_rate: float
    expected_good_quantity: int
