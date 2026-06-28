"""
SQLAlchemy ORM models
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, Enum, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from db.database import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class DietaryRegime(str, enum.Enum):
    normal = "normal"
    vegetarien = "végétarien"
    sans_gluten = "sans gluten"
    vegetalien = "végétalien"


class Difficulty(str, enum.Enum):
    facile = "facile"
    moyen = "moyen"
    difficile = "difficile"


class InteractionType(str, enum.Enum):
    view = "view"
    like = "like"
    save = "save"
    rating = "rating"


# ─── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True)

    # Profile
    avatar_url = Column(String(500), nullable=True)
    region = Column(String(100), nullable=True)
    pays = Column(String(100), nullable=True)

    # Preferences (collected at onboarding)
    regime_alimentaire = Column(Enum(DietaryRegime), default=DietaryRegime.normal)
    preferences_cuisine = Column(JSON, default=list)
    onboarding_done = Column(Boolean, default=False)

    # ALS internal index — ONLY set when this exact user was included in an actual ALS training run
    als_user_idx = Column(Integer, nullable=True, index=True)

    # Password reset
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    interactions = relationship("Interaction", back_populates="user", cascade="all, delete-orphan")
    saves = relationship("Save", back_populates="user", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="user", cascade="all, delete-orphan")
    views = relationship("View", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    fridge_items = relationship("FridgeItem", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


# ─── Recipes ──────────────────────────────────────────────────────────────────

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    cuisine = Column(String(100), nullable=True, index=True)
    regime = Column(String(100), nullable=True, index=True)
    difficulte = Column(Enum(Difficulty), default=Difficulty.moyen)
    temps_preparation = Column(Integer, nullable=True)   # minutes
    niveau_calorie = Column(Integer, nullable=True)
    n_ingredients = Column(Integer, nullable=True)
    n_instructions = Column(Integer, nullable=True)
    image_url = Column(String(500), nullable=True)
    tags = Column(JSON, default=list)
    is_published = Column(Boolean, default=True)

    # Denormalized rating cache
    note_moyenne = Column(Float, default=0.0)
    nb_avis = Column(Integer, default=0)
    seed_note_moyenne = Column(Float, default=0.0)
    seed_nb_avis = Column(Integer, default=0)

    # ALS internal index
    als_item_idx = Column(Integer, nullable=True, index=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="recipe")
    saves = relationship("Save", back_populates="recipe")
    ratings = relationship("Rating", back_populates="recipe")
    views = relationship("View", back_populates="recipe")
    comments = relationship("Comment", back_populates="recipe", cascade="all, delete-orphan")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    categorie = Column(String(100), nullable=True)
    unite_standard = Column(String(50), nullable=True)
    allergen = Column(String(200), nullable=True)

    recipe_links = relationship("RecipeIngredient", back_populates="ingredient")
    fridge_items = relationship("FridgeItem", back_populates="ingredient")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantite = Column(Float, nullable=True)
    unite = Column(String(50), nullable=True)

    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_links")

    __table_args__ = (UniqueConstraint("recipe_id", "ingredient_id"),)


# ─── User Fridge ──────────────────────────────────────────────────────────────

class FridgeItem(Base):
    __tablename__ = "fridge_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="fridge_items")
    ingredient = relationship("Ingredient", back_populates="fridge_items")

    __table_args__ = (UniqueConstraint("user_id", "ingredient_id"),)


# ─── Interactions (for ALS training) ──────────────────────────────────────────

class Interaction(Base):
    """Tracks every user-recipe touchpoint. Drives ALS retraining."""

    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    interaction_type = Column(Enum(InteractionType), nullable=False)
    score = Column(Float, nullable=True)   # computed implicit score fed to ALS
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="interactions")
    recipe = relationship("Recipe", back_populates="interactions")

    __table_args__ = (
        Index("ix_interactions_user_recipe", "user_id", "recipe_id"),
    )


class Save(Base):
    __tablename__ = "saves"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="saves")
    recipe = relationship("Recipe", back_populates="saves")

    __table_args__ = (UniqueConstraint("user_id", "recipe_id"),)


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    score = Column(Float, nullable=False)   # 1–5
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="ratings")
    recipe = relationship("Recipe", back_populates="ratings")

    __table_args__ = (UniqueConstraint("user_id", "recipe_id"),)


class View(Base):
    __tablename__ = "views"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="views")
    recipe = relationship("Recipe", back_populates="views")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="comments")
    recipe = relationship("Recipe", back_populates="comments")


class NotificationType(str, enum.Enum):
    recommendation = "recommendation"
    comment = "comment"
    system = "system"


class Notification(Base):

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(NotificationType), default=NotificationType.system)
    title = Column(String(255), nullable=False)
    message = Column(String(500), nullable=True)
    link = Column(String(255), nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")