from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from api import create_app


WORKSPACE = Path(__file__).resolve().parents[2]


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(create_app(WORKSPACE, seed=7))

    def test_http_api_exposes_world_catalog_and_match_data(self) -> None:
        state = self.client.get("/api/monde/etat")
        clubs = self.client.get("/api/clubs", params={"competition": 16})
        advance = self.client.post("/api/monde/avancer", json={"jusqu_a": "journee"})
        calendar = self.client.get("/api/competitions/16/calendrier", params={"journee": 1})
        match = self.client.get(f"/api/matches/{calendar.json()[0]['id']}")
        players = self.client.get("/api/joueurs", params={"poste": "BU", "niveau_min": 50})

        self.assertEqual(state.status_code, 200)
        self.assertEqual(len(clubs.json()), 18)
        self.assertEqual(advance.json()["current_round"], 1)
        self.assertEqual(match.status_code, 200)
        self.assertIn("events", match.json())
        self.assertTrue(players.json())
