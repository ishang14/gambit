import pytest

from app.analysis.analyzer import analyze_pgn
from app.analysis.scoring import Thresholds
from tests.fakes import SCHOLARS_MATE_PGN, ScriptedEngine, scholars_mate_engine

STALEMATE_PGN = """[Event "Test"]
[SetUp "1"]
[FEN "k7/8/8/8/3Q4/8/8/7K w - - 0 1"]
[Result "1/2-1/2"]

1. Qb6 1/2-1/2
"""


async def test_classifies_each_move() -> None:
    analysis = await analyze_pgn(SCHOLARS_MATE_PGN, scholars_mate_engine(), 12, Thresholds())

    assert [p["move_san"] for p in analysis.positions] == ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6", "Qxf7#"]
    assert [p["classification"] for p in analysis.positions] == [
        "best",
        "best",
        "good",
        "best",
        "best",
        "blunder",
        "best",
    ]


async def test_records_the_engine_line_and_evals() -> None:
    analysis = await analyze_pgn(SCHOLARS_MATE_PGN, scholars_mate_engine(), 12, Thresholds())
    blunder = analysis.positions[5]

    assert blunder["ply"] == 6
    assert blunder["color"] == "black"
    assert blunder["move_played"] == "g8f6"
    assert blunder["best_move"] == "g7g6"
    assert blunder["best_move_san"] == "g6"
    assert blunder["eval_before"] == {"cp": -10, "mate": None}
    assert blunder["eval_after"] == {"cp": None, "mate": 1}
    assert blunder["win_chance_loss"] == pytest.approx(50.9, abs=0.1)
    assert blunder["cp_loss"] == 1010  # -10 -> mate, with mate capped at 1000
    assert blunder["fen"].startswith("r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq")
    assert blunder["fen_key"] == " ".join(blunder["fen"].split(" ")[:4])


async def test_checkmate_is_scored_without_the_engine() -> None:
    engine = scholars_mate_engine()

    analysis = await analyze_pgn(SCHOLARS_MATE_PGN, engine, 12, Thresholds())

    assert len(engine.calls) == 7  # 8 positions, the final mate needs no engine
    assert analysis.positions[-1]["eval_after"] == {"cp": None, "mate": 0}
    assert analysis.positions[-1]["accuracy"] == pytest.approx(100, abs=0.1)


async def test_stalemate_is_a_draw_without_the_engine() -> None:
    engine = ScriptedEngine()

    analysis = await analyze_pgn(STALEMATE_PGN, engine, 12, Thresholds())

    assert len(engine.calls) == 1
    assert analysis.positions[0]["eval_after"] == {"cp": 0, "mate": None}


async def test_summary_by_color() -> None:
    analysis = await analyze_pgn(SCHOLARS_MATE_PGN, scholars_mate_engine(), 12, Thresholds())

    assert analysis.counts["white"] == {"best": 3, "good": 1, "inaccuracy": 0, "mistake": 0, "blunder": 0}
    assert analysis.counts["black"] == {"best": 2, "good": 0, "inaccuracy": 0, "mistake": 0, "blunder": 1}
    assert analysis.accuracy["white"] > analysis.accuracy["black"]
    assert 0 <= analysis.accuracy["black"] <= 100


async def test_reports_progress() -> None:
    seen: list[tuple[int, int]] = []

    async def on_progress(done: int, total: int) -> None:
        seen.append((done, total))

    await analyze_pgn(SCHOLARS_MATE_PGN, scholars_mate_engine(), 12, Thresholds(), on_progress)

    assert seen[0] == (1, 8)
    assert seen[-1] == (8, 8)


async def test_passes_depth_to_engine() -> None:
    engine = scholars_mate_engine()

    await analyze_pgn(SCHOLARS_MATE_PGN, engine, 7, Thresholds())

    assert {depth for _, depth in engine.calls} == {7}


async def test_rejects_bad_pgn() -> None:
    with pytest.raises(ValueError):
        await analyze_pgn("1. e4 e5 2. Ke3 Ke6", ScriptedEngine(), 12, Thresholds())
