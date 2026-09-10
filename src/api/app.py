from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from api.persistence import list_slots, load_session, save_session
from api.session import GameSession


class AdvanceRequest(BaseModel):
    jusqu_a: str


class SlotRequest(BaseModel):
    slot: str


def create_app(workspace: Path, seed: int = 20260910) -> FastAPI:
    """Create the HTTP facade; simulation state remains owned by one session."""
    session = GameSession.create(workspace / "config", workspace / "data", seed)
    saves_directory = workspace / "saves"
    app = FastAPI(title="Football Manager Light", version="0.1.0")

    @app.get("/api/monde/etat")
    def world_state() -> dict[str, object]:
        return session.world_state()

    @app.post("/api/monde/avancer")
    def advance(request: AdvanceRequest) -> dict[str, object]:
        try:
            if request.jusqu_a == "jour":
                session.advance_day()
            elif request.jusqu_a == "journee":
                session.advance_round()
            elif request.jusqu_a == "fin_saison":
                session.complete_current_season()
            else:
                raise HTTPException(status_code=422, detail="Use 'jour', 'journee' or 'fin_saison'")
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return session.world_state()

    @app.get("/api/competitions")
    def competitions() -> list[dict[str, object]]:
        return session.competition_summaries()

    @app.get("/api/clubs")
    def clubs(competition: int | None = None, recherche: str | None = None) -> list[dict[str, object]]:
        return session.clubs(competition_id=competition, search=recherche)

    @app.get("/api/clubs/{club_id}")
    def club(club_id: int) -> dict[str, object]:
        try:
            return session.club_summary(club_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Club not found") from error

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

    @app.get("/api/competitions/{competition_id}/statistiques")
    def competition_statistics(competition_id: int, type: str = "buteurs") -> list[dict[str, object]]:
        try:
            return session.competition_statistics(competition_id, type)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Competition not found") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/clubs/{club_id}/effectif")
    def roster(club_id: int) -> list[dict[str, object]]:
        try:
            return session.club_roster(club_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Active club not found") from error

    @app.get("/api/joueurs/{player_id}")
    def player(player_id: int) -> dict[str, object]:
        try:
            return session.player_detail(player_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Active player not found") from error

    @app.get("/api/joueurs")
    def players(
        poste: str | None = None, club: int | None = None, niveau_min: int | None = None
    ) -> list[dict[str, object]]:
        return session.players(position=poste, club_id=club, minimum_overall=niveau_min)

    @app.get("/api/clubs/{club_id}/calendrier")
    def club_calendar(club_id: int) -> list[dict[str, object]]:
        try:
            return session.club_calendar(club_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Active club not found") from error

    @app.get("/api/matches/{fixture_id}")
    def match(fixture_id: int) -> dict[str, object]:
        try:
            return session.match_detail(fixture_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Match not played") from error

    @app.post("/api/partie/sauvegarder")
    def save(request: SlotRequest) -> dict[str, str]:
        path = _slot_path(saves_directory, request.slot)
        save_session(session, path)
        return {"slot": request.slot}

    @app.post("/api/partie/charger")
    def load(request: SlotRequest) -> dict[str, object]:
        nonlocal session
        path = _slot_path(saves_directory, request.slot)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Save slot not found")
        try:
            session = load_session(workspace / "config", workspace / "data", path)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return session.world_state()

    @app.get("/api/partie/slots")
    def slots() -> list[str]:
        return list(list_slots(saves_directory))

    return app


def _slot_path(directory: Path, slot: str) -> Path:
    if not slot or slot != Path(slot).name or any(character in slot for character in "\\/"):
        raise HTTPException(status_code=422, detail="Invalid save slot")
    return directory / f"{slot}.json.gz"
