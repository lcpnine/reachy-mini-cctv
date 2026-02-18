#!/usr/bin/env python3
"""
Reachy Mini CCTV System - Main Entry Point
Integrates all components: camera pipeline, API server, and notifications.
"""
import sys
import signal
import argparse
from pathlib import Path
from threading import Thread, Event
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import (
    API_HOST,
    API_PORT,
    CAMERA_SOURCE,
    FAISS_INDEX_PATH,
    FAISS_MAPPING_PATH,
)
from core.detector import FaceDetector
from core.embedder import FaceEmbedder
from core.recognizer import FaceRecognizer
from camera.capture import create_camera
from camera.photo import PhotoStorage
from camera.pipeline import Pipeline, PipelineEvent
from db.database import get_db
from db.user_repo import UserRepository
from db.event_repo import EventRepository
from notifications.telegram import send_unknown_visitor_alert, get_notifier
from notifications.backoff import get_backoff_tracker


# Global state
pipeline: Optional[Pipeline] = None
stop_event = Event()


def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    print("\n" + "=" * 60)
    print("Shutdown signal received. Stopping system...")
    print("=" * 60)
    stop_event.set()

    if pipeline:
        pipeline.stop()

    sys.exit(0)


def on_pipeline_event(event: PipelineEvent):
    """
    Callback for pipeline events.
    Handles notifications for unknown visitors.
    """
    # Send Telegram notification for unknown visitors
    if not event.is_known and event.photo_path:
        try:
            backoff_tracker = get_backoff_tracker()

            # Check if we should send an alert (respects exponential backoff)
            # Note: We need the embedding for backoff tracking, but pipeline doesn't pass it
            # For now, always try to send (backoff is handled in the pipeline itself)
            photo_storage = PhotoStorage()
            photo_full_path = photo_storage.get_photo_path(event.photo_path)

            success = send_unknown_visitor_alert(photo_full_path, event.confidence)

            if success:
                print(f"✓ Telegram alert sent for unknown visitor")
            else:
                print(f"⚠ Failed to send Telegram alert")

        except Exception as e:
            print(f"Error sending Telegram notification: {e}")


def initialize_system(camera_source: str):
    """
    Initialize all system components.

    Args:
        camera_source: Camera source identifier

    Returns:
        Pipeline instance
    """
    print("=" * 60)
    print("Initializing Reachy Mini CCTV System")
    print("=" * 60)
    print()

    # Initialize database
    print("1. Initializing database...")
    db = get_db()
    user_repo = UserRepository(db)
    event_repo = EventRepository(db)
    print(f"   ✓ Database ready ({user_repo.get_user_count()} users registered)")
    print()

    # Initialize face detection and recognition
    print("2. Loading face detection model...")
    detector = FaceDetector()
    print("   ✓ Face detector loaded")
    print()

    print("3. Loading face embedding model...")
    embedder = FaceEmbedder()
    print("   ✓ Face embedder loaded")
    print()

    print("4. Loading face recognition index...")
    if FAISS_INDEX_PATH.exists() and FAISS_MAPPING_PATH.exists():
        recognizer = FaceRecognizer.load()
        print(f"   ✓ Recognizer loaded ({recognizer.get_user_count()} users, "
              f"{recognizer.get_embedding_count()} embeddings)")
    else:
        recognizer = FaceRecognizer()
        print("   ✓ Recognizer initialized (empty index)")
    print()

    # Initialize photo storage
    print("5. Initializing photo storage...")
    photo_storage = PhotoStorage()
    print(f"   ✓ Photo storage ready ({photo_storage.get_photo_count()} photos)")
    print()

    # Test Telegram connection
    print("6. Testing Telegram connection...")
    notifier = get_notifier()
    if notifier.enabled:
        if notifier.test_connection():
            print("   ✓ Telegram bot connected")
        else:
            print("   ⚠ Telegram connection failed (notifications disabled)")
    else:
        print("   ⚠ Telegram not configured (notifications disabled)")
    print()

    # Initialize camera
    print("7. Initializing camera...")
    camera = create_camera(camera_source)
    camera.start()
    print(f"   ✓ Camera ready (source: {camera_source})")
    print()

    # Create pipeline
    print("8. Starting recognition pipeline...")
    pipeline = Pipeline(
        camera=camera,
        detector=detector,
        embedder=embedder,
        recognizer=recognizer,
        event_repo=event_repo,
        photo_storage=photo_storage,
        on_event=on_pipeline_event
    )
    print("   ✓ Pipeline ready")
    print()

    print("=" * 60)
    print("System initialized successfully!")
    print("=" * 60)
    print()

    return pipeline


def run_api_server():
    """Run the FastAPI server in a separate thread."""
    import uvicorn
    from api.main import app

    print("Starting API server...")
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level="info",
        access_log=False
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reachy Mini CCTV - Face Recognition System"
    )
    parser.add_argument(
        "--camera",
        default=CAMERA_SOURCE,
        help="Camera source (0 for webcam, 'reachy' for Reachy Mini, or path to video file)"
    )
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Run pipeline only without API server"
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Run API server only without pipeline"
    )

    args = parser.parse_args()

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    global pipeline

    try:
        if not args.api_only:
            # Initialize and start pipeline
            pipeline = initialize_system(args.camera)

            if not args.no_api:
                # Start API server in a separate thread
                api_thread = Thread(target=run_api_server, daemon=True)
                api_thread.start()
                print(f"API server running at http://{API_HOST}:{API_PORT}")
                print()

            # Run pipeline in main thread
            print("=" * 60)
            print("Reachy Mini CCTV is now running!")
            print("Press Ctrl+C to stop")
            print("=" * 60)
            print()

            pipeline.run()

        else:
            # API-only mode
            print("Running in API-only mode (no camera pipeline)")
            run_api_server()

    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if pipeline:
            pipeline.stop()
        print("\nSystem stopped.")


if __name__ == "__main__":
    main()
