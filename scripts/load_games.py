import sys
from pathlib import Path

# Importing models registers the tables with Base.
from app import models  # noqa: F401
from app.db import Base, SessionLocal, engine
from app.ingest.loader import load_pgn

if __name__ == "__main__":
    # Usage: python -m scripts.load_games data/ericrosen.pgn
    path = Path(sys.argv[1])

    # Make sure the tables exist (does nothing if they already do).
    Base.metadata.create_all(engine)

    # encoding="utf-8" matters on Windows, where the default encoding can
    # mangle player names and opening names containing special characters.
    with path.open(encoding="utf-8") as handle, SessionLocal() as session:
        stats = load_pgn(handle, session)

    print(
        f"Imported {stats['imported']} games, "
        f"{stats['duplicates']} duplicates, "
        f"{stats['skipped']} skipped."
    )