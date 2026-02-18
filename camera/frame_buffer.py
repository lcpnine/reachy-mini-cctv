"""
Thread-safe frame buffer for sharing latest camera frame with API.
Updated by the pipeline, read by the MJPEG stream endpoint.
"""
import threading
from typing import Optional
import numpy as np

# Thread-safe holder for latest frame (BGR numpy array)
_latest_frame: Optional[np.ndarray] = None
_lock = threading.Lock()


def update(frame: np.ndarray) -> None:
    """Update the latest frame (called by pipeline)."""
    global _latest_frame
    with _lock:
        _latest_frame = frame.copy() if frame is not None else None


def get() -> Optional[np.ndarray]:
    """Get the latest frame (called by API). Returns None if no frame available."""
    global _latest_frame
    with _lock:
        return _latest_frame.copy() if _latest_frame is not None else None
