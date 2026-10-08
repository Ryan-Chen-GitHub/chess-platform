# Index allows for the declaration of indexes (duh)
# ForeignKey links tables together
# Mapped & mapped_column allows for declaration of columns
# relationship allows for nevigation between linked rows in Python
from datetime import datetime  # noqa: I001
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class Player(Base):
    """One row per chess player (a Lichess username)."""

    # Name of the table in the database
    __tablename__ = "players"

    # Primary key: unique identifier assigned to each row
    id: Mapped[int] = mapped_column(primary_key=True)

    # unique=True makes all usernames unique
    # index=True makes looking a player up by username fast
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)

class Game(Base):
    """One row per game played."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The game's ID on lichess (ie, "q7ZvsdUF"). Unique, so re-running
    # the import can never create duplicate games.
    lichess_id: Mapped[str] = mapped_column(String(12), unique=True)

    # Foreign keys: each one must match an existing row in players.
    white_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    black_id: Mapped[int] = mapped_column(ForeignKey("players.id"))

    # Ratings at the time of the game.
    # Starts as Nullable b.c some games have no rating
    white_elo: Mapped[int | None]
    black_elo: Mapped[int | None]

    # "1-0" (white won), "0-1" (black won), or "1/2-1/2" (draw)
    result: Mapped[str] = mapped_column(String(7))

    # How the game ended: "Normal", "Time forfeit", "Abandoned", etc.
    termination: Mapped[str | None] = mapped_column(String(30))

    # Time control like "300+3" (5 minutes + 3 seconds per move)
    time_control: Mapped[str | None] = mapped_column(String(15))

    # ECO is the standard opening code (ie, "C20") + a readable name
    eco: Mapped[str | None] = mapped_column(String(3))
    opening: Mapped[str | None] = mapped_column(String(100))

    # When the game was played.
    played_at: Mapped[datetime | None]

    # relationship() allows the writing of game.white.username in python instead
    # of writing a join manually. foreign_keys is needed because two columns
    # point at the same table, so SQLAlchemy must be told which is which.
    white: Mapped[Player] = relationship(foreign_keys=[white_id])
    black: Mapped[Player] = relationship(foreign_keys=[black_id])

    # Cascade deletes a game's moves when the game does
    moves: Mapped[list["Move"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )

    # Indexes makes reading faster, but writing a little slower, so only a little 
    __table_args__ = (
        Index("ix_games_eco", "eco"),
        Index("ix_games_played_at", "played_at"),
        Index("ix_games_white_id", "white_id"),
        Index("ix_games_black_id", "black_id"),
    )

class Move(Base):
    """One row per half-move (a single move by White or Black)."""

    __tablename__ = "moves"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))

    # "ply" counts half-moves: 1 = White's 1st move, 2 = Black's response
    ply: Mapped[int]

    # SAN is the human-readable move format (ie, "Nf3")
    # UCI is the machine's format (ie, "g1f3").
    san: Mapped[str] = mapped_column(String(10))
    uci: Mapped[str] = mapped_column(String(5))

    game: Mapped[Game] = relationship(back_populates="moves")

    __table_args__ = (
        # Fast lookup of a game's move order. unique=True guarantees
        # a game can't have two moves in the same ply.
        Index("ix_moves_game_ply", "game_id", "ply", unique=True),
        Index("ix_moves_ply_san", "ply", "san")
    )
