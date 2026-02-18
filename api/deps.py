"""
Shared dependencies for FastAPI application.
Provides database connections, models, and shared state.
"""
from typing import Optional
from fastapi import Depends

from db.database import Database, get_db
from db.user_repo import UserRepository
from db.event_repo import EventRepository
from core.detector import FaceDetector
from core.embedder import FaceEmbedder
from core.recognizer import FaceRecognizer
from camera.photo import PhotoStorage
from notifications.telegram import TelegramNotifier, get_notifier
from notifications.backoff import BackoffTracker, get_backoff_tracker


# Global instances (initialized on startup)
_detector: Optional[FaceDetector] = None
_embedder: Optional[FaceEmbedder] = None
_recognizer: Optional[FaceRecognizer] = None
_photo_storage: Optional[PhotoStorage] = None


def get_detector() -> FaceDetector:
    """Get the global face detector instance."""
    global _detector
    if _detector is None:
        raise RuntimeError("Face detector not initialized")
    return _detector


def get_embedder() -> FaceEmbedder:
    """Get the global face embedder instance."""
    global _embedder
    if _embedder is None:
        raise RuntimeError("Face embedder not initialized")
    return _embedder


def get_recognizer() -> FaceRecognizer:
    """Get the global face recognizer instance."""
    global _recognizer
    if _recognizer is None:
        raise RuntimeError("Face recognizer not initialized")
    return _recognizer


def get_photo_storage() -> PhotoStorage:
    """Get the global photo storage instance."""
    global _photo_storage
    if _photo_storage is None:
        _photo_storage = PhotoStorage()
    return _photo_storage


def get_user_repo(db: Database = Depends(get_db)) -> UserRepository:
    """Get a user repository instance."""
    return UserRepository(db)


def get_event_repo(db: Database = Depends(get_db)) -> EventRepository:
    """Get an event repository instance."""
    return EventRepository(db)


def get_telegram_notifier() -> TelegramNotifier:
    """Get the global Telegram notifier instance."""
    return get_notifier()


def get_backoff_tracker_dep() -> BackoffTracker:
    """Get the global backoff tracker instance."""
    return get_backoff_tracker()


def init_models():
    """Initialize global model instances (called on application startup)."""
    global _detector, _embedder, _recognizer, _photo_storage

    print("Initializing models...")

    try:
        # Initialize detector
        _detector = FaceDetector()
        print("✓ Detector initialized")
    except Exception as e:
        print(f"✗ Failed to initialize detector: {e}")
        _detector = None

    try:
        # Initialize embedder
        _embedder = FaceEmbedder()
        print("✓ Embedder initialized")
    except Exception as e:
        print(f"✗ Failed to initialize embedder: {e}")
        _embedder = None

    try:
        # Initialize or load recognizer
        from core.config import FAISS_INDEX_PATH, FAISS_MAPPING_PATH

        if FAISS_INDEX_PATH.exists() and FAISS_MAPPING_PATH.exists():
            _recognizer = FaceRecognizer.load()
            print("✓ Recognizer loaded from disk")
        else:
            _recognizer = FaceRecognizer()
            print("✓ Recognizer initialized (empty index)")
    except Exception as e:
        print(f"✗ Failed to initialize recognizer: {e}")
        _recognizer = None

    # Initialize photo storage
    _photo_storage = PhotoStorage()
    print("✓ Photo storage initialized")

    print("Model initialization complete")


def shutdown_models():
    """Cleanup models on application shutdown."""
    global _recognizer

    print("Shutting down models...")

    # Save recognizer state
    if _recognizer is not None:
        try:
            _recognizer.save()
            print("✓ Recognizer state saved")
        except Exception as e:
            print(f"✗ Failed to save recognizer state: {e}")

    print("Shutdown complete")


def check_models_loaded() -> bool:
    """Check if all required models are loaded."""
    return (
        _detector is not None and
        _embedder is not None and
        _recognizer is not None
    )
