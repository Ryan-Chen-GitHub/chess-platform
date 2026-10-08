# io.StringIO lets us treat a string as if it were a PGN file, because
# load_pgn expects a file-like object.
import io

# func.count() lets us ask the database "how many rows are in this table?"
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db import Base
from app.ingest.loader import load_pgn
from app.models import Game, Move, Player

# Two games written the way Lichess writes them. The first is a normal game
# (Scholar's mate); the second is an Antichess game, which should be skipped
# because our schema only models standard chess.
SAMPLE_PGN = """
[Event "Rated Blitz game"]
[Site "https://lichess.org/abcd1234"]
[Date "2024.01.15"]
[UTCDate "2024.01.15"]
[UTCTime "18:30:00"]
[White "alice"]
[Black "bob"]
[Result "1-0"]
[WhiteElo "1500"]
[BlackElo "?"]
[TimeControl "300+3"]
[Termination "Normal"]
[ECO "C20"]
[Opening "King's Pawn Game"]
[Variant "Standard"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0

[Event "Rated Antichess game"]
[Site "https://lichess.org/zzzz9999"]
[White "carol"]
[Black "dave"]
[Result "*"]
[Variant "Antichess"]

1. e3 e6 *
"""


def make_session() -> Session:
    # A fresh in-memory database for each test, so tests never touch the
    # real chess.db file and always start from an empty state.
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_load_pgn_imports_game_and_skips_variant():
    with make_session() as session:
        stats = load_pgn(io.StringIO(SAMPLE_PGN), session)

        # One game imported, the variant game skipped.
        assert stats == {"imported": 1, "duplicates": 0, "skipped": 1}

        # .one() fails the test if there isn't exactly one row.
        game = session.scalars(select(Game)).one()
        assert game.lichess_id == "abcd1234"
        assert game.white_elo == 1500
        assert game.black_elo is None   # the "?" rating became NULL
        assert game.opening == "King's Pawn Game"

        # Scholar's mate has 7 half-moves, and both players were created.
        assert session.scalar(select(func.count()).select_from(Move)) == 7
        assert session.scalar(select(func.count()).select_from(Player)) == 2


def test_loading_twice_does_not_create_duplicates():
    with make_session() as session:
        load_pgn(io.StringIO(SAMPLE_PGN), session)
        # Loading the same data a second time should add nothing. This is
        # the "idempotent import" property: safe to re-run.
        stats = load_pgn(io.StringIO(SAMPLE_PGN), session)

        assert stats["imported"] == 0
        assert stats["duplicates"] == 1
        assert session.scalar(select(func.count()).select_from(Game)) == 1