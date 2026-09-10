from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import log1p

from core.config.models import GameConfig
from core.domain.entities import SimulationStatus
from core.world.importer import ImportReport


class RatingError(ValueError):
    """Raised when a club cannot receive a deterministic source-data rating."""


@dataclass(frozen=True, slots=True)
class ClubRating:
    club_id: int
    rating: float


def derive_active_club_ratings(report: ImportReport, config: GameConfig) -> dict[int, ClubRating]:
    """Convert selected source-market values into relative 1–100 club strengths.

    This is a temporary, reproducible bridge until generated attributes feed the
    production match engine. Only benchmark fixtures consume it.
    """
    values_by_club: dict[int, list[int]] = defaultdict(list)
    for player in report.players:
        if player.simulation_status is SimulationStatus.ACTIVE and player.club_id is not None:
            values_by_club[player.club_id].append(player.market_value)
    if len(values_by_club) != report.active_club_count:
        raise RatingError("Every active club must have selected players")

    raw_strengths: dict[int, float] = {}
    for club_id, values in values_by_club.items():
        if len(values) < config.world.regles_match.joueurs_sur_terrain:
            raise RatingError(f"Club {club_id} has too few selected players")
        starters = sorted(values, reverse=True)[: config.world.regles_match.joueurs_sur_terrain]
        raw_strengths[club_id] = sum(log1p(value) for value in starters) / len(starters)

    low = min(raw_strengths.values())
    high = max(raw_strengths.values())
    if low == high:
        midpoint = (config.attribute_bounds.min + config.attribute_bounds.max) / 2
        return {club_id: ClubRating(club_id=club_id, rating=midpoint) for club_id in raw_strengths}

    span = config.attribute_bounds.max - config.attribute_bounds.min
    return {
        club_id: ClubRating(
            club_id=club_id,
            rating=config.attribute_bounds.min + span * (strength - low) / (high - low),
        )
        for club_id, strength in raw_strengths.items()
    }
