"""
Family Authentication System for DemestiChat
Provides secure authentication for family members with password hashing.
"""

import os
import hashlib
import secrets
import json
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from passlib.hash import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)


class FamilyAuthManager:
    """Manages family member authentication and authorization."""

    def __init__(self):
        self.conn = None
        self._connect()
        self._ensure_schema()

    def _connect(self):
        """Establish PostgreSQL connection."""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                database=os.getenv("POSTGRES_DB", "demestihas_db"),
                user=os.getenv("POSTGRES_USER", "mene_demestihas"),
                password=os.getenv("POSTGRES_PASSWORD"),
            )
            self.conn.autocommit = True
            logger.info("✅ FamilyAuthManager connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            self.conn = None

    def _ensure_schema(self):
        """Ensure family_members table exists."""
        if not self.conn:
            return

        try:
            with self.conn.cursor() as cursor:
                # Add password_hash column to users table if it doesn't exist
                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
                """)

                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'family';
                """)

                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(255);
                """)

                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;
                """)

                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
                """)

                logger.info("✅ Users table schema updated for authentication")
        except Exception as e:
            logger.error(f"Failed to update schema: {e}")

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.verify(password, password_hash)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def register_family_member(
        self,
        user_id: str,
        password: str,
        display_name: str,
        email: Optional[str] = None,
        role: str = "family",
        avatar_url: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Register a new family member.

        Args:
            user_id: Unique identifier for the user
            password: Plain text password (will be hashed)
            display_name: Display name for the user
            email: Optional email address
            role: User role (admin, family, child, guest)
            avatar_url: Optional avatar URL

        Returns:
            Dict with success status and user info or error message
        """
        if not self.conn:
            self._connect()

        if not self.conn:
            return {"success": False, "error": "Database connection failed"}

        # Validate role
        valid_roles = ["admin", "family", "child", "guest"]
        if role not in valid_roles:
            return {
                "success": False,
                "error": f"Invalid role. Must be one of: {valid_roles}",
            }

        # Hash the password
        password_hash = self.hash_password(password)

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check if user already exists
                cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                existing = cursor.fetchone()

                if existing:
                    return {"success": False, "error": "User ID already exists"}

                # Check if email already exists
                if email:
                    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                    existing_email = cursor.fetchone()
                    if existing_email:
                        return {"success": False, "error": "Email already registered"}

                # Insert new user
                cursor.execute(
                    """
                    INSERT INTO users
                    (id, display_name, email, password_hash, role, avatar_url, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                    RETURNING id, display_name, email, role, avatar_url, created_at
                """,
                    (user_id, display_name, email, password_hash, role, avatar_url),
                )

                user = cursor.fetchone()
                logger.info(
                    f"✅ Registered new family member: {user_id} ({display_name})"
                )

                return {"success": True, "user": dict(user)}

        except Exception as e:
            logger.error(f"Failed to register user: {e}")
            return {"success": False, "error": str(e)}

    def authenticate(self, user_id: str, password: str) -> Dict[str, any]:
        """
        Authenticate a family member.

        Args:
            user_id: User identifier
            password: Plain text password

        Returns:
            Dict with success status and user info or error message
        """
        if not self.conn:
            self._connect()

        if not self.conn:
            return {"success": False, "error": "Database connection failed"}

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get user with password hash
                cursor.execute(
                    """
                    SELECT id, display_name, email, password_hash, role, avatar_url, is_active
                    FROM users
                    WHERE id = %s
                """,
                    (user_id,),
                )

                user = cursor.fetchone()

                if not user:
                    logger.warning(f"Authentication failed: User {user_id} not found")
                    return {"success": False, "error": "Invalid credentials"}

                if not user["is_active"]:
                    logger.warning(f"Authentication failed: User {user_id} is inactive")
                    return {"success": False, "error": "Account is inactive"}

                if not user["password_hash"]:
                    logger.warning(
                        f"Authentication failed: User {user_id} has no password set"
                    )
                    return {
                        "success": False,
                        "error": "Account not properly configured",
                    }

                # Verify password
                if not self.verify_password(password, user["password_hash"]):
                    logger.warning(
                        f"Authentication failed: Invalid password for {user_id}"
                    )
                    return {"success": False, "error": "Invalid credentials"}

                # Update last login
                cursor.execute(
                    "UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,)
                )

                # Return user info (without password hash)
                user_info = dict(user)
                del user_info["password_hash"]

                logger.info(f"✅ User authenticated: {user_id}")

                return {"success": True, "user": user_info}

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return {"success": False, "error": "Authentication failed"}

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user information by user_id."""
        if not self.conn:
            self._connect()

        if not self.conn:
            return None

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, display_name, email, role, avatar_url,
                           created_at, last_login, is_active
                    FROM users
                    WHERE id = %s
                """,
                    (user_id,),
                )

                user = cursor.fetchone()
                return dict(user) if user else None

        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None

    def list_family_members(self, include_inactive: bool = False) -> List[Dict]:
        """List all family members."""
        if not self.conn:
            self._connect()

        if not self.conn:
            return []

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if include_inactive:
                    cursor.execute("""
                        SELECT id, display_name, email, role, avatar_url,
                               created_at, last_login, is_active
                        FROM users
                        ORDER BY created_at DESC
                    """)
                else:
                    cursor.execute("""
                        SELECT id, display_name, email, role, avatar_url,
                               created_at, last_login, is_active
                        FROM users
                        WHERE is_active = TRUE
                        ORDER BY created_at DESC
                    """)

                users = cursor.fetchall()
                return [dict(user) for user in users]

        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []

    def update_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> Dict[str, any]:
        """Update user password."""
        # First authenticate with old password
        auth_result = self.authenticate(user_id, old_password)
        if not auth_result["success"]:
            return {"success": False, "error": "Current password is incorrect"}

        # Hash new password
        new_hash = self.hash_password(new_password)

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                    (new_hash, user_id),
                )

                logger.info(f"✅ Password updated for user {user_id}")
                return {"success": True}

        except Exception as e:
            logger.error(f"Failed to update password: {e}")
            return {"success": False, "error": "Failed to update password"}

    def deactivate_user(self, user_id: str, admin_user_id: str) -> Dict[str, any]:
        """Deactivate a user account (admin only)."""
        # Check if admin
        admin = self.get_user(admin_user_id)
        if not admin or admin["role"] != "admin":
            return {"success": False, "error": "Admin privileges required"}

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET is_active = FALSE, updated_at = NOW() WHERE id = %s",
                    (user_id,),
                )

                logger.info(f"✅ User {user_id} deactivated by admin {admin_user_id}")
                return {"success": True}

        except Exception as e:
            logger.error(f"Failed to deactivate user: {e}")
            return {"success": False, "error": "Failed to deactivate user"}


