from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.database import get_db, SessionLocal
from db.models import Interaction, InteractionType, Recipe

from db.schemas import InteractionCreate

from core.security import require_user
from service.als_training_service import retrain_als


router = APIRouter()


def _recompute_recipe_rating(db: Session, recipe_id: int):
    latest_per_user = (
        db.query(Interaction.user_id, func.max(Interaction.created_at).label("latest_at"))
        .filter(
            Interaction.recipe_id == recipe_id,
            Interaction.interaction_type == InteractionType.rating,
        )
        .group_by(Interaction.user_id)
        .subquery()
    )
    latest_ratings = (
        db.query(Interaction)
        .join(
            latest_per_user,
            (Interaction.user_id == latest_per_user.c.user_id)
            & (Interaction.created_at == latest_per_user.c.latest_at),
        )
        .filter(
            Interaction.recipe_id == recipe_id,
            Interaction.interaction_type == InteractionType.rating,
        )
        .all()
    )

    # Frontend sends score as star/5 (0.2-1.0) — convert back to a 1-5 scale.
    real_scores = [r.score * 5 for r in latest_ratings if r.score is not None]

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return

    seed_n = recipe.seed_nb_avis or 0
    seed_avg = recipe.seed_note_moyenne or 0.0

    total_n = seed_n + len(real_scores)
    if total_n == 0:
        return 

    total_score = seed_n * seed_avg + sum(real_scores)
    recipe.nb_avis = total_n
    recipe.note_moyenne = round(total_score / total_n, 2)
    db.commit()


def _retrain_in_background():
    db = SessionLocal()
    try:
        result = retrain_als(db, force=False)
        logger_msg = result.get("status")
        print(f"[auto-retrain] {logger_msg}: {result}")
    finally:
        db.close()


@router.post("/")
def add_interaction(
    data: InteractionCreate,
    background_tasks: BackgroundTasks,
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):

    interaction = Interaction(
        user_id=int(payload["sub"]),
        recipe_id=data.recipe_id,
        interaction_type=data.interaction_type,
        score=data.score,
        metadata_=data.metadata
    )

    db.add(interaction)
    db.commit()

    if interaction.interaction_type == InteractionType.rating:
        _recompute_recipe_rating(db, data.recipe_id)

    # Try to keep the ALS model fresh automatically 

    background_tasks.add_task(_retrain_in_background)

    return {
        "message": "interaction saved"
    }