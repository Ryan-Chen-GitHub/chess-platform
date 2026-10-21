# APIRouter groups related endpoints so main.py can plug them in together.
# Depends is how an endpoint asks FastAPI for a dependency (our session).
# HTTPException lets us return proper error codes like 404.
# Query declares and validates URL query parameters.
from fastapi import APIRouter, Depends, HTTPException, Query

# case builds SQL CASE expressions ("count this row only if..."), func gives
# access to SQL functions like COUNT and SUM, or_ combines conditions.
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_session
from app.models import Game, Move, Player
from app.schemas import (
    GameDetail,
    GameSummary,
    MoveOut,
    OpeningCount,
    OpeningStats,
    PlayerRecord,
)

router = APIRouter()


def _top_openings(session: Session, limit: int, *conditions) -> list[OpeningCount]:
    """Most played openings, optionally limited to rows matching conditions."""
    # Naming the count lets us sort by it below.
    games = func.count().label("games")
    query = (
        select(Game.opening, games)
        # Games with no recorded opening would show up as a None entry.
        .where(Game.opening.is_not(None), *conditions)
        .group_by(Game.opening)
        # Sorting by name second makes the order stable when counts tie.
        .order_by(games.desc(), Game.opening)
        .limit(limit)
    )
    return [OpeningCount(opening=o, games=g) for o, g in session.execute(query)]


@router.get("/openings", response_model=list[OpeningCount])
def most_played_openings(
    # ge/le restrict the value to 1-100, so nobody can ask for a million rows.
    limit: int = Query(10, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """The most played openings across all stored games."""
    return _top_openings(session, limit)


@router.get("/openings/{eco}/stats", response_model=OpeningStats)
def opening_stats(eco: str, session: Session = Depends(get_session)):
    """How games with a given ECO code (like "C20") ended."""
    eco = eco.upper()

    # One query returns each result with its count, like ("1-0", 12).
    rows = session.execute(
        select(Game.result, func.count()).where(Game.eco == eco).group_by(Game.result)
    )
    counts = dict(rows.all())
    total = sum(counts.values())

    # No games with this code means the opening isn't in our data: 404.
    if total == 0:
        raise HTTPException(status_code=404, detail=f"No games found for ECO {eco}")

    white_wins = counts.get("1-0", 0)
    return OpeningStats(
        eco=eco,
        games=total,
        white_wins=white_wins,
        black_wins=counts.get("0-1", 0),
        draws=counts.get("1/2-1/2", 0),
        white_win_rate=round(white_wins / total, 3),
    )


@router.get("/players/{username}", response_model=PlayerRecord)
def player_record(username: str, session: Session = Depends(get_session)):
    """A player's record and favorite openings. Usernames are case-sensitive."""
    player = session.scalar(select(Player).where(Player.username == username))
    if player is None:
        raise HTTPException(status_code=404, detail=f"Unknown player {username}")

    # Every game this player took part in, on either side of the board.
    played = or_(Game.white_id == player.id, Game.black_id == player.id)

    # A win is either "White won and they were White" or "Black won and they
    # were Black". Parentheses are required around each part because & and |
    # bind more tightly than == in Python.
    won = ((Game.white_id == player.id) & (Game.result == "1-0")) | (
        (Game.black_id == player.id) & (Game.result == "0-1")
    )
    drawn = Game.result == "1/2-1/2"

    # One query computes everything. SUM(CASE WHEN ... THEN 1 ELSE 0 END) is
    # the standard SQL way to count rows matching a condition.
    total, wins, draws = session.execute(
        select(
            func.count(),
            func.sum(case((won, 1), else_=0)),
            func.sum(case((drawn, 1), else_=0)),
        ).where(played)
    ).one()

    # SUM returns NULL when there are no rows, so fall back to 0.
    wins = wins or 0
    draws = draws or 0

    return PlayerRecord(
        username=player.username,
        games=total,
        wins=wins,
        # Anything that isn't a win or a draw counts as a loss. Unfinished
        # games are not in our data, so this holds for now.
        losses=total - wins - draws,
        draws=draws,
        top_openings=_top_openings(session, 5, played),
    )

def _outcome(game: Game, player_id: int) -> str:
    """Result of a game from one player's point of view."""
    if game.result == "1/2-1/2":
        return "draw"
    # "1-0" kmeans White won and "0-1" means Black won, 
    # So the player's color decides whether that is a win or loss.
    player_is_white = game.white_id == player_id
    if game.result == "1-0":
        return "win" if player_is_white else "loss"
    if game.result == "0-1":
        return "loss" if player_is_white else "win"
    return "unknown"

@router.get("/players/{username}/games", response_model=list[GameSummary])
def player_games(
    username: str,
    # Capped at 100 so one request cannot pull a player's whole history.
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """A player's most recent games, newest first. Usernames are case-sensitive."""
    player = session.scalar(select(Player).where(Player.username == username))
    if player is None:
        raise HTTPException(status_code=404, detail=f"Unknown player {username}")

    # selectinload fetches all the players for these games in one extra query
    # instead of one query per game when .white and .black are read below.
    games = session.scalars(
        select(Game)
        .where(or_(Game.white_id == player.id, Game.black_id == player.id))
        .options(selectinload(Game.white), selectinload(Game.black))
        # Newest first; the id breaks ties so the order is always stable.
        .order_by(Game.played_at.desc(), Game.id.desc())
        .limit(limit)
    )

    summaries = []
    for game in games:
        is_white = game.white_id == player.id
        summaries.append(
            GameSummary(
                lichess_id=game.lichess_id,
                opponent=game.black.username if is_white else game.white.username,
                player_color="white" if is_white else "black",
                outcome=_outcome(game, player.id),
                opening=game.opening,
                played_at=game.played_at,
            )
        )
    return summaries

@router.get("/games/{lichess_id}", response_model=GameDetail)
def game_detail(lichess_id: str, session: Session = Depends(get_session)):
    """One game with its moves in order."""
    # lichess_id has a unique index, so this lookup is a single index read.
    game = session.scalar(select(Game).where(Game.lichess_id == lichess_id))
    if game is None:
        raise HTTPException(status_code=404, detail=f"Unknown game {lichess_id}")

    # Ordering by ply returns the moves in the order they were played.
    moves = session.scalars(
        select(Move).where(Move.game_id == game.id).order_by(Move.ply)
    )
    return GameDetail(
        lichess_id=game.lichess_id,
        white=game.white.username,
        black=game.black.username,
        white_elo=game.white_elo,
        black_elo=game.black_elo,
        result=game.result,
        eco=game.eco,
        opening=game.opening,
        played_at=game.played_at,
        moves=[MoveOut(ply=m.ply, san=m.san, uci=m.uci) for m in moves],
    )