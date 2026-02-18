"""
Best-frame selection and photo storage for unknown visitors.
"""
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass

from core.config import PHOTOS_DIR, BEST_FRAME_COUNT


@dataclass
class FrameCandidate:
    """A candidate frame for best-frame selection."""
    frame: np.ndarray
    confidence: float
    sharpness: float
    timestamp: datetime


class BestFrameSelector:
    """
    Collects multiple frames and selects the sharpest one.
    Uses Laplacian variance as a sharpness metric.
    """

    def __init__(self, max_frames: int = BEST_FRAME_COUNT):
        """
        Initialize the best-frame selector.

        Args:
            max_frames: Maximum number of frames to collect
        """
        self.max_frames = max_frames
        self.candidates: list[FrameCandidate] = []

    def calculate_sharpness(self, frame: np.ndarray) -> float:
        """
        Calculate image sharpness using Laplacian variance.
        Higher value = sharper image.

        Args:
            frame: Input BGR image

        Returns:
            Sharpness score
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Calculate Laplacian
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)

        # Calculate variance (measure of sharpness)
        variance = laplacian.var()

        return float(variance)

    def add(self, frame: np.ndarray, confidence: float):
        """
        Add a frame candidate.

        Args:
            frame: BGR image
            confidence: Recognition confidence score
        """
        if len(self.candidates) >= self.max_frames:
            # Already have enough frames
            return

        sharpness = self.calculate_sharpness(frame)

        candidate = FrameCandidate(
            frame=frame.copy(),  # Make a copy to avoid reference issues
            confidence=confidence,
            sharpness=sharpness,
            timestamp=datetime.now()
        )

        self.candidates.append(candidate)

    def is_full(self) -> bool:
        """Check if we have collected enough frames."""
        return len(self.candidates) >= self.max_frames

    def select(self) -> Optional[np.ndarray]:
        """
        Select the best (sharpest) frame from the collected candidates.

        Returns:
            The sharpest frame, or None if no candidates
        """
        if not self.candidates:
            return None

        # Find the candidate with the highest sharpness
        best_candidate = max(self.candidates, key=lambda c: c.sharpness)

        print(f"Selected best frame: sharpness={best_candidate.sharpness:.2f}, "
              f"confidence={best_candidate.confidence:.2f} "
              f"(from {len(self.candidates)} candidates)")

        return best_candidate.frame

    def reset(self):
        """Clear all collected frames."""
        self.candidates = []

    def get_count(self) -> int:
        """Get the number of collected frames."""
        return len(self.candidates)


class PhotoStorage:
    """
    Manages photo storage for unknown visitors.
    """

    def __init__(self, photo_dir: Path = PHOTOS_DIR):
        """
        Initialize photo storage.

        Args:
            photo_dir: Directory to store photos
        """
        self.photo_dir = photo_dir
        self.photo_dir.mkdir(parents=True, exist_ok=True)

    def save_photo(
        self,
        frame: np.ndarray,
        confidence: float,
        timestamp: Optional[datetime] = None
    ) -> Tuple[str, Path]:
        """
        Save a photo of an unknown visitor.

        Args:
            frame: BGR image
            confidence: Recognition confidence score
            timestamp: Photo timestamp (uses current time if None)

        Returns:
            Tuple of (relative_path, absolute_path)
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Generate filename: unknown_YYYYMMDD_HHMMSS_sequence.jpg
        base_name = f"unknown_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Find an available sequence number to avoid collisions
        sequence = 0
        while True:
            filename = f"{base_name}_{sequence:03d}.jpg"
            full_path = self.photo_dir / filename
            if not full_path.exists():
                break
            sequence += 1

        # Save the image
        success = cv2.imwrite(str(full_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

        if not success:
            raise IOError(f"Failed to save photo to {full_path}")

        # Return relative path (for database) and absolute path
        relative_path = f"photos/{filename}"

        print(f"Saved unknown visitor photo: {filename} (confidence: {confidence:.2f})")

        return relative_path, full_path

    def get_photo_path(self, relative_path: str) -> Path:
        """
        Convert a relative photo path to absolute path.

        Args:
            relative_path: Relative path from database (e.g., "photos/unknown_001.jpg")

        Returns:
            Absolute path
        """
        # Remove "photos/" prefix if present
        if relative_path.startswith("photos/"):
            filename = relative_path[7:]  # len("photos/") = 7
        else:
            filename = relative_path

        return self.photo_dir / filename

    def delete_photo(self, relative_path: str) -> bool:
        """
        Delete a photo.

        Args:
            relative_path: Relative path from database

        Returns:
            True if deleted, False if not found
        """
        full_path = self.get_photo_path(relative_path)

        if full_path.exists():
            full_path.unlink()
            print(f"Deleted photo: {relative_path}")
            return True
        else:
            print(f"Photo not found: {relative_path}")
            return False

    def delete_old_photos(self, before: datetime) -> int:
        """
        Delete photos older than a specific date.
        Useful for data retention policies.

        Args:
            before: Delete photos before this datetime

        Returns:
            Number of photos deleted
        """
        deleted_count = 0

        for photo_path in self.photo_dir.glob("unknown_*.jpg"):
            # Get file modification time
            mtime = datetime.fromtimestamp(photo_path.stat().st_mtime)

            if mtime < before:
                photo_path.unlink()
                deleted_count += 1

        if deleted_count > 0:
            print(f"Deleted {deleted_count} old photos (before {before})")

        return deleted_count

    def get_photo_count(self) -> int:
        """Get the total number of stored photos."""
        return len(list(self.photo_dir.glob("unknown_*.jpg")))


# Convenience functions
def create_best_frame_selector(max_frames: int = BEST_FRAME_COUNT) -> BestFrameSelector:
    """Create a best-frame selector instance."""
    return BestFrameSelector(max_frames=max_frames)


def create_photo_storage(photo_dir: Path = PHOTOS_DIR) -> PhotoStorage:
    """Create a photo storage instance."""
    return PhotoStorage(photo_dir=photo_dir)
