"""
Face Detection Module using ONNX Runtime.
Supports SCRFD (InsightFace) models with multi-stride output.
"""
from itertools import product
from pathlib import Path
from typing import List, NamedTuple, Tuple

import cv2
import numpy as np
import onnxruntime as ort

from core.config import (DETECTION_CONFIDENCE_THRESHOLD, FACE_DETECTION_MODEL,
                         NMS_THRESHOLD)


class BBox(NamedTuple):
    """Bounding box with confidence score."""
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float


class FaceDetector:
    """
    Face detection using SCRFD ONNX models (e.g. SCRFD-500M from InsightFace).

    SCRFD models output 9 tensors (3 strides × {scores, bboxes, keypoints}):
      - scores for stride 8, 16, 32
      - bboxes (distance-to-edge) for stride 8, 16, 32
      - keypoints for stride 8, 16, 32 (unused here)
    """

    # Feature map strides used by SCRFD
    _FEAT_STRIDES = [8, 16, 32]
    # Number of anchors per location (SCRFD-500M uses 2)
    _NUM_ANCHORS = 2

    def __init__(
        self,
        model_path: Path = FACE_DETECTION_MODEL,
        confidence_threshold: float = DETECTION_CONFIDENCE_THRESHOLD,
        nms_threshold: float = NMS_THRESHOLD,
    ):
        """
        Initialize the face detector.

        Args:
            model_path: Path to the SCRFD ONNX model file
            confidence_threshold: Minimum confidence score for detections
            nms_threshold: IoU threshold for Non-Maximum Suppression
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Face detection model not found at {self.model_path}. "
                f"Please run 'python scripts/download_models.py' or place the model manually."
            )

        # Initialize ONNX Runtime session
        providers = ['CPUExecutionProvider']
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 4  # Optimize for Pi 5 (4 cores)

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=sess_options,
            providers=providers,
        )

        # Derive the expected input size from the model itself
        input_meta = self.session.get_inputs()[0]
        self.input_name = input_meta.name
        # Shape is typically [1, 3, H, W] or ['N', 3, H, W]
        raw_shape = input_meta.shape
        self.input_height = int(raw_shape[2])
        self.input_width = int(raw_shape[3])
        self.input_size = (self.input_height, self.input_width)

        self.output_names = [o.name for o in self.session.get_outputs()]

        print(f"FaceDetector initialized: {self.model_path.name}")
        print(f"  Input : {self.input_name} {raw_shape}")
        print(f"  Outputs ({len(self.output_names)}): {self.output_names}")
        print(f"  Resolved input size: {self.input_size}")

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------
    def preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        Resize + normalise for SCRFD.

        Returns:
            (input_tensor, scale_x, scale_y) where scale_* map from
            *model* coords back to *original image* coords.
        """
        img_h, img_w = image.shape[:2]
        target_h, target_w = self.input_size

        scale_x = img_w / target_w
        scale_y = img_h / target_h

        resized = cv2.resize(image, (target_w, target_h))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # SCRFD expects float32, mean-subtracted (127.5) and scaled (/128)
        blob = (rgb.astype(np.float32) - 127.5) / 128.0
        blob = blob.transpose(2, 0, 1)[np.newaxis, ...]  # NCHW
        return blob, scale_x, scale_y

    # ------------------------------------------------------------------
    # Anchor generation (cached per input size)
    # ------------------------------------------------------------------
    def _generate_anchors(self, feat_h: int, feat_w: int, stride: int) -> np.ndarray:
        """Return anchor centres of shape (feat_h * feat_w * num_anchors, 2)."""
        anchors = []
        for y, x in product(range(feat_h), range(feat_w)):
            for _ in range(self._NUM_ANCHORS):
                cx = (x + 0.5) * stride
                cy = (y + 0.5) * stride
                anchors.append([cx, cy])
        return np.array(anchors, dtype=np.float32)

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------
    def postprocess(
        self,
        outputs: List[np.ndarray],
        scale_x: float,
        scale_y: float,
        img_height: int,
        img_width: int,
    ) -> List[BBox]:
        """
        Decode SCRFD multi-stride outputs into bounding boxes.

        SCRFD-500M produces 9 outputs in groups of 3 per stride:
          idx 0,1,2  → stride  8: scores, bboxes, keypoints
          idx 3,4,5  → stride 16: scores, bboxes, keypoints
          idx 6,7,8  → stride 32: scores, bboxes, keypoints

        Some models produce 6 outputs (no keypoints); we handle both.
        """
        num_outputs = len(outputs)

        # Determine grouping: 3 (scores+bbox+kps) or 2 (scores+bbox)
        if num_outputs == 9:
            group_size = 3  # scores, bboxes, keypoints per stride
        elif num_outputs == 6:
            group_size = 2  # scores, bboxes per stride
        else:
            print(f"Warning: unexpected {num_outputs} outputs; attempting generic parse")
            return self._postprocess_generic(outputs, scale_x, scale_y, img_height, img_width)

        all_scores = []
        all_boxes = []

        for i, stride in enumerate(self._FEAT_STRIDES):
            score_blob = outputs[i * group_size]        # (1, num_anchors*feat, 1) or (1, feat, num_anchors)
            bbox_blob = outputs[i * group_size + 1]     # (1, num_anchors*feat, 4)

            # Flatten batch dim
            scores = score_blob.reshape(-1)
            bboxes = bbox_blob.reshape(-1, 4)

            # Feature map size
            feat_h = self.input_height // stride
            feat_w = self.input_width // stride

            anchors = self._generate_anchors(feat_h, feat_w, stride)

            # Decode: bboxes are (left, top, right, bottom) distances from anchor
            x1 = anchors[:, 0] - bboxes[:, 0] * stride
            y1 = anchors[:, 1] - bboxes[:, 1] * stride
            x2 = anchors[:, 0] + bboxes[:, 2] * stride
            y2 = anchors[:, 1] + bboxes[:, 3] * stride

            decoded = np.stack([x1, y1, x2, y2], axis=1)

            all_scores.append(scores)
            all_boxes.append(decoded)

        all_scores = np.concatenate(all_scores)
        all_boxes = np.concatenate(all_boxes)

        # Filter by confidence
        mask = all_scores > self.confidence_threshold
        filtered_scores = all_scores[mask]
        filtered_boxes = all_boxes[mask]

        if len(filtered_scores) == 0:
            return []

        # Scale to original image coordinates
        filtered_boxes[:, 0] *= scale_x
        filtered_boxes[:, 1] *= scale_y
        filtered_boxes[:, 2] *= scale_x
        filtered_boxes[:, 3] *= scale_y

        # Clip
        filtered_boxes[:, 0] = np.clip(filtered_boxes[:, 0], 0, img_width)
        filtered_boxes[:, 1] = np.clip(filtered_boxes[:, 1], 0, img_height)
        filtered_boxes[:, 2] = np.clip(filtered_boxes[:, 2], 0, img_width)
        filtered_boxes[:, 3] = np.clip(filtered_boxes[:, 3], 0, img_height)

        # NMS
        boxes_for_nms = filtered_boxes.astype(np.int32)
        indices = cv2.dnn.NMSBoxes(
            boxes_for_nms.tolist(),
            filtered_scores.tolist(),
            self.confidence_threshold,
            self.nms_threshold,
        )

        results: List[BBox] = []
        if len(indices) > 0:
            for idx in indices.flatten():
                bx = boxes_for_nms[idx]
                x1, y1, x2, y2 = int(bx[0]), int(bx[1]), int(bx[2]), int(bx[3])
                if x2 > x1 and y2 > y1:
                    results.append(BBox(x1, y1, x2, y2, float(filtered_scores[idx])))

        return results

    def _postprocess_generic(
        self,
        outputs: List[np.ndarray],
        scale_x: float,
        scale_y: float,
        img_height: int,
        img_width: int,
    ) -> List[BBox]:
        """Fallback parser for unknown output layouts (best-effort)."""
        boxes: List[BBox] = []
        try:
            if len(outputs) >= 2:
                scores = outputs[0].flatten()
                bboxes = outputs[1].reshape(-1, 4)
                mask = scores > self.confidence_threshold
                for score, bbox in zip(scores[mask], bboxes[mask]):
                    x1 = int(bbox[0] * scale_x)
                    y1 = int(bbox[1] * scale_y)
                    x2 = int(bbox[2] * scale_x)
                    y2 = int(bbox[3] * scale_y)
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(img_width, x2), min(img_height, y2)
                    if x2 > x1 and y2 > y1:
                        boxes.append(BBox(x1, y1, x2, y2, float(score)))
        except Exception as e:
            print(f"Generic postprocess failed: {e}")
        return boxes

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
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

        img_h, img_w = image.shape[:2]
        input_data, scale_x, scale_y = self.preprocess(image)
        outputs = self.session.run(self.output_names, {self.input_name: input_data})
        return self.postprocess(outputs, scale_x, scale_y, img_h, img_w)

    def detect_largest(self, image: np.ndarray) -> BBox | None:
        """
        Detect and return only the largest face in the image.
        Useful for user registration where we expect one face.

        Args:
            image: Input BGR image

        Returns:
            The largest detected face bounding box, or None
        """
        boxes = self.detect(image)
        if not boxes:
            return None
        return max(boxes, key=lambda b: (b.x2 - b.x1) * (b.y2 - b.y1))
