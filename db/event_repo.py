"""
Event repository for logging and querying face detection events.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from db.database import Database, get_db


@dataclass
class Event:
    """Event model."""
    event_id: int
    user_id: Optional[int]  # None for unknown visitors
    confidence: float
    photo_path: Optional[str]  # None for known users
    occurred_at: datetime
    user_name: Optional[str] = None  # Populated when querying with user info


class EventRepository:
    """Repository for event logging and querying."""

    def __init__(self, db: Database | None = None):
        """
        Initialize the event repository.

        Args:
            db: Database instance (uses global instance if None)
        """
        self.db = db or get_db()

    def log_event(
        self,
        user_id: Optional[int],
        confidence: float,
        photo_path: Optional[str] = None
    ) -> int:
        """
        Log a face detection event.

        Args:
            user_id: User ID (None for unknown visitors)
            confidence: Recognition confidence score
            photo_path: Path to saved photo (for unknown visitors)

        Returns:
            The new event_id
        """
        with self.db.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (user_id, confidence, photo_path)
                VALUES (?, ?, ?)
                """,
                (user_id, confidence, photo_path)
            )
            event_id = cur.lastrowid

        event_type = "known" if user_id else "unknown"
        print(f"Logged {event_type} event (ID: {event_id}, confidence: {confidence:.2f})")

        return event_id

    def get_event(self, event_id: int) -> Optional[Event]:
        """
        Get an event by ID.

        Args:
            event_id: The event ID

        Returns:
            Event object or None if not found
        """
        row = self.db.fetch_one(
            """
            SELECT e.event_id, e.user_id, e.confidence, e.photo_path, e.occurred_at, u.name as user_name
            FROM events e
            LEFT JOIN users u ON e.user_id = u.user_id
            WHERE e.event_id = ?
            """,
            (event_id,)
        )

        if row:
            return self._row_to_event(row)

        return None

    def get_events(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id_filter: Optional[int] = None,
        include_unknown: bool = True,
        include_known: bool = True
    ) -> list[Event]:
        """
        Get events with optional filtering.

        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip
            user_id_filter: Filter by specific user ID (None for all)
            include_unknown: Include unknown visitor events
            include_known: Include known user events

        Returns:
            List of Event objects
        """
        # Build WHERE clause based on filters
        where_clauses = []
        params = []

        if user_id_filter is not None:
            where_clauses.append("e.user_id = ?")
            params.append(user_id_filter)
        else:
            # Apply unknown/known filters
            if not include_unknown:
                where_clauses.append("e.user_id IS NOT NULL")
            if not include_known:
                where_clauses.append("e.user_id IS NULL")

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Add pagination parameters
        params.extend([limit, offset])

        query = f"""
            SELECT e.event_id, e.user_id, e.confidence, e.photo_path, e.occurred_at, u.name as user_name
            FROM events e
            LEFT JOIN users u ON e.user_id = u.user_id
            {where_sql}
            ORDER BY e.occurred_at DESC
            LIMIT ? OFFSET ?
        """

        rows = self.db.fetch_all(query, tuple(params))

        events = []
        for row in rows:
            events.append(self._row_to_event(row))

        return events

    def get_recent_events(
        self,
        since: datetime,
        user_id_filter: Optional[int] = None
    ) -> list[Event]:
        """
        Get events that occurred after a specific datetime.

        Args:
            since: Get events after this datetime
            user_id_filter: Filter by specific user ID (None for all)

        Returns:
            List of Event objects
        """
        if user_id_filter is not None:
            query = """
                SELECT e.event_id, e.user_id, e.confidence, e.photo_path, e.occurred_at, u.name as user_name
                FROM events e
                LEFT JOIN users u ON e.user_id = u.user_id
                WHERE e.occurred_at > ? AND e.user_id = ?
                ORDER BY e.occurred_at DESC
            """
            params = (since.isoformat(), user_id_filter)
        else:
            query = """
                SELECT e.event_id, e.user_id, e.confidence, e.photo_path, e.occurred_at, u.name as user_name
                FROM events e
                LEFT JOIN users u ON e.user_id = u.user_id
                WHERE e.occurred_at > ?
                ORDER BY e.occurred_at DESC
            """
            params = (since.isoformat(),)

        rows = self.db.fetch_all(query, params)

        events = []
        for row in rows:
            events.append(self._row_to_event(row))

        return events

    def get_unknown_events(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> list[Event]:
        """
        Get only unknown visitor events.

        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of Event objects
        """
        return self.get_events(
            limit=limit,
            offset=offset,
            include_known=False,
            include_unknown=True
        )

    def get_known_events(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> list[Event]:
        """
        Get only known user events.

        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of Event objects
        """
        return self.get_events(
            limit=limit,
            offset=offset,
            include_known=True,
            include_unknown=False
        )

    def get_user_events(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> list[Event]:
        """
        Get all events for a specific user.

        Args:
            user_id: The user ID
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of Event objects
        """
        return self.get_events(
            limit=limit,
            offset=offset,
            user_id_filter=user_id
        )

    def get_event_count(
        self,
        user_id_filter: Optional[int] = None,
        include_unknown: bool = True,
        include_known: bool = True
    ) -> int:
        """
        Get the total number of events with optional filtering.

        Args:
            user_id_filter: Filter by specific user ID (None for all)
            include_unknown: Include unknown visitor events
            include_known: Include known user events

        Returns:
            Event count
        """
        where_clauses = []
        params = []

        if user_id_filter is not None:
            where_clauses.append("user_id = ?")
            params.append(user_id_filter)
        else:
            if not include_unknown:
                where_clauses.append("user_id IS NOT NULL")
            if not include_known:
                where_clauses.append("user_id IS NULL")

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"SELECT COUNT(*) as count FROM events {where_sql}"

        row = self.db.fetch_one(query, tuple(params))
        return row['count'] if row else 0

    def delete_event(self, event_id: int) -> bool:
        """
        Delete an event.

        Args:
            event_id: The event ID

        Returns:
            True if deleted, False if event not found
        """
        with self.db.get_cursor() as cur:
            cur.execute(
                "DELETE FROM events WHERE event_id = ?",
                (event_id,)
            )
            deleted = cur.rowcount > 0

        if deleted:
            print(f"Deleted event {event_id}")

        return deleted

    def delete_old_events(self, before: datetime) -> int:
        """
        Delete events older than a specific datetime.
        Useful for data retention policies.

        Args:
            before: Delete events before this datetime

        Returns:
            Number of events deleted
        """
        with self.db.get_cursor() as cur:
            cur.execute(
                "DELETE FROM events WHERE occurred_at < ?",
                (before.isoformat(),)
            )
            deleted_count = cur.rowcount

        print(f"Deleted {deleted_count} old events (before {before})")
        return deleted_count

    def _row_to_event(self, row) -> Event:
        """Convert a database row to an Event object."""
        return Event(
            event_id=row['event_id'],
            user_id=row['user_id'],
            confidence=row['confidence'],
            photo_path=row['photo_path'],
            occurred_at=datetime.fromisoformat(row['occurred_at']),
            user_name=row['user_name'] if 'user_name' in row.keys() else None
        )
