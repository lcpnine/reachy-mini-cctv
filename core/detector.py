"""
Face Detection Module using ONNX Runtime.
Supports SCRFD (InsightFace) and MediaPipe BlazeFace models.
"""
import cv2
import numpy as np
import onnxruntime as ort
from typing import List, Tuple, NamedTuple
from pathlib import Path

from core.config import (
    FACE_DETECTION_MODEL,
    DETECTION_CONFIDENCE_THRESHOLD,
    NMS_THRESHOLD,
    DETECTION_INPUT_SIZE
)


class BBox(NamedTuple):
    """Bounding box with confidence score."""
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float


class FaceDetector:
    """
    Face detection using ONNX models.
    Supports SCRFD-500M and other detection models.
    """

    def __init__(
        self,
        model_path: Path = FACE_DETECTION_MODEL,
        confidence_threshold: float = DETECTION_CONFIDENCE_THRESHOLD,
        nms_threshold: float = NMS_THRESHOLD,
        input_size: Tuple[int, int] = DETECTION_INPUT_SIZE
    ):
        """
        Initialize the face detector.

        Args:
            model_path: Path to the ONNX model file
            confidence_threshold: Minimum confidence score for detections
            nms_threshold: IoU threshold for Non-Maximum Suppression
            input_size: Model input size (height, width)
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.input_size = input_size

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Face detection model not found at {self.model_path}. "
                f"Please run 'python scripts/download_models.py' or place the model manually."
            )

        # Initialize ONNX Runtime session
        # Use CPU provider for Raspberry Pi 5
        providers = ['CPUExecutionProvider']
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 4  # Optimize for Pi 5 (4 cores per cluster)

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=sess_options,
            providers=providers
        )

        # Get model input/output names
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]

        print(f"FaceDetector initialized with model: {self.model_path.name}")
        print(f"Input shape: {self.session.get_inputs()[0].shape}")
        print(f"Outputs: {self.output_names}")

    def preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        Preprocess image for SCRFD model.

        Args:
            image: Input BGR image (OpenCV format)

        Returns:
            Tuple of (preprocessed_image, scale_x, scale_y)
        """
        img_height, img_width = image.shape[:2]
        target_height, target_width = self.input_size

        # Calculate scaling factors
        scale_y = target_height / img_height
        scale_x = target_width / img_width

        # Resize image
        resized = cv2.resize(image, (target_width, target_height))

        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Normalize to [0, 1] and convert to float32
        normalized = rgb.astype(np.float32) / 255.0

        # Transpose to CHW format (channels first)
        transposed = normalized.transpose(2, 0, 1)

        # Add batch dimension
        batched = np.expand_dims(transposed, axis=0)

        return batched, scale_x, scale_y

    def postprocess(
        self,
        outputs: List[np.ndarray],
        scale_x: float,
        scale_y: float,
        img_height: int,
        img_width: int
    ) -> List[BBox]:
        """
        Postprocess model outputs to extract bounding boxes.

        Args:
            outputs: Raw model outputs
            scale_x: Width scaling factor
            scale_y: Height scaling factor
            img_height: Original image height
            img_width: Original image width

        Returns:
            List of detected face bounding boxes
        """
        # SCRFD outputs: scores, bboxes, keypoints
        # Output format may vary by model, adjust accordingly
        boxes = []

        try:
            # For SCRFD models, outputs typically include:
            # - scores: [batch, num_anchors, 1]
            # - bboxes: [batch, num_anchors, 4]

            # Handle different output formats
            if len(outputs) >= 2:
                scores = outputs[0]  # Shape: [batch, num_dets] or [batch, num_dets, 1]
                bboxes = outputs[1]  # Shape: [batch, num_dets, 4]

                # Flatten if needed
                if len(scores.shape) == 3:
                    scores = scores.squeeze(-1)
                if len(scores.shape) == 2:
                    scores = scores[0]  # Remove batch dimension
                if len(bboxes.shape) == 3:
                    bboxes = bboxes[0]  # Remove batch dimension

                # Filter by confidence threshold
                mask = scores > self.confidence_threshold
                filtered_scores = scores[mask]
                filtered_bboxes = bboxes[mask]

                # Convert to original image coordinates
                for score, bbox in zip(filtered_scores, filtered_bboxes):
                    x1, y1, x2, y2 = bbox

                    # Scale back to original image size
                    x1 = int(x1 / scale_x)
                    y1 = int(y1 / scale_y)
                    x2 = int(x2 / scale_x)
                    y2 = int(y2 / scale_y)

                    # Clip to image boundaries
                    x1 = max(0, min(x1, img_width))
                    y1 = max(0, min(y1, img_height))
                    x2 = max(0, min(x2, img_width))
                    y2 = max(0, min(y2, img_height))

                    # Only add valid boxes
                    if x2 > x1 and y2 > y1:
                        boxes.append(BBox(x1, y1, x2, y2, float(score)))

        except Exception as e:
            print(f"Warning: Error during postprocessing: {e}")
            print(f"Output shapes: {[o.shape for o in outputs]}")

        # Apply Non-Maximum Suppression
        if boxes:
            boxes = self._nms(boxes)

        return boxes

    def _nms(self, boxes: List[BBox]) -> List[BBox]:
        """
        Apply Non-Maximum Suppression to remove overlapping boxes.

        Args:
            boxes: List of bounding boxes

        Returns:
            Filtered list of bounding boxes
        """
        if not boxes:
            return []

        # Convert to numpy arrays for easier processing
        boxes_array = np.array([[b.x1, b.y1, b.x2, b.y2] for b in boxes])
        scores = np.array([b.confidence for b in boxes])

        # Use OpenCV's NMS
        indices = cv2.dnn.NMSBoxes(
            boxes_array.tolist(),
            scores.tolist(),
            self.confidence_threshold,
            self.nms_threshold
        )

        if len(indices) > 0:
            indices = indices.flatten()
            return [boxes[i] for i in indices]

        return []

    def detect(self, image: np.ndarray) -> List[BBox]:
        """
        Detect faces in an image.

        Args:
            image: Input BGR image (OpenCV format)

        Returns:
            List of detected face bounding boxes
        """
        if image is None or image.size == 0:
            return []

        img_height, img_width = image.shape[:2]

        # Preprocess
        input_data, scale_x, scale_y = self.preprocess(image)

        # Run inference
        outputs = self.session.run(self.output_names, {self.input_name: input_data})

        # Postprocess
        boxes = self.postprocess(outputs, scale_x, scale_y, img_height, img_width)

        return boxes

    def detect_largest(self, image: np.ndarray) -> BBox | None:
        """
        Detect and return only the largest face in the image.
        Useful for user registration where we expect one face.

        Args:
            image: Input BGR image

        Returns:
            The largest detected face bounding box, or None if no faces detected
        """
        boxes = self.detect(image)

        if not boxes:
            return None

        # Find the box with the largest area
        largest = max(boxes, key=lambda b: (b.x2 - b.x1) * (b.y2 - b.y1))
        return largest
