"""
Thread-safe store for the latest per-frame face recognition results.
Used by the pipeline to expose current frame recognition to the API (live feed overlay).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class FaceRecognitionResult:
    """Recognition result for one face in the current frame."""
    is_known: bool
    user_name: str
    confidence: float


_state: List[FaceRecognitionResult] = []
_updated_at: datetime | None = None
_lock = threading.Lock()


def update(faces: List[FaceRecognitionResult]) -> None:
    """Update the latest recognition state (called by pipeline after each frame)."""
    global _state, _updated_at
    with _lock:
        _state = list(faces)
        _updated_at = datetime.now()


def get() -> tuple[List[dict], datetime | None]:
    """
    Get the latest recognition state (called by API).

    Returns:
        Tuple of (list of dicts with is_known, user_name, confidence), updated_at
    """
    global _state, _updated_at
    with _lock:
        faces = [
            {"is_known": f.is_known, "user_name": f.user_name, "confidence": round(f.confidence, 2)}
            for f in _state
        ]
        return faces, _updated_at
