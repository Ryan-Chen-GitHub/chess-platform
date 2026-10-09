# Chess Platform

A backend that loads real chess games from Lichess into a relational database and serves analytics about them through a REST API.

> **Status:** in development. Schema, ingestion pipeline, API endpoints, and CI are
> working. large-dataset performance work is next.

## Tech Stack

Python 3.14, FastAPI, SQLAlchemy, SQLite (PostgreSQL planned), python-chess, pytest, Pydantic, httpx, Ruff.

## Database Schema

| Table         | Purpose                                       |
|---------------|-----------------------------------------------|
| `players`     | One row per Lichess username                  |
| `games`       | One row per game, linked to both players      |
| `moves`       | One row per half-move (ply), linked to a game |

## API Endpoints

| Endpoint                          | Description                                    |
|-----------------------------------|------------------------------------------------|
| `GET /health`                     | Health check, returns `{"status": "ok"}`       |
| `GET /openings`                   | Most played openings (optional `limit`, 1-100) |
| `GET /openings/{eco}/stats`       | Results breakdown for an ECO code, like `C20`  |
| `GET /players/{username}`         | A player's record and top openings             |

## Design Decisions
- **Ratings are stored on the game, not the player.** A player's rating changes over time, so analytics need their rating at the time of each game.
- **Index on the columns queries filter by** (opening code, date, players, and move position). They speed up reads at the cost of slightly slower writes, so only columns that are actually queried are indexed.
- **One row per move.** This makes questions like "what is the most common reply to 1.e4 at 1500 rating?" possible in SQL. It also makes the table very large (about 80 rows per game), so query performance matters.
- **Unique `lichess_id` on games.** Re-running an import can never create duplicate games.
- **Foreign keys enforced.** SQLite ignores them by default, so they are turned on for every connection.
- **Batched, idempotent ingestion.** Games are inserted in batches per transaction, moves are bulk-inserted, and re-running an import skips games already stored.

## Getting Started

Requires Python 3.12 or newer & Git.

### Setup (Windows PowerShell)

    git clone https://github.com/Ryan-Chen-GitHub/chess-platform.git
    cd chess-platform
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt

Run all commands from the project root (`chess-platform/`), or else imports don't resolve.
Re-run the activate command in every new terminal.
If PowerShell blocks the script, run the following once:

    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

### Load Data

    python -m scripts.export_games DrNykterstein 500
    python -m scripts.load_games data/drnykterstein.pgn

The 1st command downloads a player's most recent rated games from the Lichess API into `data/`.
The 2nd command loads them into `chess.db`.
Both are safe to re-run, since duplicate games are skipped.
`data/` and `chess.db` are git-ignored, so everyone generates their own.

### Run the API

    uvicorn app.main:app --reload

Interactive API docs are available at: http://127.0.0.1:8000/docs.

### Run the Tests

    pytest