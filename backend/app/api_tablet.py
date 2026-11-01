"""Live tablet adapter. Original endpoints remain available."""
import json
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .engine.tablet import tablet_snapshot
from .models import DecisionsRequest, NewGameRequest, ProductionOrder, SupplierOrder
from .simulation import simulation

router = APIRouter(prefix="/api/v2/tablet", tags=["tablet"])
lock = simulation.lock
LOCKED_MESSAGE = "Modification interdite : le formateur a fixé ce réglage pour toute la partie."


class TabletSetup(NewGameRequest):
    rules_confirmed: bool = False


class TabletAction(BaseModel):
    action: Literal["purchase", "production", "maintenance"]
    supplier_id: str | None = Field(default=None, max_length=64)
    sku: str | None = Field(default=None, max_length=64)
    quantity: int | None = Field(default=None, gt=0, le=100000)
    line_id: str | None = Field(default=None, max_length=64)


class ConfigurationAttempt(BaseModel):
    department_id: str = Field(max_length=64)
    configuration_id: str = Field(max_length=128)
    value: str | int | float | bool | None = None


def snapshot():
    with simulation.lock:
        return tablet_snapshot(simulation.journal, game_id=simulation.generation)


@router.get("")
@router.get("/")
def get_tablet():
    with lock:
        return snapshot()


@router.post("/new-game")
def new_game(setup: TabletSetup):
    with lock:
        if not setup.rules_confirmed:
            raise HTTPException(409, "Confirmez les règles de la partie avant de démarrer.")
        try:
            simulation.new_game(NewGameRequest(**setup.model_dump(exclude={"rules_confirmed"})))
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        return snapshot()


@router.post("/next-turn")
def next_turn():
    with lock:
        if not simulation.state.started:
            raise HTTPException(409, "Démarrez une partie après confirmation des règles.")
        simulation.next_turn()
        return snapshot()


@router.post("/actions")
def take_action(action: TabletAction):
    with lock:
        if not simulation.state.started:
            raise HTTPException(409, "Démarrez une partie avant de prendre une décision.")
        try:
            if action.action == "purchase":
                if not action.supplier_id or not action.sku or action.quantity is None:
                    raise ValueError("Choisissez une matière, un fournisseur et une quantité.")
                supplier = next((item for item in simulation.state.suppliers if item.id == action.supplier_id), None)
                if supplier is None or not supplier.active:
                    raise ValueError("Fournisseur indisponible.")
                decisions = DecisionsRequest(orders=[SupplierOrder(supplier_id=action.supplier_id, sku=action.sku, quantity=action.quantity)])
            elif action.action == "production":
                if not action.sku or action.quantity is None:
                    raise ValueError("Choisissez le produit et la quantité de l’OF.")
                decisions = DecisionsRequest(production_orders=[ProductionOrder(sku=action.sku, quantity=action.quantity)])
            else:
                if not action.line_id:
                    raise ValueError("Choisissez une ligne en panne.")
                decisions = DecisionsRequest(maintenance_line_ids=[action.line_id])
            simulation.submit_decisions(decisions)
        except ValueError as error:
            simulation.journal.refusal(simulation.state.current_week, action.sku or action.line_id or "SYS-DECISION-01", action.model_dump(), str(error))
            simulation._save("decision")
            raise HTTPException(422, str(error)) from error
        return snapshot()


@router.post("/configuration")
def attempt_configuration(attempt: ConfigurationAttempt):
    with lock:
        # Annexe A: a configuration without a trainer-assigned right is locked.
        # No draft recommended right is silently promoted to an editable setting.
        simulation.journal.refusal(simulation.state.current_week, f"{attempt.department_id}.{attempt.configuration_id}", attempt.value, LOCKED_MESSAGE)
        simulation._save("decision")
        raise HTTPException(403, LOCKED_MESSAGE)


# --- Aménagement visuel de l'usine (onglet Configuration de la tablette) --------
# Purement visuel : forme du stock (I, L, U, V) et tampons entre les machines.
# Le monde 3D lit ce fichier et se réorganise ; la simulation n'en dépend pas.
from .database import DB_PATH  # noqa: E402

LAYOUT_PATH = Path(DB_PATH).with_name("layout.json")
LAYOUT_DEFAUT = {"stock": {"forme": "I"}, "production": {"tampons": {}}}
FORMES_STOCK = {"I", "L", "U", "V"}


class LayoutUpdate(BaseModel):
    stock: dict[str, Any] | None = None
    production: dict[str, Any] | None = None


def read_layout() -> dict:
    try:
        data = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    layout = json.loads(json.dumps(LAYOUT_DEFAUT))
    if isinstance(data.get("stock"), dict) and data["stock"].get("forme") in FORMES_STOCK:
        layout["stock"]["forme"] = data["stock"]["forme"]
    tampons = (data.get("production") or {}).get("tampons") or {}
    if isinstance(tampons, dict):
        layout["production"]["tampons"] = {str(k)[:32]: [max(0, min(3, int(x))) for x in v][:6] for k, v in tampons.items() if isinstance(v, list)}
    return layout


@router.get("/layout")
def get_layout():
    return read_layout()


@router.put("/layout")
def put_layout(update: LayoutUpdate):
    layout = read_layout()
    if update.stock and update.stock.get("forme") is not None:
        if update.stock["forme"] not in FORMES_STOCK:
            raise HTTPException(422, "Forme de stock : I, L, U ou V.")
        layout["stock"]["forme"] = update.stock["forme"]
    if update.production and isinstance(update.production.get("tampons"), dict):
        for ligne, valeurs in update.production["tampons"].items():
            if not isinstance(valeurs, list):
                raise HTTPException(422, "Tampons : une liste par ligne.")
            layout["production"]["tampons"][str(ligne)[:32]] = [max(0, min(3, int(x))) for x in valeurs][:6]
    LAYOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAYOUT_PATH.write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
    return layout
