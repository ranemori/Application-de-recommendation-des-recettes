"""
Pydantic schemas — request bodies, response models, and pagination wrappers
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any, Generic, TypeVar
from datetime import datetime
from enum import Enum

T = TypeVar("T")


# ─── Pagination ───────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


# ─── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def no_spaces(cls, v):
        if " " in v:
            raise ValueError("Username cannot contain spaces")
        return v.lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserPublic"


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── Users ────────────────────────────────────────────────────────────────────

class OnboardingRequest(BaseModel):
    regime_alimentaire: str
    preferences_cuisine: List[str]
    region: Optional[str] = None
    pays: Optional[str] = None


class UserPublic(BaseModel):
    id: int
    username: str
    email: str
    role: str
    avatar_url: Optional[str] = None
    region: Optional[str] = None
    pays: Optional[str] = None
    regime_alimentaire: Optional[str] = None
    preferences_cuisine: Optional[List[str]] = None
    onboarding_done: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserAdmin(UserPublic):
    is_active: bool
    last_login: Optional[datetime] = None
    region: Optional[str] = None
    pays: Optional[str] = None


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    avatar_url: Optional[str] = None
    region: Optional[str] = None
    pays: Optional[str] = None
    regime_alimentaire: Optional[str] = None
    preferences_cuisine: Optional[List[str]] = None
    allergies: Optional[List[str]] = None


# ─── Ingredients ──────────────────────────────────────────────────────────────

class IngredientBase(BaseModel):
    name: str
    categorie: Optional[str] = None
    unite_standard: Optional[str] = None
    allergen: Optional[str] = None


class IngredientCreate(IngredientBase):
    pass


class IngredientOut(IngredientBase):
    id: int
    model_config = {"from_attributes": True}


# ─── Recipes ──────────────────────────────────────────────────────────────────

class RecipeIngredientIn(BaseModel):
    ingredient_id: int
    quantite: Optional[float] = None
    unite: Optional[str] = None


class RecipeCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    cuisine: Optional[str] = None
    regime: Optional[str] = None
    difficulte: Optional[str] = "moyen"
    temps_preparation: Optional[int] = None
    niveau_calorie: Optional[int] = None
    tags: List[str] = []
    image_url: Optional[str] = None
    ingredients: List[RecipeIngredientIn] = []


class RecipeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    cuisine: Optional[str] = None
    regime: Optional[str] = None
    difficulte: Optional[str] = None
    temps_preparation: Optional[int] = None
    niveau_calorie: Optional[int] = None
    tags: Optional[List[str]] = None
    image_url: Optional[str] = None
    is_published: Optional[bool] = None
    ingredients: Optional[List[RecipeIngredientIn]] = None


class RecipeIngredientOut(BaseModel):
    ingredient: IngredientOut
    quantite: Optional[float] = None
    unite: Optional[str] = None
    model_config = {"from_attributes": True}


class RecipeCard(BaseModel):
    """Lightweight card used in lists and recommendations."""
    id: int
    title: str
    description: Optional[str] = None
    cuisine: Optional[str] = None
    regime: Optional[str] = None
    difficulte: Optional[str] = None
    temps_preparation: Optional[int] = None
    niveau_calorie: Optional[int] = None
    image_url: Optional[str] = None
    note_moyenne: float = 0.0
    nb_avis: int = 0
    tags: List[str] = []
    model_config = {"from_attributes": True}


class RecipeDetail(RecipeCard):
    instructions: Optional[str] = None
    n_ingredients: Optional[int] = None
    ingredients: List[RecipeIngredientOut] = []
    is_saved: Optional[bool] = None
    user_rating: Optional[float] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Interactions ─────────────────────────────────────────────────────────────

class InteractionCreate(BaseModel):
    recipe_id: int
    interaction_type: str  
    score: Optional[float] = None
    metadata: dict = {}


class RatingCreate(BaseModel):
    recipe_id: int
    score: float = Field(..., ge=1, le=5)


class CommentCreate(BaseModel):
    recipe_id: int
    content: str = Field(..., min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    content: str
    user: UserPublic
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Fridge ───────────────────────────────────────────────────────────────────

class FridgeUpdate(BaseModel):
    ingredient_ids: List[int]


class FridgeOut(BaseModel):
    ingredients: List[IngredientOut]


# ─── Recommendations ──────────────────────────────────────────────────────────

class RecommendationOut(BaseModel):
    recipe: RecipeCard
    score: Optional[float] = None
    reason: Optional[str] = None   # "ALS" | "content" | "popularity" | "fridge"


class FridgeRecommendRequest(BaseModel):
    ingredient_ids: List[int]
    strict: bool = True   


# ─── Admin Stats ──────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_users: int
    active_users_last_30d: int
    total_recipes: int
    total_interactions: int
    top_recipes: List[RecipeCard]
    recent_users: List[UserAdmin]


# ─── Password management ───────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# ─── Notifications ──────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    message: Optional[str] = None
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Admin: per-user activity ───────────────────────────────────────────────────

class UserInteractionOut(BaseModel):
    id: int
    interaction_type: str
    score: Optional[float] = None
    created_at: datetime
    recipe: RecipeCard

    model_config = {"from_attributes": True}