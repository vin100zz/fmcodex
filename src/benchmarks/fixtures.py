from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from core.world.ratings import ClubRating


class FixtureError(ValueError):
    """Raised when a benchmark fixture cannot be read or validated."""


@dataclass(frozen=True, slots=True)
class RatingFixture:
    source_sha256: str
    config_version: int
    ratings: tuple[ClubRating, ...]

    def by_club_id(self) -> dict[int, ClubRating]:
        return {rating.club_id: rating for rating in self.ratings}


def build_fixture(
    ratings: dict[int, ClubRating], source_data_path: Path, config_version: int
) -> RatingFixture:
    return RatingFixture(
        source_sha256=_sha256(source_data_path),
        config_version=config_version,
        ratings=tuple(sorted(ratings.values(), key=lambda item: item.club_id)),
    )


def save_fixture(fixture: RatingFixture, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_sha256": fixture.source_sha256,
        "config_version": fixture.config_version,
        "ratings": [asdict(rating) for rating in fixture.ratings],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_fixture(path: Path) -> RatingFixture:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        ratings = tuple(ClubRating(**item) for item in payload["ratings"])
        fixture = RatingFixture(
            source_sha256=str(payload["source_sha256"]),
            config_version=int(payload["config_version"]),
            ratings=ratings,
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise FixtureError(f"Cannot read fixture {path}: {error}") from error
    if not fixture.ratings or len(fixture.by_club_id()) != len(fixture.ratings):
        raise FixtureError(f"Fixture {path} contains invalid club ratings")
    return fixture


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
