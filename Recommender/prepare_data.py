"""
Prepare Data for ALS Recommender

this script is the first step of the pipeline
"""

import os
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import scipy.sparse as sp
from scipy import sparse
import numpy as np
import pickle

# ─── Configuration des chemins ─────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "Dataset")
RAW_DIR = os.path.join(DATASET_DIR, "Raw")
FEATURES_DIR = os.path.join(DATASET_DIR, "Features")
MAPPING_DIR = os.path.join(DATASET_DIR, "Mapping")
SPARSE_DIR = os.path.join(DATASET_DIR, "Sparse_matrices")

os.makedirs(FEATURES_DIR, exist_ok=True)
os.makedirs(MAPPING_DIR, exist_ok=True)
os.makedirs(SPARSE_DIR, exist_ok=True)

# ─── 1er étape : Charger des données brutes ────────────────────────────────────
interactions = pd.read_csv(os.path.join(RAW_DIR, "interactions.csv"), encoding="cp1252")
users        = pd.read_csv(os.path.join(RAW_DIR, "users.csv"),         encoding="cp1252")
recipes      = pd.read_csv(os.path.join(RAW_DIR, "raw_recipes.csv"),   encoding="cp1252")
ingredients  = pd.read_csv(os.path.join(RAW_DIR, "ingredients.csv"),   encoding="cp1252")

print("CHARGEMENT DES DONNEES")
print("----------------------")
print(f"Interactions : {interactions.shape[0]} lignes, {interactions.shape[1]} colonnes")
print(f"Users        : {users.shape[0]} lignes, {users.shape[1]} colonnes")
print(f"Recipes      : {recipes.shape[0]} lignes, {recipes.shape[1]} colonnes")
print(f"Ingredients  : {ingredients.shape[0]} lignes, {ingredients.shape[1]} colonnes")

# ─── 2ème étape : Nettoyage des données ────────────────────────────────────────
interactions["rating"]           = interactions["rating"].fillna(0)
interactions["date_interaction"] = pd.to_datetime(interactions["date_interaction"], errors="coerce")

# Score composite
interactions["score_raw"] = (
    interactions["viewed"].astype(int) * 1 +
    interactions["liked"].astype(int)  * 3 +
    interactions["saved"].astype(int)  * 4 +
    interactions["rating"]             * 5
)
# garder uniquement les interactions positives
interactions = interactions[interactions["score_raw"] > 0]
# Log transformation
interactions["score_log"] = np.log1p(interactions["score_raw"])
scaler = MinMaxScaler(feature_range=(1,10))

interactions["score"] = scaler.fit_transform(interactions[["score_log"]]).round(4)
# Supprimer doublons user-recette
interactions = (
    interactions
    .sort_values("score_raw", ascending=False)
    .drop_duplicates(subset=["user_id", "recipe_id"], keep="first")
)

# Filter users
user_counts = interactions["user_id"].value_counts()
interactions = interactions[interactions["user_id"].isin(user_counts[user_counts >= 3].index)]
# Filter items
item_counts = interactions["recipe_id"].value_counts()
interactions = interactions[interactions["recipe_id"].isin(item_counts[item_counts >= 5].index)]
# reset index
interactions = interactions.reset_index(drop=True)

print("\nNETTOYAGE")
print("---------")
print(f"Interactions valides : {len(interactions)}")
print(f"Score min / max      : {interactions['score'].min()} / {interactions['score'].max()}")
print(f"Users actifs         : {interactions['user_id'].nunique()}")
print(f"Recipes actives      : {interactions['recipe_id'].nunique()}")

# ─── 3ème étape : Encodage des IDs ────────────────────────────────────────────
user_enc = LabelEncoder()
item_enc = LabelEncoder()

interactions["user_idx"] = user_enc.fit_transform(interactions["user_id"])
interactions["item_idx"] = item_enc.fit_transform(interactions["recipe_id"])

# ─── 4ème étape : Split par utilisateur (Leave-One-Out) ──────────────────────
def split_by_user(df, test_ratio=0.2, min_train=2):
    train_list=[]
    test_list=[]
    for user, group in df.groupby("user_idx"):
        group = group.sort_values("date_interaction")
        n = len(group)
        n_test = max(1, int(n * test_ratio))
        if n <= min_train:
            train_list.append(group)
            continue
        train_part = group.iloc[:-n_test]
        test_part = group.iloc[-n_test:]
        train_list.append(train_part)
        test_list.append(test_part)
    train_df = pd.concat(train_list).reset_index(drop=True)
    test_df = pd.concat(test_list).reset_index(drop=True)
    return train_df, test_df

train_df, test_df = split_by_user(interactions, test_ratio=0.2, min_train=2)

print("\nSPLIT TRAIN / TEST")
print("------------------")
print(f"Train interactions : {len(train_df)}")
print(f"Test  interactions : {len(test_df)}")
print(f"Users en train     : {train_df['user_idx'].nunique()}")
print(f"Users en test      : {test_df['user_idx'].nunique()}")

# ─── 5ème étape : Creation des matrices utilisateur-item ─────────────────────
n_users = interactions["user_idx"].nunique()
n_items = interactions["item_idx"].nunique()

train_matrix = sp.coo_matrix(
    (train_df["score"].astype(np.float32), (train_df["user_idx"], train_df["item_idx"])),
    shape=(n_users, n_items)
).tocsr()

test_matrix = sp.coo_matrix(
    (test_df["score"].astype(np.float32), (test_df["user_idx"], test_df["item_idx"])),
    shape=(n_users, n_items)
).tocsr()

