from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import TypeAlias

from core.config.models import GameConfig
from core.engine import Lineup, MatchPlayer
from core.world.calendar import GameDate
from core.world.synthesis import GeneratedPlayer


@dataclass(frozen=True, slots=True)
class Injury:
    severity: str
    start_date: GameDate
    end_date: GameDate


@dataclass(frozen=True, slots=True)
class PlayerState:
    fatigue: float
    form: float
    morale: float
    fragility: float
    injury: Injury | None = None

    def is_available(self, date: GameDate) -> bool:
        return self.injury is None or self.injury.end_date < date


@dataclass(frozen=True, slots=True)
class FatigueConsumed:
    player_id: int
    amount: float


@dataclass(frozen=True, slots=True)
class FatigueRecovered:
    player_id: int
    amount: float


@dataclass(frozen=True, slots=True)
class InjuryOccurred:
    player_id: int
    injury: Injury


@dataclass(frozen=True, slots=True)
class InjuryRecovered:
    player_id: int


PlayerStateEvent: TypeAlias = FatigueConsumed | FatigueRecovered | InjuryOccurred | InjuryRecovered


def create_initial_player_states(
    players: dict[int, GeneratedPlayer], config: GameConfig, rng: Random
) -> dict[int, PlayerState]:
    """Create stable per-player fragility and configured initial condition."""
    return {
        player_id: PlayerState(
            fatigue=config.initial_player_state.fatigue,
            form=config.initial_player_state.form,
            morale=config.initial_player_state.morale,
            fragility=rng.uniform(config.injury_state.fragilite_min, config.injury_state.fragilite_max),
        )
        for player_id in players
    }


def fatigue_events_for_lineup(lineup: Lineup, config: GameConfig) -> tuple[FatigueConsumed, ...]:
    """Calculate match fatigue without mutating the supplied player states."""
    intensity = _block_intensity(lineup.block_height, config)
    minutes = config.possession_engine.chronologie.duree_match_secondes / 60
    return tuple(
        FatigueConsumed(
            player_id=player.id,
            amount=(
                config.fatigue_state.consommation_par_minute
                * minutes
                * intensity
                / (
                    config.fatigue_state.resistance_base
                    + config.fatigue_state.resistance_facteur_endurance
                    * player.attributes.endurance
                    / config.attribute_bounds.max
                )
            ),
        )
        for player in lineup.players
    )


def recovery_events(
    states: dict[int, PlayerState], date: GameDate, days: int, config: GameConfig
) -> tuple[PlayerStateEvent, ...]:
    """Calculate daily recovery and completed-injury events."""
    events: list[PlayerStateEvent] = []
    for player_id, state in states.items():
        if state.injury is not None and state.injury.end_date < date:
            events.append(InjuryRecovered(player_id=player_id))
            continue
        if state.injury is None:
            events.append(
                FatigueRecovered(
                    player_id=player_id,
                    amount=days * config.fatigue_state.recuperation_base_par_jour,
                )
            )
    return tuple(events)


def recover_to_date(
    states: dict[int, PlayerState], current_date: GameDate, target_date: GameDate, config: GameConfig
) -> tuple[dict[int, PlayerState], tuple[PlayerStateEvent, ...]]:
    """Advance player conditions to a later game date through explicit events."""
    events = recovery_events(states, target_date, current_date.days_until(target_date), config)
    return apply_player_state_events(states, events, config), events


def roll_match_injury(
    player: MatchPlayer,
    state: PlayerState,
    date: GameDate,
    config: GameConfig,
    rng: Random,
) -> InjuryOccurred | None:
    """Roll one possession-level injury check for an involved player."""
    intensity = _block_intensity(0.0, config)
    probability = (
        config.injury_state.probabilite_base_par_possession
        * (config.injury_state.facteur_fatigue_max - state.fatigue)
        * state.fragility
        * intensity
    )
    if rng.random() >= probability:
        return None
    severity = _weighted_severity(config, rng)
    duration = rng.randint(severity.jours_min, severity.jours_max)
    return InjuryOccurred(
        player_id=player.id,
        injury=Injury(
            severity=severity.nom,
            start_date=date,
            end_date=date.add_days(duration),
        ),
    )


def apply_player_state_events(
    states: dict[int, PlayerState], events: tuple[PlayerStateEvent, ...], config: GameConfig
) -> dict[int, PlayerState]:
    """Apply state events in one explicit reducer pass."""
    updated = dict(states)
    for event in events:
        state = updated[event.player_id]
        if isinstance(event, FatigueConsumed):
            updated[event.player_id] = _replace_state(state, fatigue=max(0.0, state.fatigue - event.amount))
        elif isinstance(event, FatigueRecovered):
            updated[event.player_id] = _replace_state(state, fatigue=min(1.0, state.fatigue + event.amount))
        elif isinstance(event, InjuryOccurred):
            updated[event.player_id] = _replace_state(state, injury=event.injury)
        elif isinstance(event, InjuryRecovered):
            updated[event.player_id] = _replace_state(
                state,
                fatigue=config.injury_state.fatigue_retour_de_blessure,
                form=config.injury_state.forme_retour_de_blessure,
                injury=None,
            )
    return updated


def apply_player_conditions(lineup: Lineup, states: dict[int, PlayerState], date: GameDate) -> Lineup:
    """Project immutable player conditions onto a selected lineup."""
    conditioned: list[MatchPlayer] = []
    for player in lineup.players:
        state = states[player.id]
        if not state.is_available(date):
            raise ValueError(f"Player {player.id} is unavailable on {date}")
        conditioned.append(
            replace(player, fatigue=state.fatigue, form=state.form, morale=state.morale)
        )
    return replace(lineup, players=tuple(conditioned))


def _block_intensity(height: float, config: GameConfig) -> float:
    intensities = config.fatigue_state.intensite_par_hauteur_bloc
    if height <= 0:
        return intensities.bloc_bas + (height + 1) * (intensities.equilibre - intensities.bloc_bas)
    return intensities.equilibre + height * (intensities.pressing_haut - intensities.equilibre)


def _weighted_severity(config: GameConfig, rng: Random):
    target = rng.random()
    total = 0.0
    for severity in config.injury_state.gravites:
        total += severity.part
        if total >= target:
            return severity
    return config.injury_state.gravites[-1]


def _replace_state(state: PlayerState, **changes: object) -> PlayerState:
    values = {
        "fatigue": state.fatigue,
        "form": state.form,
        "morale": state.morale,
        "fragility": state.fragility,
        "injury": state.injury,
    }
    values.update(changes)
    return PlayerState(**values)
