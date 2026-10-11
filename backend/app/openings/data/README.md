# Opening book data

`a.tsv` … `e.tsv` are the named opening lines from
[lichess-org/chess-openings](https://github.com/lichess-org/chess-openings)
(columns: `eco`, `name`, `pgn`), released under CC0 (public domain).

Gambit uses them to tell when a game "leaves known theory": a position is in the
book if it occurs anywhere along one of these lines.
