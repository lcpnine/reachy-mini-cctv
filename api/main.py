"""
FastAPI application for Reachy Mini CCTV system.
"""
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api import deps
from api.routes import users, events, photos, camera
from api.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager (startup and shutdown)."""
    # Startup
    print("=" * 60)
    print("Starting Reachy Mini CCTV API")
    print("=" * 60)

    # Initialize database
    from db.database import get_db
    db = get_db()
    print("✓ Database initialized")

    # Initialize models
    deps.init_models()

    yield

    # Shutdown
    print("=" * 60)
    print("Shutting down Reachy Mini CCTV API")
    print("=" * 60)
    deps.shutdown_models()


# Create FastAPI app
app = FastAPI(
    title="Reachy Mini CCTV API",
    description="Face recognition and monitoring system for Reachy Mini robot",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(photos.router, prefix="/api/photos", tags=["photos"])
app.include_router(camera.router, prefix="/api/camera", tags=["camera"])


@app.get("/", response_model=dict)
async def root():
    """Root endpoint."""
    return {
        "message": "Reachy Mini CCTV API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from db.database import get_db

    # Check database
    db_connected = False
    try:
        db = get_db()
        db.execute("SELECT 1")
        db_connected = True
    except Exception:
        pass

    # Check models
    models_loaded = deps.check_models_loaded()

    status = "healthy" if (db_connected and models_loaded) else "degraded"

    return HealthResponse(
        status=status,
        timestamp=datetime.now(),
        version="1.0.0",
        database_connected=db_connected,
        models_loaded=models_loaded
    )


if __name__ == "__main__":
    import uvicorn
    from core.config import API_HOST, API_PORT

    uvicorn.run(
        "api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,  # Disable in production
        log_level="info"
    )
