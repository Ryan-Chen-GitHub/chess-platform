# Pydantic models describe the exact JSON shape each endpoint returns.
# FastAPI uses them to validate responses and to generate the /docs page.
from datetime import datetime

from pydantic import BaseModel


class OpeningCount(BaseModel):
    """One row of the "most played openings" list."""

    opening: str
    games: int


class OpeningStats(BaseModel):
    """Results breakdown for one ECO opening code."""

    eco: str
    games: int
    white_wins: int
    black_wins: int
    draws: int
    # Fraction of games White won, from 0.0 to 1.0.
    white_win_rate: float


class PlayerRecord(BaseModel):
    """A player's overall record and most played openings."""

    username: str
    games: int
    wins: int
    losses: int
    draws: int
    top_openings: list[OpeningCount]


class MoveOut(BaseModel):
    """One half-move of a game."""

    ply: int
    san: str
    uci: str


class GameDetail(BaseModel):
    """A single game with its full move list, for replaying on a board."""

    lichess_id: str
    white: str
    black: str
    white_elo: int | None
    black_elo: int | None
    result: str
    eco: str | None
    opening: str | None
    played_at: datetime | None
    moves: list[MoveOut]