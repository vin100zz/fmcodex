from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from core.config.models import GameConfig
from core.engine import Lineup

if TYPE_CHECKING:
    from core.world.calendar import GameDate
    from core.world.player_state import PlayerState
    from core.world.synthesis import GeneratedPlayer


def choose_lineup(
    club_id: int,
    players: Mapping[int, "GeneratedPlayer"],
    states: Mapping[int, "PlayerState"],
    date: "GameDate",
    config: GameConfig,
    formation: str,
    block_height: float,
) -> Lineup:
    """Build the best legal lineup using configured condition-aware selection."""
    from core.world.player_state import apply_player_conditions
    from core.world.synthesis import build_lineup

    available = frozenset(
        player_id
        for player_id, player in players.items()
        if player.club_id == club_id and states[player_id].is_available(date)
    )
    conditions = {
        player_id: (state.form, state.fatigue)
        for player_id, state in states.items()
        if player_id in available
    }
    lineup = build_lineup(
        club_id=club_id,
        players=players,
        config=config,
        formation=formation,
        block_height=block_height,
        available_player_ids=available,
        selection_conditions=conditions,
    )
    return apply_player_conditions(lineup, dict(states), date)
