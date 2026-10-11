import chess
import pytest

from app.analysis.engine import normalize_fen
from app.openings.book import load_book
from app.openings.tree import Edge, LeakRules, build_explorer, find_leaks, position_games, shortest_paths

ROOT = normalize_fen(chess.Board())


def key_after(*sans: str) -> str:
    board = chess.Board()
    for san in sans:
        board.push_san(san)
    return normalize_fen(board)


def edge(path: tuple[str, ...], san: str, games: int, wins: int = 0, draws: int = 0, **extra) -> Edge:
    """An edge for `san` played after `path`; the user is White."""
    board = chess.Board()
    for move in path:
        board.push_san(move)
    move = board.parse_san(san)
    user_move = board.turn == chess.WHITE
    fen_key = normalize_fen(board)
    board.push(move)
    return Edge(
        fen_key=fen_key,
        move_uci=move.uci(),
        move_san=san,
        next_fen_key=normalize_fen(board),
        is_user_move=user_move,
        games=games,
        wins=wins,
        draws=draws,
        losses=games - wins - draws,
        **extra,
    )


# The user (White) has 6 games: 1. e4 in all; after 1... e5 they play 2. Qh5 (lost 3 of 3)
# or 2. Nf3 (won 2 of 2); after 1... c5 (1 game) they play 2. Nf3.
EDGES = [
    edge((), "e4", 6, wins=3),
    edge(("e4",), "e5", 5, wins=2),
    edge(("e4",), "c5", 1, wins=1),
    edge(("e4", "e5"), "Qh5", 3, wins=0),
    edge(("e4", "e5"), "Nf3", 2, wins=2),
    edge(("e4", "c5"), "Nf3", 1, wins=1),
]
RULES = LeakRules(min_occurrences=3, min_move_games=2, max_score=0.35, min_eval_loss=8.0)


def test_edge_stats() -> None:
    e = edge((), "e4", 4, wins=1, draws=2, analyzed=2, win_chance_loss_sum=10.0, cp_loss_sum=60.0)
    assert e.score == pytest.approx(0.5)
    assert e.avg_win_chance_loss == 5.0
    assert e.avg_cp_loss == 30.0
    assert edge((), "e4", 1).avg_win_chance_loss is None


def test_position_games() -> None:
    counts = position_games(EDGES)
    assert counts[ROOT] == 6
    assert counts[key_after("e4", "e5")] == 5


def test_poor_results_leak() -> None:
    leaks = find_leaks(EDGES, ROOT, RULES, load_book())

    assert len(leaks) == 1
    leak = leaks[0]
    assert leak["move_san"] == "Qh5"
    assert leak["reasons"] == ["poor_results"]
    assert [step["san"] for step in leak["path"]] == ["e4", "e5"]
    assert leak["path"][-1]["fen_key"] == key_after("e4", "e5")
    assert leak["position_games"] == 5
    assert leak["score"] == 0.0
    assert leak["impact"] == pytest.approx(150.0)  # 3 games x 50 points below an even score
    assert leak["opening_name"] == "King's Pawn Game"
    assert leak["fen"] == key_after("e4", "e5") + " 0 1"


def test_eval_loss_leak_needs_fewer_games() -> None:
    edges = [
        edge((), "e4", 3, wins=3),
        edge(("e4",), "e5", 3, wins=3),
        edge(("e4", "e5"), "Ke2", 2, wins=2, analyzed=2, win_chance_loss_sum=30.0, best_move_san="Nf3"),
        edge(("e4", "e5"), "Nf3", 1, wins=1),
    ]

    leaks = find_leaks(edges, ROOT, RULES, load_book())

    assert [(l["move_san"], l["reasons"]) for l in leaks] == [("Ke2", ["eval_loss"])]
    assert leaks[0]["avg_win_chance_loss"] == 15.0
    assert leaks[0]["best_move_san"] == "Nf3"
    assert leaks[0]["impact"] == pytest.approx(30.0)


def test_opponent_moves_are_never_leaks() -> None:
    edges = [edge((), "e4", 4, wins=4), edge(("e4",), "f6", 4, wins=4, analyzed=4, win_chance_loss_sum=80.0)]
    assert find_leaks(edges, ROOT, RULES, load_book()) == []


@pytest.mark.parametrize(
    ("rules", "expected"),
    [
        (LeakRules(min_occurrences=6), []),  # position only reached 5 times
        (LeakRules(min_move_games=4), []),  # Qh5 only played 3 times
        (LeakRules(max_score=-0.1), []),  # nothing scores that badly
        (LeakRules(), ["Qh5"]),
    ],
)
def test_leak_rules_are_configurable(rules: LeakRules, expected: list[str]) -> None:
    assert [l["move_san"] for l in find_leaks(EDGES, ROOT, rules, load_book())] == expected


