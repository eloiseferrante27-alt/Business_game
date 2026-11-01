from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import CustomerOrder, DecisionsRequest, GameState, NewGameRequest, Supplier, SupplierQuote
from .scenario import list_scenarios
from .simulation import simulation
from .api_tablet import router as tablet_router

app = FastAPI(title="G-mix API", version="0.3.0")
app.include_router(tablet_router)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def game_interface() -> FileResponse:
    return FileResponse(STATIC_DIR / "game3d.html")


@app.get("/tablet")
@app.get("/tablet/")
def tablet_interface() -> FileResponse:
    return FileResponse(STATIC_DIR / "tablet" / "index.html")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/scenarios")
def get_scenarios() -> list[dict[str, str]]:
    return list_scenarios()


@app.get("/api/state", response_model=GameState)
def get_state() -> GameState:
    with simulation.lock:
        return simulation.state.model_copy(deep=True)


@app.post("/api/new-game", response_model=GameState)
def start_new_game(setup: NewGameRequest) -> GameState:
    try:
        return simulation.new_game(setup)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/decisions")
def submit_decisions(decisions: DecisionsRequest) -> dict[str, int | str]:
    try:
        accepted = simulation.submit_decisions(decisions)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"status": "accepted", "orders_queued": accepted, "production_orders_queued": len(decisions.production_orders)}


@app.post("/api/next-turn", response_model=GameState)
def advance_turn() -> GameState:
    return simulation.next_turn()


# --- Tablette du joueur ----------------------------------------------------

@app.get("/api/tablet/suppliers", response_model=list[Supplier])
def tablet_suppliers() -> list[Supplier]:
    """Tous les fournisseurs du monde, avec leurs prix par MP, délais et fiabilité."""
    return [supplier for supplier in simulation.state.suppliers if supplier.active]


@app.get("/api/tablet/compare", response_model=list[SupplierQuote])
def tablet_compare(sku: str, quantity: int = Query(default=500, gt=0, le=100000)) -> list[SupplierQuote]:
    """Comparateur : coût total, arrivée prévue et quantité conforme attendue pour chaque fournisseur."""
    try:
        return simulation.quotes(sku, quantity)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/tablet/customer-orders", response_model=list[CustomerOrder])
def tablet_customer_orders() -> list[CustomerOrder]:
    return simulation.state.customer_orders
