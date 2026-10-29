from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import DecisionsRequest, GameState, NewGameRequest
from .simulation import simulation

app = FastAPI(title="G-mix API", version="0.1.0")
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def game_interface() -> FileResponse:
    return FileResponse(STATIC_DIR / "game3d.html")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/state", response_model=GameState)
def get_state() -> GameState:
    return simulation.state


@app.post("/api/new-game", response_model=GameState)
def start_new_game(setup: NewGameRequest) -> GameState:
    return simulation.new_game(setup)


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


