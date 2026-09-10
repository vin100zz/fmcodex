from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from api.session import GameSession


class AdvanceRequest(BaseModel):
    jusqu_a: str


def create_app(workspace: Path, seed: int = 20260910) -> FastAPI:
    """Create the HTTP facade; simulation state remains owned by one session."""
    session = GameSession.create(workspace / "config", workspace / "data", seed)
    app = FastAPI(title="Football Manager Light", version="0.1.0")

    @app.get("/api/monde/etat")
    def world_state() -> dict[str, object]:
        return session.world_state()

    @app.post("/api/monde/avancer")
    def advance(request: AdvanceRequest) -> dict[str, object]:
        if request.jusqu_a != "journee":
            raise HTTPException(status_code=422, detail="Only 'journee' is available in v1")
        try:
            session.advance_round(seed)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return session.world_state()

    @app.get("/api/competitions")
    def competitions() -> list[dict[str, object]]:
        return session.competition_summaries()

    @app.get("/api/competitions/{competition_id}/classement")
    def standings(competition_id: int) -> list[dict[str, object]]:
        try:
            return session.standings(competition_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Competition not found") from error

    @app.get("/api/competitions/{competition_id}/calendrier")
    def calendar(competition_id: int, journee: int | None = None) -> list[dict[str, object]]:
        try:
            return session.competition_calendar(competition_id, journee)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Competition not found") from error

    @app.get("/api/clubs/{club_id}/effectif")
    def roster(club_id: int) -> list[dict[str, object]]:
        try:
            return session.club_roster(club_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Active club not found") from error

    return app
