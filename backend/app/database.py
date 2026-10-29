"""SQLite persistence for the single local G-mix simulation."""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(os.getenv("GMIX_DB_PATH", Path(__file__).resolve().parents[1] / "data" / "gmix.db"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    # WAL uses shared-memory sidecar files that are unreliable on Windows bind mounts.
    # The default rollback journal works with the Docker volume and a single game writer.
    connection.execute("PRAGMA journal_mode=DELETE")
    return connection


def initialize_database() -> None:
    with _connect() as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS game_snapshot ("
            "id INTEGER PRIMARY KEY CHECK (id = 1), state_json TEXT NOT NULL, "
            "pending_orders_json TEXT NOT NULL)"
        )


def load_snapshot() -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    initialize_database()
    with _connect() as connection:
        row = connection.execute(
            "SELECT state_json, pending_orders_json FROM game_snapshot WHERE id = 1"
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0]), json.loads(row[1])


def save_snapshot(state: dict[str, Any], pending_orders: list[dict[str, Any]]) -> None:
    initialize_database()
    with _connect() as connection:
        connection.execute(
            "INSERT INTO game_snapshot (id, state_json, pending_orders_json) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET state_json=excluded.state_json, "
            "pending_orders_json=excluded.pending_orders_json",
            (json.dumps(state, ensure_ascii=False), json.dumps(pending_orders, ensure_ascii=False)),
        )
