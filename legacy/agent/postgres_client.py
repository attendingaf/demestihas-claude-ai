import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)

class PostgresClient:
    _pool = None

    def __init__(self):
        self._initialize_pool()

    def _initialize_pool(self):
        if not PostgresClient._pool:
            try:
                PostgresClient._pool = psycopg2.pool.SimpleConnectionPool(
                    1, 20,
                    host=os.getenv("POSTGRES_HOST", "postgres"),
                    port=os.getenv("POSTGRES_PORT", "5432"),
                    database=os.getenv("POSTGRES_DB", "demestihas_db"),
                    user=os.getenv("POSTGRES_USER", "demestihas_user"),
                    password=os.getenv("POSTGRES_PASSWORD", "")
                )
                logger.info("✅ PostgreSQL connection pool initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize PostgreSQL pool: {str(e)}")
                raise

    @contextmanager
    def get_cursor(self):
        conn = PostgresClient._pool.getconn()
        try:
            yield conn.cursor(cursor_factory=RealDictCursor)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed: {str(e)}")
            raise
        finally:
            PostgresClient._pool.putconn(conn)

    def create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        """Create or retrieve a conversation session."""
        if not session_id:
            session_id = str(uuid.uuid4())

        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO conversation_sessions (session_id, user_id)
                VALUES (%s, %s)
                ON CONFLICT (session_id) DO NOTHING
                RETURNING session_id
            """, (session_id, user_id))
            
            # If we didn't insert (conflict), we still return the session_id
            return session_id

    def store_message(self, user_id: str, session_id: str, role: str, content: str, 
                     routing_agent: Optional[str] = None, confidence_score: Optional[float] = None):
        """Store a message in the database."""
        # Ensure session exists first
        self.create_session(user_id, session_id)

        with self.get_cursor() as cursor:
            # Update session stats
            cursor.execute("""
                UPDATE conversation_sessions 
                SET message_count = message_count + 1,
                    ended_at = NOW()
                WHERE session_id = %s
            """, (session_id,))

            # Insert message
            cursor.execute("""
                INSERT INTO messages (session_id, user_id, role, content, routing_agent, confidence_score)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session_id, user_id, role, content, routing_agent, confidence_score))
            
            logger.debug(f"Stored {role} message in session {session_id}")

    def get_session_history(self, user_id: str, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve conversation history for a session."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT role, content, timestamp, routing_agent
                FROM messages
                WHERE user_id = %s AND session_id = %s
                ORDER BY timestamp ASC
                LIMIT %s
            """, (user_id, session_id, limit))
            return cursor.fetchall()

    def get_recent_sessions(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get list of recent sessions for a user."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT session_id, started_at, ended_at, message_count, summary
                FROM conversation_sessions
                WHERE user_id = %s
                ORDER BY ended_at DESC
                LIMIT %s
            """, (user_id, limit))
            return cursor.fetchall()

    def update_session_summary(self, session_id: str, summary: str):
        """Update the summary for a session."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE conversation_sessions
                SET summary = %s
                WHERE session_id = %s
            """, (summary, session_id))
            logger.debug(f"Updated summary for session {session_id}")

# Global instance
postgres_client = None

def get_postgres_client():
    global postgres_client
    if not postgres_client:
        try:
            postgres_client = PostgresClient()
        except Exception:
            return None
    return postgres_client
