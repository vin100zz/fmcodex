from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ClubStatus(StrEnum):
    ACTIVE = "active"
    DORMANT = "dormant"


class SimulationStatus(StrEnum):
    ACTIVE = "active"
    REDUCED = "reduced"


@dataclass(frozen=True, slots=True)
class ClubSeed:
    id: int
    name: str
    nation_source: str
    division_id: int | None
    stadium_capacity: int | None
    status: ClubStatus


@dataclass(frozen=True, slots=True)
class PlayerSeed:
    id: int
    name: str
    nationality_source: str
    primary_position: str
    secondary_positions: tuple[str, ...]
    club_id: int | None
    wage: int
    market_value: int
    simulation_status: SimulationStatus
