"""
train_als_real.py — Trains the ALS model on REAL interactions stored in
Postgres (not the synthetic CSV dataset), and re-maps every user/recipe to
fresh, consistent ALS matrix indices

Run from the Backend/ directory:

    python scripts/train_als_real.py
"""

import os
import sys
import pickle

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from db.database import SessionLocal 
from db.models import Interaction, Recipe, User 

PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
RECOMMENDER_DIR = os.path.join(PROJECT_ROOT, "Recommender")
MAPPING_DIR = os.path.join(RECOMMENDER_DIR, "Dataset", "Mapping")
SPARSE_DIR = os.path.join(RECOMMENDER_DIR, "Dataset", "Sparse_matrices")
MODELS_DIR = os.path.join(RECOMMENDER_DIR, "models")

os.makedirs(MAPPING_DIR, exist_ok=True)
os.makedirs(SPARSE_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# Make the Recommender package importable, then reuse the exact same ALS class/hyperparameters as the rest of the project
sys.path.insert(0, PROJECT_ROOT)
from Recommender.model_als import ALSRecipeRecommender

# Confirmed-optimal hyperparameters from the project's own evaluation runs
ALS_FACTORS = 64
ALS_ITERATIONS = 15
ALS_REGULARIZATION = 0.05
ALS_ALPHA = 20
ALS_USE_BM25 = True

# Same composite-score convention used by Recommender/prepare_data.py on the synthetic dataset
WEIGHT_VIEW = 1
WEIGHT_LIKE = 3
WEIGHT_SAVE = 4
WEIGHT_RATING = 5 # multiplied by the 1-5 rating value

MIN_USER_INTERACTIONS = 1 # a real user needs at least this many interacted recipes
MIN_RECIPE_INTERACTIONS = 1 # a recipe needs at least this many interacting users

REAL_USER_ID_OFFSET = 1_000_000

SYNTHETIC_INTERACTIONS_CSV = os.path.join(RECOMMENDER_DIR, "Dataset", "Raw", "interactions.csv")


def load_synthetic_seed_df():
    """The 100-user synthetic dataset used for the offline evaluation
    (Recall@10/NDCG@10 in the report) doubles as a 'seed' here: training
    real users alongside it gives ALS enough density to find meaningful
    taste neighbors even when a real user only has 1-2 interactions so
    far, instead of needing dozens of real users before anything works"""
    if not os.path.exists(SYNTHETIC_INTERACTIONS_CSV):
        return pd.DataFrame(columns=["user_id", "recipe_id", "viewed", "liked", "saved", "rating"])

    df = pd.read_csv(SYNTHETIC_INTERACTIONS_CSV)
    return df[["user_id", "recipe_id", "viewed", "liked", "saved", "rating"]].copy()


def load_interactions_df(db):
    rows = db.query(Interaction).all()
    if not rows:
        return pd.DataFrame(columns=["user_id", "recipe_id", "viewed", "liked", "saved", "rating"])

    records = []
    for r in rows:
        records.append({
            "user_id": r.user_id,
            "recipe_id": r.recipe_id,
            "type": r.interaction_type.value if hasattr(r.interaction_type, "value") else r.interaction_type,
            "score": r.score or 0.0,
        })
    df = pd.DataFrame(records)

    # Pivot interaction events into one row per (user_id, recipe_id) with the same viewed/liked/saved/rating columns as the synthetic dataset
    def _agg(g):
        rating_scores = g.loc[g["type"] == "rating", "score"]
        rating_val = float(rating_scores.max()) if len(rating_scores) > 0 else 0.0
        if pd.isna(rating_val):
            rating_val = 0.0
        return pd.Series({
            "viewed": int((g["type"] == "view").any()),
            "liked": int(((g["type"] == "like") & (g["score"] > 0)).any()),
            "saved": int(((g["type"] == "save") & (g["score"] > 0)).any()),
            # frontend sends rating as score = stars/5 -> convert back to 1-5
            "rating": rating_val * 5,
        })

    grouped = df.groupby(["user_id", "recipe_id"])
    out = grouped.apply(_agg, include_groups=False).reset_index()

    out["user_id"] = out["user_id"] + REAL_USER_ID_OFFSET
    return out


def build_train_matrix(db):
    real_df = load_interactions_df(db)
    synthetic_df = load_synthetic_seed_df()

    df = pd.concat([synthetic_df, real_df], ignore_index=True)
    if df.empty:
        return None, None, None, None

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
        return None, None, None, None

    is_real = df["user_id"] >= REAL_USER_ID_OFFSET
    user_counts = df.loc[is_real, "user_id"].value_counts()
    real_users_ok = user_counts[user_counts >= MIN_USER_INTERACTIONS].index
    df = df[~is_real | df["user_id"].isin(real_users_ok)]

    recipe_counts = df["recipe_id"].value_counts()
    df = df[df["recipe_id"].isin(recipe_counts[recipe_counts >= MIN_RECIPE_INTERACTIONS].index)]

    if df.empty or df["user_id"].nunique() < 2:
        return None, None, None, None

    # Log-transform + scale to [1, 10], same as the original pipeline
    df["score_log"] = np.log1p(df["score_raw"])
    if df["score_log"].nunique() > 1:
        scaler = MinMaxScaler(feature_range=(1, 10))
        df["score"] = scaler.fit_transform(df[["score_log"]]).round(4)
    else:
        df["score"] = 5.0 # flat fallback if every row has the identical score

    # User encoder: only users who actually have qualifying interactions
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

    return train_matrix, user_enc, item_enc, df


def update_db_indices(db, user_enc, item_enc):
    # user_enc.classes_ contains BOTH the synthetic seed users (1-100,
    # never present in Postgres — they exist purely to give the model
    # density) and real users (offset by REAL_USER_ID_OFFSET) Only the
    # latter correspond to actual User rows that need als_user_idx set
    all_ids = [int(u) for u in user_enc.classes_]
    real_ids = [uid for uid in all_ids if uid >= REAL_USER_ID_OFFSET]
    n_synthetic = len(all_ids) - len(real_ids)

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
    print(f"als_user_idx set on {len(users)} real user(s) (+ {n_synthetic} synthetic seed users in the model)")
    print(f"als_item_idx set on {len(recipes)} recipe(s)")


def main():
    db = SessionLocal()
    try:
        print("── Building train matrix from real interactions ──")
        train_matrix, user_enc, item_enc, df = build_train_matrix(db)

        if train_matrix is None:
            print(
                " Not enough interaction data to train ALS yet.\n"
                f" Need at least {MIN_USER_INTERACTIONS} interacted recipe(s) for "
                "at least 1 real user (the 100-user synthetic seed dataset "
                "provides the rest of the density).\n"
                " Go like/save/rate/view a recipe with a real account, "
                "then re-run this script.\n"
                " Nothing was changed."
            )
            return

        print(f" {train_matrix.shape[0]} users x {train_matrix.shape[1]} recipes, "
              f"{train_matrix.nnz} interactions")

        print("── Training ALS ──")
        recommender = ALSRecipeRecommender(
            factors=ALS_FACTORS,
            iterations=ALS_ITERATIONS,
            regularization=ALS_REGULARIZATION,
            alpha=ALS_ALPHA,
            use_bm25=ALS_USE_BM25,
        )
        weighted_matrix = recommender.preprocess_matrix(train_matrix)
        recommender.fit(weighted_matrix)

        print("── Saving artefacts ──")
        recommender.save_model(os.path.join(MODELS_DIR, "als_model.pkl"))
        sp.save_npz(os.path.join(SPARSE_DIR, "train_matrix.npz"), train_matrix)
        with open(os.path.join(MAPPING_DIR, "user_encoder.pkl"), "wb") as f:
            pickle.dump(user_enc, f)
        with open(os.path.join(MAPPING_DIR, "item_encoder.pkl"), "wb") as f:
            pickle.dump(item_enc, f)

        print("── Updating DB indices ──")
        update_db_indices(db, user_enc, item_enc)

        print("\nDone. Restart the FastAPI server (uvicorn) to load the new model.")
    finally:
        db.close()


if __name__ == "__main__":
    main()