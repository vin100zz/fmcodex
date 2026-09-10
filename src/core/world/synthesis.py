from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import log1p
from random import Random
from typing import Mapping

from core.config.models import GameConfig
from core.domain.entities import PlayerSeed, SimulationStatus
from core.engine import Attributes, Lineup, MatchPlayer
from core.world.importer import ImportReport


@dataclass(frozen=True, slots=True)
class GeneratedPlayer:
    id: int
    club_id: int
    primary_position: str
    secondary_positions: tuple[str, ...]
    overall: int
    attributes: Attributes


def synthesize_active_players(
    report: ImportReport, config: GameConfig, rng: Random
) -> dict[int, GeneratedPlayer]:
    """Create deterministic gameplay attributes for the selected source players."""
    selected = tuple(
        player for player in report.players if player.simulation_status is SimulationStatus.ACTIVE and player.club_id is not None
    )
    overalls = _infer_overalls(selected, config)
    profiles, noise = _generation_profiles(config)
    generated: dict[int, GeneratedPlayer] = {}
    for player in selected:
        overall = overalls[player.id]
        profile = profiles[player.primary_position]
        values = {
            name: _clamp_attribute(
                overall + float(profile.get(name, profile.get("_autres", 0))) + rng.gauss(0, noise),
                config,
            )
            for name in config.attribute_names
        }
        generated[player.id] = GeneratedPlayer(
            id=player.id,
            club_id=player.club_id,
            primary_position=player.primary_position,
            secondary_positions=player.secondary_positions,
            overall=overall,
            attributes=Attributes(**values),
        )
    return generated


def build_lineup(
    club_id: int,
    players: Mapping[int, GeneratedPlayer],
    config: GameConfig,
    formation: str,
    block_height: float,
) -> Lineup:
    """Select a deterministic best available eleven for one configured formation."""
    formation_positions = _formation_positions(config, formation)
    candidates = [player for player in players.values() if player.club_id == club_id]
    if len(candidates) < len(formation_positions):
        raise ValueError(f"Club {club_id} does not have enough generated players")
    available = {player.id: player for player in candidates}
    selected: list[MatchPlayer] = []
    for position in formation_positions:
        candidate = max(
            available.values(),
            key=lambda player: (_position_score(player, position), player.overall, -player.id),
        )
        del available[candidate.id]
        selected.append(
            MatchPlayer(
                id=candidate.id,
                position=position,
                attributes=candidate.attributes,
                form=config.initial_player_state.form,
                fatigue=config.initial_player_state.fatigue,
                morale=config.initial_player_state.morale,
            )
        )
    return Lineup(club_id=club_id, players=tuple(selected), block_height=block_height)


def _infer_overalls(players: tuple[PlayerSeed, ...], config: GameConfig) -> dict[int, int]:
    source_levels = {player.id: log1p(player.market_value) for player in players}
    lowest = min(source_levels.values())
    highest = max(source_levels.values())
    if lowest == highest:
        midpoint = round((config.attribute_bounds.min + config.attribute_bounds.max) / 2)
        return {player.id: midpoint for player in players}
    span = config.attribute_bounds.max - config.attribute_bounds.min
    return {
        player_id: round(
            config.attribute_bounds.min + span * (value - lowest) / (highest - lowest)
        )
        for player_id, value in source_levels.items()
    }


def _generation_profiles(config: GameConfig) -> tuple[Mapping[str, Mapping[str, float]], float]:
    attributes_document = _mapping(config.raw_documents["attributs"], "attributs.json")
    generation = _mapping(attributes_document["profils_generation"], "profils_generation")
    profiles = _mapping(generation["profils"], "profils_generation.profils")
    return (
        {
            position: {attribute: float(offset) for attribute, offset in _mapping(profile, position).items()}
            for position, profile in profiles.items()
        },
        _number(generation["bruit_ecart_type"], "profils_generation.bruit_ecart_type"),
    )


def _formation_positions(config: GameConfig, formation: str) -> tuple[str, ...]:
    document = _mapping(config.raw_documents["formations"], "formations.json")
    formations = _mapping(document["formations"], "formations")
    positions = formations.get(formation)
    if not isinstance(positions, list) or not all(isinstance(position, str) for position in positions):
        raise ValueError(f"Unknown formation: {formation}")
    return tuple(positions)


def _position_score(player: GeneratedPlayer, assigned_position: str) -> int:
    if player.primary_position == assigned_position:
        return 2
    if assigned_position in player.secondary_positions:
        return 1
    return 0


def _clamp_attribute(value: float, config: GameConfig) -> int:
    return round(max(config.attribute_bounds.min, min(config.attribute_bounds.max, value)))


def _mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    return value


def _number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be numeric")
    return float(value)
