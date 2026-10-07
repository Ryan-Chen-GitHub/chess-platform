from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Game, Move, Player

def test_game_with_moves_round_trip():
    # An in-memory database exists only for this test, so tests never touch
    # the real chess.db file and always start clean
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Builds a game with two palyers & two moves.
        # Due to relationship(), we can assign objects instead of IDs.
        game = Game(
            lichess_id="abc12345",
            white=Player(username="alice"),
            black=Player(username="bob"),
            result="1-0",
            white_elo=1500,
            black_elo=1480,
            moves=[
                Move(ply=1, san="e4", uci="e2e4"),
                Move(ply=2, san="e5", uci="e7e5"),
            ],
        )
        session.add(game)
        session.commit()

        # Read everything back + verify everything was saved & linked.
        saved = session.query(Game).one()
        assert saved.white.username == "alice"
        assert [m.san for m in saved.moves] == ["e4", "e5"]