from pathlib import Path
from random import Random
import unittest

from core.config import load_config
from core.engine import Attributes
from core.world import (
    CareerPlayer,
    NameEntry,
    NationNamePool,
    estimate_potential,
    generate_regen,
    load_nation_name_pool,
    progress_player_month,
)


WORKSPACE = Path(__file__).resolve().parents[2]


class DemographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(WORKSPACE / "config")

    def test_young_player_progresses_with_minutes(self) -> None:
        player = self._player(age=18, overall=50, potential=90, attribute=50)

        progressed = progress_player_month(player, minutes_played=400, config=self.config, rng=Random(7))

        self.assertGreater(progressed.overall, player.overall)

    def test_potential_estimates_converge_with_age(self) -> None:
        young = estimate_potential(self._player(16, 50, 80, 50), observer_reputation=None, config=self.config)
        mature = estimate_potential(self._player(23, 50, 80, 50), observer_reputation=None, config=self.config)

        self.assertGreater(young.maximum - young.minimum, mature.maximum - mature.minimum)
        self.assertEqual(mature.minimum, mature.maximum)

    def test_regen_has_unique_identity_and_configured_bounds(self) -> None:
        pool = NationNamePool(
            first_names=(NameEntry("Alex", 1), NameEntry("Sam", 1)),
            last_names=(NameEntry("Martin", 1), NameEntry("Durand", 1)),
        )

        regen = generate_regen(900_001, "FRA", pool, frozenset({"Alex Martin"}), self.config, Random(7))

        generation = self.config.demographics.regen_generation
        self.assertNotEqual(regen.full_name, "Alex Martin")
        self.assertTrue(generation.age_min <= regen.age <= generation.age_max)
        self.assertTrue(generation.potentiel_min <= regen.potential <= generation.potentiel_min + generation.potentiel_amplitude)
        self.assertIn(regen.position, self.config.positions)

    def test_loads_generated_name_pools_from_project_data(self) -> None:
        pool = load_nation_name_pool(WORKSPACE / "data" / "regens", "FRA")

        self.assertTrue(pool.first_names)
        self.assertTrue(pool.last_names)

    def _player(self, age: int, overall: float, potential: float, attribute: int) -> CareerPlayer:
        return CareerPlayer(
            player_id=1,
            full_name="Test Player",
            nation_code="FRA",
            position="MC",
            age=age,
            overall=overall,
            potential=potential,
            attributes=Attributes(**{name: attribute for name in self.config.attribute_names}),
        )
