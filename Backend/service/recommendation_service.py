"""
RecommendationService — orchestrates ALS, fridge, and fallback strategies.
"""

from typing import List, Optional
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from db.models import Recipe, RecipeIngredient, Interaction, InteractionType, User
from service.als_service import get_als_service
from db.schemas import RecommendationOut, RecipeCard


class RecommendationService:

    def __init__(self, db: Session):
        self.db = db
        self.als = get_als_service()

    # ── Personalized (ALS) ────────────────────────────────────────────────────

    def _effective_cuisines(self, user: User) -> set:
        """The set of cuisines that should count as 'this user's taste',
        combining:
          - what they declared once at onboarding (preferences_cuisine)
          - cuisines of recipes they've actually liked / saved / rated
            highly since then

        """
        cuisines = {c.lower() for c in (user.preferences_cuisine or []) if c}

        positive = (
            self.db.query(Recipe.cuisine)
            .join(Interaction, Interaction.recipe_id == Recipe.id)
            .filter(
                Interaction.user_id == user.id,
                Recipe.cuisine.isnot(None),
                (
                    ((Interaction.interaction_type == "like") & (Interaction.score > 0))
                    | ((Interaction.interaction_type == "save") & (Interaction.score > 0))
                    | ((Interaction.interaction_type == "rating") & (Interaction.score >= 0.6))
                ),
            )
            .distinct()
            .all()
        )
        cuisines.update(c.lower() for (c,) in positive if c)
        return cuisines

    def for_user(self, user: User, n: int = 12) -> List[RecommendationOut]:
        """Main recommendation pipeline for a logged-in user.

        Runs the 4-layer pipeline (relevance -> diversity -> fairness ->
        freshness) on top of the already-trained ALS model. Nothing is
        retrained here — only the lightweight re-ranking layers run per
        request, which is exactly why the result can legitimately differ
        on every refresh instead of always returning the same static
        top-n.
        """
        # IMPORTANT: only use ALS if this exact user was part of an actual
        # training run (als_user_idx populated by the training pipeline).
        # Do NOT derive this from user.id — the synthetic training dataset
        # and the real users table share the same auto-increment id space,
        # so a raw transform(user.id) would silently return a stranger's
        # taste profile instead of correctly falling back to popularity.
        als_idx = user.als_user_idx

        if als_idx is not None and self.als.is_ready:
            recent_idx = self._recent_als_item_idx(user, limit=30)
            recs_raw = self.als.recommend_pipeline(
                als_idx, n=n * 3, exclude_idx=recent_idx
            )
            hydrated = self._hydrate_by_idx(recs_raw, reason="ALS", score_key="score")
            filtered = self._filter_by_user_prefs(hydrated, user)
            pool = filtered if len(filtered) >= max(3, n // 2) else hydrated
            if pool:
                pool = self._apply_recency_boost(pool, user)
                return pool[:n]

        # Cold-start: use popularity + preference filters
        return self._popularity(n=n, user=user)

    def _apply_recency_boost(self, recs: List[RecommendationOut], user: User) -> List[RecommendationOut]:
        """Real-time re-ranking layer on top of the (slow-moving) ALS
        profile — this is the piece that makes a like/save feel like it
        immediately affects what you see, the way Temu/TikTok-style feeds
        do, without waiting for a full model retrain. Two things happen:

          1. Recipes sharing a cuisine with the user's last few positive
             interactions get pulled toward the top.
          2. The remaining items get lightly shuffled, so refreshing the
             page visibly varies the order instead of returning the exact
             same static list every time — ALS retraining is still what
             drives the *underlying* taste profile over time, this layer
             just makes the surface feel alive between retrains.
        """
        boost_cuisines = self._recent_positive_cuisines(user)
        if boost_cuisines:
            boosted = [r for r in recs if r.recipe.cuisine in boost_cuisines]
            rest = [r for r in recs if r.recipe.cuisine not in boost_cuisines]

            # The ALS pool might not contain ANY recipe in a recently-liked
            # cuisine at all (e.g. a long history dominated by other
            # cuisines can keep a niche one out of the model's own top-N
            # entirely) — reordering can't surface what was never in the
            # candidate list to begin with. So explicitly pull a couple of
            # well-rated recipes from those cuisines straight from the DB
            # and guarantee their presence, instead of only hoping the
            # ALS pool happens to already include one.
            already_ids = {r.recipe.id for r in recs}
            extra_query = self.db.query(Recipe).filter(
                Recipe.cuisine.in_(boost_cuisines),
                Recipe.is_published == True,
            )
            if already_ids:
                extra_query = extra_query.filter(~Recipe.id.in_(already_ids))
            extra = extra_query.order_by(Recipe.note_moyenne.desc()).limit(3).all()
            extra_out = [
                RecommendationOut(recipe=RecipeCard.model_validate(r), score=1.0, reason="Récemment apprécié")
                for r in extra
            ]
            boosted = extra_out + boosted
        else:
            boosted, rest = [], list(recs)
        random.shuffle(rest)
        return boosted + rest

    def _recent_positive_cuisines(self, user: User, limit: int = 5, minutes: int = 1440) -> set:
        """Cuisines behind the user's most recent likes/saves/good ratings
        (last `minutes`), used to give those a real-time nudge in for_user()."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        rows = (
            self.db.query(Interaction)
            .filter(
                Interaction.user_id == user.id,
                Interaction.interaction_type.in_([
                    InteractionType.like, InteractionType.save, InteractionType.rating,
                ]),
                Interaction.score > 0,
                Interaction.created_at >= cutoff,
            )
            .order_by(Interaction.created_at.desc())
            .limit(limit)
            .all()
        )
        recipe_ids = [r.recipe_id for r in rows]
        if not recipe_ids:
            return set()
        return {
            c for (c,) in self.db.query(Recipe.cuisine)
            .filter(Recipe.id.in_(recipe_ids), Recipe.cuisine.isnot(None))
            .all()
        }

    def _recent_als_item_idx(self, user: User, limit: int = 30) -> List[int]:
        """ALS matrix indices of recipes the user interacted with most
        recently — fed into the freshness layer so the same items don't
        keep reappearing in the top of the list on every refresh."""
        recent = (
            self.db.query(Interaction)
            .filter(Interaction.user_id == user.id)
            .order_by(Interaction.created_at.desc())
            .limit(limit)
            .all()
        )
        idx = []
        for inter in recent:
            recipe = self.db.query(Recipe).filter(Recipe.id == inter.recipe_id).first()
            if recipe and recipe.als_item_idx is not None:
                idx.append(recipe.als_item_idx)
        return idx

    # ── Fridge matching ───────────────────────────────────────────────────────

    def fridge_match(
        self,
        ingredient_ids: List[int],
        n: int = 12,
        strict: bool = True,
    ) -> List[RecommendationOut]:
        """
        Return recipes whose ingredient list is fully (strict=True) or
        maximally (strict=False) covered by the provided ingredient_ids.
        """
        if not ingredient_ids:
            return []

        # Subquery: count matching ingredients per recipe
        match_count = (
            self.db.query(
                RecipeIngredient.recipe_id,
                func.count(RecipeIngredient.ingredient_id).label("match_count"),
            )
            .filter(RecipeIngredient.ingredient_id.in_(ingredient_ids))
            .group_by(RecipeIngredient.recipe_id)
            .subquery()
        )

        query = (
            self.db.query(Recipe, match_count.c.match_count)
            .join(match_count, Recipe.id == match_count.c.recipe_id)
            .filter(Recipe.is_published == True)
        )

        if strict:
            # Only recipes where ALL ingredients are in the fridge
            query = query.filter(
                match_count.c.match_count == Recipe.n_ingredients
            )
        else:
            # Best coverage first
            query = query.order_by(match_count.c.match_count.desc())

        results = query.limit(n).all()

        output = []
        for recipe, _match in results:
            output.append(
                RecommendationOut(
                    recipe=RecipeCard.model_validate(recipe),
                    score=None,
                    reason="fridge",
                )
            )
        return output

    # ── Similar recipes ───────────────────────────────────────────────────────

    # Minimum real signal required before we trust ALS similarity at all.
    MIN_TRAIN_USERS = 5
    MIN_ITEM_INTERACTIONS = 2

    def similar_to(self, recipe_id: int, n: int = 6) -> List[RecommendationOut]:
        """Find recipes 'similar' to a given one.

        Tests how much real interaction data the model actually has for
        this item:
          - Not enough data yet (too few real users, or this specific
            recipe has 0-1 real interactions) -> pure content-based
            similarity (shared ingredients / tags / cuisine / regime).
          - Enough data -> blend ALS embedding similarity with content
            similarity, so we get genuine collaborative-filtering signal
            ("people who liked X also liked Y", even across cuisines)
            on top of the content guarantee, instead of either one alone.
        """
        recipe = self.db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            return []

        content_scores = self._content_scores(recipe)

        use_als = (
            recipe.als_item_idx is not None
            and self.als.is_ready
            and self.als.n_train_users >= self.MIN_TRAIN_USERS
            and self.als.item_interaction_count(recipe.als_item_idx) >= self.MIN_ITEM_INTERACTIONS
        )

        if not use_als:
            return self._rank_content(recipe, content_scores, n)

        return self._rank_hybrid(recipe, content_scores, n)

    def _ingredient_idf(self) -> dict:
        """Inverse-document-frequency weight per ingredient_id across the
        whole published catalog: an ingredient that appears in almost
        every recipe (ail, oignons, sel, eau, sucre...) gets a weight near
        0, while a distinctive one (tteokbokki, piment coréen) gets a
        weight near 1. Without this, two recipes sharing only generic
        pantry staples register as "similar" purely because their
        ingredient lists are short — which is exactly how an Indian curry
        and a Korean rice cake dish ended up looking related."""
        total_published = self.db.query(Recipe).filter(Recipe.is_published == True).count() or 1
        rows = (
            self.db.query(RecipeIngredient.ingredient_id, func.count(func.distinct(RecipeIngredient.recipe_id)))
            .join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
            .filter(Recipe.is_published == True)
            .group_by(RecipeIngredient.ingredient_id)
            .all()
        )
        import math
        return {
            ing_id: math.log(total_published / count) if count else 1.0
            for ing_id, count in rows
        }

    def _content_scores(self, recipe: Recipe) -> dict:
        """Content-similarity score (shared ingredients/tags/cuisine/regime)
        of every other published recipe against `recipe`, as {recipe_id: score}."""
        source_tags = set(recipe.tags or [])
        source_ing_ids = {
            ri.ingredient_id
            for ri in self.db.query(RecipeIngredient)
            .filter(RecipeIngredient.recipe_id == recipe.id)
            .all()
        }
        idf = self._ingredient_idf()
        # Normalize so the single most distinctive ingredient in the whole
        # catalog maps to weight 1.0 — keeps the final score on a
        # comparable scale to the cuisine/tag weights below.
        max_idf = max(idf.values(), default=1.0) or 1.0

        candidates = (
            self.db.query(Recipe)
            .filter(Recipe.id != recipe.id, Recipe.is_published == True)
            .all()
        )

        scores = {}
        for cand in candidates:
            cand_tags = set(cand.tags or [])
            cand_ing_ids = {
                ri.ingredient_id
                for ri in self.db.query(RecipeIngredient)
                .filter(RecipeIngredient.recipe_id == cand.id)
                .all()
            }

            tag_overlap = len(source_tags & cand_tags)

            shared_ing = source_ing_ids & cand_ing_ids
            union_ing = source_ing_ids | cand_ing_ids
            # IDF-weighted Jaccard: sharing one rare, distinctive ingredient
            # counts far more than sharing several generic pantry staples.
            weighted_shared = sum(idf.get(i, max_idf) for i in shared_ing) / max_idf
            weighted_union = sum(idf.get(i, max_idf) for i in union_ing) / max_idf
            ing_similarity = weighted_shared / weighted_union if weighted_union else 0.0

            same_cuisine = 1.0 if recipe.cuisine and cand.cuisine == recipe.cuisine else 0.0
            same_regime = 1.0 if recipe.regime and cand.regime == recipe.regime else 0.0

            # Cuisine/tags/ingredients are the SUBSTANTIVE signals — sharing
            # a dietary regime ("végétarien") on its own is too weak to mean
            # "similar recipe" (e.g. an Indian curry and a Korean rice cake
            # being both vegetarian tells you nothing about taste). Regime
            # only counts as a tiebreaker bonus ON TOP of a real match,
            # never as the sole reason a recipe shows up as "similar".
            substantive = same_cuisine * 2.0 + tag_overlap * 1.5 + ing_similarity * 3.0
            if substantive > 0:
                scores[cand.id] = substantive + same_regime * 0.5

        return scores

    def _rank_content(self, recipe: Recipe, content_scores: dict, n: int) -> List[RecommendationOut]:
        ranked = sorted(content_scores.items(), key=lambda kv: kv[1], reverse=True)[:n]
        recipes_by_id = {r.id: r for r in self.db.query(Recipe).filter(Recipe.id.in_([rid for rid, _ in ranked])).all()}
        top = [(score, recipes_by_id[rid]) for rid, score in ranked if rid in recipes_by_id]

        if len(top) < n:
            top = self._pad_with_same_cuisine(recipe, top, n)

        return [
            RecommendationOut(recipe=RecipeCard.model_validate(r), score=round(s, 3), reason="content")
            for s, r in top
        ]

    def _rank_hybrid(self, recipe: Recipe, content_scores: dict, n: int) -> List[RecommendationOut]:
        # Pull a wide ALS candidate pool and resolve recipe_idx -> recipe_id.
        als_raw = self.als.similar_recipes(recipe.als_item_idx, n=n * 4)
        als_scores = {}
        for raw in als_raw:
            cand_id = self._resolve_recipe_id(raw.get("recipe_idx"))
            if cand_id is not None:
                als_scores[cand_id] = raw.get("similarity", 0.0)

        # Normalize both score sets to [0, 1] so the blend isn't dominated
        # by whichever metric happens to have a larger raw scale.
        def normalize(d: dict) -> dict:
            if not d:
                return {}
            vals = list(d.values())
            lo, hi = min(vals), max(vals)
            if hi - lo < 1e-9:
                return {k: 1.0 for k in d}
            return {k: (v - lo) / (hi - lo) for k, v in d.items()}

        als_norm = normalize(als_scores)
        content_norm = normalize(content_scores)

        # Only let a candidate into the blend if it has SOME real basis for
        # being "similar" — either a substantive content match (cuisine/
        # tags/ingredients, from content_scores) or at least the same
        # cuisine. Pure ALS similarity alone is too easy to be embedding
        # noise (especially with limited real training data) and can
        # otherwise surface completely unrelated dishes that just happen
        # to sit close in latent space.
        cand_recipes = {
            r.id: r for r in self.db.query(Recipe)
            .filter(Recipe.id.in_(set(als_scores) | set(content_scores)))
            .all()
        }
        eligible_ids = {
            rid for rid in (set(als_scores) | set(content_scores))
            if rid in content_scores
            or (recipe.cuisine and cand_recipes.get(rid) and cand_recipes[rid].cuisine == recipe.cuisine)
        }

        all_ids = eligible_ids
        blended = {
            rid: 0.6 * als_norm.get(rid, 0.0) + 0.4 * content_norm.get(rid, 0.0)
            for rid in all_ids
        }

        ranked = sorted(blended.items(), key=lambda kv: kv[1], reverse=True)[:n]
        recipes_by_id = {
            r.id: r for r in self.db.query(Recipe).filter(Recipe.id.in_([rid for rid, _ in ranked])).all()
        }
        top = [(score, recipes_by_id[rid]) for rid, score in ranked if rid in recipes_by_id]

        if len(top) < n:
            top = self._pad_with_same_cuisine(recipe, top, n)

        return [
            RecommendationOut(recipe=RecipeCard.model_validate(r), score=round(s, 3), reason="hybrid")
            for s, r in top
        ]

    def _pad_with_same_cuisine(self, recipe: Recipe, top: list, n: int) -> list:
        """Not enough genuinely-scored candidates — fill remaining slots
        with same-cuisine popular recipes rather than an unrelated grab-bag."""
        already_ids = {r.id for _, r in top} | {recipe.id}
        filler = (
            self.db.query(Recipe)
            .filter(
                Recipe.cuisine == recipe.cuisine,
                Recipe.id.notin_(already_ids),
                Recipe.is_published == True,
            )
            .order_by(Recipe.note_moyenne.desc())
            .limit(n - len(top))
            .all()
        )
        return top + [(0.0, r) for r in filler]

    # ── Popularity (fallback) ─────────────────────────────────────────────────

    def _popularity(self, n: int = 12, user: Optional[User] = None) -> List[RecommendationOut]:
        """Cold-start / no-ALS-signal fallback.

        Important: when the user has several preferred cuisines, we must
        NOT just filter to "any of these cuisines" and sort the combined
        pool by rating — that lets whichever single cuisine happens to
        have the highest-rated (or most numerous) dishes crowd out all
        the others entirely (e.g. only French recipes showing up even
        though Lebanese and Moyen-orientale are also preferred). Instead
        we round-robin: best-rated pick from cuisine 1, then cuisine 2,
        then cuisine 3, repeat — so every preferred cuisine gets fair
        representation in the final list.
        """
        base_query = self.db.query(Recipe).filter(Recipe.is_published == True)

        if user and user.regime_alimentaire and user.regime_alimentaire != "normal":
            base_query = base_query.filter(Recipe.regime == user.regime_alimentaire)

        prefs_lower = list(self._effective_cuisines(user)) if user else []
        if prefs_lower:
            per_cuisine = {}
            for cuisine in prefs_lower:
                pool = (
                    base_query
                    .filter(func.lower(Recipe.cuisine) == cuisine)
                    .order_by(Recipe.note_moyenne.desc())
                    .limit(n)
                    .all()
                )
                if pool:
                    per_cuisine[cuisine] = pool

            if per_cuisine:
                ordered, seen_ids = [], set()
                while len(ordered) < n and any(per_cuisine.values()):
                    for cuisine in list(per_cuisine.keys()):
                        bucket = per_cuisine[cuisine]
                        if bucket:
                            candidate = bucket.pop(0)
                            if candidate.id not in seen_ids:
                                ordered.append(candidate)
                                seen_ids.add(candidate.id)
                            if len(ordered) >= n:
                                break

                # A brand-new account with just ONE strong signal (e.g. a
                # single like) ends up with exactly one "preferred cuisine"
                # — without a cap, round-robin over a single cuisine just
                # returns 100% of that one cuisine, which reads as way too
                # extreme an overcorrection from one click. Cap how much of
                # the list a limited set of preferred cuisines can fill,
                # and top up the rest from general popularity (any cuisine)
                # so there's always some variety, however few signals exist.
                max_from_prefs = max(3, int(n * 0.6))
                ordered = ordered[:max_from_prefs]
                if len(ordered) < n:
                    seen_ids = {r.id for r in ordered}
                    extra = (
                        base_query
                        .filter(~Recipe.id.in_(seen_ids))
                        .order_by(Recipe.note_moyenne.desc())
                        .limit(n - len(ordered))
                        .all()
                    )
                    ordered.extend(extra)

                if len(ordered) >= max(3, n // 2):
                    return [
                        RecommendationOut(recipe=RecipeCard.model_validate(r), reason="popularity")
                        for r in ordered[:n]
                    ]
                # Not enough matches across preferred cuisines combined
                # — fall through to the unfiltered popularity ranking
                # below rather than returning a too-short list.

        recipes = base_query.order_by(Recipe.note_moyenne.desc()).limit(n).all()

        # Broaden if too few results
        if len(recipes) < n // 2:
            recipes = (
                self.db.query(Recipe)
                .filter(Recipe.is_published == True)
                .order_by(Recipe.note_moyenne.desc())
                .limit(n)
                .all()
            )

        return [
            RecommendationOut(recipe=RecipeCard.model_validate(r), reason="popularity")
            for r in recipes
        ]

    def _same_cuisine(self, recipe: Recipe, n: int) -> List[RecommendationOut]:
        recipes = (
            self.db.query(Recipe)
            .filter(Recipe.cuisine == recipe.cuisine, Recipe.id != recipe.id)
            .order_by(Recipe.note_moyenne.desc())
            .limit(n)
            .all()
        )
        return [
            RecommendationOut(recipe=RecipeCard.model_validate(r), reason="content")
            for r in recipes
        ]

    # ── Hydration helpers ─────────────────────────────────────────────────────

    def _hydrate(self, recs_raw: list, reason: str) -> List[RecommendationOut]:
        """Convert ALS raw results (with recipe_id) into RecommendationOut."""
        output = []
        for raw in recs_raw:
            recipe_id = raw.get("recipe_id")
            if recipe_id is None:
                # Try resolving via item_enc
                als_idx = raw.get("recipe_idx")
                recipe_id = self._resolve_recipe_id(als_idx)
            if recipe_id is None:
                continue
            recipe = self.db.query(Recipe).filter(Recipe.id == recipe_id).first()
            if recipe and recipe.is_published:
                output.append(
                    RecommendationOut(
                        recipe=RecipeCard.model_validate(recipe),
                        score=raw.get("score"),
                        reason=reason,
                    )
                )
        return output

    def _hydrate_by_idx(self, recs_raw: list, reason: str, score_key: str = "similarity") -> List[RecommendationOut]:
        """Convert ALS raw results (with recipe_idx) into RecommendationOut."""
        output = []
        for raw in recs_raw:
            als_idx = raw.get("recipe_idx")
            recipe = (
                self.db.query(Recipe)
                .filter(Recipe.als_item_idx == als_idx, Recipe.is_published == True)
                .first()
            )
            if recipe:
                output.append(
                    RecommendationOut(
                        recipe=RecipeCard.model_validate(recipe),
                        score=raw.get(score_key),
                        reason=reason,
                    )
                )
        return output

    def _filter_by_user_prefs(self, recs: List[RecommendationOut], user: User) -> List[RecommendationOut]:
        """Filter already-hydrated ALS recommendations by the user's dietary
        regime and effective cuisines (onboarding choices + cuisines they've
        actually liked/saved/rated highly since — see _effective_cuisines)."""
        out = recs
        if user.regime_alimentaire and user.regime_alimentaire != "normal":
            out = [r for r in out if r.recipe.regime == user.regime_alimentaire]
        prefs_lower = self._effective_cuisines(user)
        if prefs_lower:
            out = [r for r in out if (r.recipe.cuisine or "").lower() in prefs_lower]
        return out

    def _resolve_recipe_id(self, als_item_idx: Optional[int]) -> Optional[int]:
        if als_item_idx is None:
            return None
        recipe = (
            self.db.query(Recipe)
            .filter(Recipe.als_item_idx == als_item_idx)
            .first()
        )
        return recipe.id if recipe else None