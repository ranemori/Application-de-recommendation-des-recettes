"""
diagnose_als.py — Bilan de santé complet du pipeline de recommandation.

Vérifie, dans l'ordre :
  1. Les artefacts ALS existent-ils sur disque et se chargent-ils sans erreur ?
  2. Le service ALS (als_service.py) est-il réellement "ready" ?
  3. Combien d'utilisateurs réels ont un als_user_idx valide ?
  4. Pour un utilisateur donné, est-ce que /recommendations/me utiliserait
     vraiment l'ALS ou retombe sur la popularité ?
  5. Si ALS : la répartition par cuisine du résultat respecte-t-elle le
     plafond d'équité (fairness) ?
  6. Deux appels successifs donnent-ils un ordre légèrement différent ?

Lancer depuis Backend/ :
    python scripts/diagnose_als.py                 # bilan général
    python scripts/diagnose_als.py --user fatima_tam_21   # + audit ciblé
"""

import os
import sys
import argparse
from collections import Counter

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from db.database import SessionLocal  
from db.models import User, Recipe, Interaction  
from service.als_service import get_als_service  
from service.recommendation_service import RecommendationService  


def section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", help="username à auditer en détail", default=None)
    parser.add_argument("--n", type=int, default=12, help="taille de la liste de recommandations à tester")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # ── 1 & 2: service ALS ────────────────────────────────────────
        section("1. Service ALS")
        als = get_als_service()
        print(f"is_ready            : {als.is_ready}")
        print(f"n_train_users       : {als.n_train_users}")
        if not als.is_ready:
            print(
                "\n  ALS n'est PAS prêt. Recommandations = popularité pour TOUT LE MONDE.\n"
                "  Regarde les logs au démarrage du serveur pour l'erreur exacte\n"
                "  (ex: 'ALS service failed to load: ...')."
            )

        # ── 3: utilisateurs réels avec als_user_idx ──────────────────
        section("2. Utilisateurs réels mappés dans le modèle ALS")
        real_users = db.query(User).filter(User.als_user_idx.isnot(None)).all()
        print(f"{len(real_users)} utilisateur(s) réel(s) ont un als_user_idx :")
        for u in real_users:
            n_interactions = db.query(Interaction).filter(Interaction.user_id == u.id).count()
            print(f"  - {u.username:<20} als_user_idx={u.als_user_idx:<5} ({n_interactions} interaction(s) réelle(s))")

        if not real_users:
            print(
                "\n  Aucun utilisateur réel n'est encore dans le modèle.\n"
                "  -> Fais une interaction (view/like/save/rating) avec un compte réel,\n"
                "     puis relance ce script."
            )

        # ── 4, 5, 6: audit ciblé sur un utilisateur ──────────────────
        if args.user:
            section(f"3. Audit ciblé : {args.user}")
            user = db.query(User).filter(User.username == args.user).first()
            if not user:
                print(f"  Utilisateur '{args.user}' introuvable.")
                return

            print(f"als_user_idx        : {user.als_user_idx}")
            print(f"preferences_cuisine  : {user.preferences_cuisine}")

            service = RecommendationService(db)
            effective = service._effective_cuisines(user)
            print(f"cuisines effectives  : {sorted(effective)}  (déclarées + likées/sauvegardées/bien notées)")

            recs = service.for_user(user, n=args.n)
            reasons = Counter(r.reason for r in recs)
            print(f"\nreasons dans la réponse : {dict(reasons)}")

            if reasons.get("ALS") or reasons.get("hybrid"):
                print("  -> L'ALS est bien utilisé pour cet utilisateur. ✔")
            else:
                print(
                    "  -> Toujours sur 'popularity'. Causes possibles :\n"
                    "     - als_user_idx est None (vérifie ci-dessus)\n"
                    "     - als.is_ready est False (voir section 1)\n"
                    "     - le pipeline ALS a levé une exception (regarde les logs serveur)"
                )

            cuisines = Counter((r.recipe.cuisine or "?").lower() for r in recs)
            print(f"\nrépartition par cuisine ({len(recs)} recettes) : {dict(cuisines)}")
            if cuisines:
                top_cuisine, top_count = cuisines.most_common(1)[0]
                share = top_count / len(recs)
                print(f"  cuisine dominante : {top_cuisine} ({share:.0%} de la liste)")
                if share > 0.5:
                    print("  -> ATTENTION : une seule cuisine dépasse 50% de la liste,")
                    print("     la couche fairness ne semble pas avoir suffisamment d'alternatives.")
                else:
                    print("  -> Répartition raisonnable. ✔")

            # Freshness check: call again and compare order
            recs2 = service.for_user(user, n=args.n)
            ids1 = [r.recipe.id for r in recs]
            ids2 = [r.recipe.id for r in recs2]
            if ids1 == ids2:
                print(
                    "\nfreshness            : IDENTIQUE entre 2 appels.\n"
                    "  -> Normal si reason='popularity' (déterministe par design).\n"
                    "  -> Anormal si reason='ALS' (la couche freshness devrait varier légèrement)."
                )
            else:
                print("\nfreshness            : les deux appels diffèrent. ✔ (la liste évolue à chaque refresh)")

        else:
            print("\nAstuce : relance avec --user <username> pour un audit complet sur un compte précis.")

    finally:
        db.close()


if __name__ == "__main__":
    main()