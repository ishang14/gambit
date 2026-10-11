"""Runs against a real Stockfish binary. Skipped when none is installed
(it is in the Docker image: `docker compose run --rm worker pytest tests/test_stockfish.py`)."""

import shutil

import chess
import pytest

from app.analysis.analyzer import analyze_pgn
from app.analysis.engine import StockfishEngine
from app.analysis.scoring import Thresholds
from app.config import get_settings
from tests.conftest import skip_or_fail
from tests.fakes import SCHOLARS_MATE_PGN

STOCKFISH = shutil.which(get_settings().stockfish_path)


@pytest.fixture
async def engine():
    if STOCKFISH is None:
        skip_or_fail("Stockfish is not installed")
    stockfish = StockfishEngine(STOCKFISH)
    await stockfish.start()
    yield stockfish
    await stockfish.close()


async def test_finds_mate_in_one(engine: StockfishEngine) -> None:
    board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")

    result = await engine.analyse(board, 10)

    assert result.best_move == "h5f7"
    assert result.evaluation == {"cp": None, "mate": 1}


async def test_scholars_mate_blunder(engine: StockfishEngine) -> None:
    analysis = await analyze_pgn(SCHOLARS_MATE_PGN, engine, 10, Thresholds())

    by_san = {p["move_san"]: p for p in analysis.positions}
    assert by_san["Nf6"]["classification"] == "blunder"
    assert by_san["Qxf7#"]["classification"] == "best"
    assert by_san["e4"]["classification"] in {"best", "good"}