# Initialize default family members if database is empty
def initialize_default_family(auth_manager: FamilyAuthManager):
    """Initialize default family members for first-time setup."""
    users = auth_manager.list_family_members(include_inactive=True)

    # If users exist and have passwords, skip initialization
    if users:
        has_password = any(
            auth_manager.conn
            and auth_manager.conn.cursor().execute(
                "SELECT password_hash FROM users WHERE id = %s", (user["id"],)
            )
            for user in users
        )
        if has_password:
            logger.info("Family members already initialized with passwords")
            return

    # Create default admin if no users exist
    if not users:
        logger.info("🔧 Initializing default admin account...")
        result = auth_manager.register_family_member(
            user_id="admin",
            password="admin123",  # MUST BE CHANGED
            display_name="Administrator",
            email="admin@demestihas.local",
            role="admin",
            avatar_url="👤",
        )

        if result["success"]:
            logger.warning(
                "⚠️  DEFAULT ADMIN CREATED - Password: admin123 - CHANGE THIS IMMEDIATELY!"
            )
        else:
            logger.error(f"Failed to create default admin: {result.get('error')}")


# Global instance (initialized in main.py)
family_auth_manager: Optional[FamilyAuthManager] = None


def get_family_auth_manager() -> Optional[FamilyAuthManager]:
    """Get the global family auth manager instance."""
    global family_auth_manager
    if family_auth_manager is None:
        family_auth_manager = FamilyAuthManager()
        initialize_default_family(family_auth_manager)
    return family_auth_manager
