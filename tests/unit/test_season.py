from pathlib import Path
from random import Random
from dataclasses import replace
import unittest

from core.config import load_config
from core.world import (
    competition_standings,
    create_initial_player_states,
    create_season_plan,
    import_source_data,
    play_round,
    play_round_with_player_states,
    recover_between_rounds,
    synthesize_active_players,
    SuspensionServed,
)


WORKSPACE = Path(__file__).resolve().parents[2]


class SeasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(WORKSPACE / "config")
        imported = import_source_data(WORKSPACE / "data", cls.config)
        players = synthesize_active_players(imported, cls.config, Random(20260910))
        cls.plan = create_season_plan(imported, players, cls.config, Random(20260910))
        cls.player_states = create_initial_player_states(players, cls.config, Random(20260910))

    def test_plan_contains_every_v1_fixture(self) -> None:
        self.assertEqual(len(self.plan.competitions), 5)
        self.assertEqual(sum(len(competition.fixtures) for competition in self.plan.competitions), 1752)
        self.assertEqual(len(self.plan.lineups), 96)

    def test_round_plays_each_active_club_once(self) -> None:
        played = play_round(self.plan, round_number=1, config=self.config, rng=Random(7))

        self.assertEqual(len(played.fixtures), 48)
        for competition in self.plan.competitions:
            fixtures = [item for item in played.fixtures if item.fixture.competition_id == competition.id]
            participants = [club_id for fixture in fixtures for club_id in (fixture.fixture.home_club_id, fixture.fixture.away_club_id)]
            self.assertEqual(len(participants), len(set(participants)))
            table = competition_standings(competition, played.fixtures, self.config)
            self.assertEqual(sum(row.played for row in table), len(fixtures) * 2)

    def test_stateful_round_applies_match_fatigue(self) -> None:
        result = play_round_with_player_states(
            self.plan,
            round_number=1,
            player_states=self.player_states,
            config=self.config,
            rng=Random(7),
        )

        self.assertEqual(len(result.played_round.fixtures), 48)
        self.assertTrue(any(state.fatigue < 1.0 for state in result.player_states.values()))
        self.assertTrue(all(state.fatigue == 1.0 for state in self.player_states.values()))

    def test_players_recover_between_scheduled_rounds(self) -> None:
        played = play_round_with_player_states(
            self.plan,
            round_number=1,
            player_states=self.player_states,
            config=self.config,
            rng=Random(7),
        )
        recovered, events = recover_between_rounds(
            self.plan,
            completed_round=1,
            next_round=2,
            player_states=played.player_states,
            config=self.config,
        )

        self.assertTrue(events)
        available_before_recovery = (
            player_id
            for player_id, state in played.player_states.items()
            if state.injury is None
        )
        self.assertTrue(
            all(
                recovered[player_id].fatigue >= played.player_states[player_id].fatigue
                for player_id in available_before_recovery
            )
        )
        self.assertTrue(all(0.0 <= state.fatigue <= 1.0 for state in recovered.values()))

    def test_suspended_player_is_replaced_and_serves_the_round(self) -> None:
        suspended_player = self.plan.lineups[next(iter(self.plan.lineups))].players[0]
        states = dict(self.player_states)
        states[suspended_player.id] = replace(
            states[suspended_player.id], suspension_matches_remaining=1
        )

        result = play_round_with_player_states(
            self.plan,
            round_number=1,
            player_states=states,
            config=self.config,
            rng=Random(7),
        )

        self.assertEqual(result.player_states[suspended_player.id].suspension_matches_remaining, 0)
        self.assertIn(
            suspended_player.id,
            {event.player_id for event in result.events if isinstance(event, SuspensionServed)},
        )
