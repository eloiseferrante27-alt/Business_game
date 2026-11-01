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
        connection.execute(
            "CREATE TABLE IF NOT EXISTS archived_snapshot ("
            "archived_at TEXT DEFAULT CURRENT_TIMESTAMP, state_json TEXT NOT NULL, "
            "pending_orders_json TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS game_runtime (id INTEGER PRIMARY KEY CHECK (id=1), "
            "generation INTEGER NOT NULL, rng_state_json TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS game_journal (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "generation INTEGER NOT NULL, sequence INTEGER NOT NULL, event_json TEXT NOT NULL, "
            "UNIQUE(generation, sequence))"
        )


def load_snapshot(expected_version: int) -> dict[str, Any] | None:
    """Return the saved state, or None when there is no save of the expected schema version.

    An older save (e.g. a v1 game) is moved to `archived_snapshot` instead of being lost.
    """
    initialize_database()
    with _connect() as connection:
        row = connection.execute(
            "SELECT state_json, pending_orders_json FROM game_snapshot WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        state = json.loads(row[0])
        if state.get("schema_version") != expected_version:
            connection.execute(
                "INSERT INTO archived_snapshot (state_json, pending_orders_json) VALUES (?, ?)", row
            )
            connection.execute("DELETE FROM game_snapshot WHERE id = 1")
            return None
    return state


def load_runtime() -> dict[str, Any] | None:
    initialize_database()
    with _connect() as connection:
        row = connection.execute("SELECT generation, rng_state_json FROM game_runtime WHERE id=1").fetchone()
        if row is None:
            return None
        events = connection.execute("SELECT event_json FROM game_journal WHERE generation=? ORDER BY sequence", (row[0],)).fetchall()
    return {"generation": row[0], "rng_state": json.loads(row[1]), "events": [json.loads(event[0]) for event in events]}


def save_snapshot(state: dict[str, Any], *, events=None, generation=0, rng_state=None) -> None:
    initialize_database()
    with _connect() as connection:
        connection.execute(
            "INSERT INTO game_snapshot (id, state_json, pending_orders_json) VALUES (1, ?, '[]') "
            "ON CONFLICT(id) DO UPDATE SET state_json=excluded.state_json",
            (json.dumps(state, ensure_ascii=False),),
        )
        if events:
            connection.executemany("INSERT INTO game_journal (generation, sequence, event_json) VALUES (?, ?, ?)",
                                   [(generation, event["sequence"], json.dumps(event, ensure_ascii=False)) for event in events])
        if rng_state is not None:
            connection.execute("INSERT INTO game_runtime (id, generation, rng_state_json) VALUES (1, ?, ?) "
                               "ON CONFLICT(id) DO UPDATE SET generation=excluded.generation, rng_state_json=excluded.rng_state_json",
                               (generation, json.dumps(rng_state)))
