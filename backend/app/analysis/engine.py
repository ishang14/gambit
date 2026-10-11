from dataclasses import dataclass
from typing import Protocol

import chess
import chess.engine
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.analysis.scoring import Evaluation


@dataclass(frozen=True)
class EngineResult:
    evaluation: Evaluation  # White's point of view
    best_move: str | None  # UCI, e.g. "e2e4"


class Engine(Protocol):
    async def analyse(self, board: chess.Board, depth: int) -> EngineResult: ...


def normalize_fen(board: chess.Board) -> str:
    """FEN without the move counters, so the same position reached at a different
    move number shares a cache entry. (En passant is only kept when legal.)"""
    return " ".join(board.fen().split(" ")[:4])


class StockfishEngine:
    """A long-lived Stockfish process, driven through python-chess."""

    def __init__(self, path: str, threads: int = 1, hash_mb: int = 64) -> None:
        self._path = path
        self._options = {"Threads": threads, "Hash": hash_mb}
        self._engine: chess.engine.UciProtocol | None = None

    async def start(self) -> None:
        _, self._engine = await chess.engine.popen_uci(self._path)
        await self._engine.configure(self._options)

    async def close(self) -> None:
        if self._engine is not None:
            try:
                await self._engine.quit()
            except chess.engine.EngineTerminatedError:
                pass
            self._engine = None

    async def restart(self) -> None:
        await self.close()
        await self.start()

    async def analyse(self, board: chess.Board, depth: int) -> EngineResult:
        if self._engine is None:
            raise RuntimeError("Engine not started")
        info = await self._engine.analyse(board, chess.engine.Limit(depth=depth))
        score = info["score"].white()
        pv = info.get("pv") or []
        return EngineResult(
            evaluation={"cp": score.score(), "mate": score.mate()},
            best_move=pv[0].uci() if pv else None,
        )


class CachedEngine:
    """Wraps an engine with the `analysis_cache` collection, keyed by normalized FEN + depth.
    Counts hits and misses for benchmarking."""

    def __init__(self, engine: Engine, db: AsyncIOMotorDatabase) -> None:
        self._engine = engine
        self._db = db
        self.hits = 0
        self.misses = 0
        # Results already loaded, and keys known to be missing, so a lookup needs no query.
        self._known: dict[tuple[str, int], EngineResult] = {}
        self._known_missing: set[tuple[str, int]] = set()

    async def prefetch(self, boards: list[chess.Board], depth: int) -> None:
        """Load the cached results for a whole game in one query, instead of one per position."""
        keys = {normalize_fen(board) for board in boards}
        async for doc in self._db.analysis_cache.find({"fen": {"$in": list(keys)}, "depth": depth}):
            self._known[(doc["fen"], depth)] = EngineResult(evaluation=doc["eval"], best_move=doc["best_move"])
        self._known_missing |= {(key, depth) for key in keys} - self._known.keys()

    async def analyse(self, board: chess.Board, depth: int) -> EngineResult:
        key = (normalize_fen(board), depth)
        cached = self._known.get(key)
        if cached is None and key not in self._known_missing:
            doc = await self._db.analysis_cache.find_one({"fen": key[0], "depth": depth})
            if doc is not None:
                cached = EngineResult(evaluation=doc["eval"], best_move=doc["best_move"])
        if cached is not None:
            self.hits += 1
            return cached

        self.misses += 1
        result = await self._engine.analyse(board, depth)
        await self._db.analysis_cache.update_one(
            {"fen": key[0], "depth": depth},
            {"$set": {"eval": result.evaluation, "best_move": result.best_move}},
            upsert=True,
        )
        # A position repeated later in the same game is now a hit.
        self._known[key] = result
        self._known_missing.discard(key)
        return result