def test_leaks_ranked_by_impact() -> None:
    edges = EDGES + [
        edge(("e4", "e5", "Nf3"), "Nc6", 2, wins=2),
        # Reached 3 times; 4. Ng5 twice, losing 25 points of win chance on average.
        edge(("e4", "e5", "Nf3", "Nc6"), "Ng5", 2, wins=2, analyzed=2, win_chance_loss_sum=50.0),
        edge(("e4", "e5", "Nf3", "Nc6"), "Bb5", 1, wins=1),
    ]

    leaks = find_leaks(edges, ROOT, RULES, load_book())

    assert [l["move_san"] for l in leaks] == ["Qh5", "Ng5"]  # 150 > 2 x 25 = 50


def test_a_losing_line_is_one_leak_not_a_chain() -> None:
    edges = [
        edge((), "e4", 8, wins=4),
        edge(("e4",), "e5", 8, wins=4),
        edge(("e4", "e5"), "Nf3", 4, wins=4),
        edge(("e4", "e5"), "Qh5", 4),  # lost all 4: the real problem
        edge(("e4", "e5", "Qh5"), "Nc6", 3),
        edge(("e4", "e5", "Qh5", "Nc6"), "Bc4", 3),  # lost these 3 too, but they're the same games
        edge(("e4", "e5", "Qh5"), "g6", 1),
    ]

    leaks = find_leaks(edges, ROOT, RULES, load_book())

    assert [l["move_san"] for l in leaks] == ["Qh5"]


def test_engine_flagged_follow_on_moves_are_kept() -> None:
    edges = [
        edge((), "e4", 8, wins=4),
        edge(("e4",), "e5", 8, wins=4),
        edge(("e4", "e5"), "Nf3", 4, wins=4),
        edge(("e4", "e5"), "Qh5", 4),
        edge(("e4", "e5", "Qh5"), "Nc6", 3),
        edge(("e4", "e5", "Qh5", "Nc6"), "Bc4", 3, analyzed=3, win_chance_loss_sum=45.0),
    ]

    leaks = find_leaks(edges, ROOT, RULES, load_book())

    assert [(l["move_san"], l["reasons"]) for l in leaks] == [
        ("Qh5", ["poor_results"]),
        ("Bc4", ["poor_results", "eval_loss"]),
    ]


def test_shortest_paths() -> None:
    paths = shortest_paths(EDGES, ROOT)
    assert [e.move_san for e in paths[key_after("e4", "e5", "Nf3")]] == ["e4", "e5", "Nf3"]
    assert paths[ROOT] == []


def test_explorer_prunes_rare_moves() -> None:
    positions = build_explorer(EDGES, ROOT, "white", 2, load_book(), [])

    assert [m["san"] for m in positions[ROOT]["moves"]] == ["e4"]
    assert [m["san"] for m in positions[key_after("e4")]["moves"]] == ["e5"]  # c5 has 1 game
    assert key_after("e4", "c5") not in positions
    assert [m["san"] for m in positions[key_after("e4", "e5")]["moves"]] == ["Qh5", "Nf3"]


def test_explorer_position_details() -> None:
    leaks = find_leaks(EDGES, ROOT, RULES, load_book())
    positions = build_explorer(EDGES, ROOT, "white", 1, load_book(), leaks)

    after_e5 = positions[key_after("e4", "e5")]
    assert after_e5["user_to_move"] is True
    assert positions[key_after("e4")]["user_to_move"] is False
    assert after_e5["name"] == "King's Pawn Game"
    assert after_e5["games"] == 5
    qh5, nf3 = after_e5["moves"]
    assert qh5["is_leak"] is True
    assert nf3["is_leak"] is False
    assert qh5["score"] == 0.0
    assert nf3["score"] == 1.0


def test_explorer_marks_where_book_ends() -> None:
    edges = [edge((), "e4", 2), edge(("e4",), "e5", 2), edge(("e4", "e5"), "Ke2", 2), edge(("e4", "e5", "Ke2"), "Ke7", 2)]

    positions = build_explorer(edges, ROOT, "white", 1, load_book(), [])

    ke2 = positions[key_after("e4", "e5")]["moves"][0]
    ke7 = positions[key_after("e4", "e5", "Ke2")]["moves"][0]
    e5 = positions[key_after("e4")]["moves"][0]
    # 2. Ke2 is the (named) Bongcloud; 2... Ke7 is not a book line.
    assert (e5["in_book"], e5["leaves_book"]) == (True, False)
    assert (ke2["in_book"], ke2["leaves_book"]) == (True, False)
    assert (ke7["in_book"], ke7["leaves_book"]) == (False, True)


def test_explorer_merges_transpositions() -> None:
    edges = [
        edge((), "d4", 1),
        edge(("d4",), "d5", 1),
        edge(("d4", "d5"), "Nf3", 1),
        edge((), "Nf3", 1),
        edge(("Nf3",), "d5", 1),
        edge(("Nf3", "d5"), "d4", 1),
        edge(("d4", "d5", "Nf3"), "Nf6", 2),  # same position reached both ways
    ]

    positions = build_explorer(edges, ROOT, "white", 1, load_book(), [])

    assert positions[key_after("d4", "d5", "Nf3")]["games"] == 2
    assert key_after("d4", "d5", "Nf3") == key_after("Nf3", "d5", "d4")
