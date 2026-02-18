"""
Database connection and initialization module.
Manages SQLite database with WAL mode for concurrent access.
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Generator

from core.config import DB_PATH


class Database:
    """
    SQLite database manager with WAL mode enabled for better concurrency.
    """

    def __init__(self, db_path: Path = DB_PATH):
        """
        Initialize the database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize the database
        self._init_database()

        print(f"Database initialized at {self.db_path}")

    def _init_database(self):
        """Initialize database with schema and enable WAL mode."""
        conn = self.get_connection()
        try:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL;")

            # Set synchronous mode to NORMAL for better performance
            # (FULL is safer but slower, NORMAL is a good balance)
            conn.execute("PRAGMA synchronous=NORMAL;")

            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys=ON;")

            # Read and execute schema
            schema_path = Path(__file__).parent / "schema.sql"
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                conn.executescript(schema_sql)
                conn.commit()
                print("Database schema initialized successfully")
            else:
                print(f"Warning: Schema file not found at {schema_path}")

        finally:
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a new database connection.

        Returns:
            sqlite3.Connection object
        """
        conn = sqlite3.Connection(str(self.db_path))

        # Enable foreign keys for this connection
        conn.execute("PRAGMA foreign_keys=ON;")

        # Return rows as sqlite3.Row objects (dict-like access)
        conn.row_factory = sqlite3.Row

        return conn

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Context manager for database operations.
        Automatically commits on success, rolls back on error.

        Usage:
            with db.get_cursor() as cur:
                cur.execute("INSERT INTO ...")

        Yields:
            sqlite3.Cursor object
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a query and return the cursor.
        Note: For SELECT queries, use this when you need to fetch results immediately.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Cursor with results
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor

    def execute_many(self, query: str, params_list: list[tuple]) -> int:
        """
        Execute a query with multiple parameter sets.

        Args:
            query: SQL query
            params_list: List of parameter tuples

        Returns:
            Number of rows affected
        """
        with self.get_cursor() as cur:
            cur.executemany(query, params_list)
            return cur.rowcount

    def fetch_one(self, query: str, params: tuple = ()) -> sqlite3.Row | None:
        """
        Execute a query and fetch one result.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Single row or None
        """
        conn = self.get_connection()
        try:
            cursor = conn.execute(query, params)
            return cursor.fetchone()
        finally:
            conn.close()

    def fetch_all(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """
        Execute a query and fetch all results.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            List of rows
        """
        conn = self.get_connection()
        try:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()

    def get_table_names(self) -> list[str]:
        """
        Get list of all tables in the database.

        Returns:
            List of table names
        """
        rows = self.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row['name'] for row in rows]

    def get_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.

        Args:
            table_name: Name of the table

        Returns:
            Row count
        """
        row = self.fetch_one(f"SELECT COUNT(*) as count FROM {table_name}")
        return row['count'] if row else 0

    def vacuum(self):
        """
        Run VACUUM to reclaim space and optimize the database.
        This should be run periodically, especially after many deletions.
        """
        conn = self.get_connection()
        try:
            conn.execute("VACUUM;")
            print("Database vacuumed successfully")
        finally:
            conn.close()

    def close(self):
        """
        Close the database connection.
        Note: In practice, we use connection pooling, so this is rarely needed.
        """
        # Since we create connections on-demand, there's nothing to close here
        pass


# Global database instance (singleton pattern)
_db_instance: Database | None = None


def get_db() -> Database:
    """
    Get the global database instance.
    Creates it if it doesn't exist yet.

    Returns:
        Database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
