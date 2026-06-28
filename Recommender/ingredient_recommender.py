"""
Ce module peut etre utilise seul ou combine avec ALS (score hybride)
Il constitue la 3eme etape du pipeline de recommandation intelligent
"""

import os
import pandas as pd
import numpy as np
import pickle
import scipy.sparse as sp

# ─── Configuration des chemins ─────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "Dataset")
RAW_DIR = os.path.join(DATASET_DIR, "Raw")
MAPPING_DIR = os.path.join(DATASET_DIR, "Mapping")
SPARSE_DIR = os.path.join(DATASET_DIR, "Sparse_matrices")

from model_als import ALSRecipeRecommender


class IngredientRecommender:
    """Recommandation de recettes basee sur les ingredients du frigo"""

    def __init__(
        self,
        recipes_path=None,
        ingredients_path=None,
        recipe_ingredients_path=None,
        user_ingredients_path=None,
        user_encoder_path=None,
        item_encoder_path=None
    ):
        self.recipes_path = recipes_path or os.path.join(RAW_DIR, "raw_recipes.csv")
        self.ingredients_path = ingredients_path or os.path.join(RAW_DIR, "ingredients.csv")
        self.recipe_ingredients_path = recipe_ingredients_path or os.path.join(RAW_DIR, "recipe_ingredients.csv")
        self.user_ingredients_path = user_ingredients_path or os.path.join(RAW_DIR, "user_ingredients.csv")
        self.user_encoder_path = user_encoder_path or os.path.join(MAPPING_DIR, "user_encoder.pkl")
        self.item_encoder_path = item_encoder_path or os.path.join(MAPPING_DIR, "item_encoder.pkl")
        self.recipes_df = None
        self.ingredients_df = None
        self.recipe_ingredients_df = None
        self.user_ingredients_df = None
        self.user_enc = None
        self.item_enc = None

    def load_data(self):
        print("\nLoading ingredient data...")
        self.recipes_df = pd.read_csv(self.recipes_path, encoding="cp1252")
        self.ingredients_df = pd.read_csv(self.ingredients_path, encoding="cp1252")
        self.recipe_ingredients_df = pd.read_csv(self.recipe_ingredients_path, encoding="cp1252")
        self.user_ingredients_df = pd.read_csv(
            self.user_ingredients_path,
            sep="\t",
            encoding="cp1252"
        )
        if os.path.exists(self.user_encoder_path):
            with open(self.user_encoder_path, "rb") as f:
                self.user_enc = pickle.load(f)
        if os.path.exists(self.item_encoder_path):
            with open(self.item_encoder_path, "rb") as f:
                self.item_enc = pickle.load(f)
        print(f"Recipes          : {len(self.recipes_df)}")
        print(f"Ingredients      : {len(self.ingredients_df)}")
        print(f"Recipe-Ingredient: {len(self.recipe_ingredients_df)} liens")
        print(f"User-Ingredients : {len(self.user_ingredients_df)} entrees")
        if self.user_enc:
            print(f"User encoder     : {len(self.user_enc.classes_)} classes")
        if self.item_enc:
            print(f"Item encoder     : {len(self.item_enc.classes_)} classes")

    def get_user_fridge(self, user_id):
        user_rows = self.user_ingredients_df[
            self.user_ingredients_df["user_id"] == user_id
        ]
        if user_rows.empty:
            print(f"\nAucun ingredient trouve pour user_id={user_id}")
            return []
        ingredients = user_rows["ingredient_id"].tolist()
        print(f"\nFrigo user {user_id} : {len(ingredients)} ingredients")
        return ingredients

    def parse_fridge_input(self, ingredient_names):
        if not ingredient_names:
            print("\nAucun ingredient fourni")
            return []
        ids = []
        not_found = []
        for name in ingredient_names:
            name_lower = name.strip().lower()
            match = self.ingredients_df[
                self.ingredients_df["name"].str.lower() == name_lower
            ]
            if match.empty:
                match = self.ingredients_df[
                    self.ingredients_df["name"].str.contains(
                        name_lower, case=False, na=False
                    )
                ]
            if not match.empty:
                ids.append(int(match.iloc[0]["ingredient_id"]))
            else:
                not_found.append(name)
        print(f"\nIngredients trouves : {len(ids)}")
        if not_found:
            print(f"Ingredients non reconnus : {not_found}")
        return ids

    def display_fridge(self, ingredient_ids):
        rows = self.ingredients_df[
            self.ingredients_df["ingredient_id"].isin(ingredient_ids)
        ][["name", "categorie"]]
        print(f"\nFrigo ({len(rows)} ingredients) :")
        for _, r in rows.iterrows():
            print(f"  - {r['name']} ({r['categorie']})")

    def get_fridge_allergens(self, ingredient_ids):
        rows = self.ingredients_df[
            self.ingredients_df["ingredient_id"].isin(ingredient_ids)
        ]
        allergens = set()
        for val in rows["allergen"].dropna():
            for a in str(val).split(","):
                allergens.add(a.strip())
        return list(allergens)

    def compute_coverage_score(self, fridge_ingredients, recipe_id):
        required = self.recipe_ingredients_df[
            self.recipe_ingredients_df["recipe_id"] == recipe_id
        ]["ingredient_id"].tolist()
        if not required:
            return 0.0
        matched = set(fridge_ingredients) & set(required)
        coverage = len(matched) / len(required)
        return round(coverage, 4)

    def coverage_detail(self, fridge_ingredients, recipe_id):
        required = set(
            self.recipe_ingredients_df[
                self.recipe_ingredients_df["recipe_id"] == recipe_id
            ]["ingredient_id"].tolist()
        )
        if not required:
            return 0.0, [], []
        matched = set(fridge_ingredients) & required
        missing = required - set(fridge_ingredients)
        coverage = round(len(matched) / len(required), 4)
        matched_names = self.ingredients_df[
            self.ingredients_df["ingredient_id"].isin(matched)
        ]["name"].tolist()
        missing_names = self.ingredients_df[
            self.ingredients_df["ingredient_id"].isin(missing)
        ]["name"].tolist()
        return coverage, matched_names, missing_names

    def recommend_by_ingredients(
        self,
        fridge_ingredients,
        n=10,
        min_coverage=0.5,
        cuisine=None,
        difficulte=None,
        regime=None,
        allergens_exclus=None
    ):
        if not fridge_ingredients:
            print("\nFrigo vide, impossible de recommander")
            return []
        recipes = self.recipes_df.copy()
        if cuisine:
            recipes = recipes[recipes["cuisine"] == cuisine]
        if difficulte:
            recipes = recipes[recipes["difficulte"] == difficulte]
        if regime:
            recipes = recipes[recipes["regime"] == regime]
        results = []
        for _, row in recipes.iterrows():
            recipe_id = row["recipe_id"]
            coverage, matched, missing = self.coverage_detail(
                fridge_ingredients,
                recipe_id
            )
            if coverage < min_coverage:
                continue
            if allergens_exclus:
                recipe_ing_ids = self.recipe_ingredients_df[
                    self.recipe_ingredients_df["recipe_id"] == recipe_id
                ]["ingredient_id"].tolist()
                recipe_allergens = set()
                for val in self.ingredients_df[
                    self.ingredients_df["ingredient_id"].isin(recipe_ing_ids)
                ]["allergen"].dropna():
                    for a in str(val).split(","):
                        recipe_allergens.add(a.strip())
                if recipe_allergens & set(allergens_exclus):
                    continue
            results.append(
                {
                    "recipe_id": int(recipe_id),
                    "recipe_name": row["title"],
                    "cuisine": row.get("cuisine", ""),
                    "difficulte": row.get("difficulte", ""),
                    "regime": row.get("regime", ""),
                    "temps_preparation": row.get("temps_preparation", ""),
                    "note_moyenne": row.get("note_moyenne", ""),
                    "coverage_score": coverage,
                    "ingredients_disponibles": matched,
                    "ingredients_manquants": missing
                }
            )
        results = sorted(
            results,
            key=lambda x: (x["coverage_score"], x["note_moyenne"]),
            reverse=True
        )[:n]
        return results

    def hybrid_score(self, als_score, coverage_score, als_weight=0.6, ingredient_weight=0.4):
        return round(als_weight * als_score + ingredient_weight * coverage_score, 4)

    def recommend_hybrid(
        self,
        user_id,
        fridge_ingredients,
        als_recommender,
        train_matrix,
        n=10,
        min_coverage=0.0,
        allergens_exclus=None
    ):
        user_idx = self._get_user_idx(user_id)
        if user_idx is None:
            print(f"\nUser {user_id} inconnu dans l'encoder, recs par ingredients seules")
            return self.recommend_by_ingredients(fridge_ingredients, n)

        if als_recommender.model is None:
            print("\nModele ALS non charge, recs par ingredients seules")
            return self.recommend_by_ingredients(fridge_ingredients, n)

        als_recs = als_recommender.recommend(user_idx, train_matrix, n=n * 2)
        results = []
        for rec in als_recs:
            recipe_idx = rec["recipe_idx"]
            recipe_id = self._get_recipe_id(recipe_idx)
            if recipe_id is None:
                continue
            coverage, matched, missing = self.coverage_detail(
                fridge_ingredients,
                recipe_id
            )
            if coverage < min_coverage:
                continue
            if allergens_exclus:
                recipe_ing_ids = self.recipe_ingredients_df[
                    self.recipe_ingredients_df["recipe_id"] == recipe_id
                ]["ingredient_id"].tolist()
                recipe_allergens = set()
                for val in self.ingredients_df[
                    self.ingredients_df["ingredient_id"].isin(recipe_ing_ids)
                ]["allergen"].dropna():
                    for a in str(val).split(","):
                        recipe_allergens.add(a.strip())
                if recipe_allergens & set(allergens_exclus):
                    continue
            als_norm = max(0.0, min(1.0, rec["score"]))
            score = self.hybrid_score(als_norm, coverage)
            row = self.recipes_df[self.recipes_df["recipe_id"] == recipe_id]
            results.append(
                {
                    "recipe_id": int(recipe_id),
                    "recipe_name": row["title"].values[0] if not row.empty else str(recipe_id),
                    "cuisine": row["cuisine"].values[0] if not row.empty else "",
                    "als_score": round(rec["score"], 4),
                    "coverage_score": coverage,
                    "hybrid_score": score,
                    "ingredients_disponibles": matched,
                    "ingredients_manquants": missing
                }
            )
        results = sorted(results, key=lambda x: x["hybrid_score"], reverse=True)[:n]
        return results

    def _get_recipe_id(self, recipe_idx):
        if self.item_enc is None:
            return None
        try:
            return int(self.item_enc.inverse_transform([recipe_idx])[0])
        except (ValueError, IndexError):
            return None

    def _get_user_idx(self, user_id):
        if self.user_enc is None:
            return None
        try:
            return int(self.user_enc.transform([user_id])[0])
        except (ValueError, IndexError):
            return None

    def display_results(self, results, mode="ingredients"):
        if not results:
            print("\nAucune recommandation trouvee")
            return
        print(f"\nTOP {len(results)} RECOMMANDATIONS")
        print("-" * 50)
        for i, r in enumerate(results, 1):
            name = r.get("recipe_name", r.get("recipe_id"))
            cuisine = r.get("cuisine", "")
            temps = r.get("temps_preparation", "")
            note = r.get("note_moyenne", "")
            print(f"{i}. {name} ({cuisine}) | {temps} min | note {note}")
            print(f"   Couverture  : {r['coverage_score']}")
            print(f"   Disponibles : {r['ingredients_disponibles']}")
            if r.get("ingredients_manquants"):
                print(f"   Manquants   : {r['ingredients_manquants']}")
            if mode == "hybrid":
                print(f"   Scores      : hybrid={r['hybrid_score']} | ALS={r['als_score']}")
            print()


