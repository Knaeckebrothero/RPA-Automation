"""
This module holds security-related functions for the application.
"""
import os
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
import streamlit as st
from streamlit import runtime
from streamlit.runtime.scriptrunner import get_script_run_ctx


# Set up logging
log = logging.getLogger(__name__)


def get_client_ip():
    """
    Get the client's remote IP address using Streamlit's runtime API.
    Returns the IP or 'unknown' if not found.
    """
    try:
        # Get the current script run context
        ctx = get_script_run_ctx()
        if ctx is None:
            log.warning("No script run context available")
            return 'unknown'

        # Get the client info from the runtime
        session_info = runtime.get_instance().get_client(ctx.session_id)
        if session_info is None:
            log.warning("No session info available")
            return 'unknown'

        # Return the remote IP address
        return session_info.request.remote_ip
    except Exception as e:
        log.error(f"Error getting client IP: {e}")
        return 'unknown'


def check_login_attempts(ip_address, db, max_attempts=5, window_minutes=15):
    """
    Check if an IP address has exceeded the maximum number of failed login attempts.

    :param ip_address: The client IP address
    :param db: Database connection
    :param max_attempts: Maximum number of failed attempts allowed
    :param window_minutes: Time window in minutes to consider for failed attempts
    :return: True if too many attempts, False otherwise
    """
    if ip_address == 'unknown':
        # Can't reliably track unknown IPs, so don't block
        return False

    try:
        # Create login_attempts table if it doesn't exist
        db.query("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            successful BOOLEAN NOT NULL DEFAULT 0
        )
        """)

        # Calculate the time window
        window_start = (datetime.now() - timedelta(minutes=window_minutes)).isoformat()

        # Count failed attempts within the time window
        result = db.query("""
        SELECT COUNT(*) FROM login_attempts 
        WHERE ip_address = ? 
        AND attempt_time > ? 
        AND successful = 0
        """, (ip_address, window_start))

        failed_attempts = result[0][0] if result else 0

        # Log if approaching limit
        if failed_attempts >= max_attempts - 1:
            log.warning(f"IP {ip_address} has {failed_attempts} failed login attempts")

        return failed_attempts >= max_attempts

    except Exception as e:
        log.error(f"Error checking login attempts: {e}")
        # On error, don't block (fail open for usability)
        return False


def record_failed_attempt(ip_address, username, db):
    """
    Record a failed login attempt.

    :param ip_address: The client IP address
    :param username: The username that was attempted
    :param db: Database connection
    """
    if ip_address == 'unknown':
        return

    try:
        db.insert("""
        INSERT INTO login_attempts (ip_address, successful, username_attempted)
        VALUES (?, 0, ?)
        """, (ip_address, username))

        log.info(f"Recorded failed login attempt for username: {username} from IP: {ip_address}")

    except Exception as e:
        log.error(f"Error recording failed login attempt: {e}")


def record_successful_login(ip_address, user_id, db):
    """
    Record a successful login and clean up old failed attempts.

    :param ip_address: The client IP address
    :param user_id: The user ID that successfully logged in
    :param db: Database connection
    """
    if ip_address == 'unknown':
        return

    try:
        # Record the successful login
        db.insert("""
        INSERT INTO login_attempts (ip_address, successful)
        VALUES (?, 1)
        """, (ip_address,))

        # Optionally, clean up old records to keep the table size manageable
        # Keep only the last 30 days of data
        cleanup_before = (datetime.now() - timedelta(days=30)).isoformat()
        db.query("""
        DELETE FROM login_attempts 
        WHERE attempt_time < ?
        """, (cleanup_before,))

        log.info(f"Recorded successful login for user {user_id} from IP: {ip_address}")

    except Exception as e:
        log.error(f"Error recording successful login: {e}")


# TODO: Move this stuff to a separate user class!
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


