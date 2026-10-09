# insert() builds a bulk INSERT statement; select() builds a SELECT query.
import chess.pgn
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.ingest.parser import ParsedGame, parse_game
from app.models import Game, Move, Player

# How many games to write per database transaction. Bigger batches are
# faster because commits are slow, but they use more memory.
BATCH_SIZE = 200


def _get_or_create_player_id(
    session: Session, username: str, cache: dict[str, int]
) -> int:
    """Return the ID of a player, creating the row if it doesn't exist."""
    # The cache is a dictionary of username -> id for players we've already
    # looked up. It saves a database query for every repeat appearance.
    if username in cache:
        return cache[username]

    player = session.scalar(select(Player).where(Player.username == username))
    if player is None:
        player = Player(username=username)
        session.add(player)
        # flush() sends the INSERT to the database (without committing) so
        # the new row gets its ID.
        session.flush()

    cache[username] = player.id
    return player.id


def _flush_batch(
    session: Session,
    batch: list[ParsedGame],
    cache: dict[str, int],
    stats: dict[str, int],
) -> None:
    """Write one batch of parsed games to the database in one transaction."""
    # One query finds which games in this batch are already in the database.
    # Asking once per batch is far cheaper than asking once per game.
    ids = [g.lichess_id for g in batch]
    seen = set(session.scalars(select(Game.lichess_id).where(Game.lichess_id.in_(ids))))

    new_pairs = []  # (parsed game, Game row) pairs for games we're inserting
    for parsed in batch:
        # `seen` also grows as we go, which catches duplicates inside the
        # same file, not just ones already in the database.
        if parsed.lichess_id in seen:
            stats["duplicates"] += 1
            continue
        seen.add(parsed.lichess_id)

        game = Game(
            lichess_id=parsed.lichess_id,
            white_id=_get_or_create_player_id(session, parsed.white, cache),
            black_id=_get_or_create_player_id(session, parsed.black, cache),
            white_elo=parsed.white_elo,
            black_elo=parsed.black_elo,
            result=parsed.result,
            termination=parsed.termination,
            time_control=parsed.time_control,
            eco=parsed.eco,
            opening=parsed.opening,
            played_at=parsed.played_at,
        )
        new_pairs.append((parsed, game))

    # Insert all the games, then flush so every one gets its database ID.
    session.add_all([game for _, game in new_pairs])
    session.flush()

    # Build the move rows as plain dictionaries and insert them in one bulk
    # statement. This is much faster than creating one Move object per row,
    # and moves are by far our biggest table.
    move_rows = [
        {"game_id": game.id, "ply": ply, "san": san, "uci": uci}
        for parsed, game in new_pairs
        for ply, san, uci in parsed.moves
    ]
    if move_rows:
        session.execute(insert(Move), move_rows)

    # One commit per batch. If anything above failed, nothing from this
    # batch is saved, so we never end up with a game missing its moves.
    session.commit()
    stats["imported"] += len(new_pairs)


def load_pgn(handle, session: Session, batch_size: int = BATCH_SIZE) -> dict[str, int]:
    """Read every game from an open PGN file and store it in the database.

    Safe to run repeatedly: games already in the database are skipped.
    """
    stats = {"imported": 0, "duplicates": 0, "skipped": 0}
    cache: dict[str, int] = {}
    batch: list[ParsedGame] = []

    while True:
        # read_game returns the next game each time, or None at end of file.
        game = chess.pgn.read_game(handle)
        if game is None:
            break

        parsed = parse_game(game)
        if parsed is None:
            stats["skipped"] += 1
            continue

        batch.append(parsed)
        if len(batch) >= batch_size:
            _flush_batch(session, batch, cache, stats)
            batch = []

    # Write the final partial batch.
    if batch:
        _flush_batch(session, batch, cache, stats)

    return stats