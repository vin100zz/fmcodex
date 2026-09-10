from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.session import GameSession


SCHEMA_VERSION = 1


def save_session(session: "GameSession", path: Path) -> None:
    """Persist the deterministic session checkpoint as a compact JSON gzip file."""
    payload = {
        "schema_version": SCHEMA_VERSION,
        "config_version": session.config.world.version_config,
        "seed": session.seed,
        "current_round": session.current_round,
        "completed_seasons": len(session.season_history) // len(session.plan.competitions),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, mode="wt", encoding="utf-8") as file:
        json.dump(payload, file, separators=(",", ":"), sort_keys=True)


def load_session(config_directory: Path, data_directory: Path, path: Path) -> "GameSession":
    """Restore a checkpoint by deterministically replaying its completed rounds."""
    from api.session import GameSession

    try:
        with gzip.open(path, mode="rt", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot load save {path}: {error}") from error
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported save schema version")
    seed = payload.get("seed")
    current_round = payload.get("current_round")
    completed_seasons = payload.get("completed_seasons", 0)
    if (
        not isinstance(seed, int)
        or not isinstance(current_round, int)
        or not isinstance(completed_seasons, int)
        or current_round < 0
        or completed_seasons < 0
    ):
        raise ValueError("Save has invalid deterministic checkpoint data")
    session = GameSession.create(config_directory, data_directory, seed)
    if payload.get("config_version") != session.config.world.version_config:
        raise ValueError("Save configuration version does not match the loaded configuration")
    for _ in range(completed_seasons):
        for _ in range(session.plan.round_count):
            session.advance_round()
        session.start_next_season()
    for _ in range(current_round):
        session.advance_round()
    return session


def list_slots(directory: Path) -> tuple[str, ...]:
    if not directory.is_dir():
        return ()
    return tuple(sorted(path.name.removesuffix(".json.gz") for path in directory.glob("*.json.gz")))
