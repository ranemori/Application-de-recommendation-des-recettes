from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Recipe
from db.schemas import RecipeCard, RecipeDetail


router=APIRouter()



@router.get("/",
response_model=list[RecipeCard])
def all_recipes(
    db:Session=Depends(get_db)
):

    return db.query(Recipe)\
        .filter(
            Recipe.is_published==True
        ).all()



@router.get("/{recipe_id}",
response_model=RecipeDetail)
def recipe_detail(
    recipe_id:int,
    db:Session=Depends(get_db)
):

    return db.query(Recipe)\
        .filter(
            Recipe.id==recipe_id
        ).first()