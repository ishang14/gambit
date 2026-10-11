"""Pure functions that turn aggregated move statistics into the opening explorer and leaks."""

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from app.openings.book import OpeningBook


@dataclass
class Edge:
    """One move from one position, summed over the user's games (as one color)."""

    fen_key: str
    move_uci: str
    move_san: str
    next_fen_key: str
    is_user_move: bool
    games: int
    wins: int
    draws: int
    losses: int
    analyzed: int = 0
    win_chance_loss_sum: float = 0.0
    cp_loss_sum: float = 0.0
    best_move_uci: str | None = None
    best_move_san: str | None = None
    example_game_id: str | None = None

    @property
    def score(self) -> float:
        """Points per game from the user's side: win = 1, draw = 0.5."""
        return (self.wins + 0.5 * self.draws) / self.games

    @property
    def avg_win_chance_loss(self) -> float | None:
        return self.win_chance_loss_sum / self.analyzed if self.analyzed else None

    @property
    def avg_cp_loss(self) -> float | None:
        return self.cp_loss_sum / self.analyzed if self.analyzed else None


@dataclass(frozen=True)
class LeakRules:
    min_occurrences: int = 3
    min_move_games: int = 2
    max_score: float = 0.35
    min_eval_loss: float = 8.0


def full_fen(fen_key: str) -> str:
    """A normalized FEN plus placeholder move counters, so boards can load it."""
    return f"{fen_key} 0 1"


def position_games(edges: list[Edge]) -> dict[str, int]:
    """How many games reached each position (counted by the moves played from it)."""
    totals: dict[str, int] = defaultdict(int)
    for edge in edges:
        totals[edge.fen_key] += edge.games
    return totals


def shortest_paths(edges: list[Edge], root: str) -> dict[str, list[Edge]]:
    """The shortest move sequence from the start to each position (positions can
    be reached by several move orders; any shortest one will do for display)."""
    by_position: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        by_position[edge.fen_key].append(edge)
    paths: dict[str, list[Edge]] = {root: []}
    queue = deque([root])
    while queue:
        fen_key = queue.popleft()
        for edge in sorted(by_position[fen_key], key=lambda e: -e.games):
            if edge.next_fen_key not in paths:
                paths[edge.next_fen_key] = paths[fen_key] + [edge]
                queue.append(edge.next_fen_key)
    return paths


def opening_name_along(path: list[Edge], root: str, book: OpeningBook) -> str | None:
    """Name of the deepest named book position on the path."""
    name = book.name(root)
    for edge in path:
        name = book.name(edge.next_fen_key) or name
    return name


def find_leaks(edges: list[Edge], root: str, rules: LeakRules, book: OpeningBook) -> list[dict[str, Any]]:
    """Positions the user keeps reaching where their usual move scores badly or loses
    a lot of win chance, ranked by impact (games affected x how bad it is)."""
    reached = position_games(edges)
    paths = shortest_paths(edges, root)
    leaks = []
    for edge in edges:
        if not edge.is_user_move:
            continue
        if reached[edge.fen_key] < rules.min_occurrences or edge.games < rules.min_move_games:
            continue

        reasons = []
        badness = 0.0
        if edge.games >= rules.min_occurrences and edge.score <= rules.max_score:
            reasons.append("poor_results")
            badness = max(badness, (0.5 - edge.score) * 100)
        eval_loss = edge.avg_win_chance_loss
        if eval_loss is not None and eval_loss >= rules.min_eval_loss:
            reasons.append("eval_loss")
            badness = max(badness, eval_loss)
        if not reasons:
            continue

        path = paths.get(edge.fen_key, [])
        leaks.append(
            {
                "fen_key": edge.fen_key,
                "fen": full_fen(edge.fen_key),
                "path": [{"san": e.move_san, "uci": e.move_uci, "fen_key": e.next_fen_key} for e in path],
                "opening_name": opening_name_along(path, root, book),
                "move_uci": edge.move_uci,
                "move_san": edge.move_san,
                "games": edge.games,
                "position_games": reached[edge.fen_key],
                "wins": edge.wins,
                "draws": edge.draws,
                "losses": edge.losses,
                "score": round(edge.score, 3),
                "analyzed": edge.analyzed,
                "avg_win_chance_loss": round(eval_loss, 1) if eval_loss is not None else None,
                "best_move_uci": edge.best_move_uci,
                "best_move_san": edge.best_move_san,
                "reasons": reasons,
                "impact": round(edge.games * badness, 1),
                "example_game_id": edge.example_game_id,
            }
        )
    leaks = drop_follow_on_leaks(leaks, root)
    leaks.sort(key=lambda leak: (-leak["impact"], leak["fen_key"], leak["move_uci"]))
    return leaks


def drop_follow_on_leaks(leaks: list[dict[str, Any]], root: str) -> list[dict[str, Any]]:
    """Losing games count against every later move in the same line, so one bad line
    would show up as a chain of results-only leaks. Keep only the earliest: drop a
    results-only leak when an earlier move on its path is a leak covering as many games.
    Engine-flagged leaks are about the move itself, so they are always kept."""
    by_edge = {(leak["fen_key"], leak["move_uci"]): leak for leak in leaks}
    kept = []
    for leak in leaks:
        if leak["reasons"] == ["poor_results"]:
            before = root
            covered = False
            for step in leak["path"]:
                earlier = by_edge.get((before, step["uci"]))
                if earlier is not None and earlier["games"] >= leak["games"]:
                    covered = True
                    break
                before = step["fen_key"]
            if covered:
                continue
        kept.append(leak)
    return kept


def build_explorer(
    edges: list[Edge],
    root: str,
    user_color: str,
    min_games: int,
    book: OpeningBook,
    leaks: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Positions reachable from the start through moves played at least `min_games`
    times, keyed by normalized FEN. Each lists its moves, most played first."""
    by_position: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        if edge.games >= min_games:
            by_position[edge.fen_key].append(edge)
    leak_keys = {(leak["fen_key"], leak["move_uci"]) for leak in leaks}
    reached = position_games(edges)
    user_letter = "w" if user_color == "white" else "b"

    positions: dict[str, dict[str, Any]] = {}
    queue = deque([root])
    while queue:
        fen_key = queue.popleft()
        if fen_key in positions:
            continue
        moves = []
        for edge in sorted(by_position[fen_key], key=lambda e: (-e.games, e.move_san)):
            in_book = book.contains(edge.next_fen_key)
            moves.append(
                {
                    "uci": edge.move_uci,
                    "san": edge.move_san,
                    "next": edge.next_fen_key,
                    "games": edge.games,
                    "wins": edge.wins,
                    "draws": edge.draws,
                    "losses": edge.losses,
                    "score": round(edge.score, 3),
                    "analyzed": edge.analyzed,
                    "avg_win_chance_loss": round(edge.avg_win_chance_loss, 1) if edge.analyzed else None,
                    "avg_cp_loss": round(edge.avg_cp_loss) if edge.analyzed else None,
                    "best_move_san": edge.best_move_san,
                    "in_book": in_book,
                    "leaves_book": book.contains(fen_key) and not in_book,
                    "is_leak": (fen_key, edge.move_uci) in leak_keys,
                }
            )
            queue.append(edge.next_fen_key)
        positions[fen_key] = {
            "fen": full_fen(fen_key),
            "games": reached.get(fen_key, 0),
            "user_to_move": fen_key.split(" ")[1] == user_letter,
            "in_book": book.contains(fen_key),
            "name": book.name(fen_key),
            "moves": moves,
        }
    return positions
