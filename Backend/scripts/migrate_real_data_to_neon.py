"""
migrate_real_data_to_neon.py — Copie les données réelles générées par les
utilisateurs (comptes, commentaires, interactions, notifications, et toute
recette créée via l'admin) depuis la base PostgreSQL locale vers Neon.

Utilisation, depuis Backend/ :

    $env:LOCAL_DATABASE_URL = "postgresql://user:pass@localhost:5432/recommender_db"
    $env:NEON_DATABASE_URL  = "postgresql://...neon.tech/neondb?sslmode=require"
    python scripts/migrate_real_data_to_neon.py
"""

import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, MetaData, Table, select, text  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

# Order matters: a table must come after every table it has a foreign key
# pointing to, so the rows it references already exist when it's inserted.
TABLES_IN_ORDER = [
    "users",
    "recipes",
    "recipe_ingredients",
    "interactions",
    "comments",
    "notifications",
]


def main():
    local_url = os.environ.get("LOCAL_DATABASE_URL")
    neon_url = os.environ.get("NEON_DATABASE_URL")
    if not local_url or not neon_url:
        print("Définis LOCAL_DATABASE_URL et NEON_DATABASE_URL avant de lancer ce script.")
        return

    local_engine = create_engine(local_url)
    neon_engine = create_engine(neon_url)

    local_meta = MetaData()
    neon_meta = MetaData()

    with local_engine.connect() as local_conn, neon_engine.connect() as neon_conn:
        for table_name in TABLES_IN_ORDER:
            local_table = Table(table_name, local_meta, autoload_with=local_engine)
            neon_table = Table(table_name, neon_meta, autoload_with=neon_engine)
            pk_cols = [c.name for c in neon_table.primary_key.columns]
            if not pk_cols:
                print(f"{table_name}: pas de clé primaire détectée, ignoré par sécurité.")
                continue

            rows = local_conn.execute(select(local_table)).mappings().all()
            if not rows:
                print(f"{table_name}: rien à copier.")
                continue

            inserted = 0
            for row in rows:
                data = dict(row)
                stmt = pg_insert(neon_table).values(**data).on_conflict_do_nothing(
                    index_elements=pk_cols
                )
                result = neon_conn.execute(stmt)
                inserted += result.rowcount
            neon_conn.commit()
            print(f"{table_name}: {inserted}/{len(rows)} ligne(s) copiée(s) (le reste existait déjà).")

        for table_name in TABLES_IN_ORDER:
            seq = neon_conn.execute(text(
                "SELECT pg_get_serial_sequence(:t, 'id')"
            ), {"t": table_name}).scalar()
            if not seq:
                continue  # no auto-increment "id" column on this table (e.g. recipe_ingredients)
            neon_conn.execute(text(
                f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM {table_name}), 1))"
            ))
        neon_conn.commit()
        print("Séquences d'auto-incrémentation resynchronisées.")

    print("\nTerminé.")


if __name__ == "__main__":
    main()