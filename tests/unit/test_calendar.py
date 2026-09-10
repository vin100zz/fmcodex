from random import Random
import unittest

from core.world import GameDate, generate_double_round_robin


class CalendarTests(unittest.TestCase):
    def test_generates_a_complete_double_round_robin(self) -> None:
        clubs = tuple(range(1, 21))
        fixtures = generate_double_round_robin(
            clubs,
            competition_id=1,
            first_fixture_id=1,
            start_date=GameDate(2026, 8, 10),
            days_between_rounds=7,
            rng=Random(7),
        )

        self.assertEqual(len(fixtures), 380)
        self.assertEqual({fixture.round_number for fixture in fixtures}, set(range(1, 39)))
        pairs = {(fixture.home_club_id, fixture.away_club_id) for fixture in fixtures}
        self.assertEqual(len(pairs), 380)
        self.assertTrue(all(sum(fixture.home_club_id == club or fixture.away_club_id == club for fixture in fixtures) == 38 for club in clubs))

    def test_game_date_handles_a_leap_day(self) -> None:
        self.assertEqual(GameDate(2028, 2, 28).add_days(1), GameDate(2028, 2, 29))
        self.assertEqual(GameDate(2027, 2, 28).add_days(1), GameDate(2027, 3, 1))
        self.assertEqual(GameDate(2026, 8, 10).days_until(GameDate(2026, 8, 17)), 7)
