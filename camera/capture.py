"""
Camera capture module supporting Reachy Mini SDK and OpenCV fallback.
"""
import cv2
import numpy as np
from typing import Optional
from abc import ABC, abstractmethod

from core.config import CAMERA_SOURCE, CAMERA_FPS, REACHY_MEDIA_BACKEND


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
    Prefers official reachy_mini SDK (Wireless: gstreamer/webrtc); falls back to
    reachy_sdk_api (ReachySDK) then OpenCV if unavailable.
    """

    def __init__(self):
        """Initialize Reachy Mini camera."""
        self.reachy = None
        self._reachy_ctx = None  # for reachy_mini context manager
        self.sdk_available = False
        self.sdk_kind = None  # "reachy_mini" | "reachy_sdk_api"

        try:
            from reachy_mini import ReachyMini
            self._ReachyMini = ReachyMini
            self.sdk_available = True
            self.sdk_kind = "reachy_mini"
            print("Reachy Mini SDK (reachy_mini) available")
        except ImportError:
            try:
                from reachy_sdk_api import ReachySDK
                self.sdk_available = True
                self.sdk_kind = "reachy_sdk_api"
                print("Reachy SDK (reachy_sdk_api) available")
            except ImportError:
                print("Warning: Reachy SDK not available, will use OpenCV fallback")
                self.fallback = OpenCVCamera(source=0)

    def start(self):
        """Start capturing frames."""
        if not self.sdk_available:
            raise RuntimeError(
                "Reachy SDK를 찾을 수 없습니다 (reachy_mini 또는 reachy_sdk_api 설치 필요). "
                "--camera reachy 사용 시 폴백하지 않습니다."
            )
        if self.sdk_kind == "reachy_mini":
            try:
                self._reachy_ctx = self._ReachyMini(media_backend=REACHY_MEDIA_BACKEND)
                self.reachy = self._reachy_ctx.__enter__()
                print("Connected to Reachy Mini (reachy_mini)")
            except Exception as e:
                raise RuntimeError(
                    "Reachy Mini 연결 실패 (--camera reachy 지정 시 폴백하지 않음). "
                    "로봇/데몬이 켜져 있는지, 같은 네트워크/호스트인지 확인하세요. "
                    f"원인: {e}"
                ) from e
        else:
            try:
                from reachy_sdk_api import ReachySDK
                self.reachy = ReachySDK(host="localhost")
                print("Connected to Reachy Mini (reachy_sdk_api)")
            except Exception as e:
                raise RuntimeError(
                    "Reachy Mini 연결 실패 (--camera reachy 지정 시 폴백하지 않음). "
                    "로봇/데몬이 켜져 있는지 확인하세요. "
                    f"원인: {e}"
                ) from e

    def read(self) -> Optional[np.ndarray]:
        """
        Read the latest frame.

        Returns:
            BGR image as numpy array, or None if no frame available
        """
        if not self.sdk_available or self.reachy is None:
            return self.fallback.read() if hasattr(self, "fallback") else None
        try:
            if self.sdk_kind == "reachy_mini":
                frame = self.reachy.media.get_frame()
            else:
                frame = self.reachy.cameras.teleop.get_frame()
            if frame is None:
                return None
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame
        except Exception as e:
            print(f"Error reading from Reachy camera: {e}")
            return None

    def stop(self):
        """Stop capturing and release resources."""
        if not self.sdk_available:
            self.fallback.stop()
            return
        if self.sdk_kind == "reachy_mini" and self._reachy_ctx is not None:
            try:
                self._reachy_ctx.__exit__(None, None, None)
                self._reachy_ctx = None
                self.reachy = None
                print("Disconnected from Reachy Mini (reachy_mini)")
            except Exception as e:
                print(f"Error disconnecting from Reachy: {e}")
        elif self.sdk_kind == "reachy_sdk_api" and self.reachy is not None:
            try:
                del self.reachy
                self.reachy = None
                print("Disconnected from Reachy Mini (reachy_sdk_api)")
            except Exception as e:
                print(f"Error disconnecting from Reachy: {e}")
        else:
            if hasattr(self, "fallback"):
                self.fallback.stop()

    def is_opened(self) -> bool:
        """Check if camera is open and ready."""
        if self.sdk_available:
            return self.reachy is not None
        return getattr(self, "fallback", None) is not None and self.fallback.is_opened()


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
