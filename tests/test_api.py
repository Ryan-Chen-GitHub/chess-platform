import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# StaticPool makes every connection share one in-memory database. Without it,
# each new connection would get its own empty database.
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.deps import get_session
from app.main import app
from app.models import Game, Player


@pytest.fixture
def client():
    """A test client backed by a small in-memory database."""
    engine = create_engine(
        "sqlite://",
        # The test client runs requests in another thread, which SQLite
        # forbids by default.
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    # Seed three games between alice and bob:
    #   1. alice (White) beats bob, King's Pawn Game (C20)
    #   2. bob (White) beats alice, King's Pawn Game (C20)
    #   3. alice and bob draw, Scandinavian Defense (B01)
    with Session(engine) as session:
        alice, bob = Player(username="alice"), Player(username="bob")
        session.add_all(
            [
                Game(lichess_id="g1", white=alice, black=bob, result="1-0",
                     eco="C20", opening="King's Pawn Game"),
                Game(lichess_id="g2", white=bob, black=alice, result="1-0",
                     eco="C20", opening="King's Pawn Game"),
                Game(lichess_id="g3", white=alice, black=bob, result="1/2-1/2",
                     eco="B01", opening="Scandinavian Defense"),
            ]
        )
        session.commit()

    # Replace the real database session with one bound to the test database.
    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    yield TestClient(app)
    # Undo the override so we don't affect other tests.
    app.dependency_overrides.clear()

# Testing if games are counted correctly
def test_most_played_openings(client):
    response = client.get("/openings")
    assert response.status_code == 200
    assert response.json() == [
        {"opening": "King's Pawn Game", "games": 2},
        {"opening": "Scandinavian Defense", "games": 1},
    ]

# Testing if results output as expected
def test_opening_stats(client):
    response = client.get("/openings/c20/stats")  # lowercase works too
    assert response.status_code == 200
    assert response.json() == {
        "eco": "C20",
        "games": 2,
        "white_wins": 2,
        "black_wins": 0,
        "draws": 0,
        "white_win_rate": 1.0,
    }

# Testing if opening errors work as expected
def test_opening_stats_unknown_code_is_404(client):
    assert client.get("/openings/Z99/stats").status_code == 404

# Testing if player match history is checked properly
def test_player_record(client):
    data = client.get("/players/alice").json()
    # alice won game 1, lost game 2, and drew game 3.
    assert (data["games"], data["wins"], data["losses"], data["draws"]) == (3, 1, 1, 1)
    assert data["top_openings"][0] == {"opening": "King's Pawn Game", "games": 2}

# Testing if player errors work as expected
def test_unknown_player_is_404(client):
    assert client.get("/players/nobody").status_code == 404