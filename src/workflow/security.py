"""
This module holds security-related functions for the application.
"""
import os
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
import streamlit as st


# Set up logging
log = logging.getLogger(__name__)


def generate_session_key(length=32):
    """
    Generate a random session key.

    :param length: Length of the session key in bytes
    :return: Hexadecimal session key string
    """
    return secrets.token_hex(length)


def hash_password(password, salt=None):
    """
    Hash a password using SHA-256 with a salt.

    :param password: Plain text password
    :param salt: Optional salt, will be generated if not provided
    :return: Tuple of (hash, salt)
    """
    if salt is None:
        salt = os.urandom(32)  # 32 bytes = 256 bits
    elif isinstance(salt, str):
        salt = bytes.fromhex(salt)

    # Convert password to bytes if it's a string
    if isinstance(password, str):
        password = password.encode('utf-8')

    # Hash the password with the salt
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password,
        salt,
        100000  # Number of iterations
    )

    return password_hash.hex(), salt.hex()


def verify_password(stored_hash, stored_salt, provided_password):
    """
    Verify if a provided password matches the stored hash.

    :param stored_hash: Stored password hash
    :param stored_salt: Stored salt
    :param provided_password: Password to verify
    :return: True if password matches, False otherwise
    """
    # Convert hex string to bytes
    salt = bytes.fromhex(stored_salt)

    # Hash the provided password with the stored salt
    new_hash, _ = hash_password(provided_password, salt)

    return new_hash == stored_hash


def create_session(user_id, db, session_duration_hours=1):
    """
    Create a new session for the user.

    :param user_id: User ID
    :param db: Database connection
    :param session_duration_hours: Session duration in hours
    :return: Session key
    """
    session_key = generate_session_key()
    expires_at = datetime.now() + timedelta(hours=session_duration_hours)

    try:
        db.insert("""
            INSERT INTO session_key (session_key, user_id, expires_at)
            VALUES (?, ?, ?)
        """, (session_key, user_id, expires_at.isoformat()))

        # Update user's last login time
        # TODO: Do we still need last_login?
        #db.query("""
        #    UPDATE user
        #    SET last_login = CURRENT_TIMESTAMP
        #    WHERE id = ?
        #""", (user_id,))

        log.info(f"Created session for user {user_id}")
        return session_key
    except Exception as e:
        log.error(f"Error creating session: {e}")
        return None


def validate_session(session_key, db):
    """
    Validate a session key.

    :param session_key: Session key to validate
    :param db: Database connection
    :return: User ID if session is valid, None otherwise
    """
    if not session_key:
        return None

    try:
        result = db.query("""
            SELECT user_id, expires_at
            FROM session_key
            WHERE session_key = ?
        """, (session_key,))

        if not result:
            log.warning(f"Session key not found: {session_key[:8]}...")
            return None

        user_id, expires_at = result[0]
        expires_at = datetime.fromisoformat(expires_at)

        if expires_at < datetime.now():
            log.warning(f"Session expired for user {user_id}")
            # Delete expired session
            db.query("DELETE FROM session_key WHERE session_key = ?", (session_key,))
            return None

        return user_id
    except Exception as e:
        log.error(f"Error validating session: {e}")
        return None


def get_user_role(user_id, db):
    """
    Get the role of a user.

    :param user_id: User ID
    :param db: Database connection
    :return: User role or None if user not found
    """
    try:
        result = db.query("SELECT role FROM user WHERE id = ?", (user_id,))
        if result:
            return result[0][0]
        return None
    except Exception as e:
        log.error(f"Error getting user role: {e}")
        return None


def logout(session_key, db):
    """
    Log out a user by deleting their session.

    :param session_key: Session key
    :param db: Database connection
    :return: True if successful, False otherwise
    """
    try:
        db.query("DELETE FROM session_key WHERE session_key = ?", (session_key,))
        log.info(f"User logged out: {session_key[:8]}...")
        return True
    except Exception as e:
        log.error(f"Error logging out: {e}")
        return False


def require_auth(db, required_role=None):
    """
    Check if current user is authenticated and has required role.

    :param db: Database connection
    :param required_role: Role required to access the page (optional)
    :return: True if authenticated with required role, False otherwise
    """
    if 'session_key' not in st.session_state or not st.session_state['session_key']:
        return False

    user_id = validate_session(st.session_state['session_key'], db)

    if not user_id:
        return False

    if required_role:
        user_role = get_user_role(user_id, db)
        if user_role != required_role:
            log.warning(f"User {user_id} with role {user_role} tried to access a {required_role} page")
            return False

    return True


def init_session_state():
    """
    Initialize the session state with authentication variables if they don't exist.
    """
    if 'session_key' not in st.session_state:
        st.session_state['session_key'] = None

    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None

    if 'user_role' not in st.session_state:
        st.session_state['user_role'] = None
