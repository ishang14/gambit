# Analysis benchmark

30 games (2029 plies), 30 standard games from one public chess.com account (Apr-Jul 2026), moves only.
Machine: 13th Gen Intel(R) Core(TM) i5-13420H (12 CPUs visible), Stockfish with 1 thread and 64 MB hash.
Run at 2026-10-11T00:40:38+00:00.

| Depth | Mean s/game (cold cache) | Median | p95 | ms per engine call | Cache hit rate, first pass | Mean s/game (warm cache) |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1.09 | 0.95 | 1.96 | 16 | 10% | 0.018 |
| 14 | 7.21 | 7.13 | 13.64 | 115 | 10% | 0.018 |
| 18 | 36.80 | 35.61 | 62.36 | 592 | 10% | 0.018 |

- **Cold cache:** the games are analyzed in order starting from an empty cache, as one user analyzing their history would. Positions repeated across games (mostly openings) are only sent to the engine once; the first-pass hit rate is how often that happened.
- **Warm cache:** the same games analyzed again; every position comes from the cache (hit rate 100%).
