from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from api import list_slots, load_session, save_session
from api.session import GameSession


WORKSPACE = Path(__file__).resolve().parents[2]


class PersistenceTests(unittest.TestCase):
    def test_save_and_load_restore_the_same_round_and_table(self) -> None:
        session = GameSession.create(WORKSPACE / "config", WORKSPACE / "data", seed=7)
        session.advance_round()
        expected_table = session.standings(16)
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "slot-1.json.gz"
            save_session(session, path)
            restored = load_session(WORKSPACE / "config", WORKSPACE / "data", path)
            slots = list_slots(Path(temporary))

        self.assertEqual(restored.current_round, 1)
        self.assertEqual(restored.world_state(), session.world_state())
        self.assertEqual(restored.standings(16), expected_table)
        self.assertEqual(slots, ("slot-1",))
