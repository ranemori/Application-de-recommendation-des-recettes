# À Ton Goût 

Moteur de recommandation de recettes intelligent — propose des recettes
personnalisées par cuisine, ingrédients disponibles ("Mon Frigo") et goûts
appris au fil des interactions, via un modèle collaboratif **ALS**
(*Alternating Least Squares*) entraîné en continu.

> *"Ton goût. Ma recette. Parfait !"*

---

## Architecture du projet

```
moteur de recommandation intelligent/
├── Backend/          # API FastAPI + PostgreSQL
├── Frontend/         # Application React (client + admin)
└── Recommender/      # Données, modèle ALS, scripts d'entraînement
```

| Composant | Stack |
|---|---|
| Backend | FastAPI, SQLAlchemy, PostgreSQL, JWT, APScheduler |
| Frontend | React 18 (Create React App), React Router |
| Recommandation | `implicit` (ALS), pandas, numpy, scikit-learn |

---

## Prérequis

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+

---

## 1. Installation du Backend

```bash
cd Backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

Crée la base de données PostgreSQL :
```sql
CREATE DATABASE recommender_db;
```

Configure `Backend/core/config.py` (ou des variables d'environnement) avec
ton `DATABASE_URL` et un vrai `SECRET_KEY` en production.

### Importer les données et entraîner le modèle (une seule fois)
```bash
python scripts/seed_data.py        # importe les recettes/ingrédients du CSV
python scripts/train_als_real.py   # entraîne le modèle ALS initial
```

### Lancer le serveur
```bash
uvicorn main:app --reload
```
→ API disponible sur `http://localhost:8000`, doc interactive sur
`http://localhost:8000/docs`.

---

## 2. Installation du Frontend

```bash
cd Frontend
npm install
npm start
```
→ Application disponible sur `http://localhost:3000`.

Variable d'environnement optionnelle (`Frontend/.env`) pour pointer vers un
backend déployé :
```
REACT_APP_API_URL=https://mon-backend.onrender.com/api/v1
```
Par défaut, le frontend appelle `http://localhost:8000/api/v1`.

---

## 3. Scripts utiles (`Backend/scripts/`)

| Script | Rôle |
|---|---|
| `seed_data.py` | Importe `Recommender/Dataset/Raw/*.csv` dans PostgreSQL (recettes, ingrédients, liens) |
| `train_als_real.py` | Entraîne le modèle ALS en fusionnant les interactions réelles + le jeu de données synthétique de seed |
| `diagnose_als.py --user <username>` | Diagnostic complet : état du modèle, mapping utilisateur réel ↔ ALS, raison des recommandations, répartition par cuisine |
| `recompute_ratings.py` | Recalcule `note_moyenne`/`nb_avis` à partir des vraies interactions (usage ponctuel) |
| `backfill_seed_baseline.py` | Restaure/peuple le socle de notes "seed" (`seed_note_moyenne`/`seed_nb_avis`) depuis le CSV |
| `restore_seed_ratings.py` | Restaure les notes de seed corrompues par un recalcul erroné |

---

## 4. Fonctionnement du moteur de recommandation

1. **Nouvel utilisateur (cold-start)** → recommandations basées sur la
   popularité + cuisines préférées déclarées à l'inscription (réparties en
   tour de rôle entre cuisines, pas juste triées par note).
2. **Premières interactions réelles** → un ré-entraînement ALS se déclenche
   automatiquement en tâche de fond après chaque interaction
   (like/sauvegarde/note/vue).
3. **Profil ALS établi** → recommandations personnalisées (`reason: "ALS"`),
   avec une couche de **boost temps réel** qui met en avant les cuisines
   récemment aimées/sauvegardées (dernières 24h) sans attendre le prochain
   ré-entraînement complet — et un léger mélange aléatoire pour que
   l'actualisation de la page varie un peu, façon fil social.
4. **Mon Frigo** → recommandation par ingrédients disponibles, en mode
   strict (recette réalisable telle quelle) ou relâché (meilleures
   correspondances).
5. **Recettes similaires** → score de contenu pondéré par IDF (les
   ingrédients rares comptent plus que les ingrédients courants comme
   sel/ail/eau) + cuisine + tags, combiné à l'ALS quand assez de données
   réelles existent.

---

## 5. Comptes de démonstration

Voir `Backend/scripts/seed_data.py` / la base seedée pour la liste des
utilisateurs synthétiques. Un compte administrateur doit être créé/promu
manuellement en base (`role = 'admin'`) pour accéder à `/admin`.

---

## 6. Déploiement

Résumé rapide :
- **Backend + PostgreSQL** → Render (ou Railway)
- **Frontend** → Vercel (ou Netlify), avec `REACT_APP_API_URL` pointant
  vers l'URL du backend déployé
- Les fichiers du modèle ALS (`Recommender/models/`) et les CSV doivent
  être présents dans le dépôt déployé, ou régénérés au démarrage via les
  scripts de seed/entraînement.

---

## Licence

Projet de fin d'études (PFE) — usage académique.
