import chess
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.analysis.analyzer import analyze_pgn
from app.analysis.engine import CachedEngine, normalize_fen
from app.analysis.scoring import Thresholds
from tests.fakes import SCHOLARS_MATE_PGN, ScriptedEngine, scholars_mate_engine


def test_normalize_fen_drops_move_counters() -> None:
    board = chess.Board()
    assert normalize_fen(board) == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"


def test_normalize_fen_ignores_unusable_en_passant() -> None:
    board = chess.Board()
    board.push_san("e4")  # no black pawn can capture en passant
    assert normalize_fen(board).endswith(" b KQkq -")


async def test_second_lookup_hits_the_cache(test_db: AsyncIOMotorDatabase) -> None:
    engine = ScriptedEngine()
    cached = CachedEngine(engine, test_db)

    first = await cached.analyse(chess.Board(), 12)
    second = await cached.analyse(chess.Board(), 12)

    assert first == second
    assert len(engine.calls) == 1
    assert (cached.hits, cached.misses) == (1, 1)


async def test_same_position_at_another_move_number_hits(test_db: AsyncIOMotorDatabase) -> None:
    engine = ScriptedEngine()
    cached = CachedEngine(engine, test_db)
    board = chess.Board()
    await cached.analyse(board, 12)

    # Knights out and back: same position, later move number.
    for san in ["Nf3", "Nf6", "Ng1", "Ng8"]:
        board.push_san(san)
    await cached.analyse(board, 12)

    assert len(engine.calls) == 1


async def test_depth_is_part_of_the_key(test_db: AsyncIOMotorDatabase) -> None:
    engine = ScriptedEngine()
    cached = CachedEngine(engine, test_db)

    await cached.analyse(chess.Board(), 12)
    await cached.analyse(chess.Board(), 18)

    assert len(engine.calls) == 2
    assert await test_db.analysis_cache.count_documents({}) == 2


async def test_cache_is_shared_between_instances(test_db: AsyncIOMotorDatabase) -> None:
    engine = ScriptedEngine()
    await CachedEngine(engine, test_db).analyse(chess.Board(), 12)

    later = CachedEngine(engine, test_db)
    await later.analyse(chess.Board(), 12)

    assert later.hits == 1
    assert len(engine.calls) == 1


async def test_prefetch_loads_a_game_in_one_query(test_db: AsyncIOMotorDatabase, monkeypatch) -> None:
    engine = ScriptedEngine()
    start, after_e4 = chess.Board(), chess.Board()
    after_e4.push_san("e4")
    await CachedEngine(engine, test_db).analyse(start, 12)  # cached
    cached = CachedEngine(engine, test_db)

    await cached.prefetch([start, after_e4], 12)

    async def no_single_lookups(*args, **kwargs):
        raise AssertionError("prefetched positions must not be looked up one by one")

    monkeypatch.setattr(test_db.analysis_cache, "find_one", no_single_lookups)
    assert await cached.analyse(start, 12) is not None  # from the prefetch
    await cached.analyse(after_e4, 12)  # known missing: straight to the engine
    await cached.analyse(after_e4, 12)  # cached by the call above
    assert (cached.hits, cached.misses) == (2, 1)
    assert len(engine.calls) == 2  # the first CachedEngine's call + one miss


async def test_analyzer_uses_prefetch(test_db: AsyncIOMotorDatabase) -> None:
    first = CachedEngine(scholars_mate_engine(), test_db)
    await analyze_pgn(SCHOLARS_MATE_PGN, first, 12, Thresholds())
    second = CachedEngine(scholars_mate_engine(), test_db)
    calls = []
    original = second.prefetch

    async def spy(boards, depth):
        calls.append(len(boards))
        await original(boards, depth)

    second.prefetch = spy
    await analyze_pgn(SCHOLARS_MATE_PGN, second, 12, Thresholds())

    assert calls == [8]
    assert (second.hits, second.misses) == (7, 0)
