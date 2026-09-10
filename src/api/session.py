from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from random import Random

from core.config import GameConfig, load_config
from core.world import (
    GameDate,
    PlayedFixture,
    PlayerState,
    SeasonPlan,
    create_initial_player_states,
    create_season_plan,
    import_source_data,
    play_round_with_player_states,
    recover_between_rounds,
    synthesize_active_players,
)


@dataclass(slots=True)
class GameSession:
    config: GameConfig
    plan: SeasonPlan
    source_player_names: dict[int, str]
    player_states: dict[int, PlayerState]
    current_round: int
    current_date: GameDate
    played_fixtures: list[PlayedFixture]

    @classmethod
    def create(cls, config_directory: Path, data_directory: Path, seed: int) -> GameSession:
        config = load_config(config_directory)
        imported = import_source_data(data_directory, config)
        players = synthesize_active_players(imported, config, Random(seed))
        plan = create_season_plan(imported, players, config, Random(seed))
        return cls(
            config=config,
            plan=plan,
            source_player_names={player.id: player.name for player in imported.players},
            player_states=create_initial_player_states(players, config, Random(seed)),
            current_round=0,
            current_date=plan.start_date,
            played_fixtures=[],
        )

    def advance_round(self, seed: int) -> None:
        if self.current_round >= self.plan.round_count:
            raise ValueError("The current season is complete")
        next_round = self.current_round + 1
        if self.current_round:
            self.player_states, _ = recover_between_rounds(
                self.plan,
                completed_round=self.current_round,
                next_round=next_round,
                player_states=self.player_states,
                config=self.config,
            )
        played = play_round_with_player_states(
            self.plan,
            round_number=next_round,
            player_states=self.player_states,
            config=self.config,
            rng=Random(seed + next_round),
        )
        self.player_states = played.player_states
        self.played_fixtures.extend(played.played_round.fixtures)
        self.current_round = next_round
        self.current_date = self._round_date(next_round)

    def world_state(self) -> dict[str, object]:
        return {
            "date": self.current_date.isoformat(),
            "season": f"{self.plan.start_date.year}-{self.plan.start_date.year + 1}",
            "current_round": self.current_round,
            "round_count": self.plan.round_count,
            "next_event": "season_complete" if self.current_round == self.plan.round_count else "match_round",
        }

    def competition_summaries(self) -> list[dict[str, object]]:
        return [
            {"id": competition.id, "name": competition.name, "club_count": len(competition.club_ids)}
            for competition in self.plan.competitions
        ]

    def standings(self, competition_id: int) -> list[dict[str, object]]:
        competition = self._competition(competition_id)
        rows = [
            fixture.as_played_match()
            for fixture in self.played_fixtures
            if fixture.fixture.competition_id == competition.id
        ]
        from core.world import calculate_standings

        return [asdict(row) | {"goal_difference": row.goal_difference} for row in calculate_standings(competition.club_ids, rows, self.config.world.saison)]

    def competition_calendar(self, competition_id: int, round_number: int | None) -> list[dict[str, object]]:
        competition = self._competition(competition_id)
        results = {fixture.fixture.id: fixture for fixture in self.played_fixtures}
        return [
            {
                "id": fixture.id,
                "round": fixture.round_number,
                "date": fixture.date.isoformat(),
                "home_club_id": fixture.home_club_id,
                "away_club_id": fixture.away_club_id,
                "result": None if fixture.id not in results else {
                    "home_goals": results[fixture.id].result.home_goals,
                    "away_goals": results[fixture.id].result.away_goals,
                },
            }
            for fixture in competition.fixtures
            if round_number is None or fixture.round_number == round_number
        ]

    def club_roster(self, club_id: int) -> list[dict[str, object]]:
        if club_id not in self.plan.lineups:
            raise KeyError(club_id)
        return [
            {
                "id": player.id,
                "name": self.source_player_names[player.id],
                "position": player.primary_position,
                "overall": player.overall,
                "fatigue": self.player_states[player.id].fatigue,
                "injury": None if self.player_states[player.id].injury is None else self.player_states[player.id].injury.severity,
                "suspension_matches_remaining": self.player_states[player.id].suspension_matches_remaining,
            }
            for player in sorted(
                (player for player in self.plan.players.values() if player.club_id == club_id),
                key=lambda player: (-player.overall, player.id),
            )
        ]

    def _competition(self, competition_id: int):
        for competition in self.plan.competitions:
            if competition.id == competition_id:
                return competition
        raise KeyError(competition_id)

    def _round_date(self, round_number: int) -> GameDate:
        return next(
            fixture.date
            for competition in self.plan.competitions
            for fixture in competition.fixtures
            if fixture.round_number == round_number
        )
