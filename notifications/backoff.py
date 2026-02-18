"""
Exponential backoff tracker for notification throttling.
Prevents notification spam for repeatedly detected unknown visitors.
"""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass

from core.config import (
    BACKOFF_INITIAL_DELAY,
    BACKOFF_MAX_DELAY,
    BACKOFF_MULTIPLIER,
    BACKOFF_VISITOR_TIMEOUT
)


@dataclass
class VisitorState:
    """State for a tracked unknown visitor."""
    embedding: np.ndarray
    first_seen: datetime
    last_seen: datetime
    alert_count: int
    next_alert_time: datetime


class BackoffTracker:
    """
    Tracks unknown visitors and implements exponential backoff for notifications.

    Each unknown visitor is tracked by their embedding similarity.
    Alert schedule:
    - 1st detection: send immediately
    - 2nd detection: after BACKOFF_INITIAL_DELAY seconds
    - 3rd detection: after BACKOFF_INITIAL_DELAY * BACKOFF_MULTIPLIER seconds
    - nth detection: interval doubles each time, up to BACKOFF_MAX_DELAY
    """

    def __init__(
        self,
        initial_delay: int = BACKOFF_INITIAL_DELAY,
        max_delay: int = BACKOFF_MAX_DELAY,
        multiplier: float = BACKOFF_MULTIPLIER,
        visitor_timeout: int = BACKOFF_VISITOR_TIMEOUT,
        similarity_threshold: float = 0.6
    ):
        """
        Initialize the backoff tracker.

        Args:
            initial_delay: Initial delay in seconds for the 2nd alert
            max_delay: Maximum delay in seconds between alerts
            multiplier: Delay multiplier for exponential backoff
            visitor_timeout: Seconds after which a visitor is considered gone
            similarity_threshold: Cosine similarity threshold to consider two embeddings as the same visitor
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.visitor_timeout = visitor_timeout
        self.similarity_threshold = similarity_threshold

        # Track visitors by a unique ID (auto-incrementing)
        self.visitors: Dict[int, VisitorState] = {}
        self.next_visitor_id = 0

        print(f"BackoffTracker initialized (initial_delay={initial_delay}s, "
              f"max_delay={max_delay}s, timeout={visitor_timeout}s)")

    def _find_visitor(self, embedding: np.ndarray) -> Optional[int]:
        """
        Find a visitor by embedding similarity.

        Args:
            embedding: L2-normalized embedding

        Returns:
            Visitor ID if found, None otherwise
        """
        best_match_id = None
        best_similarity = 0.0

        for visitor_id, state in self.visitors.items():
            # Calculate cosine similarity (dot product for normalized vectors)
            similarity = float(np.dot(embedding, state.embedding))

            if similarity > self.similarity_threshold and similarity > best_similarity:
                best_similarity = similarity
                best_match_id = visitor_id

        return best_match_id

    def _calculate_next_delay(self, alert_count: int) -> int:
        """
        Calculate the delay until the next alert based on alert count.

        Args:
            alert_count: Number of alerts already sent

        Returns:
            Delay in seconds
        """
        if alert_count == 0:
            # First alert: immediate
            return 0
        elif alert_count == 1:
            # Second alert: initial delay
            return self.initial_delay
        else:
            # Exponential backoff
            delay = self.initial_delay * (self.multiplier ** (alert_count - 1))
            return min(int(delay), self.max_delay)

    def should_alert(self, embedding: np.ndarray, current_time: Optional[datetime] = None) -> bool:
        """
        Check if an alert should be sent for this visitor.

        Args:
            embedding: L2-normalized face embedding
            current_time: Current time (uses datetime.now() if None)

        Returns:
            True if an alert should be sent, False otherwise
        """
        if current_time is None:
            current_time = datetime.now()

        # Clean up old visitors first
        self._cleanup_old_visitors(current_time)

        # Find if this visitor is already tracked
        visitor_id = self._find_visitor(embedding)

        if visitor_id is None:
            # New visitor: create entry and send alert immediately
            visitor_id = self.next_visitor_id
            self.next_visitor_id += 1

            delay = self._calculate_next_delay(0)
            next_alert_time = current_time + timedelta(seconds=delay)

            self.visitors[visitor_id] = VisitorState(
                embedding=embedding.copy(),
                first_seen=current_time,
                last_seen=current_time,
                alert_count=1,
                next_alert_time=next_alert_time
            )

            print(f"New visitor tracked (ID: {visitor_id}) - Alert sent immediately")
            return True

        else:
            # Existing visitor
            state = self.visitors[visitor_id]
            state.last_seen = current_time

            # Check if it's time for the next alert
            if current_time >= state.next_alert_time:
                # Time to send another alert
                state.alert_count += 1
                delay = self._calculate_next_delay(state.alert_count)
                state.next_alert_time = current_time + timedelta(seconds=delay)

                print(f"Visitor {visitor_id}: Alert #{state.alert_count} sent "
                      f"(next in {delay}s)")
                return True
            else:
                # Still in backoff period
                remaining = (state.next_alert_time - current_time).total_seconds()
                print(f"Visitor {visitor_id}: In backoff (next alert in {remaining:.0f}s)")
                return False

    def _cleanup_old_visitors(self, current_time: datetime):
        """
        Remove visitors who haven't been seen recently.

        Args:
            current_time: Current time
        """
        timeout_threshold = current_time - timedelta(seconds=self.visitor_timeout)
        to_remove = []

        for visitor_id, state in self.visitors.items():
            if state.last_seen < timeout_threshold:
                to_remove.append(visitor_id)

        for visitor_id in to_remove:
            del self.visitors[visitor_id]
            print(f"Visitor {visitor_id} removed from tracker (timed out)")

    def get_visitor_count(self) -> int:
        """Get the number of currently tracked visitors."""
        return len(self.visitors)

    def reset(self):
        """Clear all tracked visitors."""
        self.visitors.clear()
        self.next_visitor_id = 0
        print("BackoffTracker reset")

    def get_visitor_info(self, embedding: np.ndarray) -> Optional[dict]:
        """
        Get information about a visitor.

        Args:
            embedding: Face embedding

        Returns:
            Dict with visitor info, or None if not tracked
        """
        visitor_id = self._find_visitor(embedding)

        if visitor_id is None:
            return None

        state = self.visitors[visitor_id]

        return {
            "visitor_id": visitor_id,
            "first_seen": state.first_seen,
            "last_seen": state.last_seen,
            "alert_count": state.alert_count,
            "next_alert_time": state.next_alert_time
        }


# Global tracker instance (singleton pattern)
_tracker_instance: Optional[BackoffTracker] = None


def get_backoff_tracker() -> BackoffTracker:
    """
    Get the global backoff tracker instance.

    Returns:
        BackoffTracker instance
    """
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = BackoffTracker()
    return _tracker_instance
