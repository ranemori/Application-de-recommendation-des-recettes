from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.database import get_db
from db.models import User, Recipe, Interaction, RecipeIngredient, Ingredient, InteractionType
from db.schemas import (
    DashboardStats, UserAdmin, RecipeCard, RecipeDetail,
    RecipeCreate, RecipeUpdate, UserInteractionOut
)
from core.security import require_admin

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    payload=Depends(require_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(func.count(User.id)).scalar()
    total_recipes = db.query(func.count(Recipe.id)).scalar()
    total_interactions = db.query(func.count(Interaction.id)).scalar()

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    active_users = (
        db.query(func.count(func.distinct(Interaction.user_id)))
        .filter(Interaction.created_at >= cutoff)
        .scalar()
    )

    top_recipes = (
        db.query(Recipe)
        .order_by(Recipe.note_moyenne.desc())
        .limit(5)
        .all()
    )

    recent_users = (
        db.query(User)
        .order_by(User.created_at.desc())
        .limit(5)
        .all()
    )

    return DashboardStats(
        total_users=total_users or 0,
        active_users_last_30d=active_users or 0,
        total_recipes=total_recipes or 0,
        total_interactions=total_interactions or 0,
        top_recipes=top_recipes,
        recent_users=recent_users,
    )


# ─── Users ─────────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserAdmin])
def list_users(
    payload=Depends(require_admin),
    db: Session = Depends(get_db)
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/users/{user_id}/interactions", response_model=list[UserInteractionOut])
def list_user_interactions(
    user_id: int,
    interaction_type: str | None = None,
    limit: int = 200,
    payload=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activity feed for one user — what they've viewed/liked/saved/rated,
    most recent first. Optional `interaction_type` filters to just one
    kind (view/like/save/rating)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    query = db.query(Interaction).filter(Interaction.user_id == user_id)
    if interaction_type:
        try:
            type_enum = InteractionType(interaction_type)
        except ValueError:
            raise HTTPException(400, f"Invalid interaction_type: {interaction_type}")
        query = query.filter(Interaction.interaction_type == type_enum)

    return (
        query.order_by(Interaction.created_at.desc())
        .limit(limit)
        .all()
    )


@router.patch("/users/{user_id}/toggle-active", response_model=UserAdmin)
def toggle_user_active(
    user_id: int,
    payload=Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    payload=Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    db.delete(user)
    db.commit()
    return {"message": "user deleted"}


# ─── Recipes ───────────────────────────────────────────────────────────────

@router.get("/recipes", response_model=list[RecipeCard])
def list_all_recipes(
    payload=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Includes unpublished recipes, unlike the public endpoint."""
    return db.query(Recipe).order_by(Recipe.created_at.desc()).all()


@router.post("/recipes", response_model=RecipeDetail)
def create_recipe(
    data: RecipeCreate,
    payload=Depends(require_admin),
    db: Session = Depends(get_db)
):
    recipe = Recipe(
        title=data.title,
        description=data.description,
        instructions=data.instructions,
        cuisine=data.cuisine,
        regime=data.regime,
        difficulte=data.difficulte,
        temps_preparation=data.temps_preparation,
        niveau_calorie=data.niveau_calorie,
        tags=data.tags,
        image_url=data.image_url,
        n_ingredients=len(data.ingredients),
        created_by=int(payload["sub"]),
    )
    db.add(recipe)
    db.flush()

    for ing in data.ingredients:
        db.add(RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ing.ingredient_id,
            quantite=ing.quantite,
            unite=ing.unite,
        ))

    db.commit()
    db.refresh(recipe)
    return recipe


@router.patch("/recipes/{recipe_id}", response_model=RecipeDetail)
def update_recipe(
    recipe_id: int,
    data: RecipeUpdate,
    payload=Depends(require_admin),
    db: Session = Depends(get_db)
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    update_data = data.model_dump(exclude_unset=True)
    # ingredients aren't a plain column on Recipe — they live in a separate
    # RecipeIngredient table and need their own replace logic below.
    new_ingredients = update_data.pop("ingredients", None)

    for field, value in update_data.items():
        setattr(recipe, field, value)

    if new_ingredients is not None:
        db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).delete()
        for ing in new_ingredients:
            db.add(RecipeIngredient(
                recipe_id=recipe_id,
                ingredient_id=ing["ingredient_id"],
                quantite=ing.get("quantite"),
                unite=ing.get("unite"),
            ))
        recipe.n_ingredients = len(new_ingredients)

    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/recipes/{recipe_id}")
def delete_recipe(
    recipe_id: int,
    payload=Depends(require_admin),
    db: Session = Depends(get_db)
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "Recipe not found")
    db.delete(recipe)
    db.commit()
    return {"message": "recipe deleted"}


@router.get("/ingredients-all")
def list_all_ingredients_admin(
    payload=Depends(require_admin),
    db: Session = Depends(get_db)
):
    return db.query(Ingredient).order_by(Ingredient.name.asc()).all()