# dataclass gives us a simple "bag of named fields" class without writing
# __init__ by hand.
from dataclasses import dataclass, field
from datetime import datetime

import chess.pgn


@dataclass
class ParsedGame:
    """A game cleaned up and ready to store, independent of the database."""

    lichess_id: str
    white: str
    black: str
    white_elo: int | None
    black_elo: int | None
    result: str
    termination: str | None
    time_control: str | None
    eco: str | None
    opening: str | None
    played_at: datetime | None
    # Each move is a tuple of (ply, san, uci).
    moves: list[tuple[int, str, str]] = field(default_factory=list)


def _parse_elo(value: str | None) -> int | None:
    """Lichess writes "?" for unknown ratings; turn that into None."""
    if value is None or not value.isdigit():
        return None
    return int(value)


def _parse_datetime(headers) -> datetime | None:
    """Combine the UTCDate and UTCTime headers into one datetime."""
    date = headers.get("UTCDate", headers.get("Date", ""))
    time = headers.get("UTCTime", "00:00:00")
    try:
        return datetime.strptime(f"{date} {time}", "%Y.%m.%d %H:%M:%S")
    except ValueError:
        # Malformed or missing dates become NULL instead of crashing the import.
        return None


def parse_game(game: chess.pgn.Game) -> ParsedGame | None:
    """Convert a python-chess Game into a ParsedGame.

    Returns None for games we deliberately don't store (variants, anonymous
    players, missing ID).
    """
    headers = game.headers

    # Our schema models standard chess only. This check comes BEFORE we
    # build a board, because variant rules differ.
    if headers.get("Variant", "Standard") != "Standard":
        return None

    # The Site header looks like "https://lichess.org/q7ZvsdUF"; the game ID
    # is the last part of that URL.
    site = headers.get("Site", "")
    lichess_id = site.rstrip("/").split("/")[-1]
    if not lichess_id or "lichess.org" not in site:
        return None

    # Skip games where either player is unknown or anonymous.
    white = headers.get("White", "?")
    black = headers.get("Black", "?")
    if white in ("?", "Anonymous") or black in ("?", "Anonymous"):
        return None

    # Replay the game to produce each move in both notations. SAN must be
    # computed BEFORE push(), as in the smoke test.
    board = game.board()
    moves = []
    for ply, move in enumerate(game.mainline_moves(), start=1):
        moves.append((ply, board.san(move), move.uci()))
        board.push(move)

    return ParsedGame(
        lichess_id=lichess_id,
        white=white,
        black=black,
        white_elo=_parse_elo(headers.get("WhiteElo")),
        black_elo=_parse_elo(headers.get("BlackElo")),
        result=headers.get("Result", "*"),
        termination=headers.get("Termination"),
        time_control=headers.get("TimeControl"),
        eco=headers.get("ECO"),
        opening=headers.get("Opening"),
        played_at=_parse_datetime(headers),
        moves=moves,
    )