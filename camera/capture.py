"""
Camera capture module supporting Reachy Mini SDK and OpenCV fallback.
"""
import cv2
import numpy as np
from typing import Optional
from abc import ABC, abstractmethod

from core.config import CAMERA_SOURCE, CAMERA_FPS


class CameraInterface(ABC):
    """Abstract interface for camera capture."""

    @abstractmethod
    def start(self):
        """Start capturing frames."""
        pass

    @abstractmethod
    def read(self) -> Optional[np.ndarray]:
        """
        Read the latest frame.

        Returns:
            BGR image as numpy array, or None if no frame available
        """
        pass

    @abstractmethod
    def stop(self):
        """Stop capturing and release resources."""
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """Check if camera is open and ready."""
        pass


class OpenCVCamera(CameraInterface):
    """
    OpenCV-based camera capture.
    Supports webcams and video files.
    """

    def __init__(self, source: str | int = 0):
        """
        Initialize OpenCV camera.

        Args:
            source: Camera index (e.g., 0, 1) or path to video file
        """
        # Convert string numbers to integers
        if isinstance(source, str) and source.isdigit():
            source = int(source)

        self.source = source
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_video_file = isinstance(source, str) and source != "0"

        print(f"OpenCVCamera initialized with source: {source}")
        print(f"Is video file: {self.is_video_file}")

    def start(self):
        """Start capturing frames."""
        if self.cap is not None:
            print("Camera already started")
            return

        self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera/video: {self.source}")

        # Set camera properties (only for real cameras, not video files)
        if not self.is_video_file:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)

        print(f"Camera started successfully")
        print(f"Resolution: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
              f"{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
        print(f"FPS: {self.cap.get(cv2.CAP_PROP_FPS)}")

    def read(self) -> Optional[np.ndarray]:
        """
        Read the latest frame.

        Returns:
            BGR image as numpy array, or None if no frame available
        """
        if self.cap is None or not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()

        if not ret:
            if self.is_video_file:
                # Loop video file
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()

            if not ret:
                return None

        return frame

    def stop(self):
        """Stop capturing and release resources."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print("Camera stopped")

    def is_opened(self) -> bool:
        """Check if camera is open and ready."""
        return self.cap is not None and self.cap.isOpened()


class ReachyMiniCamera(CameraInterface):
    """
    Reachy Mini SDK camera capture.
    Falls back to OpenCV if SDK is not available.
    """

    def __init__(self):
        """Initialize Reachy Mini camera."""
        self.reachy = None
        self.sdk_available = False

        try:
            from reachy_sdk_api import ReachySDK
            self.sdk_available = True
            print("Reachy SDK available")
        except ImportError:
            print("Warning: Reachy SDK not available, will use OpenCV fallback")
            self.fallback = OpenCVCamera(source=0)

    def start(self):
        """Start capturing frames."""
        if self.sdk_available:
            try:
                from reachy_sdk_api import ReachySDK
                self.reachy = ReachySDK(host='localhost')
                print("Connected to Reachy Mini")
            except Exception as e:
                print(f"Failed to connect to Reachy Mini: {e}")
                print("Falling back to OpenCV")
                self.sdk_available = False
                self.fallback = OpenCVCamera(source=0)
                self.fallback.start()
        else:
            self.fallback.start()

    def read(self) -> Optional[np.ndarray]:
        """
        Read the latest frame.

        Returns:
            BGR image as numpy array, or None if no frame available
        """
        if self.sdk_available and self.reachy is not None:
            try:
                # Get frame from Reachy Mini's camera
                # Note: Adjust this based on actual Reachy SDK API
                frame = self.reachy.cameras.teleop.get_frame()

                # Convert to BGR if necessary (Reachy might provide RGB)
                if frame is not None and len(frame.shape) == 3:
                    if frame.shape[2] == 3:
                        # Assume RGB, convert to BGR
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                return frame
            except Exception as e:
                print(f"Error reading from Reachy camera: {e}")
                return None
        else:
            return self.fallback.read()

    def stop(self):
        """Stop capturing and release resources."""
        if self.sdk_available and self.reachy is not None:
            try:
                # Disconnect from Reachy
                # Note: Adjust based on actual SDK cleanup method
                del self.reachy
                self.reachy = None
                print("Disconnected from Reachy Mini")
            except Exception as e:
                print(f"Error disconnecting from Reachy: {e}")
        else:
            self.fallback.stop()

    def is_opened(self) -> bool:
        """Check if camera is open and ready."""
        if self.sdk_available:
            return self.reachy is not None
        else:
            return self.fallback.is_opened()


class CameraCapture:
    """
    Factory class for camera capture.
    Automatically selects the appropriate camera based on configuration.
    """

    @staticmethod
    def create(source: Optional[str] = None) -> CameraInterface:
        """
        Create a camera capture instance.

        Args:
            source: Camera source (from config if None)
                   - "reachy": Use Reachy Mini SDK
                   - "0", "1", etc.: Webcam index
                   - Path to video file

        Returns:
            CameraInterface instance
        """
        if source is None:
            source = CAMERA_SOURCE

        if source.lower() == "reachy":
            return ReachyMiniCamera()
        else:
            return OpenCVCamera(source=source)


# Convenience function
def create_camera(source: Optional[str] = None) -> CameraInterface:
    """
    Create a camera capture instance.

    Args:
        source: Camera source (from config if None)

    Returns:
        CameraInterface instance
    """
    return CameraCapture.create(source)
