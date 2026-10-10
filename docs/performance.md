# Performance notes

Dataset: Lichess standard rated games, January 2013 (121,114 games,
8,143,801 moves), SQLite. Timings are the median of 5 runs after one warm-up
run, measured with `python -m scripts.benchmark`.

## Baseline (indexes from the original schema)

| Query                                 | Time     | Plan                           |
|---------------------------------------|----------|--------------------------------|
| Most played openings                  | 91.7 ms  | full scan of games             |
| Results for one ECO code              | 10.2 ms  | index on eco                   |
| Games between 1500-1600 rated players | 17.1 ms  | full scan of games             |
| Most common reply to 1.e4 at ~1500    | 716.6 ms | index lookups, poor join order |
| One player's record                   | 4.8 ms   | both player indexes            |

## Experiments: "most common reply to 1.e4 at ~1500"

| Change                                 | Median time | Notes                                                  |
|----------------------------------------|-------------|--------------------------------------------------------|
| Baseline                               | 716.6 ms    | plan starts from every ply-2 move                      |
| `ANALYZE`                              | 263.6 ms    | planner starts from `ply=1 AND san='e4'` (2.7x faster) |
| + index on `moves (game_id, ply, san)` | 265.9 ms    | never used by the planner; dropped                     |
| + index on `games (white_elo)`         | 265.4 ms    | not used by the planner for this query; dropped        |

Other queries were measured and left alone: full scans of 121k rows take
17-92 ms, which doesn't justify extra indexes.

`ANALYZE` is now run at the end of `scripts.load_games`, because its
statistics are stored in the database file and would otherwise be missing
from a fresh load.

An index on `games (white_elo)` made the rating-band count (1500-1600 for
both players) about 5x slower, 84.4 ms against 16.9 ms for a full scan. The
band matches a large share of the games, so per-row index lookups cost more
than a sequential scan. Indexes help with selective filters, not broad ranges.