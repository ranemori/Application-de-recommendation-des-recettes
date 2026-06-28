"""
backfill_seed_baseline.py — À lancer UNE FOIS après avoir ajouté les
colonnes seed_note_moyenne/seed_nb_avis 

1. Lit raw_recipes.csv et enregistre son note_moyenne/nb_avis 
2. Recalcule note_moyenne/nb_avis pour toute recette ayant déjà reçu une
   vraie note 

Depuis Backend/ :
    python scripts/backfill_seed_baseline.py
"""

import os
import sys
import csv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
RECIPES_CSV = os.path.join(PROJECT_ROOT, "Recommender", "Dataset", "Raw", "raw_recipes.csv")

from db.database import SessionLocal  
from db.models import Recipe, Interaction, InteractionType 
from api.interactions import _recompute_recipe_rating  


def safe_int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def main():
    if not os.path.exists(RECIPES_CSV):
        print(f"Introuvable : {RECIPES_CSV}")
        return

    with open(RECIPES_CSV, "r", encoding="cp1252", newline="") as f:
        rows = {safe_int(row["recipe_id"]): row for row in csv.DictReader(f)}

    db = SessionLocal()
    try:
        print("── Étape 1 : socle seed_note_moyenne / seed_nb_avis ──")
        recipes = db.query(Recipe).filter(Recipe.id.in_(rows.keys())).all()
        n = 0
        for recipe in recipes:
            row = rows[recipe.id]
            recipe.seed_note_moyenne = safe_float(row.get("note_moyenne"), 0.0)
            recipe.seed_nb_avis = safe_int(row.get("nb_avis"), 0)
            recipe.note_moyenne = recipe.seed_note_moyenne
            recipe.nb_avis = recipe.seed_nb_avis
            n += 1
        db.commit()
        print(f"{n} recette(s) avec un socle CSV.")

        print("── Étape 2 : recombinaison des recettes déjà notées réellement ──")
        rated_recipe_ids = {
            row.recipe_id for row in
            db.query(Interaction.recipe_id)
            .filter(Interaction.interaction_type == InteractionType.rating)
            .distinct()
            .all()
        }
        for rid in rated_recipe_ids:
            _recompute_recipe_rating(db, rid)
        print(f"{len(rated_recipe_ids)} recette(s) recombinée(s).")

    finally:
        db.close()


if __name__ == "__main__":
    main()