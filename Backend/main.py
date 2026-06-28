"""
A Ton Gout - Intelligent Recipe Recommendation API
Main FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import os

from core.config import settings
from db.database import engine, Base, SessionLocal
from api.router import api_router
from service.als_training_service import retrain_als

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _scheduled_retrain_job():
    """Runs periodically in the background. Cheap no-op if there isn't
    enough new interaction data yet (retrain_als() guards that itself)"""
    db = SessionLocal()
    try:
        result = retrain_als(db, force=False)
        if result.get("status") == "trained":
            logger.info(f"Auto-retrain: {result}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)

    """ Automatic ALS retraining: checks every RETRAIN_INTERVAL_MINUTES whether
    enough new real interactions have piled up, and retrains in the
    background if so — no manual script run needed during normal use"""
    scheduler.add_job(
        _scheduled_retrain_job,
        "interval",
        minutes=settings.ALS_RETRAIN_INTERVAL_MINUTES,
        id="als_retrain",
    )
    scheduler.start()

    yield

    # Shutdown
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="A Ton Gout API",
    description="Intelligent Recipe Recommendation System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],
    allow_credentials=False,
    allow_methods=[
        "*"
    ],
    allow_headers=[
        "*"
    ],
)

# Static files (recipe images)
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)


@app.get("/static/images/{filename}")
def serve_recipe_image(filename: str):
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    exact_path = os.path.join(IMAGES_DIR, filename)
    if os.path.isfile(exact_path):
        return FileResponse(exact_path)

    stem = os.path.splitext(filename)[0]
    if os.path.isdir(IMAGES_DIR):
        for fname in os.listdir(IMAGES_DIR):
            if os.path.splitext(fname)[0] == stem:
                return FileResponse(os.path.join(IMAGES_DIR, fname))

    raise HTTPException(status_code=404, detail="Image not found")


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "static")), name="static")

# Routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "A Ton Gout API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}