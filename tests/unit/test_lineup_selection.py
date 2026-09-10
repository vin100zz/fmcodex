from pathlib import Path
import unittest

from core.ai import choose_lineup
from core.config import load_config
from core.engine import Attributes
from core.world import GameDate, GeneratedPlayer, PlayerState


WORKSPACE = Path(__file__).resolve().parents[2]


class LineupSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(WORKSPACE / "config")

    def test_fatigued_starters_are_rotated_for_fresher_adequate_players(self) -> None:
        formation = tuple(self.config.raw_documents["formations"]["formations"]["4-3-3"])
        players: dict[int, GeneratedPlayer] = {}
        states: dict[int, PlayerState] = {}
        for index, position in enumerate(formation, start=1):
            players[index] = self._player(index, position, attribute=80)
            players[100 + index] = self._player(100 + index, position, attribute=74)
            states[index] = PlayerState(fatigue=0.1, form=1.0, morale=0.6, fragility=1.0)
            states[100 + index] = PlayerState(fatigue=1.0, form=1.0, morale=0.6, fragility=1.0)

        lineup = choose_lineup(
            club_id=1,
            players=players,
            states=states,
            date=GameDate(2026, 8, 10),
            config=self.config,
            formation="4-3-3",
            block_height=0.0,
        )

        self.assertEqual({player.id for player in lineup.players}, {101 + index for index in range(11)})

    def test_rotation_does_not_replace_a_clearly_better_player(self) -> None:
        formation = tuple(self.config.raw_documents["formations"]["formations"]["4-3-3"])
        players: dict[int, GeneratedPlayer] = {}
        states: dict[int, PlayerState] = {}
        for index, position in enumerate(formation, start=1):
            players[index] = self._player(index, position, attribute=90)
            players[100 + index] = self._player(100 + index, position, attribute=70)
            states[index] = PlayerState(fatigue=0.1, form=1.0, morale=0.6, fragility=1.0)
            states[100 + index] = PlayerState(fatigue=1.0, form=1.0, morale=0.6, fragility=1.0)

        lineup = choose_lineup(
            club_id=1,
            players=players,
            states=states,
            date=GameDate(2026, 8, 10),
            config=self.config,
            formation="4-3-3",
            block_height=0.0,
        )

        self.assertEqual({player.id for player in lineup.players}, set(range(1, 12)))

    def _player(self, player_id: int, position: str, attribute: int) -> GeneratedPlayer:
        return GeneratedPlayer(
            id=player_id,
            club_id=1,
            primary_position=position,
            secondary_positions=(),
            overall=attribute,
            attributes=Attributes(**{name: attribute for name in self.config.attribute_names}),
        )
