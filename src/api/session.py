from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from random import Random

from core.config import GameConfig, load_config
from core.world import (
    GameDate,
    ImportReport,
    PlayedFixture,
    PlayerState,
    SeasonPlan,
    create_initial_player_states,
    create_season_plan,
    import_source_data,
    play_round_with_player_states,
    recover_to_date,
    reset_season_discipline,
    synthesize_active_players,
)


@dataclass(slots=True)
class GameSession:
    config_directory: Path
    data_directory: Path
    seed: int
    config: GameConfig
    import_report: ImportReport
    plan: SeasonPlan
    source_player_names: dict[int, str]
    player_states: dict[int, PlayerState]
    current_round: int
    current_date: GameDate
    played_fixtures: list[PlayedFixture]
    season_history: list[dict[str, object]]

    @classmethod
    def create(cls, config_directory: Path, data_directory: Path, seed: int) -> GameSession:
        config = load_config(config_directory)
        imported = import_source_data(data_directory, config)
        players = synthesize_active_players(imported, config, Random(seed))
        plan = create_season_plan(imported, players, config, Random(seed))
        return cls(
            config_directory=config_directory,
            data_directory=data_directory,
            seed=seed,
            config=config,
            import_report=imported,
            plan=plan,
            source_player_names={player.id: player.name for player in imported.players},
            player_states=create_initial_player_states(players, config, Random(seed)),
            current_round=0,
            current_date=plan.start_date,
            played_fixtures=[],
            season_history=[],
        )

    def advance_round(self, seed: int | None = None) -> None:
        if self.current_round >= self.plan.round_count:
            raise ValueError("The current season is complete")
        next_round = self.current_round + 1
        next_date = self._round_date(next_round)
        if self.current_date < next_date:
            self.player_states, _ = recover_to_date(
                self.player_states,
                current_date=self.current_date,
                target_date=next_date,
                config=self.config,
            )
        played = play_round_with_player_states(
            self.plan,
            round_number=next_round,
            player_states=self.player_states,
            config=self.config,
            rng=Random(self.seed + next_round),
        )
        self.player_states = played.player_states
        self.played_fixtures.extend(played.played_round.fixtures)
        self.current_round = next_round
        self.current_date = next_date

    def advance_day(self) -> None:
        """Advance one calendar day, automatically playing a scheduled match round."""
        if self.current_round >= self.plan.round_count:
            raise ValueError("The current season is complete")
        next_date = self._round_date(self.current_round + 1)
        if self.current_date == next_date:
            self.advance_round()
            return
        target_date = self.current_date.add_days(1)
        self.player_states, _ = recover_to_date(
            self.player_states,
            current_date=self.current_date,
            target_date=target_date,
            config=self.config,
        )
        self.current_date = target_date
        if self.current_date == next_date:
            self.advance_round()

    def start_next_season(self) -> None:
        """Archive a completed season and create the following season's fixtures."""
        if self.current_round != self.plan.round_count:
            raise ValueError("The current season is not complete")
        season_label = f"{self.plan.start_date.year}-{self.plan.start_date.year + 1}"
        self.season_history.extend(
            {
                "season": season_label,
                "competition_id": competition.id,
                "champion_club_id": self.standings(competition.id)[0]["club_id"],
            }
            for competition in self.plan.competitions
        )
        next_start = GameDate(
            self.plan.start_date.year + 1,
            self.plan.start_date.month,
            self.plan.start_date.day,
        )
        self.player_states = reset_season_discipline(self.player_states, self.config)
        self.plan = create_season_plan(
            self.import_report,
            self.plan.players,
            self.config,
            Random(self.seed + next_start.year),
            start_date=next_start,
        )
        self.current_round = 0
        self.current_date = next_start
        self.played_fixtures = []

    def complete_current_season(self) -> None:
        """Simulate every remaining scheduled round of the current season."""
        while self.current_round < self.plan.round_count:
            self.advance_round()

    def world_state(self) -> dict[str, object]:
        return {
            "date": self.current_date.isoformat(),
            "season": f"{self.plan.start_date.year}-{self.plan.start_date.year + 1}",
            "current_round": self.current_round,
            "round_count": self.plan.round_count,
            "next_event": "season_complete" if self.current_round == self.plan.round_count else "match_round",
            "completed_seasons": len(self.season_history) // len(self.plan.competitions),
        }

    def competition_summaries(self) -> list[dict[str, object]]:
        return [
            {"id": competition.id, "name": competition.name, "club_count": len(competition.club_ids)}
            for competition in self.plan.competitions
        ]

    def clubs(self, competition_id: int | None = None, search: str | None = None) -> list[dict[str, object]]:
        active_competitions = {
            club_id: competition.id
            for competition in self.plan.competitions
            for club_id in competition.club_ids
        }
        needle = (search or "").casefold()
        return [
            {
                "id": club.id,
                "name": club.name,
                "nation": club.nation_source,
                "status": club.status.value,
                "competition_id": active_competitions.get(club.id),
            }
            for club in self.import_report.clubs
            if (competition_id is None or active_competitions.get(club.id) == competition_id)
            and (not needle or needle in club.name.casefold())
        ]

    def club_summary(self, club_id: int) -> dict[str, object]:
        club = next((club for club in self.import_report.clubs if club.id == club_id), None)
        if club is None:
            raise KeyError(club_id)
        active_competition = next(
            (competition for competition in self.plan.competitions if club_id in competition.club_ids),
            None,
        )
        return {
            "id": club.id,
            "name": club.name,
            "nation": club.nation_source,
            "status": club.status.value,
            "competition_id": None if active_competition is None else active_competition.id,
            "current_position": None
            if active_competition is None
            else next(
                index
                for index, row in enumerate(self.standings(active_competition.id), start=1)
                if row["club_id"] == club_id
            ),
        }

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
                "season": self.player_statistics().get(player.id, PlayerSeasonStatistics()).as_dict(),
            }
            for player in sorted(
                (player for player in self.plan.players.values() if player.club_id == club_id),
                key=lambda player: (-player.overall, player.id),
            )
        ]

    def player_detail(self, player_id: int) -> dict[str, object]:
        player = self.plan.players.get(player_id)
        if player is None:
            raise KeyError(player_id)
        state = self.player_states[player_id]
        return {
            "id": player.id,
            "name": self.source_player_names[player.id],
            "club_id": player.club_id,
            "position": player.primary_position,
            "secondary_positions": list(player.secondary_positions),
            "overall": player.overall,
            "attributes": asdict(player.attributes),
            "fatigue": state.fatigue,
            "form": state.form,
            "morale": state.morale,
            "injury": None if state.injury is None else {
                "severity": state.injury.severity,
                "end_date": state.injury.end_date.isoformat(),
            },
            "suspension_matches_remaining": state.suspension_matches_remaining,
            "season": self.player_statistics().get(player_id, PlayerSeasonStatistics()).as_dict(),
        }

    def players(
        self, position: str | None = None, club_id: int | None = None, minimum_overall: int | None = None
    ) -> list[dict[str, object]]:
        return [
            {
                "id": player.id,
                "name": self.source_player_names[player.id],
                "club_id": player.club_id,
                "position": player.primary_position,
                "overall": player.overall,
            }
            for player in sorted(self.plan.players.values(), key=lambda player: (-player.overall, player.id))
            if (position is None or player.primary_position == position)
            and (club_id is None or player.club_id == club_id)
            and (minimum_overall is None or player.overall >= minimum_overall)
        ]

    def club_calendar(self, club_id: int) -> list[dict[str, object]]:
        competition = next((item for item in self.plan.competitions if club_id in item.club_ids), None)
        if competition is None:
            raise KeyError(club_id)
        return [
            item
            for item in self.competition_calendar(competition.id, round_number=None)
            if item["home_club_id"] == club_id or item["away_club_id"] == club_id
        ]

    def match_detail(self, fixture_id: int) -> dict[str, object]:
        played = next((fixture for fixture in self.played_fixtures if fixture.fixture.id == fixture_id), None)
        if played is None:
            raise KeyError(fixture_id)
        return {
            "id": played.fixture.id,
            "competition_id": played.fixture.competition_id,
            "round": played.fixture.round_number,
            "date": played.fixture.date.isoformat(),
            "home_club_id": played.fixture.home_club_id,
            "away_club_id": played.fixture.away_club_id,
            "home_goals": played.result.home_goals,
            "away_goals": played.result.away_goals,
            "home_stats": asdict(played.result.home_stats),
            "away_stats": asdict(played.result.away_stats),
            "events": [asdict(event) for event in played.result.events],
        }

    def player_statistics(self, competition_id: int | None = None) -> dict[int, PlayerSeasonStatistics]:
        statistics: dict[int, PlayerSeasonStatistics] = {}
        for played in self.played_fixtures:
            if competition_id is not None and played.fixture.competition_id != competition_id:
                continue
            for player_id in (*played.home_player_ids, *played.away_player_ids):
                statistics[player_id] = statistics.get(player_id, PlayerSeasonStatistics()).played_match()
            for event in played.result.events:
                current = statistics.get(event.primary_player_id, PlayerSeasonStatistics())
                if event.kind == "goal":
                    statistics[event.primary_player_id] = current.with_goal()
                elif event.kind == "shot":
                    statistics[event.primary_player_id] = current.with_shot()
                elif event.kind == "yellow_card":
                    statistics[event.primary_player_id] = current.with_yellow()
                elif event.kind == "red_card":
                    statistics[event.primary_player_id] = current.with_red()
        return statistics

    def competition_statistics(self, competition_id: int, kind: str) -> list[dict[str, object]]:
        self._competition(competition_id)
        statistics = self.player_statistics(competition_id)
        field = {"buteurs": "goals", "tirs": "shots", "cartons": "yellow_cards"}.get(kind)
        if field is None:
            raise ValueError("Unsupported competition statistic")
        return [
            {"player_id": player_id, "name": self.source_player_names[player_id], **stats.as_dict()}
            for player_id, stats in sorted(
                statistics.items(), key=lambda item: (-getattr(item[1], field), -item[1].matches, item[0])
            )
            if getattr(stats, field) > 0
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


@dataclass(frozen=True, slots=True)
class PlayerSeasonStatistics:
    matches: int = 0
    goals: int = 0
    shots: int = 0
    yellow_cards: int = 0
    red_cards: int = 0

    def played_match(self) -> PlayerSeasonStatistics:
        return PlayerSeasonStatistics(
            matches=self.matches + 1,
            goals=self.goals,
            shots=self.shots,
            yellow_cards=self.yellow_cards,
            red_cards=self.red_cards,
        )

    def with_goal(self) -> PlayerSeasonStatistics:
        return PlayerSeasonStatistics(
            matches=self.matches,
            goals=self.goals + 1,
            shots=self.shots,
            yellow_cards=self.yellow_cards,
            red_cards=self.red_cards,
        )

    def with_shot(self) -> PlayerSeasonStatistics:
        return PlayerSeasonStatistics(
            matches=self.matches,
            goals=self.goals,
            shots=self.shots + 1,
            yellow_cards=self.yellow_cards,
            red_cards=self.red_cards,
        )

    def with_yellow(self) -> PlayerSeasonStatistics:
        return PlayerSeasonStatistics(
            matches=self.matches,
            goals=self.goals,
            shots=self.shots,
            yellow_cards=self.yellow_cards + 1,
            red_cards=self.red_cards,
        )

    def with_red(self) -> PlayerSeasonStatistics:
        return PlayerSeasonStatistics(
            matches=self.matches,
            goals=self.goals,
            shots=self.shots,
            yellow_cards=self.yellow_cards,
            red_cards=self.red_cards + 1,
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "matches": self.matches,
            "goals": self.goals,
            "shots": self.shots,
            "yellow_cards": self.yellow_cards,
            "red_cards": self.red_cards,
        }
