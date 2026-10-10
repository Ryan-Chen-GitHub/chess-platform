# Times a fixed set of analytics queries against the configured database and
# prints each query plan, so results can be compared before and after schema
# changes such as new indexes.
import statistics
import time

from sqlalchemy import text

from app.db import engine

# Timed runs per query, after one untimed warm-up run.
RUNS = 5


def build_queries(player_id: int) -> dict[str, str]:
    """The queries to measure. player_id comes from the database itself."""
    return {
        "most played openings": """
            SELECT opening, COUNT(*) AS n FROM games
            WHERE opening IS NOT NULL
            GROUP BY opening ORDER BY n DESC LIMIT 10
        """,
        "results for one ECO code": """
            SELECT result, COUNT(*) FROM games
            WHERE eco = 'C20' GROUP BY result
        """,
        "games between 1500-1600 rated players": """
            SELECT COUNT(*) FROM games
            WHERE white_elo BETWEEN 1500 AND 1600
              AND black_elo BETWEEN 1500 AND 1600
        """,
        "most common reply to 1.e4 at ~1500": """
            SELECT m2.san, COUNT(*) AS n
            FROM games g
            JOIN moves m1 ON m1.game_id = g.id AND m1.ply = 1 AND m1.san = 'e4'
            JOIN moves m2 ON m2.game_id = g.id AND m2.ply = 2
            WHERE g.white_elo BETWEEN 1400 AND 1600
            GROUP BY m2.san ORDER BY n DESC LIMIT 5
        """,
        "one player's record": f"""
            SELECT result, COUNT(*) FROM games
            WHERE white_id = {player_id} OR black_id = {player_id}
            GROUP BY result
        """,
    }


def time_query(conn, sql: str) -> float:
    """Median runtime in milliseconds, including fetching every row."""
    # The first run warms caches, so it is not counted.
    conn.execute(text(sql)).fetchall()
    samples = []
    for _ in range(RUNS):
        start = time.perf_counter()
        conn.execute(text(sql)).fetchall()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)


if __name__ == "__main__":
    with engine.connect() as conn:
        # The most active White player makes a realistic "busy player" case.
        busiest = conn.execute(
            text(
                "SELECT white_id FROM games "
                "GROUP BY white_id ORDER BY COUNT(*) DESC LIMIT 1"
            )
        ).scalar_one()

        print(f"Database: {engine.url}")
        for name, sql in build_queries(busiest).items():
            print(f"\n{name}: {time_query(conn, sql):.1f} ms (median of {RUNS})")
            # EXPLAIN QUERY PLAN shows whether SQLite scans a whole table or
            # uses an index; the last column holds the readable description.
            for row in conn.execute(text("EXPLAIN QUERY PLAN " + sql)):
                print("   ", row[-1])