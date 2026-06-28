"""
ALSService — thin wrapper around the existing ALSRecipeRecommender
Loads the model once at startup and exposes clean methods for the API
Falls back gracefully to popularity-based recommendations when the model
is unavailable 
"""

import os
import sys
import pickle
import logging
from typing import List, Optional
from functools import lru_cache

import numpy as np
import scipy.sparse as sp

from core.config import settings

logger = logging.getLogger(__name__)


def _import_recommender():
    """Dynamically import ALSRecipeRecommender from the Recommender package."""
    # settings.RECOMMENDER_BASE_DIR points AT the Recommender/ folder itself...
    base = os.path.dirname(os.path.abspath(settings.RECOMMENDER_BASE_DIR))
    if base not in sys.path:
        sys.path.insert(0, base)
    try:
        from Recommender.model_als import ALSRecipeRecommender
        return ALSRecipeRecommender
    except ImportError as e:
        logger.warning(f"Could not import ALSRecipeRecommender: {e}")
        return None


class ALSService:
    """Singleton service — call get_als_service() to obtain it"""

    def __init__(self):
        self._recommender = None
        self._train_matrix = None
        self._user_enc = None
        self._item_enc = None
        self._ready = False
        self._load()

    def _load(self):
        """Try to load all artefacts. Silently degrade if any is missing"""
        try:
            ALS = _import_recommender()
            if ALS is None:
                return

            self._recommender = ALS()

            # Load encoders
            for path_attr, enc_attr in [
                ("USER_ENCODER_PATH", "_user_enc"),
                ("ITEM_ENCODER_PATH", "_item_enc"),
            ]:
                path = getattr(settings, path_attr)
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        setattr(self, enc_attr, pickle.load(f))

            # Load trained model
            if os.path.exists(settings.ALS_MODEL_PATH):
                self._recommender.load_model(settings.ALS_MODEL_PATH)

            # Load train matrix
            if os.path.exists(settings.TRAIN_MATRIX_PATH):
                self._train_matrix = sp.load_npz(settings.TRAIN_MATRIX_PATH)

            try:
                self._recommender.load_metadata(
                    recipes_path=settings.RAW_RECIPES_PATH,
                    users_path=settings.RAW_USERS_PATH,
                    user_enc_path=settings.USER_ENCODER_PATH,
                    item_enc_path=settings.ITEM_ENCODER_PATH,
                )
            except Exception as meta_exc:
                logger.warning(
                    f"ALS metadata (recipes/users CSV) failed to load — "
                    f"cuisine fairness layer will be skipped, but core "
                    f"ALS recommendations still work: {meta_exc}"
                )

            if (
                self._recommender.model is not None
                and self._train_matrix is not None
                and self._user_enc is not None
                and self._item_enc is not None
            ):
                self._ready = True
                logger.info("ALS service ready")
            else:
                logger.warning("ALS service partially loaded — using fallback")

        except Exception as exc:
            logger.error(f"ALS service failed to load: {exc}", exc_info=True)

    @property
    def is_ready(self) -> bool:
        return self._ready

    def reload(self):
        """Re-read all model/encoder/matrix files from disk. Call this right
        after a (re)training run so the running server picks up the new
        artefacts immediately, with no restart needed"""
        self._recommender = None
        self._train_matrix = None
        self._user_enc = None
        self._item_enc = None
        self._ready = False
        self._load()

    @property
    def n_train_users(self) -> int:
        """How many users the currently loaded model was actually trained
        on — used to decide whether ALS similarity is trustworthy yet"""
        if self._train_matrix is None:
            return 0
        return self._train_matrix.shape[0]

    def item_interaction_count(self, als_item_idx: Optional[int]) -> int:
        """How many (real) users interacted with this item in the training
        matrix. An item with 0 or 1 interactions has barely moved away
        from its random/regularized initialization, so its ALS similarity
        score is not trustworthy yet"""
        if als_item_idx is None or self._train_matrix is None:
            return 0
        if als_item_idx >= self._train_matrix.shape[1]:
            return 0
        return int(self._train_matrix[:, als_item_idx].getnnz())

    def recommend_for_user(
        self, als_user_idx: int, n: int = 12, diverse: bool = True
    ) -> List[dict]:
        """
        Return up to n recommendations for a user identified by their
        ALS matrix index. Returns empty list if model is not ready
        """
        if not self._ready:
            return []
        try:
            if diverse:
                recs = self._recommender.recommend_diverse(
                    als_user_idx, self._train_matrix, n=n
                )
            else:
                recs = self._recommender.recommend(
                    als_user_idx, self._train_matrix, n=n
                )
            return recs
        except Exception as exc:
            logger.error(f"recommend_for_user error: {exc}")
            return []

    def recommend_pipeline(
        self,
        als_user_idx: int,
        n: int = 12,
        exclude_idx: Optional[List[int]] = None,
        seed: Optional[int] = None,
    ) -> List[dict]:
        """Run the full 4-layer pipeline (relevance -> diversity ->
        fairness -> freshness) using the already-trained model. This does
        NOT retrain anything — it only re-ranks candidates produced by the
        pre-trained ALS factors, which is why it is cheap enough to run on
        every page refresh and still return a different, still-relevant
        set of recipes
        """
        if not self._ready:
            return []
        try:
            return self._recommender.recommend_pipeline(
                als_user_idx,
                self._train_matrix,
                n=n,
                exclude_idx=exclude_idx,
                seed=seed,
            )
        except Exception as exc:
            logger.error(f"recommend_pipeline error: {exc}")
            return []

    def recommend_filtered(
        self, als_user_idx: int, n: int = 12
    ) -> List[dict]:
        """Recommendations filtered by user's dietary regime"""
        if not self._ready:
            return []
        try:
            return self._recommender.recommend_with_regime_filter(
                als_user_idx,
                self._train_matrix,
                self._user_enc,
                self._item_enc,
                n=n,
            )
        except Exception as exc:
            logger.error(f"recommend_filtered error: {exc}")
            return []

    def similar_recipes(self, als_item_idx: int, n: int = 8) -> List[dict]:
        """Find similar recipes using item embeddings"""
        if not self._ready:
            return []
        try:
            return self._recommender.similar_recipes(als_item_idx, n=n)
        except Exception as exc:
            logger.error(f"similar_recipes error: {exc}")
            return []

    def popularity_fallback(self, n: int = 12) -> List[int]:
        """Return most-popular item indices as a cold-start fallback"""
        if not self._ready or self._train_matrix is None:
            return []
        try:
            return self._recommender.popularity_fallback(self._train_matrix, top_n=n)
        except Exception as exc:
            logger.error(f"popularity_fallback error: {exc}")
            return []

    def get_als_user_idx(self, db_user_id: int) -> Optional[int]:
        """Map a DB user_id to an ALS matrix row index"""
        if self._user_enc is None:
            return None
        try:
            return int(self._user_enc.transform([db_user_id])[0])
        except Exception:
            return None

    def get_als_item_idx(self, db_recipe_id: int) -> Optional[int]:
        """Map a DB recipe_id to an ALS matrix column index"""
        if self._item_enc is None:
            return None
        try:
            return int(self._item_enc.transform([db_recipe_id])[0])
        except Exception:
            return None


# ─── Singleton ────────────────────────────────────────────────────────────────

_als_service: Optional[ALSService] = None


def get_als_service() -> ALSService:
    global _als_service
    if _als_service is None:
        _als_service = ALSService()
    return _als_service