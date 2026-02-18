"""
Face Embedding Module using ONNX Runtime.
Extracts 512-dimensional embeddings from face images using EdgeFace or similar models.
"""
import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import Optional

from core.config import (
    FACE_EMBEDDING_MODEL,
    EMBEDDING_SIZE,
    FACE_INPUT_SIZE
)


class FaceEmbedder:
    """
    Face embedding extraction using ONNX models.
    Supports EdgeFace-XS and other face recognition models.
    """

    def __init__(
        self,
        model_path: Path = FACE_EMBEDDING_MODEL,
        input_size: tuple[int, int] = FACE_INPUT_SIZE,
        embedding_size: int = EMBEDDING_SIZE
    ):
        """
        Initialize the face embedder.

        Args:
            model_path: Path to the ONNX model file
            input_size: Model input size (height, width)
            embedding_size: Expected embedding dimension
        """
        self.model_path = model_path
        self.input_size = input_size
        self.embedding_size = embedding_size

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Face embedding model not found at {self.model_path}. "
                f"Please run 'python scripts/setup_models_from_insightface.py' "
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

        print(f"FaceEmbedder initialized with model: {self.model_path.name}")
        print(f"Input shape: {self.session.get_inputs()[0].shape}")
        print(f"Output shape: {self.session.get_outputs()[0].shape}")

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

        # Normalize to [-1, 1] or [0, 1] depending on model
        # Most face recognition models use [-1, 1] normalization
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
            512-dimensional L2-normalized embedding, or None if extraction fails
        """
        if face_image is None or face_image.size == 0:
            return None

        try:
            # Preprocess
            input_data = self.preprocess(face_image)

            # Run inference
            output = self.session.run([self.output_name], {self.input_name: input_data})[0]

            # Extract embedding (remove batch dimension)
            embedding = output.flatten()

            # Verify embedding size
            if len(embedding) != self.embedding_size:
                print(f"Warning: Expected embedding size {self.embedding_size}, "
                      f"got {len(embedding)}")

            # L2 normalize
            normalized = self.normalize_embedding(embedding)

            return normalized

        except Exception as e:
            print(f"Error extracting embedding: {e}")
            return None

    def embed_batch(self, face_images: list[np.ndarray]) -> list[Optional[np.ndarray]]:
        """
        Extract embeddings from multiple face images.
        Note: This processes images sequentially. For true batch processing,
        modify to create a batched input tensor.

        Args:
            face_images: List of BGR face images

        Returns:
            List of embeddings (None for failed extractions)
        """
        embeddings = []
        for face_image in face_images:
            embedding = self.embed(face_image)
            embeddings.append(embedding)
        return embeddings

    def cosine_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        For L2-normalized embeddings, this is simply the dot product.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Cosine similarity score [-1, 1]
        """
        return float(np.dot(embedding1, embedding2))

    def euclidean_distance(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate Euclidean distance between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Euclidean distance
        """
        return float(np.linalg.norm(embedding1 - embedding2))
