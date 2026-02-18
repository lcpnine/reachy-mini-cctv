"""
User repository for CRUD operations on the users table.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from db.database import Database, get_db


@dataclass
class User:
    """User model."""
    user_id: int
    name: str
    created_at: datetime


class UserRepository:
    """Repository for user management operations."""

    def __init__(self, db: Database | None = None):
        """
        Initialize the user repository.

        Args:
            db: Database instance (uses global instance if None)
        """
        self.db = db or get_db()

    def create_user(self, name: str) -> int:
        """
        Create a new user.

        Args:
            name: User's name

        Returns:
            The new user_id
        """
        with self.db.get_cursor() as cur:
            cur.execute(
                "INSERT INTO users (name) VALUES (?)",
                (name,)
            )
            user_id = cur.lastrowid

        print(f"Created user: {name} (ID: {user_id})")
        return user_id

    def get_user(self, user_id: int) -> Optional[User]:
        """
        Get a user by ID.

        Args:
            user_id: The user ID

        Returns:
            User object or None if not found
        """
        row = self.db.fetch_one(
            "SELECT user_id, name, created_at FROM users WHERE user_id = ?",
            (user_id,)
        )

        if row:
            return User(
                user_id=row['user_id'],
                name=row['name'],
                created_at=datetime.fromisoformat(row['created_at'])
            )

        return None

    def get_user_by_name(self, name: str) -> Optional[User]:
        """
        Get a user by name (exact match).

        Args:
            name: The user's name

        Returns:
            User object or None if not found
        """
        row = self.db.fetch_one(
            "SELECT user_id, name, created_at FROM users WHERE name = ?",
            (name,)
        )

        if row:
            return User(
                user_id=row['user_id'],
                name=row['name'],
                created_at=datetime.fromisoformat(row['created_at'])
            )

        return None

    def list_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        """
        List all users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of User objects
        """
        rows = self.db.fetch_all(
            """
            SELECT user_id, name, created_at
            FROM users
            ORDER BY name
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )

        users = []
        for row in rows:
            users.append(User(
                user_id=row['user_id'],
                name=row['name'],
                created_at=datetime.fromisoformat(row['created_at'])
            ))

        return users

    def get_user_count(self) -> int:
        """
        Get the total number of registered users.

        Returns:
            User count
        """
        row = self.db.fetch_one("SELECT COUNT(*) as count FROM users")
        return row['count'] if row else 0

    def update_user(self, user_id: int, name: str) -> bool:
        """
        Update a user's name.

        Args:
            user_id: The user ID
            name: New name

        Returns:
            True if updated, False if user not found
        """
        with self.db.get_cursor() as cur:
            cur.execute(
                "UPDATE users SET name = ? WHERE user_id = ?",
                (name, user_id)
            )
            updated = cur.rowcount > 0

        if updated:
            print(f"Updated user {user_id}: {name}")

        return updated

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user.
        Note: This will leave user_id as NULL in related events (orphan events).

        Args:
            user_id: The user ID

        Returns:
            True if deleted, False if user not found
        """
        with self.db.get_cursor() as cur:
            cur.execute(
                "DELETE FROM users WHERE user_id = ?",
                (user_id,)
            )
            deleted = cur.rowcount > 0

        if deleted:
            print(f"Deleted user {user_id}")

        return deleted

    def user_exists(self, user_id: int) -> bool:
        """
        Check if a user exists.

        Args:
            user_id: The user ID

        Returns:
            True if user exists, False otherwise
        """
        row = self.db.fetch_one(
            "SELECT 1 FROM users WHERE user_id = ?",
            (user_id,)
        )
        return row is not None

    def search_users(self, query: str, limit: int = 20) -> list[User]:
        """
        Search users by name (case-insensitive partial match).

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching User objects
        """
        rows = self.db.fetch_all(
            """
            SELECT user_id, name, created_at
            FROM users
            WHERE name LIKE ?
            ORDER BY name
            LIMIT ?
            """,
            (f"%{query}%", limit)
        )

        users = []
        for row in rows:
            users.append(User(
                user_id=row['user_id'],
                name=row['name'],
                created_at=datetime.fromisoformat(row['created_at'])
            ))

        return users
