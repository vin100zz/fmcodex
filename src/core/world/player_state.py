from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import TypeAlias

from core.config.models import GameConfig
from core.engine import Lineup, MatchEvent, MatchPlayer
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
    yellow_cards: int = 0
    suspension_matches_remaining: int = 0

    def is_available(self, date: GameDate) -> bool:
        return (self.injury is None or self.injury.end_date < date) and self.suspension_matches_remaining == 0


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


@dataclass(frozen=True, slots=True)
class YellowCarded:
    player_id: int


@dataclass(frozen=True, slots=True)
class SuspensionAssigned:
    player_id: int
    matches: int


@dataclass(frozen=True, slots=True)
class SuspensionServed:
    player_id: int


PlayerStateEvent: TypeAlias = (
    FatigueConsumed
    | FatigueRecovered
    | InjuryOccurred
    | InjuryRecovered
    | YellowCarded
    | SuspensionAssigned
    | SuspensionServed
)


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
    block_height: float,
) -> InjuryOccurred | None:
    """Roll one possession-level injury check for an involved player."""
    intensity = _block_intensity(block_height, config)
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
        elif isinstance(event, YellowCarded):
            updated[event.player_id] = _replace_state(state, yellow_cards=state.yellow_cards + 1)
        elif isinstance(event, SuspensionAssigned):
            updated[event.player_id] = _replace_state(
                state,
                suspension_matches_remaining=max(state.suspension_matches_remaining, event.matches),
            )
        elif isinstance(event, SuspensionServed):
            updated[event.player_id] = _replace_state(
                state,
                suspension_matches_remaining=max(0, state.suspension_matches_remaining - 1),
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


def disciplinary_events(
    match_events: tuple[MatchEvent, ...], states: dict[int, PlayerState], config: GameConfig, rng: Random
) -> tuple[PlayerStateEvent, ...]:
    """Convert on-pitch cards into persistent yellow-card and suspension events."""
    yellow_totals = {player_id: state.yellow_cards for player_id, state in states.items()}
    match_yellows = {player_id: 0 for player_id in states}
    events: list[PlayerStateEvent] = []
    for event in match_events:
        if event.kind == "yellow_card":
            yellow_totals[event.primary_player_id] += 1
            match_yellows[event.primary_player_id] += 1
            events.append(YellowCarded(player_id=event.primary_player_id))
            if match_yellows[event.primary_player_id] == 2:
                events.append(
                    SuspensionAssigned(
                        player_id=event.primary_player_id,
                        matches=config.suspension_state.matches_double_jaune,
                    )
                )
            for threshold in config.suspension_state.seuils_cumul_jaunes:
                if yellow_totals[event.primary_player_id] == threshold.jaunes:
                    events.append(SuspensionAssigned(player_id=event.primary_player_id, matches=threshold.matches))
        elif event.kind == "red_card":
            events.append(
                SuspensionAssigned(
                    player_id=event.primary_player_id,
                    matches=rng.randint(
                        config.suspension_state.matches_rouge_min,
                        config.suspension_state.matches_rouge_max,
                    ),
                )
            )
    return tuple(events)


def suspension_served_events(
    player_ids: tuple[int, ...], states: dict[int, PlayerState]
) -> tuple[SuspensionServed, ...]:
    return tuple(
        SuspensionServed(player_id=player_id)
        for player_id in player_ids
        if states[player_id].suspension_matches_remaining > 0
    )


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
        "yellow_cards": state.yellow_cards,
        "suspension_matches_remaining": state.suspension_matches_remaining,
    }
    values.update(changes)
    return PlayerState(**values)
