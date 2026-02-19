"""
Configuration file for Reachy Mini CCTV system.
Contains paths, thresholds, and constants.
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "core" / "models"
DATA_DIR = BASE_DIR / "data"
PHOTOS_DIR = DATA_DIR / "photos"

# Create directories if they don't exist
MODELS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# Model paths
FACE_DETECTION_MODEL = MODELS_DIR / "face_detection.onnx"
FACE_EMBEDDING_MODEL = MODELS_DIR / "edgeface_xs_gamma_06.onnx"

# Detection thresholds
DETECTION_CONFIDENCE_THRESHOLD = float(os.getenv("DETECTION_THRESHOLD", "0.5"))
RECOGNITION_THRESHOLD = float(os.getenv("RECOGNITION_THRESHOLD", "0.45"))

# NMS (Non-Maximum Suppression) parameters
NMS_THRESHOLD = 0.4

# Face embedding parameters
EMBEDDING_SIZE = 512
FACE_INPUT_SIZE = (112, 112)  # EdgeFace input size

# NOTE: Detection input size is now auto-detected from the ONNX model itself
# inside FaceDetector.__init__().  No hardcoded DETECTION_INPUT_SIZE needed.

# Pipeline parameters
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "30"))
BEST_FRAME_COUNT = 15  # Number of frames to collect for best-frame selection

# Database
DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "cctv.db")))
FAISS_INDEX_PATH = Path(os.getenv("FAISS_INDEX_PATH", str(DATA_DIR / "faces.index")))
FAISS_MAPPING_PATH = Path(os.getenv("FAISS_MAPPING_PATH", str(DATA_DIR / "faces_mapping.json")))

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Notification backoff parameters (in seconds)
BACKOFF_INITIAL_DELAY = 10
BACKOFF_MAX_DELAY = 3600  # 1 hour
BACKOFF_MULTIPLIER = 2
BACKOFF_VISITOR_TIMEOUT = 300  # 5 minutes - remove visitor from tracker after this period

# Camera parameters
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")  # "0" for webcam, path for video file, or "reachy" for Reachy Mini
CAMERA_FPS = 30
# Reachy Mini Wireless: "gstreamer" when running on robot (SSH), "webrtc" when running remotely
REACHY_MEDIA_BACKEND = os.getenv("REACHY_MEDIA_BACKEND", "gstreamer")

# API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8501"))
