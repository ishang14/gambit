from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.auth.dependencies import get_current_user
from app.config import Settings, get_settings
from app.db import get_db
from app.models.training import DueCards, ReviewRequest, ReviewResult, SyncResult, TrainingCard, TrainingStats
from app.training.cards import legal_san, sync_cards
from app.training.sm2 import Schedule, quality_for, review

router = APIRouter(prefix="/training", tags=["training"])

MATURE_INTERVAL_DAYS = 21


def card_out(doc: dict[str, Any]) -> TrainingCard:
    return TrainingCard(id=str(doc["_id"]), **doc)


async def new_cards_left(db: AsyncIOMotorDatabase, user_id: ObjectId, settings: Settings, now: datetime) -> int:
    """How many never-seen cards may still be started in the current 24 hours."""
    started = await db.training_cards.count_documents(
        {"user_id": user_id, "first_reviewed_at": {"$gte": now - timedelta(hours=24)}}
    )
    return max(0, settings.training_new_cards_per_day - started)


async def due_counts(db: AsyncIOMotorDatabase, user_id: ObjectId, settings: Settings, now: datetime) -> tuple[int, int, int]:
    """(reviews due, new cards available now, new cards left today)."""
    reviews_due = await db.training_cards.count_documents({"user_id": user_id, "reviews": {"$gt": 0}, "due_at": {"$lte": now}})
    left = await new_cards_left(db, user_id, settings, now)
    unseen = await db.training_cards.count_documents({"user_id": user_id, "reviews": 0})
    return reviews_due, min(left, unseen), left


@router.post("/sync", response_model=SyncResult)
async def sync(
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, int]:
    """Create cards from new blunders and opening leaks."""
    return await sync_cards(db, user["_id"], settings)


@router.get("/due", response_model=DueCards)
async def due_cards(
    limit: int = Query(default=20, ge=1, le=100),
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DueCards:
    """Reviews that are due come first, then new cards up to today's allowance."""
    user_id, now = user["_id"], datetime.now(timezone.utc)
    reviews_due, new_available, _ = await due_counts(db, user_id, settings, now)

    reviews = (
        db.training_cards.find({"user_id": user_id, "reviews": {"$gt": 0}, "due_at": {"$lte": now}})
        .sort([("due_at", 1), ("_id", 1)])
        .limit(limit)
    )
    cards = [card_out(doc) async for doc in reviews]
    room = min(new_available, limit - len(cards))
    if room > 0:
        unseen = db.training_cards.find({"user_id": user_id, "reviews": 0}).sort([("created_at", 1), ("_id", 1)]).limit(room)
        cards += [card_out(doc) async for doc in unseen]
    return DueCards(due=reviews_due + new_available, cards=cards)


@router.post("/cards/{card_id}/review", response_model=ReviewResult)
async def review_card(
    card_id: str,
    body: ReviewRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ReviewResult:
    if not ObjectId.is_valid(card_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Card not found")
    card = await db.training_cards.find_one({"_id": ObjectId(card_id), "user_id": user["_id"]})
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Card not found")

    played_san = legal_san(card["fen"], body.move)
    if played_san is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "That move isn't legal in this position")

    correct = body.move == card["correct_move"]
    quality = quality_for(correct, body.rating)
    now = datetime.now(timezone.utc)
    schedule, due_at = review(Schedule(card["ease"], card["interval"], card["repetitions"]), quality, now)

    updated = await db.training_cards.find_one_and_update(
        {"_id": card["_id"]},
        {
            "$set": {
                "ease": schedule.ease,
                "interval": schedule.interval,
                "repetitions": schedule.repetitions,
                "due_at": due_at,
                "last_reviewed_at": now,
                **({"first_reviewed_at": now} if card["reviews"] == 0 else {}),
            },
            "$inc": {"reviews": 1, "lapses": 0 if correct else 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    await db.training_reviews.insert_one(
        {
            "user_id": user["_id"],
            "card_id": card["_id"],
            "reviewed_at": now,
            "move": body.move,
            "correct": correct,
            "rating": body.rating,
            "quality": quality,
            "interval_after": schedule.interval,
        }
    )
    return ReviewResult(
        correct=correct,
        played_san=played_san,
        correct_move_san=card["correct_move_san"],
        card=card_out(updated),
    )


@router.get("/stats", response_model=TrainingStats)
async def stats(
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TrainingStats:
    user_id = user["_id"]
    now = datetime.now(timezone.utc)
    cards = db.training_cards

    by_source = {
        row["_id"]: row["count"]
        async for row in cards.aggregate(
            [{"$match": {"user_id": user_id}}, {"$group": {"_id": "$source", "count": {"$sum": 1}}}]
        )
    }
    week = [
        row
        async for row in db.training_reviews.aggregate(
            [
                {"$match": {"user_id": user_id, "reviewed_at": {"$gte": now - timedelta(days=7)}}},
                {"$group": {"_id": None, "total": {"$sum": 1}, "correct": {"$sum": {"$cond": ["$correct", 1, 0]}}}},
            ]
        )
    ]
    next_card = await cards.find_one(
        {"user_id": user_id, "reviews": {"$gt": 0}, "due_at": {"$gt": now}}, sort=[("due_at", 1)]
    )
    reviews_due, new_available, new_left = await due_counts(db, user_id, settings, now)

    return TrainingStats(
        total=sum(by_source.values()),
        due_now=reviews_due + new_available,
        new=await cards.count_documents({"user_id": user_id, "reviews": 0}),
        learning=await cards.count_documents(
            {"user_id": user_id, "reviews": {"$gt": 0}, "interval": {"$lt": MATURE_INTERVAL_DAYS}}
        ),
        mature=await cards.count_documents({"user_id": user_id, "interval": {"$gte": MATURE_INTERVAL_DAYS}}),
        by_source=by_source,
        reviews_last_24h=await db.training_reviews.count_documents(
            {"user_id": user_id, "reviewed_at": {"$gte": now - timedelta(hours=24)}}
        ),
        accuracy_last_7d=round(week[0]["correct"] / week[0]["total"], 3) if week and week[0]["total"] else None,
        next_due_at=next_card["due_at"] if next_card else None,
        new_cards_per_day=settings.training_new_cards_per_day,
        new_left_today=new_left,
    )
