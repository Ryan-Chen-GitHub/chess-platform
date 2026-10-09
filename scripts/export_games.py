# sys reads command-line arguments; Path builds file paths that work on
# Windows, macOS and Linux.
import sys
from pathlib import Path

# httpx is the HTTP client library (like a programmatic web browser).
import httpx


def export_games(username: str, max_games: int, out_path: Path) -> None:
    """Download a player's games from the Lichess API as one PGN file."""
    # Lichess's public endpoint for a user's games. No login needed.
    url = f"https://lichess.org/api/games/user/{username}"

    # Deliberately minimal parameters. "perfType" is left out because the
    # parser already skips variant games.
    params = {
        "max": max_games,
        "rated": "true",    # skip casual games
        "opening": "true",  # include the opening name and ECO code
    }

    # Lichess asks API clients to identify themselves with a User-Agent.
    # Without the Accept header, Lichess returns PGN by default.
    # So we use me! The guy that made the project :)
    headers = {"User-Agent": "chess-platform-portfolio (github.com/Ryan-Chen-GitHub)"}

    # Make sure the output folder (data/) exists. It's git-ignored, so it
    # won't be there on fresh clones.
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # stream() downloads in chunks instead of loading everything into memory at once.
    with httpx.stream(
        "GET", url, params=params, headers=headers, timeout=60
    ) as response:
        # For any error, show the exact URL and the server's own message,
        # so we can see what Lichess actually objected to.
        if response.status_code != 200:
            body = response.read().decode("utf-8", errors="replace")
            print(f"Lichess returned {response.status_code} for {response.url}")
            print(f"Response body: {body[:300]}")
            return

        # Write the chunks to disk as they arrive ("wb" = write bytes).
        with out_path.open("wb") as file:
            for chunk in response.iter_bytes():
                file.write(chunk)

    print(f"Saved games for {username} to {out_path}")


# This block only runs when the file is executed directly, not when imported.
if __name__ == "__main__":
    # Usage: python -m scripts.export_games EricRosen 500
    user = sys.argv[1] if len(sys.argv) > 1 else "EricRosen"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    export_games(user, count, Path("data") / f"{user.lower()}.pgn")