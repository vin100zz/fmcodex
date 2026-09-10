from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from core.config.models import GameConfig
from core.domain.entities import ClubSeed, ClubStatus, PlayerSeed, SimulationStatus


class ImportErrorReport(ValueError):
    """Raised when source data cannot be imported safely."""


@dataclass(frozen=True, slots=True)
class ImportReport:
    clubs: tuple[ClubSeed, ...]
    players: tuple[PlayerSeed, ...]
    active_club_count: int
    active_player_count: int
    reduced_player_count: int
    unknown_position_count: int


POSITION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("GK", "GB"),
    ("D/WB L", "DL"),
    ("D/WB R", "DR"),
    ("WB L", "DL"),
    ("WB R", "DR"),
    ("D L", "DL"),
    ("D R", "DR"),
    ("D C", "DC"),
    ("DM", "MDC"),
    ("M C", "MC"),
    ("M L", "AILG"),
    ("M R", "AILD"),
    ("AM L", "AILG"),
    ("AM R", "AILD"),
    ("AM/F C", "MOC"),
    ("F C", "BU"),
    ("AM C", "MOC"),
    ("ST", "BU"),
)


def import_source_data(data_directory: Path, config: GameConfig) -> ImportReport:
    """Import cp1252 source CSVs and apply the configured active-roster selection."""
    club_rows = _read_csv(data_directory / "clubs.csv")
    player_rows = _read_csv(data_directory / "players.csv")
    clubs = _build_clubs(club_rows, config)
    club_ids = {club.id for club in clubs}
    selected_player_ids = _select_active_player_ids(player_rows, clubs, config)
    players, unknown_position_count = _build_players(player_rows, club_ids, selected_player_ids)
    active_club_count = sum(club.status is ClubStatus.ACTIVE for club in clubs)
    active_player_count = sum(player.simulation_status is SimulationStatus.ACTIVE for player in players)
    return ImportReport(
        clubs=tuple(clubs),
        players=tuple(players),
        active_club_count=active_club_count,
        active_player_count=active_player_count,
        reduced_player_count=len(players) - active_player_count,
        unknown_position_count=unknown_position_count,
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="cp1252", newline="") as file:
            return list(csv.DictReader(file, delimiter=";"))
    except OSError as error:
        raise ImportErrorReport(f"Cannot read source file {path}: {error}") from error


def _build_clubs(rows: list[dict[str, str]], config: GameConfig) -> list[ClubSeed]:
    active_division_ids = {competition.division_id for competition in config.world.competitions_simulees}
    clubs: list[ClubSeed] = []
    seen_ids: set[int] = set()
    for row in rows:
        club_id = _required_int(row, "Unique ID", "clubs.csv")
        if club_id in seen_ids:
            raise ImportErrorReport(f"Duplicate club ID: {club_id}")
        seen_ids.add(club_id)
        division_id = _optional_int(row["Division ID"])
        clubs.append(
            ClubSeed(
                id=club_id,
                name=_required_text(row, "Name", "clubs.csv"),
                nation_source=_required_text(row, "Nation", "clubs.csv"),
                division_id=division_id,
                stadium_capacity=_optional_int(row["Stad Cap"]),
                status=ClubStatus.ACTIVE if division_id in active_division_ids else ClubStatus.DORMANT,
            )
        )
    active_counts = Counter(club.division_id for club in clubs if club.status is ClubStatus.ACTIVE)
    for competition in config.world.competitions_simulees:
        if active_counts[competition.division_id] != competition.nb_clubs:
            raise ImportErrorReport(
                f"Division {competition.division_id} has {active_counts[competition.division_id]} clubs; "
                f"expected {competition.nb_clubs}"
            )
    return clubs


def _select_active_player_ids(
    rows: list[dict[str, str]], clubs: list[ClubSeed], config: GameConfig
) -> set[int]:
    active_club_ids = {club.id for club in clubs if club.status is ClubStatus.ACTIVE}
    by_club: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        club_id = _optional_int(row["Club ID"])
        if club_id in active_club_ids:
            by_club[club_id].append(row)
    limit = config.world.importation.effectif_actif.joueurs_max_par_club
    selected: set[int] = set()
    for club_id in active_club_ids:
        ranked = sorted(
            by_club[club_id],
            key=lambda row: (-_source_money(row["Value"]), -_source_money(row["Wage"]), _required_int(row, "Unique ID", "players.csv")),
        )
        if len(ranked) < limit:
            raise ImportErrorReport(f"Active club {club_id} has fewer than {limit} players")
        selected.update(_required_int(row, "Unique ID", "players.csv") for row in ranked[:limit])
    return selected


def _build_players(
    rows: list[dict[str, str]], club_ids: set[int], selected_player_ids: set[int]
) -> tuple[list[PlayerSeed], int]:
    players: list[PlayerSeed] = []
    seen_ids: set[int] = set()
    unknown_position_count = 0
    for row in rows:
        player_id = _required_int(row, "Unique ID", "players.csv")
        if player_id in seen_ids:
            raise ImportErrorReport(f"Duplicate player ID: {player_id}")
        seen_ids.add(player_id)
        club_id = _optional_int(row["Club ID"])
        if club_id is not None and club_id not in club_ids:
            raise ImportErrorReport(f"Player {player_id} references unknown club {club_id}")
        primary, secondary = _positions_from_source(row["Position"])
        if primary is None:
            unknown_position_count += 1
            primary, secondary = "MC", ()
        players.append(
            PlayerSeed(
                id=player_id,
                name=_required_text(row, "Name", "players.csv"),
                nationality_source=_required_text(row, "Nation", "players.csv"),
                primary_position=primary,
                secondary_positions=secondary,
                club_id=club_id,
                wage=_source_money(row["Wage"]),
                market_value=_source_money(row["Value"]),
                simulation_status=(SimulationStatus.ACTIVE if player_id in selected_player_ids else SimulationStatus.REDUCED),
            )
        )
    return players, unknown_position_count


def _positions_from_source(source: str) -> tuple[str | None, tuple[str, ...]]:
    normalized = source.replace("/", "/").strip()
    found: list[str] = []
    for pattern, position in POSITION_PATTERNS:
        if pattern in normalized and position not in found:
            found.append(position)
    if not found:
        return None, ()
    return found[0], tuple(found[1:])


def _required_text(row: dict[str, str], key: str, source: str) -> str:
    value = row.get(key, "").strip()
    if not value:
        raise ImportErrorReport(f"Missing {key} in {source}")
    return value


def _required_int(row: dict[str, str], key: str, source: str) -> int:
    value = _optional_int(row.get(key, ""))
    if value is None:
        raise ImportErrorReport(f"Missing {key} in {source}")
    return value


def _optional_int(value: str | None) -> int | None:
    if value is None or value.strip() in {"", "-1"}:
        return None
    try:
        return int(value)
    except ValueError as error:
        raise ImportErrorReport(f"Expected an integer value, got {value!r}") from error


def _source_money(value: str) -> int:
    parsed = _optional_int(value)
    return 0 if parsed is None else max(0, parsed)
