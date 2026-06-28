"""
restore_seed_ratings.py — Restaure note_moyenne/nb_avis depuis
raw_recipes.csv pour les recettes que recompute_ratings.py a remises à
0.0 (0) par erreur (il recalculait uniquement à partir des vraies
interactions Postgres, écrasant les notes de démo importées du CSV)


Depuis Backend/ :
    python scripts/restore_seed_ratings.py
"""

import os
import sys
import csv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
RECIPES_CSV = os.path.join(PROJECT_ROOT, "Recommender", "Dataset", "Raw", "raw_recipes.csv")

from db.database import SessionLocal  
from db.models import Recipe  


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
        restored = 0
        recipes = db.query(Recipe).filter(Recipe.id.in_(rows.keys())).all()
        for recipe in recipes:
            if recipe.nb_avis:  # already has a real rating — don't touch it
                continue
            row = rows.get(recipe.id)
            if not row:
                continue
            recipe.note_moyenne = safe_float(row.get("note_moyenne"), 0.0)
            recipe.nb_avis = safe_int(row.get("nb_avis"), 0)
            restored += 1
        db.commit()
        print(f"{restored} recette(s) restaurée(s) depuis raw_recipes.csv.")
    finally:
        db.close()


if __name__ == "__main__":
    main()