from typing import Literal

from pydantic import BaseModel, Field


class KPIs(BaseModel):
    otif: float = Field(ge=0, le=100, description="Livraisons complètes et à l'heure (%)")
    trs: float = Field(ge=0, le=100, description="Taux de rendement synthétique (%)")
    stock_value: float = Field(ge=0, description="Valeur totale du stock (€)")
    stockouts: int = Field(ge=0, description="Nombre de références en rupture")
    produced: int = Field(default=0, ge=0, description="Produits bons fabriqués cette semaine")
    delivered: int = Field(default=0, ge=0, description="Produits expédiés cette semaine")
    quality_rate: float = Field(default=100, ge=0, le=100, description="Taux de conformité qualité (%)")


class Supplier(BaseModel):
    id: str
    name: str
    lead_time_weeks: int = Field(ge=0)
    reliability: float = Field(ge=0, le=100, description="Fiabilité (%)")
    unit_cost: float = Field(ge=0, description="Coût unitaire (€)")
    active: bool = True
    specialty: str = "Fournisseur généraliste"
    region: str = "France"


class Stock(BaseModel):
    sku: str
    name: str
    quantity: int = Field(ge=0)
    safety_stock: int = Field(ge=0)
    unit_value: float = Field(ge=0, description="Valeur unitaire (€)")
    category: str = "Produit fini"
    unit: str = "pièce"


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
    weekly_capacity: int = Field(gt=0)
    efficiency: float = Field(ge=0, le=100)
    base_efficiency: float = Field(default=85, ge=0, le=100)
    machines: list[Machine] = Field(default_factory=list)
    operational: bool = True


class MaterialStock(BaseModel):
    sku: str
    name: str
    quantity: int = Field(ge=0)
    safety_stock: int = Field(ge=0)
    unit_value: float = Field(ge=0)
    unit: str = "unité"


class GameState(BaseModel):
    current_week: int = Field(ge=1)
    company_name: str = "G-mix"
    difficulty: Literal["facile", "normal", "difficile"] = "normal"
    started: bool = False
    kpis: KPIs
    suppliers: list[Supplier]
    stocks: list[Stock]
    production_lines: list[ProductionLine]
    events: list[str] = Field(default_factory=list)
    raw_materials: list[MaterialStock] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=lambda: ["Réception", "Stock MP", "Production", "Contrôle qualité", "Emballage", "Entrepôt PF", "Pilotage", "Maintenance et PDR"])
    pending_orders: list[dict[str, object]] = Field(default_factory=list)
    purchase_orders: list[dict[str, object]] = Field(default_factory=list)
    production_orders: list[dict[str, object]] = Field(default_factory=list)
    maintenance_queue: list[str] = Field(default_factory=list)
    spare_parts: int = Field(default=3, ge=0)
    last_week: dict[str, int | float] = Field(default_factory=dict)


class SupplierOrder(BaseModel):
    supplier_id: str
    sku: str
    quantity: int = Field(gt=0)


class ProductionOrder(BaseModel):
    sku: str
    quantity: int = Field(gt=0, le=10000)
    line_count: int = Field(default=1, ge=1, le=3)


class DecisionsRequest(BaseModel):
    orders: list[SupplierOrder] = Field(default_factory=list)
    production_orders: list[ProductionOrder] = Field(default_factory=list)
    maintenance_line_ids: list[str] = Field(default_factory=list)


class NewGameRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=32)
    difficulty: Literal["facile", "normal", "difficile"] = "normal"
    additional_suppliers: list["NewSupplierRequest"] = Field(default_factory=list, max_length=20)


class NewSupplierRequest(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    lead_time_weeks: int = Field(ge=1, le=8)
    reliability: float = Field(ge=0, le=100)
    unit_cost: float = Field(ge=0)
    specialty: str = Field(default="Fournisseur généraliste", max_length=50)
    region: str = Field(default="France", max_length=50)

