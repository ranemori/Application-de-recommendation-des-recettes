from fastapi import APIRouter

from api import auth
from api import users
from api import recipes
from api import interactions
from api import recommendations
from api import ingredients
from api import admin
from api import comments
from api import notifications


api_router = APIRouter()


api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    recipes.router,
    prefix="/recipes",
    tags=["Recipes"]
)

api_router.include_router(
    interactions.router,
    prefix="/interactions",
    tags=["Interactions"]
)

api_router.include_router(
    recommendations.router,
    prefix="/recommendations",
    tags=["Recommendation"]
)

api_router.include_router(
    ingredients.router,
    prefix="/ingredients",
    tags=["Ingredients"]
)

api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"]
)

api_router.include_router(
    comments.router,
    prefix="/comments",
    tags=["Comments"]
)

api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["Notifications"]
)