from pathlib import Path
from random import Random
import unittest

from core.config import load_config
from core.world import (
    GameDate,
    PlayerState,
    apply_player_state_events,
    fatigue_events_for_lineup,
    recovery_events,
)
from benchmarks.synthetic import synthetic_lineup


WORKSPACE = Path(__file__).resolve().parents[2]


class PlayerStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(WORKSPACE / "config")

    def test_match_fatigue_is_applied_by_the_event_reducer(self) -> None:
        lineup = synthetic_lineup(self.config, club_id=1, level=70, formation="4-3-3")
        states = {
            player.id: PlayerState(fatigue=1.0, form=1.0, morale=0.6, fragility=1.0)
            for player in lineup.players
        }

        events = fatigue_events_for_lineup(lineup, self.config)
        updated = apply_player_state_events(states, events, self.config)

        self.assertTrue(all(state.fatigue < 1.0 for state in updated.values()))
        self.assertTrue(all(states[player_id].fatigue == 1.0 for player_id in states))

    def test_recovery_restores_fatigue_without_mutating_input(self) -> None:
        states = {1: PlayerState(fatigue=0.4, form=1.0, morale=0.6, fragility=1.0)}
        events = recovery_events(states, GameDate(2026, 8, 11), days=1, config=self.config)
        updated = apply_player_state_events(states, events, self.config)

        self.assertGreater(updated[1].fatigue, states[1].fatigue)
        self.assertEqual(states[1].fatigue, 0.4)
