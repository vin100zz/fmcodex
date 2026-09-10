from pathlib import Path
import unittest

from core.config import load_config


WORKSPACE = Path(__file__).resolve().parents[2]


class ConfigTests(unittest.TestCase):
    def test_loads_the_project_configuration(self) -> None:
        config = load_config(WORKSPACE / "config")

        self.assertEqual(config.world.version_config, 2)
        self.assertEqual(config.world.date_depart.annee, 2026)
        self.assertEqual(config.world.importation.effectif_actif.joueurs_max_par_club, 30)
        self.assertEqual(len(config.world.competitions_simulees), 5)
        self.assertEqual(sum(item.nb_clubs for item in config.world.competitions_simulees), 96)
        self.assertEqual(len(config.attribute_names), 13)
