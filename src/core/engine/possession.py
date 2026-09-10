from __future__ import annotations

from dataclasses import dataclass
from math import exp, log
from random import Random
from typing import Iterable

from core.config.models import GameConfig


@dataclass(frozen=True, slots=True)
class Attributes:
    passe: float
    technique: float
    finition: float
    tacle: float
    jeu_tete: float
    vision: float
    placement: float
    sang_froid: float
    vitesse: float
    endurance: float
    reflexes: float
    sorties: float
    relance: float

    def weighted(self, weights: dict[str, float]) -> float:
        return sum(getattr(self, attribute) * weight for attribute, weight in weights.items())


@dataclass(frozen=True, slots=True)
class MatchPlayer:
    id: int
    position: str
    attributes: Attributes
    form: float
    fatigue: float
    morale: float


@dataclass(frozen=True, slots=True)
class Lineup:
    club_id: int
    players: tuple[MatchPlayer, ...]
    block_height: float

    def goalkeeper(self) -> MatchPlayer:
        for player in self.players:
            if player.position == "GB":
                return player
        raise ValueError(f"Lineup {self.club_id} has no goalkeeper")


@dataclass(frozen=True, slots=True)
class MatchEvent:
    second: int
    kind: str
    club_id: int
    primary_player_id: int
    secondary_player_id: int | None
    zone: str
    lane: str
    xg: float | None = None


@dataclass(frozen=True, slots=True)
class TeamMatchStats:
    possessions: int
    shots: int
    expected_goals: float


@dataclass(frozen=True, slots=True)
class PossessionMatchResult:
    home_goals: int
    away_goals: int
    events: tuple[MatchEvent, ...]
    home_stats: TeamMatchStats
    away_stats: TeamMatchStats
    involved_player_ids: tuple[int, ...]


@dataclass(slots=True)
class _MutableStats:
    possessions: int = 0
    shots: int = 0
    expected_goals: float = 0.0

    def freeze(self) -> TeamMatchStats:
        return TeamMatchStats(
            possessions=self.possessions,
            shots=self.shots,
            expected_goals=self.expected_goals,
        )


@dataclass(frozen=True, slots=True)
class _PossessionStart:
    attacking_home: bool
    start_zone: int
    counter_attack: bool


@dataclass(frozen=True, slots=True)
class _PossessionResolution:
    events: tuple[MatchEvent, ...]
    turnover_zone: int
    involved_player_id: int


