# Chess Platform

A backend that loads real chess games from Lichess into a relational database and serves analytics about them through a REST API.

> **Status:** in development. Database schema complete; ingestion
> pipeline & API endpoints in progress.

## Tech Stack

Python 3.14, FastAPI, SQLAlchemy, SQLite (PostgreSQL planned), python-chess, pytest.

## Database Schema

| Table         | Purpose                                       |
|---------------|-----------------------------------------------|
| 'players'     | One row per Lichess username                  |
| 'games'       | One row per game, linked to both palyers      |
| 'moves'       | One row per half-move (ply), linked to a game |

## Design Decisions
- **Ratings are stored on the game, not the player.** A Player's rating changes over time, so analytics need their rating at the time of each game.
- **Index on the columns queries filter by** (opening code, date, players, and move position). They speed up reads at the cost of slightly slower writes, so only columns that are actually queried are indexed.
- **One row per move.** This makes questions like "what is the most common reply to 1.e4 at 1500 rating?" possible in SQL. It also makes the table very large (about 80 rows per game), so query performance matters.
- **Unique 'lichess_id' on games.** Re-running an import can never create duplcate games.
- **Foreign keys enforced.** SQLite ignores them by default, so they are turned on for every connection.

## Running Locally

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requriements.txt
    python -m scripts.create_tables
    uvicorn app.main:app --reload
    pytest