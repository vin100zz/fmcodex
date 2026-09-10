from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.config.models import SeasonConfig


@dataclass(frozen=True, slots=True)
class PlayedMatch:
    home_club_id: int
    away_club_id: int
    home_goals: int
    away_goals: int


@dataclass(frozen=True, slots=True)
class StandingRow:
    club_id: int
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    points: int

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


def calculate_standings(
    club_ids: Iterable[int], matches: Iterable[PlayedMatch], rules: SeasonConfig
) -> tuple[StandingRow, ...]:
    """Calculate a league table without mutating world state."""
    rows = {club_id: _MutableStanding(club_id) for club_id in club_ids}
    for match in matches:
        home = _row(rows, match.home_club_id)
        away = _row(rows, match.away_club_id)
        home.played += 1
        away.played += 1
        home.goals_for += match.home_goals
        home.goals_against += match.away_goals
        away.goals_for += match.away_goals
        away.goals_against += match.home_goals
        if match.home_goals > match.away_goals:
            home.wins += 1
            away.losses += 1
            home.points += rules.points_victoire
            away.points += rules.points_defaite
        elif match.home_goals < match.away_goals:
            away.wins += 1
            home.losses += 1
            away.points += rules.points_victoire
            home.points += rules.points_defaite
        else:
            home.draws += 1
            away.draws += 1
            home.points += rules.points_nul
            away.points += rules.points_nul
    frozen = tuple(row.freeze() for row in rows.values())
    return tuple(sorted(frozen, key=lambda row: (-row.points, -row.goal_difference, -row.goals_for, row.club_id)))


@dataclass(slots=True)
class _MutableStanding:
    club_id: int
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    def freeze(self) -> StandingRow:
        return StandingRow(
            club_id=self.club_id,
            played=self.played,
            wins=self.wins,
            draws=self.draws,
            losses=self.losses,
            goals_for=self.goals_for,
            goals_against=self.goals_against,
            points=self.points,
        )


def _row(rows: dict[int, _MutableStanding], club_id: int) -> _MutableStanding:
    try:
        return rows[club_id]
    except KeyError as error:
        raise ValueError(f"Match references club {club_id} outside this competition") from error
