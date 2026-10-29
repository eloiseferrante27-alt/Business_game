from pathlib import Path
import json
from urllib.error import URLError
from urllib.request import Request, urlopen

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
    try:
        return simulation.new_game(setup)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/clear-catalog", response_model=GameState)
def clear_catalog() -> GameState:
    return simulation.clear_catalog()


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


@app.post("/api/npc-chat")
def npc_chat(payload: dict[str, object]) -> dict[str, str]:
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=422, detail="Écris une question pour le personnage.")
    if len(question) > 700:
        raise HTTPException(status_code=422, detail="La question est trop longue (700 caractères maximum).")

    role = str(payload.get("role", "")).strip()
    name = str(payload.get("name", "Équipier")).strip()[:60]
    role_profiles = {
        "Stock MP": "magasinier cariste, spécialiste des matières premières, seuils de sécurité et FIFO",
        "Production": "opérateur de production, attentif aux ordres de fabrication, cadences et pannes",
        "Qualité": "contrôleuse qualité, précise sur les non-conformités, retouches et satisfaction client",
        "Réception": "réceptionnaire, spécialiste des arrivages, fournisseurs et contrôle des palettes",
        "Emballage": "emballeuse, attentive à la conformité des colis, étiquettes et palettes",
        "Entrepôt PF": "magasinier des produits finis, spécialiste du stockage, préparation et expédition client",
        "Maintenance": "technicien de maintenance, pragmatique sur les pannes, prévention et pièces de rechange",
        "Pilotage": "responsable de pilotage, qui relie les indicateurs aux décisions de l’usine",
        "Direction": "collègue de l’usine qui connaît les opérations et aide à comprendre les décisions",
    }
    profile = role_profiles.get(role, role_profiles["Direction"])
    state = simulation.state
    snapshot = {
        "semaine": state.current_week,
        "matières": [{"nom": item.name, "stock": item.quantity, "seuil": item.safety_stock} for item in state.raw_materials],
        "produits_finis": [{"nom": item.name, "stock": item.quantity, "seuil": item.safety_stock} for item in state.stocks],
        "lignes": [{"nom": item.name, "efficacité": item.efficiency, "capacité_hebdomadaire": item.weekly_capacity, "opérationnelle": item.operational} for item in state.production_lines],
        "indicateurs": {"OTIF": state.kpis.otif, "TRS": state.kpis.trs, "qualité": state.kpis.quality_rate, "ruptures": state.kpis.stockouts},
        "aléas": state.events,
        "pièces_de_rechange": state.spare_parts,
    }
    messages = [{"role": "system", "content": (
        f"Tu es {name}, {profile}, dans le jeu de gestion d'usine G-mix. "
        "Réponds en français en parlant à la première personne et tutoie le directeur. "
        "Fais exactement 2 phrases courtes, environ 25 à 40 mots au total. Pas de liste, pas de titre, pas de fragment. "
        "Exemple de ton: ‘Je surveille le stock de composants, car il approche du seuil. Si on le commande maintenant, on évitera de bloquer la production la semaine prochaine.’ "
        "Réponds d’abord clairement, puis développe avec une conséquence concrète ou une action réaliste. "
        "Personnalise tes réponses selon ton métier et reste naturel. Base les chiffres uniquement sur l'état ci-dessous. "
        "N'invente pas de fait et ne prétends jamais avoir exécuté une action dans le jeu. "
        f"État actuel de l'usine: {json.dumps(snapshot, ensure_ascii=False)}"
    )}]
    history = payload.get("history", [])
    if isinstance(history, list):
        for item in history[-8:]:
            if isinstance(item, dict) and item.get("role") in ("user", "assistant"):
                content = str(item.get("content", ""))[:700]
                if content:
                    messages.append({"role": str(item["role"]), "content": content})
    messages.append({"role": "user", "content": question})
    request = Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps({"model": "qwen2.5:1.5b", "messages": messages, "stream": False, "options": {"temperature": 0.35, "num_predict": 110}}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
        answer = str(result.get("message", {}).get("content", "")).strip()
        if not answer:
            raise ValueError("Réponse vide du modèle")
        return {"answer": answer}
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="Le collègue IA est momentanément indisponible. Réessaie dans un instant.") from error


@app.post("/api/help-chat")
def help_chat(payload: dict[str, object]) -> dict[str, str]:
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=422, detail="Écris ton problème ou ta question.")
    if len(question) > 700:
        raise HTTPException(status_code=422, detail="Le message est trop long (700 caractères maximum).")
    messages = [
        {"role": "system", "content": (
            "Tu es l'assistant d'aide du jeu de gestion G-mix. Réponds en français, de manière naturelle, claire et brève. "
            "Aide à utiliser le jeu et à résoudre les problèmes de connexion, de commandes et de simulation. "
            "Donne des étapes concrètes, une ou deux à la fois. Si tu ne connais pas la cause, pose une question précise. "
            "Le jeu est accessible sur le port 8001 et son modèle local est qwen2.5:1.5b via Ollama. "
            "Ne prétends pas avoir réparé ou modifié quoi que ce soit."
        )},
    ]
    history = payload.get("history", [])
    if isinstance(history, list):
        for item in history[-8:]:
            if isinstance(item, dict) and item.get("role") in ("user", "assistant"):
                content = str(item.get("content", ""))[:700]
                if content:
                    messages.append({"role": str(item["role"]), "content": content})
    messages.append({"role": "user", "content": question})
    request = Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps({"model": "qwen2.5:1.5b", "messages": messages, "stream": False, "options": {"temperature": 0.4, "num_predict": 140}}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
        answer = str(result.get("message", {}).get("content", "")).strip()
        if not answer:
            raise ValueError("Réponse vide du modèle")
        return {"answer": answer}
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="Le modèle IA ne répond pas. Vérifie qu’Ollama est lancé, puis réessaie.") from error


