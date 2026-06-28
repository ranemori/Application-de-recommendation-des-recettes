"""
Seed script — imports the CSV datasets from Recommender/Dataset/Raw into the
PostgreSQL database, and copies the recipe images into the static folder
served by FastAPI.

Run from the Backend/ directory:

    python scripts/seed_data.py
"""

import os
import sys
import csv
import shutil

# Make sure Backend/ is on sys.path 
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from db.database import SessionLocal, engine, Base 
from db.models import Recipe, Ingredient, RecipeIngredient 
from sqlalchemy import text 

# ─── Paths ─────────────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
RECOMMENDER_DIR = os.path.join(PROJECT_ROOT, "Recommender")
RAW_DIR = os.path.join(RECOMMENDER_DIR, "Dataset", "Raw")
IMAGES_SRC_DIR = os.path.join(RECOMMENDER_DIR, "Dataset", "Images")

IMAGES_DEST_DIR = os.path.join(PROJECT_ROOT, "static", "images")

RECIPES_CSV = os.path.join(RAW_DIR, "raw_recipes.csv")
INGREDIENTS_CSV = os.path.join(RAW_DIR, "ingredients.csv")
RECIPE_INGREDIENTS_CSV = os.path.join(RAW_DIR, "recipe_ingredients.csv")

# The CSVs were exported from Windows tools 
ENCODING = "cp1252"

# Allowed enum values on the Recipe/User models (db/models.py)
VALID_REGIMES = {"normal", "végétarien", "sans gluten", "végétalien"}
VALID_DIFFS = {"facile", "moyen", "difficile"}


def read_csv(path):
    with open(path, encoding=ENCODING, newline="") as f:
        return list(csv.DictReader(f))


def safe_int(v, default=None):
    try:
        return int(float(v)) if v not in (None, "") else default
    except (ValueError, TypeError):
        return default


def safe_float(v, default=None):
    try:
        return float(v) if v not in (None, "") else default
    except (ValueError, TypeError):
        return default


def normalize_regime(v):
    v = (v or "").strip()
    return v if v in VALID_REGIMES else "normal"


def normalize_diff(v):
    v = (v or "").strip()
    return v if v in VALID_DIFFS else "moyen"


def copy_images():
    os.makedirs(IMAGES_DEST_DIR, exist_ok=True)
    if not os.path.isdir(IMAGES_SRC_DIR):
        print(f" Image source folder not found: {IMAGES_SRC_DIR} (skipping image copy)")
        return
    count = 0
    for fname in os.listdir(IMAGES_SRC_DIR):
        src = os.path.join(IMAGES_SRC_DIR, fname)
        dst = os.path.join(IMAGES_DEST_DIR, fname)
        if os.path.isfile(src):
            shutil.copyfile(src, dst)
            count += 1
    print(f" Copied {count} image(s) to {IMAGES_DEST_DIR}")


def image_url_for(image_path):
    """Build the public /static/images/<file> URL for a recipe.
    """
    if not image_path:
        return None

    raw_name = os.path.basename(image_path.replace("\\", "/"))
    stem, ext = os.path.splitext(raw_name)

    if ext:
        # Extension already present — use it directly if the file exists.
        if os.path.exists(os.path.join(IMAGES_DEST_DIR, raw_name)):
            return f"/static/images/{raw_name}"

    if os.path.isdir(IMAGES_DEST_DIR):
        for fname in os.listdir(IMAGES_DEST_DIR):
            if os.path.splitext(fname)[0] == (stem or raw_name):
                return f"/static/images/{fname}"

    # Last resort: keep the original behaviour so nothing silently disappears, even if we couldn't verify the file is there
    return f"/static/images/{raw_name}"


def seed_ingredients(db):
    rows = read_csv(INGREDIENTS_CSV)
    existing_ids = {i.id for i in db.query(Ingredient.id).all()}
    created = 0
    for row in rows:
        ing_id = safe_int(row["ingredient_id"])
        if ing_id in existing_ids:
            continue
        db.add(Ingredient(
            id=ing_id,
            name=row["name"].strip(),
            categorie=row.get("categorie") or None,
            unite_standard=row.get("unite_standard") or None,
            allergen=row.get("allergen") or None,
        ))
        created += 1
    db.commit()
    print(f" Ingredients: {created} created ({len(rows)} in CSV)")


