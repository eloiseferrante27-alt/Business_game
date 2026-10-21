from typing import Literal

from pydantic import BaseModel, Field


class KPIs(BaseModel):
    otif: float = Field(ge=0, le=100, description="Livraisons complètes et à l'heure (%)")
    trs: float = Field(ge=0, le=100, description="Taux de rendement synthétique (%)")
    stock_value: float = Field(ge=0, description="Valeur totale du stock (€)")
    stockouts: int = Field(ge=0, description="Nombre de références en rupture")


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


class ProductionLine(BaseModel):
    id: str
    name: str
    product_sku: str
    weekly_capacity: int = Field(gt=0)
    efficiency: float = Field(ge=0, le=100)


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


class SupplierOrder(BaseModel):
    supplier_id: str
    sku: str
    quantity: int = Field(gt=0)


class DecisionsRequest(BaseModel):
    orders: list[SupplierOrder] = Field(default_factory=list)


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

