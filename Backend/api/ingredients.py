from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from db.database import get_db
from db.models import Ingredient
from db.schemas import IngredientOut

router = APIRouter()


@router.get("/", response_model=list[IngredientOut])
def list_ingredients(
    search: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Ingredient)
    if search:
        query = query.filter(Ingredient.name.ilike(f"%{search}%"))
    return query.order_by(Ingredient.name.asc()).limit(limit).all()