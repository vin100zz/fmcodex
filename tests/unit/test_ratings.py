from pathlib import Path
import unittest

from core.config import load_config
from core.world import derive_active_club_ratings, import_source_data


WORKSPACE = Path(__file__).resolve().parents[2]


class RatingsTests(unittest.TestCase):
    def test_derives_one_bounded_rating_per_active_club(self) -> None:
        config = load_config(WORKSPACE / "config")
        imported = import_source_data(WORKSPACE / "data", config)
        ratings = derive_active_club_ratings(imported, config)

        self.assertEqual(len(ratings), 96)
        self.assertTrue(
            all(config.attribute_bounds.min <= item.rating <= config.attribute_bounds.max for item in ratings.values())
        )
