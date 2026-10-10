import io
import sys
from pathlib import Path

import zstandard
from sqlalchemy import text

# Importing models registers the tables with Base.
from app import models  # noqa: F401
from app.db import Base, SessionLocal, engine
from app.ingest.loader import load_pgn


def open_pgn(path: Path):
    """Open a PGN file as text, decompressing on the fly if it is .zst."""
    if path.suffix == ".zst":
        # Streaming decompression keep memory use flat for multi-GB files.
        reader = zstandard.ZstdDecompressor().stream_reader(path.open("rb"))
        return io.TextIOWrapper(reader, encoding="utf-8")
    return path.open(encoding="utf-8")


def print_progress(stats: dict[str, int]) -> None:
    """Report running totals after each batch."""
    print(f"  {stats['imported']:,} imported, {stats['duplicates']:,} duplicates", flush=True)


if __name__ == "__main__":
    # Usage: python -m scripts.load_games data/ericrosen.pgn
    path = Path(sys.argv[1])

    # Make sure the tables exist (does nothing if they already do).
    Base.metadata.create_all(engine)

    # encoding="utf-8" matters on Windows, where the default encoding can
    # mess up player names and opening names that have special characters.
    with open_pgn(path) as handle, SessionLocal() as session:
        stats = load_pgn(handle, session, batch_size=2000, on_batch=print_progress)
        # Refresh planner statistics so SQLite picks efficient query plans
        # for the newly loaded data.
        session.execute(text("ANALYZE"))
        session.commit()

    print(
        f"Imported {stats['imported']} games, "
        f"{stats['duplicates']} duplicates, "
        f"{stats['skipped']} skipped."
    )