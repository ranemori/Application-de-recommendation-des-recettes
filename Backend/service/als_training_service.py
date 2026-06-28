"""
als_training_service.py — Reusable ALS training logic on real Postgres
interactions, shared between:
  - scripts/train_als_real.py (manual CLI run)
  - the periodic background scheduler started in main.py (automatic runs)

"""

import os
import sys
import pickle
import logging
import threading

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sqlalchemy.orm import Session

from db.models import Interaction, Recipe, User, Notification, NotificationType

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
RECOMMENDER_DIR = os.path.join(PROJECT_ROOT, "Recommender")
MAPPING_DIR = os.path.join(RECOMMENDER_DIR, "Dataset", "Mapping")
SPARSE_DIR = os.path.join(RECOMMENDER_DIR, "Dataset", "Sparse_matrices")
MODELS_DIR = os.path.join(RECOMMENDER_DIR, "models")

os.makedirs(MAPPING_DIR, exist_ok=True)
os.makedirs(SPARSE_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Confirmed-optimal hyperparameters from the project's own evaluation runs
ALS_FACTORS = 64
ALS_ITERATIONS = 15
ALS_REGULARIZATION = 0.05
ALS_ALPHA = 20
ALS_USE_BM25 = True

WEIGHT_VIEW = 1
WEIGHT_LIKE = 3
WEIGHT_SAVE = 4
WEIGHT_RATING = 5  # multiplied by the 1-5 rating value

MIN_USER_INTERACTIONS = 1     # a real user needs at least this many distinct recipes
MIN_RECIPE_INTERACTIONS = 1   # a recipe needs at least this many interacting users
MIN_NEW_INTERACTIONS_SINCE_LAST_TRAIN = 1  # retrain on (essentially) every new interaction


REAL_USER_ID_OFFSET = 1_000_000
SYNTHETIC_INTERACTIONS_CSV = os.path.join(RECOMMENDER_DIR, "Dataset", "Raw", "interactions.csv")

# Only one retrain at a time, even if triggered from two places at once
_train_lock = threading.Lock()
_last_trained_interaction_count = 0


def _load_synthetic_seed_df() -> pd.DataFrame:
    if not os.path.exists(SYNTHETIC_INTERACTIONS_CSV):
        return pd.DataFrame(columns=["user_id", "recipe_id", "viewed", "liked", "saved", "rating"])
    df = pd.read_csv(SYNTHETIC_INTERACTIONS_CSV)
    return df[["user_id", "recipe_id", "viewed", "liked", "saved", "rating"]].copy()


def _load_interactions_df(db: Session) -> pd.DataFrame:
    rows = db.query(Interaction).all()
    if not rows:
        return pd.DataFrame(columns=["user_id", "recipe_id", "type", "score"])

    records = [{
        "user_id": r.user_id,
        "recipe_id": r.recipe_id,
        "type": r.interaction_type.value if hasattr(r.interaction_type, "value") else r.interaction_type,
        "score": r.score or 0.0,
    } for r in rows]
    df = pd.DataFrame(records)

    def _agg(g):
        rating_scores = g.loc[g["type"] == "rating", "score"]
        rating_val = float(rating_scores.max()) if len(rating_scores) > 0 else 0.0
        if pd.isna(rating_val):
            rating_val = 0.0
        return pd.Series({
            "viewed": int((g["type"] == "view").any()),
            "liked": int(((g["type"] == "like") & (g["score"] > 0)).any()),
            "saved": int(((g["type"] == "save") & (g["score"] > 0)).any()),
            "rating": rating_val * 5,  # frontend sends score = stars/5
        })

    grouped = df.groupby(["user_id", "recipe_id"])
    out = grouped.apply(_agg, include_groups=False).reset_index()
    out["user_id"] = out["user_id"] + REAL_USER_ID_OFFSET
    return out


def _build_train_matrix(db: Session):
    real_df = _load_interactions_df(db)
    synthetic_df = _load_synthetic_seed_df()
    df = pd.concat([synthetic_df, real_df], ignore_index=True)
    if df.empty:
        return None, None, None

    for col in ["viewed", "liked", "saved", "rating"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(np.float64)

    df["score_raw"] = (
        df["viewed"] * WEIGHT_VIEW
        + df["liked"] * WEIGHT_LIKE
        + df["saved"] * WEIGHT_SAVE
        + df["rating"] * WEIGHT_RATING
    )
    df = df[df["score_raw"] > 0]
    if df.empty:
        return None, None, None

    is_real = df["user_id"] >= REAL_USER_ID_OFFSET
    user_counts = df.loc[is_real, "user_id"].value_counts()
    real_users_ok = user_counts[user_counts >= MIN_USER_INTERACTIONS].index
    df = df[~is_real | df["user_id"].isin(real_users_ok)]

    recipe_counts = df["recipe_id"].value_counts()
    df = df[df["recipe_id"].isin(recipe_counts[recipe_counts >= MIN_RECIPE_INTERACTIONS].index)]

    if df.empty or df["user_id"].nunique() < 2:
        return None, None, None

    df["score_log"] = np.log1p(df["score_raw"])
    if df["score_log"].nunique() > 1:
        scaler = MinMaxScaler(feature_range=(1, 10))
        df["score"] = scaler.fit_transform(df[["score_log"]]).round(4)
    else:
        df["score"] = 5.0

    user_enc = LabelEncoder()
    df["user_idx"] = user_enc.fit_transform(df["user_id"])

    all_recipe_ids = sorted(r.id for r in db.query(Recipe.id).all())
    item_enc = LabelEncoder()
    item_enc.fit(all_recipe_ids)
    df["item_idx"] = item_enc.transform(df["recipe_id"])

    n_users = len(user_enc.classes_)
    n_items = len(item_enc.classes_)

    train_matrix = sp.coo_matrix(
        (df["score"].astype(np.float32), (df["user_idx"], df["item_idx"])),
        shape=(n_users, n_items),
    ).tocsr()

    return train_matrix, user_enc, item_enc


def _update_db_indices(db: Session, user_enc, item_enc):
    all_ids = [int(u) for u in user_enc.classes_]
    real_ids = [uid for uid in all_ids if uid >= REAL_USER_ID_OFFSET]
    real_db_ids = [uid - REAL_USER_ID_OFFSET for uid in real_ids]

    users = db.query(User).filter(User.id.in_(real_db_ids)).all()
    by_id = {u.id: u for u in users}
    for offset_uid, real_uid in zip(real_ids, real_db_ids):
        u = by_id.get(real_uid)
        if u is None:
            continue
        u.als_user_idx = int(user_enc.transform([offset_uid])[0])

    recipe_ids = [int(r) for r in item_enc.classes_]
    recipes = db.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()
    for r in recipes:
        r.als_item_idx = int(item_enc.transform([r.id])[0])

    db.commit()
    return len(users), len(recipes)


def _notify_users_of_new_recommendations(db: Session, user_enc):
    """After a successful retrain, let each retrained user know their
    recommendations have been refreshed. Skips a user if they already have
    an unread notification of this type, so we don't spam them every time
    a retrain happens to fire"""
    user_ids = [int(u) - REAL_USER_ID_OFFSET for u in user_enc.classes_ if int(u) >= REAL_USER_ID_OFFSET]
    for uid in user_ids:
        already_unread = (
            db.query(Notification)
            .filter(
                Notification.user_id == uid,
                Notification.type == NotificationType.recommendation,
                Notification.is_read == False,
            )
            .first()
        )
        if already_unread:
            continue
        db.add(Notification(
            user_id=uid,
            type=NotificationType.recommendation,
            title="Nouvelles recommandations disponibles",
            message="Vous trouvez ce que vous plaise.",
            link="/recommendations",
        ))
    db.commit()


def retrain_als(db: Session, force: bool = False) -> dict:
    """
    Train ALS on real interactions and refresh the on-disk artefacts +
    DB index columns. Returns a small status dict instead of raising, so
    callers (scheduler, CLI, future admin endpoint) can decide what to do
    """
    global _last_trained_interaction_count

    if not _train_lock.acquire(blocking=False):
        return {"status": "skipped", "reason": "a retrain is already in progress"}

    try:
        total_interactions = db.query(Interaction).count()
        if not force and (total_interactions - _last_trained_interaction_count) < MIN_NEW_INTERACTIONS_SINCE_LAST_TRAIN:
            return {
                "status": "skipped",
                "reason": "not enough new interactions since last training run",
                "total_interactions": total_interactions,
            }

        train_matrix, user_enc, item_enc = _build_train_matrix(db)
        if train_matrix is None:
            return {
                "status": "skipped",
                "reason": (
                    f"not enough interaction data yet (need >= {MIN_USER_INTERACTIONS} "
                    "interacted recipe(s) from at least 1 real user; the synthetic "
                    "seed dataset provides the rest of the density)"
                ),
            }

        from Recommender.model_als import ALSRecipeRecommender

        recommender = ALSRecipeRecommender(
            factors=ALS_FACTORS,
            iterations=ALS_ITERATIONS,
            regularization=ALS_REGULARIZATION,
            alpha=ALS_ALPHA,
            use_bm25=ALS_USE_BM25,
        )
        weighted_matrix = recommender.preprocess_matrix(train_matrix)
        recommender.fit(weighted_matrix)

        recommender.save_model(os.path.join(MODELS_DIR, "als_model.pkl"))
        sp.save_npz(os.path.join(SPARSE_DIR, "train_matrix.npz"), train_matrix)
        with open(os.path.join(MAPPING_DIR, "user_encoder.pkl"), "wb") as f:
            pickle.dump(user_enc, f)
        with open(os.path.join(MAPPING_DIR, "item_encoder.pkl"), "wb") as f:
            pickle.dump(item_enc, f)

        n_users, n_recipes = _update_db_indices(db, user_enc, item_enc)
        _last_trained_interaction_count = total_interactions

        _notify_users_of_new_recommendations(db, user_enc)

        # Hot-reload the inference service so the new model is used immediately, with no server restart needed
        from service.als_service import get_als_service
        get_als_service().reload()

        logger.info(
            f"ALS retrained: {train_matrix.shape[0]} users x {train_matrix.shape[1]} "
            f"recipes, {train_matrix.nnz} interactions"
        )
        return {
            "status": "trained",
            "users": n_users,
            "recipes": n_recipes,
            "interactions_used": int(train_matrix.nnz),
        }
    except Exception as exc:
        logger.error(f"ALS retrain failed: {exc}", exc_info=True)
        return {"status": "error", "reason": str(exc)}
    finally:
        _train_lock.release()