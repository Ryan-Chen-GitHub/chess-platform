# Pydantic models describe the exact JSON shape each endpoint returns.
# FastAPI uses them to validate responses and to generate the /docs page.
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