if __name__ == "__main__":
    rec = IngredientRecommender()
    rec.load_data()

    fridge = rec.get_user_fridge(user_id=1)
    rec.display_fridge(fridge)
    allergens = rec.get_fridge_allergens(fridge)
    print(f"Allergenes detectes : {allergens}")
    recs = rec.recommend_by_ingredients(
        fridge_ingredients=fridge,
        n=5,
        min_coverage=0.5
    )
    rec.display_results(recs, mode="ingredients")

    print("=" * 50)
    manual_ingredients = ["poulet", "tomates", "oignons", "ail", "curcuma"]
    fridge_manual = rec.parse_fridge_input(manual_ingredients)
    recs_manual = rec.recommend_by_ingredients(
        fridge_ingredients=fridge_manual,
        n=5,
        min_coverage=0.3,
        allergens_exclus=["gluten", "lait"]
    )
    rec.display_results(recs_manual, mode="ingredients")

    als = ALSRecipeRecommender()
    als.load_model()
    als.load_metadata()
    train_matrix = sp.load_npz(os.path.join(SPARSE_DIR, "train_matrix.npz"))
    recs_hybrid = rec.recommend_hybrid(
        user_id=1,
        fridge_ingredients=fridge,
        als_recommender=als,
        train_matrix=train_matrix,
        n=5,
        min_coverage=0.3,
        allergens_exclus=["gluten"]
    )
    rec.display_results(recs_hybrid, mode="hybrid")
