"""
Application configuration
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "A Ton Gout"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database — PostgreSQL
    DATABASE_URL: str = "postgresql://postgres:TON_MOTDEPASSE@localhost:5432/recommender_db"

    # Security
    SECRET_KEY: str = "TON_MOTDEPASSE"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24          # 24h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]

    # Recommender paths
    RECOMMENDER_BASE_DIR: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "Recommender"
    )
    ALS_MODEL_PATH: str = ""         
    USER_ENCODER_PATH: str = ""
    ITEM_ENCODER_PATH: str = ""
    TRAIN_MATRIX_PATH: str = ""
    RAW_RECIPES_PATH: str = ""
    RAW_USERS_PATH: str = ""

    # ALS auto-retraining
    ALS_RETRAIN_INTERVAL_MINUTES: int = 10

    # Pagination
    DEFAULT_PAGE_SIZE: int = 12
    MAX_PAGE_SIZE: int = 50

    # Upload
    UPLOAD_DIR: str = "static/uploads"
    MAX_UPLOAD_SIZE_MB: int = 5

    def model_post_init(self, __context):
        base = self.RECOMMENDER_BASE_DIR
        if not self.ALS_MODEL_PATH:
            object.__setattr__(self, "ALS_MODEL_PATH", os.path.join(base, "models", "als_model.pkl"))
        if not self.USER_ENCODER_PATH:
            object.__setattr__(self, "USER_ENCODER_PATH", os.path.join(base, "Dataset", "Mapping", "user_encoder.pkl"))
        if not self.ITEM_ENCODER_PATH:
            object.__setattr__(self, "ITEM_ENCODER_PATH", os.path.join(base, "Dataset", "Mapping", "item_encoder.pkl"))
        if not self.TRAIN_MATRIX_PATH:
            object.__setattr__(self, "TRAIN_MATRIX_PATH", os.path.join(base, "Dataset", "Sparse_matrices", "train_matrix.npz"))
        if not self.RAW_RECIPES_PATH:
            object.__setattr__(self, "RAW_RECIPES_PATH", os.path.join(base, "Dataset", "Raw", "raw_recipes.csv"))
        if not self.RAW_USERS_PATH:
            object.__setattr__(self, "RAW_USERS_PATH", os.path.join(base, "Dataset", "Raw", "users.csv"))

    class Config:
        env_file = ".env"
        env_file_encoding = "cp1252"


settings = Settings()