# verification
train_set = set(zip(train_df["user_idx"], train_df["item_idx"]))
test_set  = set(zip(test_df["user_idx"],  test_df["item_idx"]))
overlap   = train_set & test_set
print(f"\nOverlap train/test : {len(overlap)} interactions (doit etre 0)")

sparsity = 1 - train_matrix.nnz / (n_users * n_items)
print(f"Sparsite matrice   : {round(sparsity, 4)}")

# ─── 6ème étape : Features utilisateur enrichies ───────────────────────────────
user_cf_features = interactions.groupby("user_idx").agg(
    liked_mean  = ("liked",  "mean"),
    saved_mean  = ("saved",  "mean"),
    rating_mean = ("rating", "mean"),
    n_interactions = ("recipe_id", "count")
).fillna(0)

users_encoded = users.copy()
users_encoded["user_idx"] = user_enc.transform(users_encoded["user_id"].values)     if set(users_encoded["user_id"]).issubset(set(user_enc.classes_))     else users_encoded.index

regime_dummies   = pd.get_dummies(users["regime_alimentaire"], prefix="regime")
cuisine_expanded = users["preferences_cuisine"].str.get_dummies(sep=",").add_prefix("pref_cuisine_")

user_content_features = pd.concat([
    users[["user_id", "region", "pays"]],
    regime_dummies,
    cuisine_expanded
], axis=1)

# ─── 7ème étape : Features recettes enrichies ──────────────────────────────────
recipe_features = recipes[[
    "recipe_id", "cuisine", "regime", "difficulte",
    "n_ingredients", "n_instructions", "temps_preparation", "niveau_calorie",
    "note_moyenne", "nb_avis"
]].copy()

cuisine_dummies   = pd.get_dummies(recipes["cuisine"],   prefix="cuisine")
regime_r_dummies  = pd.get_dummies(recipes["regime"],    prefix="regime")
difficulte_dummies = pd.get_dummies(recipes["difficulte"], prefix="diff")
tags_expanded     = recipes["tags"].str.get_dummies(sep=",").add_prefix("tag_")

numeric_cols = ["n_ingredients", "n_instructions", "temps_preparation", "niveau_calorie", "note_moyenne", "nb_avis"]
recipe_numeric = recipes[["recipe_id"] + numeric_cols].copy()
recipe_numeric[numeric_cols] = MinMaxScaler().fit_transform(recipe_numeric[numeric_cols])

recipe_content_features = pd.concat([
    recipe_features[["recipe_id"]],
    cuisine_dummies,
    regime_r_dummies,
    difficulte_dummies,
    tags_expanded,
    recipe_numeric[numeric_cols]
], axis=1)

# ─── 8ème étape : EDA / Stats descriptives ────────────────────────────────────
print("\nEDA / STATS DESCRIPTIVES")
print("------------------------")
print(f"Score composite — min: {interactions['score_raw'].min()}  max: {interactions['score_raw'].max()}  moy: {interactions['score_raw'].mean():.2f}")
print(f"Score normalise — min: {interactions['score'].min()}  max: {interactions['score'].max()}  moy: {interactions['score'].mean():.2f}")
print(f"Rating moyen (non nul)    : {interactions[interactions['rating']>0]['rating'].mean():.2f}")
print(f"Taux de likes             : {interactions['liked'].mean():.2%}")
print(f"Taux de sauvegardes       : {interactions['saved'].mean():.2%}")
print(f"\nTop 5 recettes les plus interagies :")
top_recipes = interactions.groupby("recipe_id")["score"].sum().sort_values(ascending=False).head(5)
for rid, s in top_recipes.items():
    title = recipes[recipes["recipe_id"] == rid]["title"].values
    label = title[0] if len(title) > 0 else str(rid)
    print(f"  recipe {rid} — {label[:40]} — score total: {s:.1f}")
print(f"\nDistribution regimes utilisateurs :")
print(users["regime_alimentaire"].value_counts().to_string())
print(f"\nDistribution cuisines recettes :")
print(recipes["cuisine"].value_counts().to_string())

# ─── 9ème étape : Sauvegarder tout ─────────────────────────────────────────────
sparse.save_npz(os.path.join(SPARSE_DIR, "train_matrix.npz"), train_matrix)
sparse.save_npz(os.path.join(SPARSE_DIR, "test_matrix.npz"),  test_matrix)
pickle.dump(user_enc, open(os.path.join(MAPPING_DIR, "user_encoder.pkl"), "wb"))
pickle.dump(item_enc, open(os.path.join(MAPPING_DIR, "item_encoder.pkl"), "wb"))
pickle.dump(scaler,   open(os.path.join(MAPPING_DIR, "score_scaler.pkl"), "wb"))
interactions.to_csv(os.path.join(FEATURES_DIR, "processed_interactions.csv"),  index=False)
user_cf_features.to_csv(os.path.join(FEATURES_DIR, "user_cf_features.csv"))
user_content_features.to_csv(os.path.join(FEATURES_DIR, "user_content_features.csv"), index=False)
recipe_content_features.to_csv(os.path.join(FEATURES_DIR, "recipe_content_features.csv"), index=False)

print("\nSAUVEGARDE")
print("----------")
print(f"Train matrix          : {train_matrix.shape} — {train_matrix.nnz} interactions")
print(f"Test  matrix          : {test_matrix.shape} — {test_matrix.nnz} interactions")
print("Encoders + scaler     : Dataset/Mapping/")
print("Features              : Dataset/Features/")
