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