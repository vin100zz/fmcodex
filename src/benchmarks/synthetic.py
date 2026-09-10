from __future__ import annotations

from typing import Mapping

from core.config.models import GameConfig
from core.engine import Attributes, Lineup, MatchPlayer


def synthetic_lineup(config: GameConfig, club_id: int, level: int, formation: str) -> Lineup:
    """Build an equal-strength lineup for distribution benchmarks."""
    formations = _mapping(config.raw_documents["formations"], "formations.json")["formations"]
    positions = _mapping(formations, "formations").get(formation)
    if not isinstance(positions, list):
        raise ValueError(f"Unknown synthetic formation: {formation}")
    attributes = Attributes(
        passe=level,
        technique=level,
        finition=level,
        tacle=level,
        jeu_tete=level,
        vision=level,
        placement=level,
        sang_froid=level,
        vitesse=level,
        endurance=level,
        reflexes=level,
        sorties=level,
        relance=level,
    )
    return Lineup(
        club_id=club_id,
        players=tuple(
            MatchPlayer(
                id=club_id * len(positions) + index,
                position=position,
                attributes=attributes,
                form=config.initial_player_state.form,
                fatigue=config.initial_player_state.fatigue,
                morale=config.initial_player_state.morale,
            )
            for index, position in enumerate(positions)
        ),
        block_height=0.0,
    )


def _mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    return value
