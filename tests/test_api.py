from datetime import datetime

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
from app.models import Game, Move, Player


def utc_naive(year: int, month: int, day: int) -> datetime:
    """A naive datetime meant as UTC, matching how game times are stored."""
    return datetime(year, month, day) # noqa: DTZ001

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
                Game(
                    lichess_id="g1", white=alice, black=bob, result="1-0",
                    eco="C20", opening="King's Pawn Game",
                    moves=[Move(ply=1, san="e4", uci="e2e4"),
                           Move(ply=2, san="e5", uci="e7e5")],
                    played_at=utc_naive(2024, 1, 1),
                ),
                Game(
                    lichess_id="g2", white=bob, black=alice, result="1-0",
                    eco="C20", opening="King's Pawn Game",
                    played_at=utc_naive(2024, 1, 2),
                ),
                Game(
                    lichess_id="g3", white=alice, black=bob, result="1/2-1/2",
                    eco="B01", opening="Scandinavian Defense",
                    played_at=utc_naive(2024, 1, 3),
                ),
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

# Testing if the game endpoint returns players and moves in order
def test_game_detail(client):
    response = client.get("/games/g1")
    # Checked first, so a failure shows the status and error body.
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["white"] == "alice"
    assert [m["san"] for m in data["moves"]] == ["e4","e5"]

# Testing if 404 error is checked as expected
def test_unknown_game_is_404(client):
    assert client.get("/games/nope").status_code == 404

# Testing that a player's game come back newest first, from their point of view
def test_player_games_newest_first(client):
    data = client.get("/players/alice/games").json()
    assert [g["lichess_id"] for g in data] == ["g3", "g2", "g1"]
    # g3 was a draw, g2 was won by bob (White), and g1 was won by alice (White).
    assert [g["outcome"] for g in data] == ["draw", "loss", "win"]
    # In g2 alice had Black, so her opponent was bob, the White palyer.
    assert data[1]["player_color"] == "black"
    assert data[1]["opponent"] == "bob"

# Testing that the limit parameter caps the number of games returned
def test_player_games_respects_limit(client):
    data = client.get("/players/alice/games?limit=1").json()
    assert [g["lichess_id"] for g in data] == ["g3"]

# Testing that an unknown player gives a 404 with the expected message
def test_player_games_unknown_player_is_404(client):
    response = client.get("/players/nobody/games")
    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown player nobody"