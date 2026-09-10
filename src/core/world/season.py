from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from random import Random

from core.config.models import GameConfig
from core.ai import choose_lineup
from core.engine import Lineup, PossessionMatchEngine, PossessionMatchResult
from core.world.calendar import Fixture, GameDate, generate_double_round_robin
from core.world.importer import ImportReport
from core.world.standings import PlayedMatch, StandingRow, calculate_standings
from core.world.synthesis import GeneratedPlayer, build_lineup
from core.world.player_state import (
    PlayerState,
    PlayerStateEvent,
    apply_player_state_events,
    disciplinary_events,
    fatigue_events_for_lineup,
    recover_to_date,
    roll_match_injury,
    suspension_served_events,
)


@dataclass(frozen=True, slots=True)
class ScheduledCompetition:
    id: int
    name: str
    club_ids: tuple[int, ...]
    fixtures: tuple[Fixture, ...]


@dataclass(frozen=True, slots=True)
class SeasonPlan:
    start_date: GameDate
    competitions: tuple[ScheduledCompetition, ...]
    lineups: dict[int, Lineup]
    players: dict[int, GeneratedPlayer]

    @property
    def round_count(self) -> int:
        return max(len(competition.club_ids) - 1 for competition in self.competitions) * 2


@dataclass(frozen=True, slots=True)
class PlayedFixture:
    fixture: Fixture
    result: PossessionMatchResult
    home_player_ids: tuple[int, ...] = ()
    away_player_ids: tuple[int, ...] = ()

    def as_played_match(self) -> PlayedMatch:
        return PlayedMatch(
            home_club_id=self.fixture.home_club_id,
            away_club_id=self.fixture.away_club_id,
            home_goals=self.result.home_goals,
            away_goals=self.result.away_goals,
        )


@dataclass(frozen=True, slots=True)
class PlayedRound:
    round_number: int
    fixtures: tuple[PlayedFixture, ...]


@dataclass(frozen=True, slots=True)
class StatefulPlayedRound:
    played_round: PlayedRound
    player_states: dict[int, PlayerState]
    events: tuple[PlayerStateEvent, ...]


def create_season_plan(
    report: ImportReport,
    players: dict[int, GeneratedPlayer],
    config: GameConfig,
    rng: Random,
    start_date: GameDate | None = None,
) -> SeasonPlan:
    """Create every v1 league calendar and its initial, deterministic lineups."""
    if config.world.saison.matches_par_adversaire != 2:
        raise ValueError("The v1 calendar supports exactly two matches per opponent")
    active_by_division: dict[int, list[int]] = defaultdict(list)
    for club in report.clubs:
        if club.status.value == "active" and club.division_id is not None:
            active_by_division[club.division_id].append(club.id)

    start_date = start_date or GameDate(
        year=config.world.date_depart.annee,
        month=config.world.date_depart.mois,
        day=config.world.date_depart.jour,
    )
    fixture_id = 1
    competitions: list[ScheduledCompetition] = []
    for definition in config.world.competitions_simulees:
        club_ids = tuple(sorted(active_by_division[definition.division_id]))
        if len(club_ids) != definition.nb_clubs:
            raise ValueError(f"Competition {definition.nom} has an invalid club count")
        fixtures = generate_double_round_robin(
            club_ids=club_ids,
            competition_id=definition.division_id,
            first_fixture_id=fixture_id,
            start_date=start_date,
            days_between_rounds=config.world.saison.jours_entre_journees,
            rng=rng,
        )
        fixture_id += len(fixtures)
        competitions.append(
            ScheduledCompetition(
                id=definition.division_id,
                name=definition.nom,
                club_ids=club_ids,
                fixtures=fixtures,
            )
        )
    lineups = {
        club_id: build_lineup(
            club_id=club_id,
            players=players,
            config=config,
            formation=config.world.importation.formation_initiale,
            block_height=config.default_block_height.defaut,
        )
        for club_id in (club.id for club in report.clubs if club.status.value == "active")
    }
    return SeasonPlan(start_date=start_date, competitions=tuple(competitions), lineups=lineups, players=players)


