from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session


from db.database import get_db
from db.models import User, FridgeItem

from service.recommendation_service import RecommendationService
from db.schemas import FridgeRecommendRequest

from core.security import require_user


router=APIRouter()



@router.get("/me")
def my_recommendations(
    n:int=12,
    payload=Depends(require_user),
    db:Session=Depends(get_db)
):


    user=db.query(User).filter(
        User.id==int(payload["sub"])
    ).first()



    service=RecommendationService(db)


    return service.for_user(
        user,
        n
    )


@router.post("/fridge")
def fridge_recommendations(
    data: FridgeRecommendRequest,
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    """Recommend recipes that can be made with the given ingredients only."""
    service = RecommendationService(db)
    return service.fridge_match(
        ingredient_ids=data.ingredient_ids,
        n=24,
        strict=data.strict,
    )


@router.get("/my-fridge")
def my_fridge_recommendations(
    strict: bool = True,
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    """Same as /fridge but uses the ingredients already saved in the user's fridge."""
    user_id = int(payload["sub"])
    ingredient_ids = [
        row.ingredient_id
        for row in db.query(FridgeItem).filter(FridgeItem.user_id == user_id).all()
    ]
    service = RecommendationService(db)
    return service.fridge_match(ingredient_ids=ingredient_ids, n=24, strict=strict)


@router.get("/similar/{recipe_id}")
def similar_recipes(
    recipe_id: int,
    n: int = 6,
    db: Session = Depends(get_db)
):
    service = RecommendationService(db)
    return service.similar_to(recipe_id, n=n)