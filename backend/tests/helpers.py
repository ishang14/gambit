import chess
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.analysis.engine import EngineResult, normalize_fen
from app.analysis.jobs import run_analysis
from app.config import Settings
from tests.conftest import insert_game
from tests.fakes import ScriptedEngine


def pgn(moves: str, result: str = "*") -> str:
    return f'[Event "Test"]\n[Result "{result}"]\n\n{moves} {result}\n'


def key_after(*sans: str) -> str:
    board = chess.Board()
    for san in sans:
        board.push_san(san)
    return normalize_fen(board)


async def add_games(db: AsyncIOMotorDatabase, user_id: ObjectId, games: list[tuple[str, str, str]]) -> list[ObjectId]:
    """games: (moves, user_color, user_result)"""
    ids = []
    for moves, color, result in games:
        ids.append(
            await insert_game(
                db,
                user_id,
                source_url=f"https://example.com/{ObjectId()}",
                pgn=pgn(moves),
                user_color=color,
                user_result=result,
            )
        )
    return ids


def blunder_engine(after: tuple[str, ...], blunder_uci: str) -> ScriptedEngine:
    """An engine that thinks the position after `after` is equal (best move Nf3)
    and that `blunder_uci` loses a queen's worth."""
    board = chess.Board()
    for san in after:
        board.push_san(san)
    script = {normalize_fen(board): EngineResult({"cp": 0, "mate": None}, "g1f3")}
    board.push_uci(blunder_uci)
    script[normalize_fen(board)] = EngineResult({"cp": -900, "mate": None}, "a7a6")
    return ScriptedEngine(script)


async def analyze(db: AsyncIOMotorDatabase, game_id: ObjectId, engine: ScriptedEngine) -> None:
    await db.games.update_one({"_id": game_id}, {"$set": {"analysis_status": "queued", "analysis_job_id": "job"}})
    await run_analysis(db, engine, game_id, "job", Settings())
