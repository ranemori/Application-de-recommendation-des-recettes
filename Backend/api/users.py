from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import os, uuid

from db.database import get_db
from db.models import User, Ingredient, FridgeItem, Interaction, Recipe, InteractionType
from db.schemas import (
    UserPublic, UserUpdate, OnboardingRequest,
    FridgeOut, FridgeUpdate, IngredientOut, RecipeCard
)

from core.security import require_user


router = APIRouter()

AVATAR_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "avatars")
ALLOWED_AVATAR_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.get("/me", response_model=UserPublic)
def get_profile(
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == int(payload["sub"])
    ).first()

    return user


@router.patch("/me", response_model=UserPublic)
def update_profile(
    data: UserUpdate,
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(404, "User not found")

    update_data = data.model_dump(exclude_unset=True, exclude={"allergies"})
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.post("/me/deactivate")
def deactivate_account(
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    """Deactivates the current user's account.

    This is a soft deactivation (is_active=False), not a hard delete —
    the account and its data (recipes, comments, interactions) are kept
    so the model and history stay intact, and an admin could reactivate
    it later if needed. The frontend logs the user out immediately after
    a successful call, and login is rejected for deactivated accounts.
    """
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = False
    db.commit()
    return {"message": "Account deactivated"}


@router.post("/me/avatar", response_model=UserPublic)
def upload_avatar(
    file: UploadFile = File(...),
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AVATAR_EXT:
        raise HTTPException(400, "Unsupported image format")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(404, "User not found")

    content_type = file.content_type or "image/jpeg"
    user.avatar_data = file.file.read()
    user.avatar_mime = content_type
    # Served from the DB-backed route below — no file on disk involved,
    # so it survives container restarts / redeploys / a deleted local file.
    user.avatar_url = f"/api/v1/users/{user.id}/avatar"
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/avatar")
def get_avatar(user_id: int, db: Session = Depends(get_db)):
    """Serves the avatar straight from the database (see upload_avatar)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.avatar_data:
        raise HTTPException(404, "No avatar")
    return Response(content=user.avatar_data, media_type=user.avatar_mime or "image/jpeg")


@router.post("/onboarding", response_model=UserPublic)
def submit_onboarding(
    data: OnboardingRequest,
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    """First-login quiz: dietary regime + favorite cuisines."""
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.regime_alimentaire = data.regime_alimentaire
    user.preferences_cuisine = data.preferences_cuisine
    if data.region:
        user.region = data.region
    if data.pays:
        user.pays = data.pays
    user.onboarding_done = True

    db.commit()
    db.refresh(user)
    return user


# ─── Saved recipes ───────────────────────────────────────────────────────────

@router.get("/me/saved", response_model=List[RecipeCard])
def get_saved_recipes(
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    """Recipes the user currently has saved.

    Each click on 'Sauvegarder' inserts a new Interaction row (save toggle
    history) rather than updating a single flag, so 'currently saved' means:
    for each recipe, look at the MOST RECENT 'save' interaction and check
    whether its score is 1 (saved) rather than 0 (un-saved).
    """
    user_id = int(payload["sub"])

    latest_save_subq = (
        db.query(
            Interaction.recipe_id,
            func.max(Interaction.created_at).label("latest_at"),
        )
        .filter(
            Interaction.user_id == user_id,
            Interaction.interaction_type == InteractionType.save,
        )
        .group_by(Interaction.recipe_id)
        .subquery()
    )

    latest_saves = (
        db.query(Interaction)
        .join(
            latest_save_subq,
            (Interaction.recipe_id == latest_save_subq.c.recipe_id)
            & (Interaction.created_at == latest_save_subq.c.latest_at),
        )
        .filter(
            Interaction.user_id == user_id,
            Interaction.interaction_type == InteractionType.save,
        )
        .all()
    )

    saved_recipe_ids = [i.recipe_id for i in latest_saves if (i.score or 0) > 0]
    if not saved_recipe_ids:
        return []

    recipes = db.query(Recipe).filter(Recipe.id.in_(saved_recipe_ids)).all()
    # Keep most-recently-saved first.
    order = {rid: idx for idx, rid in enumerate(saved_recipe_ids)}
    recipes.sort(key=lambda r: order.get(r.id, 0))
    return recipes


# ─── Fridge ────────────────────────────────────────────────────────────────

@router.get("/fridge", response_model=FridgeOut)
def get_fridge(
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    items = (
        db.query(Ingredient)
        .join(FridgeItem, FridgeItem.ingredient_id == Ingredient.id)
        .filter(FridgeItem.user_id == int(payload["sub"]))
        .all()
    )
    return {"ingredients": items}


@router.put("/fridge", response_model=FridgeOut)
def set_fridge(
    data: FridgeUpdate,
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    """Replace the whole fridge content with the given ingredient ids."""
    user_id = int(payload["sub"])

    db.query(FridgeItem).filter(FridgeItem.user_id == user_id).delete()

    for ing_id in set(data.ingredient_ids):
        db.add(FridgeItem(user_id=user_id, ingredient_id=ing_id))

    db.commit()

    items = (
        db.query(Ingredient)
        .join(FridgeItem, FridgeItem.ingredient_id == Ingredient.id)
        .filter(FridgeItem.user_id == user_id)
        .all()
    )
    return {"ingredients": items}


@router.delete("/fridge/{ingredient_id}", response_model=FridgeOut)
def remove_fridge_item(
    ingredient_id: int,
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    user_id = int(payload["sub"])
    db.query(FridgeItem).filter(
        FridgeItem.user_id == user_id,
        FridgeItem.ingredient_id == ingredient_id
    ).delete()
    db.commit()

    items = (
        db.query(Ingredient)
        .join(FridgeItem, FridgeItem.ingredient_id == Ingredient.id)
        .filter(FridgeItem.user_id == user_id)
        .all()
    )
    return {"ingredients": items}