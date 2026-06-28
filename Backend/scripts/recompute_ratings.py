"""
recompute_ratings.py — Recalcule note_moyenne/nb_avis pour TOUTES les
recettes à partir des interactions de type "rating" déjà en base

À lancer une seule fois après avoir déployé le correctif de
api/interactions.py 

Depuis Backend/ :
    python scripts/recompute_ratings.py
"""

import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from db.database import SessionLocal  
from db.models import Recipe  
from api.interactions import _recompute_recipe_rating  


def main():
    db = SessionLocal()
    try:
        recipe_ids = [r.id for r in db.query(Recipe.id).all()]
        print(f"Recalcul de la note pour {len(recipe_ids)} recette(s)…")
        for rid in recipe_ids:
            _recompute_recipe_rating(db, rid)
        print("Terminé.")
    finally:
        db.close()


if __name__ == "__main__":
    main()