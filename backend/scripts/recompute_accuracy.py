"""Recompute every analyzed game's accuracy with the current method, from the stored
move evaluations (no engine needed).

    docker compose exec api python -m scripts.recompute_accuracy
"""

import asyncio
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app import db
from app.analysis.scoring import game_accuracies, white_win_percent
from app.config import get_settings


def accuracies_from_positions(positions: list[dict[str, Any]]) -> dict[str, float | None]:
    """positions: one game's analyzed moves, in ply order."""
    if not positions:
        return {"white": None, "black": None}
    first = positions[0]
    win = [white_win_percent(first["eval_before"], first["color"] == "white")]
    for p in positions:
        # After White moves it's Black's turn, and the other way round.
        win.append(white_win_percent(p["eval_after"], p["color"] == "black"))
    return game_accuracies(win, [p["color"] for p in positions])


async def recompute(database: AsyncIOMotorDatabase) -> int:
    updated = 0
    async for game in database.games.find({"analysis_status": "done"}, {"user_color": 1}):
        positions = await database.positions.find({"game_id": game["_id"]}).sort("ply", 1).to_list(None)
        accuracy = accuracies_from_positions(positions)
        opponent = "black" if game["user_color"] == "white" else "white"
        await database.games.update_one(
            {"_id": game["_id"]},
            {
                "$set": {
                    "accuracy": accuracy[game["user_color"]],
                    "opponent_accuracy": accuracy[opponent],
                    "analysis.accuracy": accuracy,
                }
            },
        )
        updated += 1
    return updated


async def main() -> None:
    settings = get_settings()
    db.connect(settings)
    try:
        print(f"Recomputed accuracy for {await recompute(db.get_db())} games")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
