from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True, slots=True, order=True)
class GameDate:
    year: int
    month: int
    day: int

    def add_days(self, days: int) -> GameDate:
        if days < 0:
            raise ValueError("GameDate only supports forward scheduling")
        year, month, day = self.year, self.month, self.day
        for _ in range(days):
            day += 1
            if day > _days_in_month(year, month):
                day = 1
                month += 1
                if month > 12:
                    month = 1
                    year += 1
        return GameDate(year=year, month=month, day=day)

    def days_until(self, other: GameDate) -> int:
        if other < self:
            raise ValueError("GameDate only supports forward elapsed-time calculations")
        current = self
        elapsed = 0
        while current < other:
            current = current.add_days(1)
            elapsed += 1
        return elapsed


@dataclass(frozen=True, slots=True)
class Fixture:
    id: int
    competition_id: int
    round_number: int
    date: GameDate
    home_club_id: int
    away_club_id: int


def generate_double_round_robin(
    club_ids: tuple[int, ...],
    competition_id: int,
    first_fixture_id: int,
    start_date: GameDate,
    days_between_rounds: int,
    rng: Random,
) -> tuple[Fixture, ...]:
    """Generate a reproducible home-and-away schedule for an even-sized league."""
    if len(club_ids) < 2 or len(club_ids) % 2:
        raise ValueError("A round-robin competition requires an even number of at least two clubs")
    if len(set(club_ids)) != len(club_ids):
        raise ValueError("Competition club IDs must be unique")
    ordered = list(club_ids)
    rng.shuffle(ordered)
    first_leg = _round_pairs(ordered)
    fixtures: list[Fixture] = []
    fixture_id = first_fixture_id
    total_rounds = len(first_leg) * 2
    for round_index in range(total_rounds):
        date = start_date.add_days(round_index * days_between_rounds)
        pairings = first_leg[round_index] if round_index < len(first_leg) else first_leg[round_index - len(first_leg)]
        reverse = round_index >= len(first_leg)
        for home_id, away_id in pairings:
            fixtures.append(
                Fixture(
                    id=fixture_id,
                    competition_id=competition_id,
                    round_number=round_index + 1,
                    date=date,
                    home_club_id=away_id if reverse else home_id,
                    away_club_id=home_id if reverse else away_id,
                )
            )
            fixture_id += 1
    return tuple(fixtures)


def _round_pairs(club_ids: list[int]) -> tuple[tuple[tuple[int, int], ...], ...]:
    rotating = list(club_ids)
    rounds: list[tuple[tuple[int, int], ...]] = []
    for round_index in range(len(rotating) - 1):
        pairs: list[tuple[int, int]] = []
        midpoint = len(rotating) // 2
        for index in range(midpoint):
            first = rotating[index]
            second = rotating[-(index + 1)]
            pairs.append((second, first) if (round_index + index) % 2 else (first, second))
        rounds.append(tuple(pairs))
        rotating = [rotating[0], rotating[-1], *rotating[1:-1]]
    return tuple(rounds)


def _days_in_month(year: int, month: int) -> int:
    if month == 2:
        return 29 if _is_leap_year(year) else 28
    if month in {4, 6, 9, 11}:
        return 30
    return 31


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