class PossessionMatchEngine:
    """Event-producing match engine based on zone and lane possessions."""

    def __init__(self, config: GameConfig) -> None:
        self._config = config
        self._engine = config.possession_engine
        self._zones = config.implications.zones
        self._lanes = config.implications.couloirs
        if self._engine.turnover.zone_declenchant_contre not in self._zones:
            raise ValueError("Counter-attack zone must exist in the implication configuration")

    def simulate(self, home: Lineup, away: Lineup, rng: Random) -> PossessionMatchResult:
        self._validate_lineups(home, away)
        home_stats = _MutableStats()
        away_stats = _MutableStats()
        events: list[MatchEvent] = []
        involved_player_ids: list[int] = []
        home_goals = away_goals = 0
        current_second = 0
        stoppages = 0
        start = _PossessionStart(attacking_home=rng.random() < 0.5, start_zone=0, counter_attack=False)

        while current_second < self._engine.chronologie.duree_match_secondes:
            current_second += self._possession_duration(rng)
            attacking = home if start.attacking_home else away
            defending = away if start.attacking_home else home
            stats = home_stats if start.attacking_home else away_stats
            stats.possessions += 1
            resolution = self._play_possession(
                attacking=attacking,
                defending=defending,
                attacking_is_home=start.attacking_home,
                start=start,
                second=current_second,
                rng=rng,
            )
            events.extend(resolution.events)
            involved_player_ids.append(resolution.involved_player_id)
            for event in resolution.events:
                if event.kind == "shot":
                    stats.shots += 1
                    stats.expected_goals += event.xg or 0.0
                if event.kind == "goal":
                    stoppages += 1
                    if start.attacking_home:
                        home_goals += 1
                    else:
                        away_goals += 1
            start = self._next_possession(start, resolution.turnover_zone)

        additional_seconds = self._additional_time(stoppages, rng)
        while current_second < self._engine.chronologie.duree_match_secondes + additional_seconds:
            current_second += self._possession_duration(rng)
            attacking = home if start.attacking_home else away
            defending = away if start.attacking_home else home
            stats = home_stats if start.attacking_home else away_stats
            stats.possessions += 1
            resolution = self._play_possession(
                attacking=attacking,
                defending=defending,
                attacking_is_home=start.attacking_home,
                start=start,
                second=current_second,
                rng=rng,
            )
            events.extend(resolution.events)
            involved_player_ids.append(resolution.involved_player_id)
            for event in resolution.events:
                if event.kind == "shot":
                    stats.shots += 1
                    stats.expected_goals += event.xg or 0.0
                if event.kind == "goal":
                    if start.attacking_home:
                        home_goals += 1
                    else:
                        away_goals += 1
            start = self._next_possession(start, resolution.turnover_zone)

        return PossessionMatchResult(
            home_goals=home_goals,
            away_goals=away_goals,
            events=tuple(events),
            home_stats=home_stats.freeze(),
            away_stats=away_stats.freeze(),
            involved_player_ids=tuple(involved_player_ids),
        )

    def _play_possession(
        self,
        attacking: Lineup,
        defending: Lineup,
        attacking_is_home: bool,
        start: _PossessionStart,
        second: int,
        rng: Random,
    ) -> _PossessionResolution:
        zone_index = start.start_zone
        lane_index = self._choose_lane(attacking, defending, zone_index, rng)
        involved_player = self._select_player(attacking.players, zone_index, lane_index, rng)
        final_zone = len(self._zones) - 1
        while zone_index < final_zone:
            attack_note = self._zone_note(attacking, zone_index, lane_index, "progression_attaque")
            defense_note = self._zone_note(defending, zone_index, lane_index, "progression_defense")
            if start.counter_attack:
                defense_note -= self._engine.turnover.malus_defensif_contre
                defense_note -= self._engine.turnover.malus_defensif_couloir_concerne
            bias = self._engine.transitions.bonus_domicile if attacking_is_home else 0.0
            if not _success(self._engine.transitions.k_prog * (attack_note - defense_note) + bias, rng):
                return _PossessionResolution(
                    events=self._card_events(defending, zone_index, lane_index, second, rng),
                    turnover_zone=zone_index,
                    involved_player_id=involved_player.id,
                )
            zone_index += 1
            lane_index = self._maybe_change_lane(attacking, lane_index, rng)

        attack_note = self._zone_note(attacking, zone_index, lane_index, "occasion_attaque")
        defense_note = self._zone_note(defending, zone_index, lane_index, "occasion_defense")
        if start.counter_attack:
            defense_note -= self._engine.turnover.malus_defensif_contre
        if not _success(self._engine.transitions.k_occ * (attack_note - defense_note), rng):
            return _PossessionResolution(
                events=self._card_events(defending, zone_index, lane_index, second, rng),
                turnover_zone=zone_index,
                involved_player_id=involved_player.id,
            )
        return _PossessionResolution(
            events=self._resolve_chance(attacking, defending, zone_index, lane_index, start.counter_attack, second, rng),
            turnover_zone=-1,
            involved_player_id=involved_player.id,
        )

    def _card_events(
        self, defending: Lineup, zone_index: int, lane_index: int, second: int, rng: Random
    ) -> tuple[MatchEvent, ...]:
        defender = self._select_player(defending.players, zone_index, lane_index, rng)
        zone_factor = self._engine.cartons.poids_zone_defense if zone_index == 0 else 1.0
        yellow_probability = (
            self._engine.cartons.probabilite_jaune_par_turnover_defensif
            * zone_factor
            * (1 + self._engine.cartons.poids_agressivite_tacle * defender.attributes.tacle)
        )
        direct_red_probability = self._engine.cartons.probabilite_rouge_direct_par_turnover_defensif * zone_factor
        zone = self._zones[zone_index]
        lane = self._lanes[lane_index]
        if rng.random() < direct_red_probability:
            return (
                MatchEvent(second, "red_card", defending.club_id, defender.id, None, zone, lane),
            )
        if rng.random() < min(1.0, yellow_probability):
            return (
                MatchEvent(second, "yellow_card", defending.club_id, defender.id, None, zone, lane),
            )
        return ()

    def _zone_note(self, lineup: Lineup, zone_index: int, lane_index: int, composite: str) -> float:
        defensive_phase = composite.endswith("defense")
        activities = [
            self._activity(player.position, zone_index, lane_index, defensive_phase)
            for player in lineup.players
        ]
        density = sum(activities)
        if density == 0:
            return self._engine.densite.note_plancher
        quality = sum(
            activity
            * player.attributes.weighted(self._config.composites[composite])
            * player.form
            * player.fatigue
            * self._morale_multiplier(player.morale)
            for activity, player in zip(activities, lineup.players, strict=True)
        ) / density
        density_factor = (density / self._engine.densite.reference) ** self._engine.densite.exposant
        return quality * density_factor

    def _activity(self, position: str, zone_index: int, lane_index: int, defensive_phase: bool) -> float:
        vertical = (
            self._config.implications.vertical_defense
            if defensive_phase
            else self._config.implications.vertical_attaque
        )
        return (
            vertical[position][zone_index]
            * self._config.implications.lateral[position][lane_index]
        )

    def _choose_lane(self, attacking: Lineup, defending: Lineup, zone_index: int, rng: Random) -> int:
        gaps = [
            self._zone_note(attacking, zone_index, lane, "progression_attaque")
            - self._zone_note(defending, zone_index, lane, "progression_defense")
            for lane in range(len(self._lanes))
        ]
        highest = max(gaps)
        weights = [exp(self._engine.couloirs.beta_softmax * (gap - highest)) for gap in gaps]
        return _weighted_index(weights, rng)

    def _maybe_change_lane(self, attacking: Lineup, lane_index: int, rng: Random) -> int:
        average_vision = sum(player.attributes.vision for player in attacking.players) / len(attacking.players)
        probability = min(
            1.0,
            self._engine.couloirs.probabilite_changement_aile
            + self._engine.couloirs.poids_vision_changement_aile * average_vision,
        )
        if rng.random() >= probability:
            return lane_index
        alternatives = [index for index in range(len(self._lanes)) if index != lane_index]
        return alternatives[_weighted_index([1.0] * len(alternatives), rng)]

    def _resolve_chance(
        self,
        attacking: Lineup,
        defending: Lineup,
        zone_index: int,
        lane_index: int,
        counter_attack: bool,
        second: int,
        rng: Random,
    ) -> tuple[MatchEvent, ...]:
        is_central = lane_index == len(self._lanes) // 2
        shooter = self._select_player(attacking.players, zone_index, lane_index, rng)
        goalkeeper = defending.goalkeeper()
        if is_central:
            base_xg = self._engine.occasion.xg_base_frappe
            attacker_note = shooter.attributes.weighted(self._config.composites["tir"])
            goalkeeper_note = goalkeeper.attributes.weighted(self._config.composites["arret"])
        else:
            base_xg = self._engine.occasion.xg_base_centre
            attacker_note = shooter.attributes.weighted(self._config.composites["tete"])
            goalkeeper_note = goalkeeper.attributes.weighted(self._config.composites["sortie"])
        if counter_attack:
            base_xg *= self._engine.occasion.multiplicateur_contre
        chance = _adjust_probability(
            base_xg,
            self._engine.occasion.sensibilite_tireur_gardien * (attacker_note - goalkeeper_note),
        )
        zone = self._zones[zone_index]
        lane = self._lanes[lane_index]
        shot = MatchEvent(
            second=second,
            kind="shot",
            club_id=attacking.club_id,
            primary_player_id=shooter.id,
            secondary_player_id=goalkeeper.id,
            zone=zone,
            lane=lane,
            xg=chance,
        )
        if rng.random() < chance:
            return (
                shot,
                MatchEvent(
                    second=second,
                    kind="goal",
                    club_id=attacking.club_id,
                    primary_player_id=shooter.id,
                    secondary_player_id=None,
                    zone=zone,
                    lane=lane,
                    xg=chance,
                ),
            )
        return (
            shot,
            MatchEvent(
                second=second,
                kind="save",
                club_id=defending.club_id,
                primary_player_id=goalkeeper.id,
                secondary_player_id=shooter.id,
                zone=zone,
                lane=lane,
                xg=chance,
            ),
        )

    def _select_player(
        self, players: Iterable[MatchPlayer], zone_index: int, lane_index: int, rng: Random
    ) -> MatchPlayer:
        candidates = tuple(players)
        weights = [self._activity(player.position, zone_index, lane_index, False) for player in candidates]
        return candidates[_weighted_index(weights, rng)]

    def _next_possession(self, start: _PossessionStart, turnover_zone: int) -> _PossessionStart:
        threshold = self._zones.index(self._engine.turnover.zone_declenchant_contre)
        is_counter = turnover_zone >= threshold
        next_zone = turnover_zone if is_counter else 0
        return _PossessionStart(
            attacking_home=not start.attacking_home,
            start_zone=next_zone,
            counter_attack=is_counter,
        )

    def _possession_duration(self, rng: Random) -> int:
        shape = self._engine.chronologie.duree_possession_forme_gamma
        scale = self._engine.chronologie.duree_possession_moyenne / shape
        return max(self._engine.chronologie.duree_possession_min, round(rng.gammavariate(shape, scale)))

    def _additional_time(self, stoppages: int, rng: Random) -> int:
        base = rng.randint(
            self._engine.chronologie.temps_additionnel_min,
            self._engine.chronologie.temps_additionnel_max,
        )
        return base + stoppages * self._engine.chronologie.secondes_par_arret_de_jeu

    def _morale_multiplier(self, morale: float) -> float:
        return 1.0 + self._config.morale_match_amplitude * (2 * morale - 1)

    def _validate_lineups(self, home: Lineup, away: Lineup) -> None:
        allowed_positions = set(self._config.implications.vertical_attaque)
        for lineup in (home, away):
            if len(lineup.players) != self._config.world.regles_match.joueurs_sur_terrain:
                raise ValueError(f"Lineup {lineup.club_id} must contain eleven players")
            if any(player.position not in allowed_positions for player in lineup.players):
                raise ValueError(f"Lineup {lineup.club_id} contains an unsupported position")
            lineup.goalkeeper()


def _success(value: float, rng: Random) -> bool:
    return rng.random() < 1 / (1 + exp(-value))


def _adjust_probability(base_probability: float, adjustment: float) -> float:
    odds = log(base_probability / (1 - base_probability))
    return 1 / (1 + exp(-(odds + adjustment)))


def _weighted_index(weights: list[float], rng: Random) -> int:
    total = sum(weights)
    if total <= 0:
        return 0
    target = rng.random() * total
    cumulative = 0.0
    for index, weight in enumerate(weights):
        cumulative += weight
        if cumulative >= target:
            return index
    return len(weights) - 1