def seed_recipes(db):
    rows = read_csv(RECIPES_CSV)
    existing_ids = {r.id for r in db.query(Recipe.id).all()}
    created = 0
    for row in rows:
        recipe_id = safe_int(row["recipe_id"])
        if recipe_id in existing_ids:
            continue

        instructions = (row.get("instructions") or "").replace(";", "\n").strip()
        tags = [t.strip() for t in (row.get("tags") or "").split(",") if t.strip()]

        db.add(Recipe(
            id=recipe_id,
            title=row["title"].strip(),
            description=row.get("description") or None,
            instructions=instructions or None,
            cuisine=(row.get("cuisine") or "").strip() or None,
            regime=normalize_regime(row.get("regime")),
            difficulte=normalize_diff(row.get("difficulte")),
            temps_preparation=safe_int(row.get("temps_preparation")),
            niveau_calorie=safe_int(row.get("niveau_calorie")),
            n_ingredients=safe_int(row.get("n_ingredients")),
            n_instructions=safe_int(row.get("n_instructions")),
            image_url=image_url_for(row.get("image_path")),
            tags=tags,
            is_published=True,
            note_moyenne=safe_float(row.get("note_moyenne"), 0.0),
            nb_avis=safe_int(row.get("nb_avis"), 0),
        ))
        created += 1
    db.commit()
    print(f" Recipes: {created} created ({len(rows)} in CSV)")


def seed_recipe_ingredients(db):
    rows = read_csv(RECIPE_INGREDIENTS_CSV)
    existing_recipes = {r.id: r for r in db.query(Recipe).all()}
    existing_ingredients = {i.id: i for i in db.query(Ingredient).all()}
    existing_links = {
        (l.recipe_id, l.ingredient_id) for l in db.query(RecipeIngredient).all()
    }
    created = 0
    skipped = 0
    for row in rows:
        recipe_id = safe_int(row["recipe_id"])
        ingredient_id = safe_int(row["ingredient_id"])
        if recipe_id not in existing_recipes or ingredient_id not in existing_ingredients:
            skipped += 1
            continue
        if (recipe_id, ingredient_id) in existing_links:
            continue
        
        unite = row.get("unite") or existing_ingredients[ingredient_id].unite_standard or None
        db.add(RecipeIngredient(
            recipe_id=recipe_id,
            ingredient_id=ingredient_id,
            quantite=safe_float(row.get("quantite")),
            unite=unite,
        ))
        existing_links.add((recipe_id, ingredient_id))
        created += 1
    db.commit()
    print(f"Recipe-Ingredient links: {created} created, {skipped} skipped (missing FK)")


def seed_als_item_idx(db):
    """Populate Recipe.als_item_idx from the trained item_encoder, so the
    ALS 'similar recipes' feature works without needing a retrain."""
    item_encoder_path = os.path.join(RECOMMENDER_DIR, "Dataset", "Mapping", "item_encoder.pkl")
    if not os.path.exists(item_encoder_path):
        print(f" Item encoder not found: {item_encoder_path} (skipping als_item_idx)")
        return
    try:
        import pickle
        with open(item_encoder_path, "rb") as f:
            item_enc = pickle.load(f)
    except Exception as exc:
        print(f" Could not load item encoder ({exc}); skipping als_item_idx")
        return

    updated = 0
    recipes = db.query(Recipe).all()
    known_ids = set(int(c) for c in getattr(item_enc, "classes_", []))
    for recipe in recipes:
        if recipe.id not in known_ids:
            continue
        try:
            idx = int(item_enc.transform([recipe.id])[0])
        except Exception:
            continue
        if recipe.als_item_idx != idx:
            recipe.als_item_idx = idx
            updated += 1
    db.commit()
    print(f" als_item_idx set on {updated} recipe(s)")


def resync_id_sequences(db):
    for table, pk in [("recipes", "id"), ("ingredients", "id")]:
        db.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{table}', '{pk}'), "
            f"COALESCE((SELECT MAX({pk}) FROM {table}), 1))"
        ))
    db.commit()


def main():
    print("── Creating tables if missing ──")
    Base.metadata.create_all(bind=engine)

    print("── Copying images ──")
    copy_images()

    db = SessionLocal()
    try:
        print("── Seeding ingredients ──")
        seed_ingredients(db)
        print("── Seeding recipes ──")
        seed_recipes(db)
        print("── Seeding recipe-ingredient links ──")
        seed_recipe_ingredients(db)
        print("── Mapping ALS item indices ──")
        seed_als_item_idx(db)
        print("── Resyncing id sequences ──")
        resync_id_sequences(db)
    finally:
        db.close()

    print(" Done.")


if __name__ == "__main__":
    main()