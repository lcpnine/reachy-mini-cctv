"""
Face Recognition Module using FAISS for vector similarity search.
Manages a searchable index of face embeddings for user identification.
"""
import json
import numpy as np
import faiss
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass, asdict

from core.config import (
    RECOGNITION_THRESHOLD,
    EMBEDDING_SIZE,
    FAISS_INDEX_PATH,
    FAISS_MAPPING_PATH
)


@dataclass
class RecognitionResult:
    """Result of a face recognition query."""
    user_id: Optional[int]
    confidence: float
    is_known: bool


class FaceRecognizer:
    """
    Face recognition using FAISS IndexFlatIP (Inner Product) for cosine similarity search.
    Manages the mapping between FAISS indices and user IDs.
    """

    def __init__(
        self,
        embedding_size: int = EMBEDDING_SIZE,
        threshold: float = RECOGNITION_THRESHOLD
    ):
        """
        Initialize the face recognizer.

        Args:
            embedding_size: Dimension of face embeddings
            threshold: Minimum similarity score to consider a match
        """
        self.embedding_size = embedding_size
        self.threshold = threshold

        # Initialize FAISS index for cosine similarity (Inner Product for normalized vectors)
        self.index = faiss.IndexFlatIP(embedding_size)

        # Mapping between FAISS index positions and user IDs
        # Format: {index_position: user_id}
        self.index_to_user: dict[int, int] = {}

        # Reverse mapping for quick lookup
        # Format: {user_id: [index_positions]}
        self.user_to_indices: dict[int, list[int]] = {}

        print(f"FaceRecognizer initialized (threshold={threshold})")

    def register(self, user_id: int, embedding: np.ndarray) -> int:
        """
        Register a new face embedding for a user.
        A user can have multiple embeddings (multiple photos).

        Args:
            user_id: The user ID to associate with this embedding
            embedding: L2-normalized 512-dim embedding

        Returns:
            The FAISS index position where the embedding was added
        """
        if len(embedding) != self.embedding_size:
            raise ValueError(
                f"Embedding size mismatch: expected {self.embedding_size}, "
                f"got {len(embedding)}"
            )

        # Ensure embedding is L2-normalized
        norm = np.linalg.norm(embedding)
        if not np.isclose(norm, 1.0, atol=1e-5):
            print(f"Warning: Embedding not normalized (norm={norm}). Normalizing...")
            embedding = embedding / norm

        # Add to FAISS index
        embedding_2d = embedding.reshape(1, -1).astype(np.float32)
        index_position = self.index.ntotal
        self.index.add(embedding_2d)

        # Update mappings
        self.index_to_user[index_position] = user_id

        if user_id not in self.user_to_indices:
            self.user_to_indices[user_id] = []
        self.user_to_indices[user_id].append(index_position)

        print(f"Registered user {user_id} at index {index_position} "
              f"(total: {self.index.ntotal})")

        return index_position

    def remove(self, user_id: int) -> bool:
        """
        Remove all embeddings associated with a user.
        Note: FAISS IndexFlatIP doesn't support true removal, so we rebuild the index.

        Args:
            user_id: The user ID to remove

        Returns:
            True if user was found and removed, False otherwise
        """
        if user_id not in self.user_to_indices:
            print(f"User {user_id} not found in index")
            return False

        # Get all embeddings except those belonging to this user
        embeddings_to_keep = []
        new_mappings = {}

        for idx in range(self.index.ntotal):
            if self.index_to_user.get(idx) != user_id:
                # Reconstruct the embedding
                embedding = self.index.reconstruct(int(idx))
                embeddings_to_keep.append(embedding)
                new_mappings[len(embeddings_to_keep) - 1] = self.index_to_user[idx]

        # Rebuild the index
        self.index = faiss.IndexFlatIP(self.embedding_size)

        if embeddings_to_keep:
            embeddings_array = np.vstack(embeddings_to_keep).astype(np.float32)
            self.index.add(embeddings_array)

        # Update mappings
        self.index_to_user = new_mappings
        self.user_to_indices = {}

        for idx, uid in new_mappings.items():
            if uid not in self.user_to_indices:
                self.user_to_indices[uid] = []
            self.user_to_indices[uid].append(idx)

        # Remove user from reverse mapping
        if user_id in self.user_to_indices:
            del self.user_to_indices[user_id]

        print(f"Removed user {user_id} from index (remaining: {self.index.ntotal})")
        return True

    def recognize(self, embedding: np.ndarray) -> RecognitionResult:
        """
        Recognize a face by searching for the most similar embedding in the index.

        Args:
            embedding: L2-normalized 512-dim embedding to search for

        Returns:
            RecognitionResult containing user_id (or None if unknown) and confidence
        """
        if self.index.ntotal == 0:
            # No users registered yet
            return RecognitionResult(
                user_id=None,
                confidence=0.0,
                is_known=False
            )

        if len(embedding) != self.embedding_size:
            raise ValueError(
                f"Embedding size mismatch: expected {self.embedding_size}, "
                f"got {len(embedding)}"
            )

        # Ensure embedding is L2-normalized
        norm = np.linalg.norm(embedding)
        if not np.isclose(norm, 1.0, atol=1e-5):
            embedding = embedding / norm

        # Search for the most similar embedding (k=1)
        embedding_2d = embedding.reshape(1, -1).astype(np.float32)
        distances, indices = self.index.search(embedding_2d, k=1)

        # Extract results
        confidence = float(distances[0][0])  # Cosine similarity (inner product)
        index_position = int(indices[0][0])

        # Check if confidence meets threshold
        if confidence >= self.threshold:
            user_id = self.index_to_user.get(index_position)
            return RecognitionResult(
                user_id=user_id,
                confidence=confidence,
                is_known=True
            )
        else:
            return RecognitionResult(
                user_id=None,
                confidence=confidence,
                is_known=False
            )

    def recognize_top_k(
        self,
        embedding: np.ndarray,
        k: int = 5
    ) -> list[RecognitionResult]:
        """
        Get the top K most similar faces from the index.

        Args:
            embedding: L2-normalized 512-dim embedding to search for
            k: Number of results to return

        Returns:
            List of RecognitionResult objects, sorted by confidence (descending)
        """
        if self.index.ntotal == 0:
            return []

        k = min(k, self.index.ntotal)  # Don't search for more than we have

        # Ensure embedding is L2-normalized
        norm = np.linalg.norm(embedding)
        if not np.isclose(norm, 1.0, atol=1e-5):
            embedding = embedding / norm

        # Search
        embedding_2d = embedding.reshape(1, -1).astype(np.float32)
        distances, indices = self.index.search(embedding_2d, k=k)

        # Build results
        results = []
        for confidence, index_position in zip(distances[0], indices[0]):
            confidence = float(confidence)
            user_id = self.index_to_user.get(int(index_position))
            is_known = confidence >= self.threshold

            results.append(RecognitionResult(
                user_id=user_id if is_known else None,
                confidence=confidence,
                is_known=is_known
            ))

        return results

    def save(self, index_path: Path = FAISS_INDEX_PATH, mapping_path: Path = FAISS_MAPPING_PATH):
        """
        Save the FAISS index and user mappings to disk.

        Args:
            index_path: Path to save the FAISS index
            mapping_path: Path to save the user mappings (JSON)
        """
        # Ensure parent directories exist
        index_path.parent.mkdir(parents=True, exist_ok=True)
        mapping_path.parent.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, str(index_path))

        # Save mappings
        mappings = {
            "index_to_user": {str(k): v for k, v in self.index_to_user.items()},
            "user_to_indices": {str(k): v for k, v in self.user_to_indices.items()},
            "embedding_size": self.embedding_size,
            "threshold": self.threshold
        }

        with open(mapping_path, 'w') as f:
            json.dump(mappings, f, indent=2)

        print(f"Saved FAISS index to {index_path}")
        print(f"Saved mappings to {mapping_path}")

    @classmethod
    def load(
        cls,
        index_path: Path = FAISS_INDEX_PATH,
        mapping_path: Path = FAISS_MAPPING_PATH
    ) -> 'FaceRecognizer':
        """
        Load a saved FAISS index and user mappings from disk.

        Args:
            index_path: Path to the FAISS index file
            mapping_path: Path to the user mappings file (JSON)

        Returns:
            A FaceRecognizer instance with loaded data
        """
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found at {index_path}")
        if not mapping_path.exists():
            raise FileNotFoundError(f"Mappings file not found at {mapping_path}")

        # Load mappings
        with open(mapping_path, 'r') as f:
            mappings = json.load(f)

        # Create instance
        recognizer = cls(
            embedding_size=mappings["embedding_size"],
            threshold=mappings["threshold"]
        )

        # Load FAISS index
        recognizer.index = faiss.read_index(str(index_path))

        # Restore mappings
        recognizer.index_to_user = {int(k): v for k, v in mappings["index_to_user"].items()}
        recognizer.user_to_indices = {int(k): v for k, v in mappings["user_to_indices"].items()}

        print(f"Loaded FAISS index from {index_path} ({recognizer.index.ntotal} embeddings)")
        print(f"Loaded mappings for {len(recognizer.user_to_indices)} users")

        return recognizer

    def get_user_count(self) -> int:
        """Get the number of registered users."""
        return len(self.user_to_indices)

    def get_embedding_count(self) -> int:
        """Get the total number of embeddings in the index."""
        return self.index.ntotal

    def get_user_embedding_count(self, user_id: int) -> int:
        """Get the number of embeddings for a specific user."""
        return len(self.user_to_indices.get(user_id, []))
