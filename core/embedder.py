"""
Face Embedding Module using ONNX Runtime.
Extracts 512-dimensional embeddings from face images using MobileFaceNet (w600k_mbf)
or compatible face recognition models.
"""
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import onnxruntime as ort

from core.config import FACE_EMBEDDING_MODEL, FACE_INPUT_SIZE


class FaceEmbedder:
    """
    Face embedding extraction using ONNX models.
    Supports MobileFaceNet (w600k_mbf), EdgeFace-XS, and other models
    that output a single embedding vector.
    """

    def __init__(
        self,
        model_path: Path = FACE_EMBEDDING_MODEL,
        input_size: tuple[int, int] = FACE_INPUT_SIZE,
    ):
        """
        Initialize the face embedder.

        Args:
            model_path: Path to the ONNX model file
            input_size: Model input size (height, width)
        """
        self.model_path = model_path
        self.input_size = input_size

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Face embedding model not found at {self.model_path}. "
                f"Please run 'python scripts/download_models.py' "
                f"or place the model manually."
            )

        # Initialize ONNX Runtime session
        providers = ['CPUExecutionProvider']
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 4  # Optimize for Pi 5

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=sess_options,
            providers=providers
        )

        # Get model input/output names
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        # Auto-detect embedding size from model output shape
        out_shape = self.session.get_outputs()[0].shape
        # Shape is typically [1, 512] or [None, 512]
        self.embedding_size = int(out_shape[-1]) if out_shape[-1] is not None else 512

        # Auto-detect input size from model if available
        in_shape = self.session.get_inputs()[0].shape
        if len(in_shape) == 4 and isinstance(in_shape[2], int) and isinstance(in_shape[3], int):
            self.input_size = (int(in_shape[2]), int(in_shape[3]))

        print(f"FaceEmbedder initialized: {self.model_path.name}")
        print(f"  Input : {self.input_name} {self.session.get_inputs()[0].shape}")
        print(f"  Output: {self.output_name} {out_shape}")
        print(f"  Embedding size: {self.embedding_size}")
        print(f"  Input size (H×W): {self.input_size}")

    def preprocess(self, face_image: np.ndarray) -> np.ndarray:
        """
        Preprocess face image for embedding extraction.

        Args:
            face_image: Input BGR face image (OpenCV format)

        Returns:
            Preprocessed image tensor
        """
        # Resize to model input size
        resized = cv2.resize(face_image, self.input_size)

        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Normalize to [-1, 1] (standard for InsightFace / ArcFace models)
        normalized = (rgb.astype(np.float32) - 127.5) / 127.5

        # Transpose to CHW format (channels first)
        transposed = normalized.transpose(2, 0, 1)

        # Add batch dimension
        batched = np.expand_dims(transposed, axis=0)

        return batched

    def normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """
        L2-normalize the embedding vector.

        Args:
            embedding: Raw embedding vector

        Returns:
            L2-normalized embedding
        """
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return embedding / norm

    def embed(self, face_image: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract L2-normalized embedding from a face image.

        Args:
            face_image: Input BGR face image (OpenCV format)

        Returns:
            L2-normalized embedding vector, or None if extraction fails
        """
        if face_image is None or face_image.size == 0:
            return None

        # Reject very small crops that would produce garbage embeddings
        if face_image.shape[0] < 10 or face_image.shape[1] < 10:
            return None

        try:
            input_data = self.preprocess(face_image)
            output = self.session.run([self.output_name], {self.input_name: input_data})[0]

            # Extract embedding (remove batch dimension)
            embedding = output.flatten()

            # Verify embedding size
            if len(embedding) != self.embedding_size:
                print(f"Warning: Expected embedding size {self.embedding_size}, "
                      f"got {len(embedding)}")

            # L2 normalize
            return self.normalize_embedding(embedding)

        except Exception as e:
            print(f"Error extracting embedding: {e}")
            return None

    def embed_batch(self, face_images: list[np.ndarray]) -> list[Optional[np.ndarray]]:
        """
        Extract embeddings from multiple face images (sequential).

        Args:
            face_images: List of BGR face images

        Returns:
            List of embeddings (None for failed extractions)
        """
        return [self.embed(img) for img in face_images]

    def cosine_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Cosine similarity between two L2-normalized embeddings (= dot product).
        """
        return float(np.dot(embedding1, embedding2))

    def euclidean_distance(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """Euclidean distance between two embeddings."""
        return float(np.linalg.norm(embedding1 - embedding2))
