"""Benchmark game analysis: time per game at several engine depths, and the cache hit rate.

For each depth it starts from an empty cache and analyzes the benchmark games in order, as
one user analyzing their history would (repeated opening positions hit the cache), then
analyzes them all again (everything cached). It uses the real pipeline: Stockfish through
python-chess, the MongoDB-backed cache, and the analyzer.

Needs Stockfish and MongoDB, so run it in the worker image:

    docker compose run --rm worker python -m benchmarks.analysis_benchmark --depths 10 14 18

Results go to benchmarks/results.json and benchmarks/results.md.
"""

import argparse
import asyncio
import json
import os
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import chess
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.analysis.analyzer import analyze_pgn
from app.analysis.engine import CachedEngine, EngineResult, StockfishEngine
from app.analysis.scoring import Thresholds
from app.config import get_settings
from app.db import ensure_indexes

HERE = Path(__file__).parent


class TimedEngine:
    """Wraps the engine to time every call that actually reaches Stockfish."""

    def __init__(self, engine: StockfishEngine) -> None:
        self.engine = engine
        self.seconds: list[float] = []

    async def analyse(self, board: chess.Board, depth: int) -> EngineResult:
        start = time.perf_counter()
        result = await self.engine.analyse(board, depth)
        self.seconds.append(time.perf_counter() - start)
        return result


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))
    return ordered[index]


async def run_pass(games: list[dict[str, Any]], cached: CachedEngine, depth: int) -> dict[str, Any]:
    hits_before, misses_before = cached.hits, cached.misses
    per_game = []
    for game in games:
        start = time.perf_counter()
        await analyze_pgn(game["pgn"], cached, depth, Thresholds())
        per_game.append(time.perf_counter() - start)
    hits, misses = cached.hits - hits_before, cached.misses - misses_before
    return {
        "total_seconds": round(sum(per_game), 2),
        "mean_seconds_per_game": round(statistics.mean(per_game), 3),
        "median_seconds_per_game": round(statistics.median(per_game), 3),
        "p95_seconds_per_game": round(percentile(per_game, 95), 3),
        "engine_calls": misses,
        "cache_hits": hits,
        "cache_hit_rate": round(hits / (hits + misses), 3) if hits + misses else None,
    }


async def benchmark_depth(mongo: AsyncIOMotorClient, games: list[dict[str, Any]], depth: int) -> dict[str, Any]:
    settings = get_settings()
    name = f"gambit_bench_{uuid4().hex[:12]}"
    db: AsyncIOMotorDatabase = mongo[name]
    stockfish = StockfishEngine(settings.stockfish_path, threads=1, hash_mb=64)
    await stockfish.start()
    try:
        await ensure_indexes(db)
        timed = TimedEngine(stockfish)
        cached = CachedEngine(timed, db)
        cold = await run_pass(games, cached, depth)
        engine_ms = [s * 1000 for s in timed.seconds]
        warm = await run_pass(games, cached, depth)
        return {
            "depth": depth,
            "cold": cold,
            "warm": warm,
            "mean_ms_per_engine_call": round(statistics.mean(engine_ms), 1),
            "p95_ms_per_engine_call": round(percentile(engine_ms, 95), 1),
        }
    finally:
        await stockfish.close()
        await mongo.drop_database(name)


def machine() -> dict[str, Any]:
    cpu = platform.processor() or "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return {"cpu": cpu, "cpus_visible": os.cpu_count(), "python": platform.python_version(), "engine_threads": 1, "engine_hash_mb": 64}


def markdown(report: dict[str, Any]) -> str:
    games = report["games"]
    lines = [
        "# Analysis benchmark",
        "",
        f"{games['count']} games ({games['plies']} plies), {games['source']}.",
        f"Machine: {report['machine']['cpu']} ({report['machine']['cpus_visible']} CPUs visible), Stockfish with 1 thread and 64 MB hash.",
        f"Run at {report['run_at']}.",
        "",
        "| Depth | Mean s/game (cold cache) | Median | p95 | ms per engine call | Cache hit rate, first pass | Mean s/game (warm cache) |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["results"]:
        cold, warm = row["cold"], row["warm"]
        lines.append(
            f"| {row['depth']} | {cold['mean_seconds_per_game']:.2f} | {cold['median_seconds_per_game']:.2f} | "
            f"{cold['p95_seconds_per_game']:.2f} | {row['mean_ms_per_engine_call']:.0f} | "
            f"{cold['cache_hit_rate']:.0%} | {warm['mean_seconds_per_game']:.3f} |"
        )
    lines += [
        "",
        "- **Cold cache:** the games are analyzed in order starting from an empty cache, as one user analyzing "
        "their history would. Positions repeated across games (mostly openings) are only sent to the engine once; "
        "the first-pass hit rate is how often that happened.",
        "- **Warm cache:** the same games analyzed again; every position comes from the cache (hit rate 100%).",
    ]
    return "\n".join(lines) + "\n"


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--depths", type=int, nargs="+", default=[10, 14, 18])
    parser.add_argument("--games", type=int, default=None, help="use only the first N benchmark games")
    args = parser.parse_args()

    data = json.loads((HERE / "games.json").read_text())
    games = data["games"][: args.games] if args.games else data["games"]
    mongo = AsyncIOMotorClient(get_settings().mongo_url, tz_aware=True)
    results = []
    try:
        for depth in args.depths:
            print(f"depth {depth}: analyzing {len(games)} games...", flush=True)
            results.append(await benchmark_depth(mongo, games, depth))
            print(json.dumps(results[-1]), flush=True)
    finally:
        mongo.close()

    report = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "machine": machine(),
        "games": {"count": len(games), "plies": sum(g["plies"] for g in games), "source": data["source"]},
        "results": results,
    }
    (HERE / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    (HERE / "results.md").write_text(markdown(report))
    print(markdown(report))


if __name__ == "__main__":
    asyncio.run(main())