def play_round(plan: SeasonPlan, round_number: int, config: GameConfig, rng: Random) -> PlayedRound:
    """Simulate a complete cross-league round without mutating the season plan."""
    if round_number < 1 or round_number > plan.round_count:
        raise ValueError(f"Round {round_number} does not exist")
    engine = PossessionMatchEngine(config)
    played: list[PlayedFixture] = []
    for competition in plan.competitions:
        for fixture in competition.fixtures:
            if fixture.round_number != round_number:
                continue
            played.append(
                PlayedFixture(
                    fixture=fixture,
                    result=engine.simulate(
                        home=plan.lineups[fixture.home_club_id],
                        away=plan.lineups[fixture.away_club_id],
                        rng=rng,
                    ),
                )
            )
    return PlayedRound(round_number=round_number, fixtures=tuple(played))


def play_round_with_player_states(
    plan: SeasonPlan,
    round_number: int,
    player_states: dict[int, PlayerState],
    config: GameConfig,
    rng: Random,
) -> StatefulPlayedRound:
    """Play a round and apply its match-fatigue events in one reducer pass."""
    if round_number < 1 or round_number > plan.round_count:
        raise ValueError(f"Round {round_number} does not exist")
    engine = PossessionMatchEngine(config)
    played: list[PlayedFixture] = []
    events: list[PlayerStateEvent] = []
    for competition in plan.competitions:
        for fixture in competition.fixtures:
            if fixture.round_number != round_number:
                continue
            home = _available_lineup(plan, fixture.home_club_id, player_states, fixture.date, config)
            away = _available_lineup(plan, fixture.away_club_id, player_states, fixture.date, config)
            result = engine.simulate(home=home, away=away, rng=rng)
            played.append(
                PlayedFixture(
                    fixture=fixture,
                    result=result,
                    home_player_ids=tuple(player.id for player in home.players),
                    away_player_ids=tuple(player.id for player in away.players),
                )
            )
            events.extend(fatigue_events_for_lineup(home, config))
            events.extend(fatigue_events_for_lineup(away, config))
            events.extend(disciplinary_events(result.events, player_states, config, rng))
            involved = {player.id: player for player in (*home.players, *away.players)}
            injured: set[int] = set()
            for player_id in result.involved_player_ids:
                if player_id in injured:
                    continue
                injury = roll_match_injury(
                    player=involved[player_id],
                    state=player_states[player_id],
                    date=fixture.date,
                    config=config,
                    rng=rng,
                    block_height=home.block_height if player_id in {player.id for player in home.players} else away.block_height,
                )
                if injury is not None:
                    events.append(injury)
                    injured.add(player_id)
            events.extend(
                suspension_served_events(
                    tuple(player.id for player in plan.players.values() if player.club_id == fixture.home_club_id),
                    player_states,
                )
            )
            events.extend(
                suspension_served_events(
                    tuple(player.id for player in plan.players.values() if player.club_id == fixture.away_club_id),
                    player_states,
                )
            )
    round_result = PlayedRound(round_number=round_number, fixtures=tuple(played))
    return StatefulPlayedRound(
        played_round=round_result,
        player_states=apply_player_state_events(player_states, tuple(events), config),
        events=tuple(events),
    )


def recover_between_rounds(
    plan: SeasonPlan,
    completed_round: int,
    next_round: int,
    player_states: dict[int, PlayerState],
    config: GameConfig,
) -> tuple[dict[int, PlayerState], tuple[PlayerStateEvent, ...]]:
    """Recover all player conditions from one scheduled round date to the next."""
    return recover_to_date(
        player_states,
        current_date=_round_date(plan, completed_round),
        target_date=_round_date(plan, next_round),
        config=config,
    )


def competition_standings(
    competition: ScheduledCompetition, played_fixtures: tuple[PlayedFixture, ...], config: GameConfig
) -> tuple[StandingRow, ...]:
    matches = tuple(
        played.as_played_match()
        for played in played_fixtures
        if played.fixture.competition_id == competition.id
    )
    return calculate_standings(competition.club_ids, matches, config.world.saison)


def _round_date(plan: SeasonPlan, round_number: int) -> GameDate:
    for competition in plan.competitions:
        for fixture in competition.fixtures:
            if fixture.round_number == round_number:
                return fixture.date
    raise ValueError(f"Round {round_number} does not exist")


def _available_lineup(
    plan: SeasonPlan,
    club_id: int,
    states: dict[int, PlayerState],
    date: GameDate,
    config: GameConfig,
) -> Lineup:
    return choose_lineup(
        club_id=club_id,
        players=plan.players,
        states=states,
        date=date,
        config=config,
        formation=config.world.importation.formation_initiale,
        block_height=config.default_block_height.defaut,
    )
