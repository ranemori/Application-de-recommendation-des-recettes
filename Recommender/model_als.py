"""
Model training and recommendation generation using ALS (Alternating Least Squares)
this script is the second step of the pipeline
"""

import os
import pickle
import numpy as np
import pandas as pd
import scipy.sparse as sp
from implicit.als import AlternatingLeastSquares
from implicit.nearest_neighbours import bm25_weight

# ─── Configuration des chemins ─────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "Dataset")
RAW_DIR = os.path.join(DATASET_DIR, "Raw")
MAPPING_DIR = os.path.join(DATASET_DIR, "Mapping")
SPARSE_DIR = os.path.join(DATASET_DIR, "Sparse_matrices")
MODELS_DIR = os.path.join(BASE_DIR, "models")

os.makedirs(MODELS_DIR, exist_ok=True)


class ALSRecipeRecommender:
    def __init__(self, factors=64, iterations=15, regularization=0.05, alpha=20, use_gpu=False, use_bm25=True):
        self.factors = factors
        self.regularization = regularization
        self.iterations = iterations
        self.alpha = alpha
        self.use_gpu = use_gpu
        self.use_bm25 = use_bm25
        self.model = None
        self.recipes_df = None
        self.users_df = None
        self.user_enc = None
        self.item_enc = None

    def load_matrix(self, matrix_path):
        print(f"\nLoading matrix: {matrix_path}")
        matrix = sp.load_npz(matrix_path)
        print(f"Users        : {matrix.shape[0]}")
        print(f"Recipes      : {matrix.shape[1]}")
        print(f"Interactions : {matrix.nnz}")
        return matrix

    def load_metadata(self, recipes_path=None, users_path=None, user_enc_path=None, item_enc_path=None):
        recipes_path = recipes_path or os.path.join(RAW_DIR, "raw_recipes.csv")
        users_path = users_path or os.path.join(RAW_DIR, "users.csv")
        user_enc_path = user_enc_path or os.path.join(MAPPING_DIR, "user_encoder.pkl")
        item_enc_path = item_enc_path or os.path.join(MAPPING_DIR, "item_encoder.pkl")

        self.recipes_df = pd.read_csv(recipes_path, encoding="cp1252")
        self.users_df = pd.read_csv(users_path, encoding="cp1252")
        print(f"\nMetadata loaded — {len(self.recipes_df)} recipes, {len(self.users_df)} users")
        if user_enc_path and os.path.exists(user_enc_path):
            with open(user_enc_path, "rb") as f:
                self.user_enc = pickle.load(f)
            print(f"User encoder loaded: {len(self.user_enc.classes_)} classes")
        if item_enc_path and os.path.exists(item_enc_path):
            with open(item_enc_path, "rb") as f:
                self.item_enc = pickle.load(f)
            print(f"Item encoder loaded: {len(self.item_enc.classes_)} classes")

    def preprocess_matrix(self, matrix):
        if self.use_bm25:
            print("\nApplying BM25 weighting...")
            matrix = bm25_weight(matrix, K1=50, B=0.6)
        print(f"Applying alpha={self.alpha}")
        matrix = matrix * self.alpha
        return matrix.tocsr()

    def initialize_model(self):
        print("\nInitializing ALS model...")
        self.model = AlternatingLeastSquares(
            factors=self.factors,
            regularization=self.regularization,
            iterations=self.iterations,
            use_gpu=self.use_gpu,
            random_state=42
        )
        return self.model

    def fit(self, train_matrix):
        print("TRAINING ALS MODEL...")
        self.initialize_model()
        self.model.fit(train_matrix, show_progress=True)
        print("\nTraining completed!")

    def partial_fit(self, train_matrix, new_users=None, new_items=None, iterations=5):
        if self.model is None:
            print("\nAucun modele existant — lancement d'un entrainement complet...")
            self.fit(train_matrix)
            return

        print(f"\nINCREMENTAL UPDATE — {iterations} iterations...")
        print(f"Nouvelle matrice: {train_matrix.shape[0]} users x {train_matrix.shape[1]} items")

        old_user_factors = self.model.user_factors.copy()
        old_item_factors = self.model.item_factors.copy()

        n_users_new, n_items_new = train_matrix.shape
        n_users_old, n_items_old = old_user_factors.shape[0], old_item_factors.shape[0]

        if n_users_new > n_users_old:
            new_user_factors = np.random.normal(
                scale=1.0 / np.sqrt(self.factors),
                size=(n_users_new - n_users_old, self.factors)
            ).astype(np.float32)
            user_factors = np.vstack([old_user_factors, new_user_factors])
            print(f"  + {n_users_new - n_users_old} nouveaux utilisateurs initialises")
        else:
            user_factors = old_user_factors[:n_users_new]

        if n_items_new > n_items_old:
            new_item_factors = np.random.normal(
                scale=1.0 / np.sqrt(self.factors),
                size=(n_items_new - n_items_old, self.factors)
            ).astype(np.float32)
            item_factors = np.vstack([old_item_factors, new_item_factors])
            print(f"  + {n_items_new - n_items_old} nouvelles recettes initialises")
        else:
            item_factors = old_item_factors[:n_items_new]

        self.model = AlternatingLeastSquares(
            factors=self.factors,
            regularization=self.regularization,
            iterations=iterations,
            use_gpu=self.use_gpu,
            random_state=42
        )
        self.model.user_factors = user_factors
        self.model.item_factors = item_factors
        self.model.fit(train_matrix, show_progress=True)
        print("\nIncremental update completed!")

    def update_model(self, new_interactions_df, user_enc, item_enc, min_new_interactions=10):
        if len(new_interactions_df) < min_new_interactions:
            print(f"\nPas assez de nouvelles interactions ({len(new_interactions_df)} < {min_new_interactions}) — skip update")
            return False

        print(f"\nUPDATE MODEL — {len(new_interactions_df)} nouvelles interactions detectees")
        n_users = len(user_enc.classes_)
        n_items = len(item_enc.classes_)

        new_interactions_df["user_idx"] = user_enc.transform(new_interactions_df["user_id"])
        new_interactions_df["item_idx"] = item_enc.transform(new_interactions_df["recipe_id"])

        train_matrix = sp.coo_matrix(
            (
                new_interactions_df["score"].astype(np.float32),
                (new_interactions_df["user_idx"], new_interactions_df["item_idx"])
            ),
            shape=(n_users, n_items)
        ).tocsr()

        old_n_users = self.model.user_factors.shape[0] if self.model else 0
        old_n_items = self.model.item_factors.shape[0] if self.model else 0
        new_users = list(range(old_n_users, n_users)) if n_users > old_n_users else None
        new_items = list(range(old_n_items, n_items)) if n_items > old_n_items else None

        self.partial_fit(train_matrix, new_users=new_users, new_items=new_items, iterations=5)
        self.save_model()
        self.save_embeddings()
        return True

    def save_model(self, path=None):
        path = path or os.path.join(MODELS_DIR, "als_model.pkl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        print(f"\nModel saved: {path}")

    def load_model(self, path=None):
        path = path or os.path.join(MODELS_DIR, "als_model.pkl")
        with open(path, "rb") as f:
            self.model = pickle.load(f)
        print(f"\nModel loaded: {path}")

    def save_embeddings(self):
        os.makedirs(MODELS_DIR, exist_ok=True)
        np.save(os.path.join(MODELS_DIR, "user_embeddings.npy"), self.model.user_factors)
        np.save(os.path.join(MODELS_DIR, "recipe_embeddings.npy"), self.model.item_factors)
        print("\nEmbeddings saved")

    def recommend(self, user_idx, train_matrix, n=10):
        if user_idx >= train_matrix.shape[0]:
            print(f"\nUser {user_idx} inconnu, fallback popularite")
            return [{"recipe_idx": int(i), "score": 0.0} for i in self.popularity_fallback(train_matrix, n)]
        ids, scores = self.model.recommend(
            userid=user_idx,
            user_items=train_matrix[user_idx],
            N=n,
            filter_already_liked_items=True
        )
        return [
            {"recipe_idx": int(recipe_idx), "score": float(score)}
            for recipe_idx, score in zip(ids, scores)
        ]

    def recommend_with_regime_filter(self, user_idx, train_matrix, user_enc, item_enc, n=10):
        if self.users_df is None or self.recipes_df is None:
            return self.recommend(user_idx, train_matrix, n)

        recs_raw = self.recommend(user_idx, train_matrix, n=n * 3)
        if not recs_raw:
            return recs_raw

        try:
            user_id = user_enc.inverse_transform([user_idx])[0]
        except (ValueError, IndexError):
            print(f"\nUser {user_idx} non trouve dans l'encoder, fallback sans filtre")
            return self.recommend(user_idx, train_matrix, n)

        row = self.users_df[self.users_df["user_id"] == user_id]
        if row.empty:
            print(f"\nUser {user_id} non trouve dans users_df, fallback sans filtre")
            return self.recommend(user_idx, train_matrix, n)

        regime_user = row.iloc[0]["regime_alimentaire"]

        results = []
        for rec in recs_raw:
            recipe_idx = rec["recipe_idx"]
            try:
                recipe_id = int(item_enc.inverse_transform([recipe_idx])[0])
            except (ValueError, IndexError):
                continue

            row_recipe = self.recipes_df[self.recipes_df["recipe_id"] == recipe_id]
            if row_recipe.empty:
                continue

            recipe_regime = row_recipe.iloc[0]["regime"]
            if regime_user and regime_user != "normal" and recipe_regime != regime_user:
                continue

            rec["recipe_id"] = int(recipe_id)
            rec["title"] = row_recipe.iloc[0]["title"]
            rec["cuisine"] = row_recipe.iloc[0]["cuisine"]
            rec["regime"] = recipe_regime
            rec["difficulte"] = row_recipe.iloc[0]["difficulte"]
            rec["temps_preparation"] = int(row_recipe.iloc[0]["temps_preparation"])
            results.append(rec)

            if len(results) >= n:
                break

        if len(results) < n:
            for rec in recs_raw:
                recipe_idx = rec["recipe_idx"]
                try:
                    recipe_id = int(item_enc.inverse_transform([recipe_idx])[0])
                except (ValueError, IndexError):
                    continue
                if any(r.get("recipe_id") == recipe_id for r in results):
                    continue
                row_recipe = self.recipes_df[self.recipes_df["recipe_id"] == recipe_id]
                if not row_recipe.empty:
                    rec["recipe_id"] = int(recipe_id)
                    rec["title"] = row_recipe.iloc[0]["title"]
                    rec["cuisine"] = row_recipe.iloc[0]["cuisine"]
                    rec["regime"] = row_recipe.iloc[0]["regime"]
                    rec["difficulte"] = row_recipe.iloc[0]["difficulte"]
                    rec["temps_preparation"] = int(row_recipe.iloc[0]["temps_preparation"])
                results.append(rec)
                if len(results) >= n:
                    break

        return results[:n]

    def recommend_diverse(self, user_idx, train_matrix, n=10, lambda_diversity=0.5, pool=None):
        """Layer 2 — Diversity re-ranker (Maximal Marginal Relevance).

        Re-orders a candidate pool so that each newly picked item trades
        off its raw relevance score against how similar it is (in item-
        embedding space) to items already selected, pushing near-duplicate
        recipes down the list.
        """
        candidates = pool if pool is not None else self.recommend(user_idx, train_matrix, n=n * 3)
        if not candidates or self.model is None:
            return candidates[:n]

        item_factors = self.model.item_factors
        norms = np.linalg.norm(item_factors, axis=1) + 1e-8
        selected = []
        remaining = candidates.copy()

        while remaining and len(selected) < n:
            best_idx = None
            best_score = -np.inf
            for i, cand in enumerate(remaining):
                relevance = cand["score"]
                if not selected:
                    mmr = relevance
                else:
                    cand_vec = item_factors[cand["recipe_idx"]]
                    sim_max = max(
                        float(np.dot(cand_vec, item_factors[s["recipe_idx"]]))
                        / (norms[cand["recipe_idx"]] * norms[s["recipe_idx"]])
                        for s in selected
                    )
                    mmr = lambda_diversity * relevance - (1 - lambda_diversity) * sim_max
                if mmr > best_score:
                    best_score = mmr
                    best_idx = i
            selected.append(remaining.pop(best_idx))

        return selected

    # ── Fairness monitor (Layer 3) ──────────────────────────────────────────

    def _recipe_cuisine(self, recipe_idx):
        """Look up the cuisine of a recipe from its ALS matrix index."""
        if self.recipes_df is None or self.item_enc is None:
            return None
        try:
            recipe_id = int(self.item_enc.inverse_transform([recipe_idx])[0])
        except (ValueError, IndexError):
            return None
        row = self.recipes_df[self.recipes_df["recipe_id"] == recipe_id]
        if row.empty:
            return None
        return row.iloc[0].get("cuisine")

    def apply_fairness_cap(self, ranked, n, max_share=0.4):
        """Layer 3 — Fairness monitor.

        Prevents a single cuisine (or, more generally, any one item
        attribute group) from dominating the final list — e.g. capping
        any single cuisine to at most `max_share` of the slots — so that
        smaller / less-popular categories still get exposure instead of
        the list collapsing into "whatever the model is most confident
        about", which would otherwise tend to be the few cuisines with
        the most historical interactions.
        """
        if not ranked:
            return ranked

        max_per_group = max(1, int(np.ceil(n * max_share)))
        counts = {}
        accepted, deferred = [], []

        for cand in ranked:
            group = self._recipe_cuisine(cand["recipe_idx"]) or "unknown"
            if counts.get(group, 0) < max_per_group:
                counts[group] = counts.get(group, 0) + 1
                accepted.append(cand)
            else:
                deferred.append(cand)
            if len(accepted) >= n:
                break

        # If the cap left empty slots (not enough diverse groups available),
        # backfill with the best of the deferred candidates.
        if len(accepted) < n:
            accepted.extend(deferred[: n - len(accepted)])

        return accepted[:n]

    # ── Freshness layer (Layer 4) ───────────────────────────────────────────

    def apply_freshness(self, candidates, exclude_idx=None, jitter=0.12, seed=None):
        """Layer 4 — Freshness.

        - Drops items the user was already shown very recently (so the
          same top-10 doesn't reappear on every refresh).
        - Adds a small amount of controlled randomness to the relevance
          score before final ranking, so that ties near the top of the
          list reshuffle slightly between requests instead of being
          perfectly deterministic, while still respecting the model's
          overall ordering (high jitter would break relevance, so this
          stays small).
        """
        exclude_idx = set(exclude_idx or [])
        rng = np.random.default_rng(seed)

        fresh = [c for c in candidates if c["recipe_idx"] not in exclude_idx]
        # If excluding recently-seen items leaves too few candidates,
        # fall back to the full pool rather than starving the user.
        pool = fresh if len(fresh) >= max(3, len(candidates) // 3) else candidates

        out = []
        for cand in pool:
            noisy = dict(cand)
            noisy["score"] = float(cand["score"]) * (1.0 + rng.uniform(-jitter, jitter))
            out.append(noisy)
        out.sort(key=lambda c: c["score"], reverse=True)
        return out

    def recommend_pipeline(
        self,
        user_idx,
        train_matrix,
        n=10,
        exclude_idx=None,
        lambda_diversity=0.5,
        fairness_max_share=0.34,
        freshness_jitter=0.12,
        seed=None,
    ):
        """Full 4-layer recommendation pipeline.

            INPUT: user request
              -> Layer 1: Base model (ALS)              -> relevance
              -> Layer 4: Freshness (jitter + exclude)   -> freshness
              -> Layer 3: Fairness monitor (cuisine cap) -> fairness
              -> Layer 2: Diversity re-ranker (MMR)      -> diversity
              -> FINAL OUTPUT: top-n recommendations

        Fairness runs BEFORE the MMR diversity narrowing, deliberately:
        it needs to see the wide, multi-cuisine candidate pool to have
        any alternates to backfill with. If a user's taste vector skews
        heavily toward one cuisine (very common with few real
        interactions), MMR's narrowed top-n*2 picks can end up almost
        entirely that one cuisine — at which point fairness has nothing
        left to balance against.

        The base ALS model is loaded once at startup from the pre-trained
        artefacts (als_model.pkl) — it is NOT retrained on every request.
        Only this lightweight re-ranking pipeline runs per request, which
        is why recommendations can legitimately change on every refresh
        without needing to retrain the model each time.
        """
        # Layer 1 — relevance: pull a wide candidate pool from the trained
        # ALS model (much larger than n so the later layers have enough
        # room to re-rank / filter / diversify without running dry).
        candidates = self.recommend(user_idx, train_matrix, n=max(n * 5, 30))
        if not candidates:
            return candidates

        # Layer 4 happens first in terms of candidate *selection* (exclude
        # recently-seen items + jitter) so the diversity/fairness layers
        # work over a pool that already varies between requests.
        candidates = self.apply_freshness(
            candidates, exclude_idx=exclude_idx, jitter=freshness_jitter, seed=seed
        )

        # Layer 3 — fairness monitor: cap any single cuisine's share,
        # applied on the WIDE candidate pool (not yet narrowed by MMR) so
        # there are actually enough alternate-cuisine candidates to pick
        # from. Running this after MMR (on an already-narrowed pool) was
        # the original bug: if a user's ALS vector skews heavily toward
        # one cuisine (very likely with few real interactions), MMR's
        # top n*2 picks can end up almost entirely that one cuisine,
        # leaving fairness with nothing else to backfill from.
        pool_size = min(n * 2, len(candidates))
        balanced = self.apply_fairness_cap(candidates, n=pool_size, max_share=fairness_max_share)

        # Layer 2 — diversity re-ranking via MMR over item embeddings,
        # within the already cuisine-balanced pool. MMR's own formula
        # still weighs raw relevance, so when relevance scores are very
        # skewed (e.g. one cuisine scoring far above everything else —
        # again, typical with very few real interactions), MMR alone can
        # re-concentrate the final top-n back toward that cuisine even
        # though the pool it drew from was balanced.
        reranked = self.recommend_diverse(
            user_idx, train_matrix, n=pool_size,
            lambda_diversity=lambda_diversity, pool=balanced,
        )

        # Fairness cap again, now on the MMR output, as a hard final
        # guarantee — backfilling (if needed) from the same already
        # cuisine-balanced pool, so it never has to fall back to
        # re-admitting over-cap items the way a single fairness pass
        # would when it runs out of alternates.
        final = self.apply_fairness_cap(reranked, n=n, max_share=fairness_max_share)

        return final[:n]

    def cold_start_item(self, recipe_idx, train_matrix, n=10):
        if self.recipes_df is None:
            return []
        known_ids = set(range(train_matrix.shape[1]))
        if recipe_idx in known_ids:
            return self.similar_recipes(recipe_idx, n)
        print(f"\nRecipe {recipe_idx} absente de la matrice — fallback content-based")
        return self.popularity_fallback(train_matrix, n)

    def similar_recipes(self, recipe_idx, n=10):
        ids, scores = self.model.similar_items(recipe_idx, N=n + 1)
        return [
            {"recipe_idx": int(idx), "similarity": float(score)}
            for idx, score in zip(ids[1:], scores[1:])
        ]

    def get_user_embeddings(self):
        return self.model.user_factors

    def get_recipe_embeddings(self):
        return self.model.item_factors

    def predict_score(self, user_idx, recipe_idx):
        user_vector = self.model.user_factors[user_idx]
        recipe_vector = self.model.item_factors[recipe_idx]
        return float(np.dot(user_vector, recipe_vector))

    def predict_scores_batch(self, user_indices, item_indices):
        user_vectors = self.model.user_factors[user_indices]
        item_vectors = self.model.item_factors[item_indices]
        return np.sum(user_vectors * item_vectors, axis=1)

    def popularity_fallback(self, train_matrix, top_n=10):
        popularity = np.array(train_matrix.sum(axis=0)).flatten()
        return np.argsort(popularity)[::-1][:top_n].tolist()

    def recall_at_k(self, train_matrix, test_matrix, k=10):
        hits, total = 0, 0
        for user_idx in range(train_matrix.shape[0]):
            true_items = set(test_matrix[user_idx].indices)
            if not true_items:
                continue
            rec_ids = {r["recipe_idx"] for r in self.recommend(user_idx, train_matrix, n=k)}
            hits += len(rec_ids & true_items)
            total += min(k, len(true_items))
        return round(hits / total, 4) if total > 0 else 0.0

    def precision_at_k(self, train_matrix, test_matrix, k=10):
        hits, total = 0, 0
        for user_idx in range(train_matrix.shape[0]):
            true_items = set(test_matrix[user_idx].indices)
            if not true_items:
                continue
            rec_ids = {r["recipe_idx"] for r in self.recommend(user_idx, train_matrix, n=k)}
            hits += len(rec_ids & true_items)
            total += k
        return round(hits / total, 4) if total > 0 else 0.0

    def ndcg_at_k(self, train_matrix, test_matrix, k=10):
        ndcg_scores = []
        for user_idx in range(train_matrix.shape[0]):
            true_items = set(test_matrix[user_idx].indices)
            if not true_items:
                continue
            rec_ids = [r["recipe_idx"] for r in self.recommend(user_idx, train_matrix, n=k)]
            dcg = sum(1.0 / np.log2(rank + 2) for rank, item in enumerate(rec_ids) if item in true_items)
            idcg = sum(1.0 / np.log2(rank + 2) for rank in range(min(k, len(true_items))))
            ndcg_scores.append(dcg / idcg if idcg > 0 else 0.0)
        return round(float(np.mean(ndcg_scores)), 4) if ndcg_scores else 0.0

    def map_at_k(self, train_matrix, test_matrix, k=10):
        ap_scores = []
        for user_idx in range(train_matrix.shape[0]):
            true_items = set(test_matrix[user_idx].indices)
            if not true_items:
                continue
            rec_ids = [r["recipe_idx"] for r in self.recommend(user_idx, train_matrix, n=k)]
            hits, ap = 0, 0.0
            for rank, item in enumerate(rec_ids, 1):
                if item in true_items:
                    hits += 1
                    ap += hits / rank
            ap_scores.append(ap / min(k, len(true_items)))
        return round(float(np.mean(ap_scores)), 4) if ap_scores else 0.0

    def rmse(self, train_matrix, test_matrix):
        users, items = test_matrix.nonzero()
        if len(users) == 0:
            return 0.0
        preds = self.predict_scores_batch(users, items)
        reals = np.array([test_matrix[u, i] for u, i in zip(users, items)])
        errors = (reals - preds) ** 2
        return round(np.sqrt(np.mean(errors)), 4)

    def mae(self, train_matrix, test_matrix):
        users, items = test_matrix.nonzero()
        if len(users) == 0:
            return 0.0
        preds = self.predict_scores_batch(users, items)
        reals = np.array([test_matrix[u, i] for u, i in zip(users, items)])
        errors = np.abs(reals - preds)
        return round(np.mean(errors), 4)

    def evaluate(self, train_matrix, test_matrix, k=10):
        print("\nEVALUATION DU MODELE")
        print("--------------------")
        recall = self.recall_at_k(train_matrix, test_matrix, k)
        precision = self.precision_at_k(train_matrix, test_matrix, k)
        ndcg = self.ndcg_at_k(train_matrix, test_matrix, k)
        map_k = self.map_at_k(train_matrix, test_matrix, k)
        rmse = self.rmse(train_matrix, test_matrix)
        mae = self.mae(train_matrix, test_matrix)
        print(f"Recall@{k}    : {recall}")
        print(f"Precision@{k} : {precision}")
        print(f"NDCG@{k}      : {ndcg}")
        print(f"MAP@{k}       : {map_k}")
        print(f"RMSE          : {rmse}")
        print(f"MAE           : {mae}")
        return {"recall": recall, "precision": precision, "ndcg": ndcg, "map": map_k, "rmse": rmse, "mae": mae}


if __name__ == "__main__":
    recommender = ALSRecipeRecommender(
        factors=64, regularization=0.05, iterations=15, alpha=20, use_gpu=False, use_bm25=True
    )
    recommender.load_metadata()
    train_matrix = recommender.load_matrix(os.path.join(SPARSE_DIR, "train_matrix.npz"))
    train_matrix = recommender.preprocess_matrix(train_matrix)
    recommender.fit(train_matrix)
    recommender.save_model()
    recommender.save_embeddings()

    print("\n")
    print("MODEL STATISTICS")
    print("----------------")
    print("User embeddings   :", recommender.get_user_embeddings().shape)
    print("Recipe embeddings :", recommender.get_recipe_embeddings().shape)

    test_matrix = recommender.load_matrix(os.path.join(SPARSE_DIR, "test_matrix.npz"))
    recommender.evaluate(train_matrix, test_matrix, k=10)

    print("\n")
    print("TEST FILTRAGE PAR REGIME")
    print("------------------------")
    if recommender.user_enc is not None and recommender.item_enc is not None:
        sample_user_idx = 0
        recs_filtered = recommender.recommend_with_regime_filter(
            sample_user_idx, train_matrix,
            recommender.user_enc, recommender.item_enc, n=5
        )
        print(f"Recommandations filtrees pour user {sample_user_idx}:")
        for r in recs_filtered:
            print(f"  - {r.get('title', 'N/A')} ({r.get('cuisine', 'N/A')}) | regime: {r.get('regime', 'N/A')} | score: {r['score']:.4f}")

    print("\n")
    print("DEMO INCREMENTAL UPDATE")
    print("-----------------------")
    print("Pour mettre a jour le modele avec de nouvelles interactions:")
    print("  recommender.update_model(new_interactions_df, user_enc, item_enc)")

    print("\nALS model successfully trained")