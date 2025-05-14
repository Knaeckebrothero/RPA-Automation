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

# Custom imports
from cls import Database


# Set up logging
log = logging.getLogger(__name__)


def get_client_ip() -> str:
    """
    Get the client's remote IP address using Streamlit's runtime API.

    :return: Client IP address or 'unknown' if not found
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


def check_login_attempts(ip_address, database: Database = None, max_attempts=5, window_minutes=15):
    """
    Check if an IP address has exceeded the maximum number of failed login attempts.

    :param ip_address: The client IP address
    :param database: Database connection
    :param max_attempts: Maximum number of failed attempts allowed
    :param window_minutes: Time window in minutes to consider for failed attempts
    :return: True if too many attempts, False otherwise
    """
    if ip_address == 'unknown':
        return False

    # Check if the database instance is provided, otherwise fetch the instance
    if database:
        db = database
    else:
        db = Database().get_instance()

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
        # TODO: On error, don't block (fail open for usability)
        return False


def record_failed_attempt(ip_address, username, database: Database = None):
    """
    Record a failed login attempt.

    :param ip_address: The client IP address
    :param username: The username that was attempted
    :param database: Database connection
    """
    if ip_address == 'unknown':
        return

    # Check if the database instance is provided, otherwise fetch the instance
    if database:
        db = database
    else:
        db = Database().get_instance()

    try:
        # Record the failed login attempt
        db.insert("""
        INSERT INTO login_attempts (ip_address, successful, username_attempted)
        VALUES (?, 0, ?)
        """, (ip_address, username))
        log.info(f"Recorded failed login attempt for username: {username} from IP: {ip_address}")
    except Exception as e:
        log.error(f"Error recording failed login attempt: {e}")


def record_successful_login(ip_address, user_id, database: Database = None):
    """
    Record a successful login and clean up old failed attempts.

    :param ip_address: The client IP address
    :param user_id: The user ID that successfully logged in
    :param database: Database connection
    """
    if ip_address == 'unknown':
        return

    # Check if the database instance is provided, otherwise fetch the instance
    if database:
        db = database
    else:
        db = Database().get_instance()

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


def hash_password(password, salt=None) -> tuple[str, str]:
    """
    Hash a password using SHA-256 with a salt.

    :param password: Plain text password
    :param salt: Optional salt, will be generated if not provided
    :return: Tuple of (hash, salt)
    """
    if salt is None:
        # Generate a random salt if not provided
        salt = os.urandom(32)  # 32 bytes = 256 bits
    elif isinstance(salt, str):
        # Convert hex string to bytes
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

    # Compare the new hash with the stored hash and return the result
    return new_hash == stored_hash


def create_session(user_id, database: Database = None, session_duration_hours=1):
    """
    Create a new session for the user.

    :param user_id: User ID
    :param database: Database connection
    :param session_duration_hours: Session duration in hours
    :return: Session key
    """
    session_key = generate_session_key()
    expires_at = datetime.now() + timedelta(hours=session_duration_hours)

    # Check if the database instance is provided, otherwise fetch the instance
    if database:
        db = database
    else:
        db = Database().get_instance()

    try:
        # Add the session key to the database
        db.insert("""
            INSERT INTO session_key (session_key, user_id, expires_at)
            VALUES (?, ?, ?)
        """, (session_key, user_id, expires_at.isoformat()))

        # TODO: Do we still need last_login?
        # Update user's last login time
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


def validate_session(session_key, database: Database = None):
    """
    Validate a session key.

    :param session_key: Session key to validate
    :param database: Database connection
    :return: User ID if session is valid, None otherwise
    """
    if not session_key:
        return None

    # Check if the database instance is provided, otherwise fetch the instance
    if database:
        db = database
    else:
        db = Database().get_instance()

    try:
        result = db.query("""
            SELECT user_id, expires_at
            FROM session_key
            WHERE session_key = ?
        """, (session_key,))

        # Check if the session key exists
        if not result:
            log.warning(f"Session key not found: {session_key[:8]}...")
            return None

        # Check if the session key is expired
        user_id, expires_at = result[0]
        expires_at = datetime.fromisoformat(expires_at)

        # If the session key is expired, delete it from the database
        if expires_at < datetime.now():
            log.warning(f"Session expired for user {user_id}")
            db.query("DELETE FROM session_key WHERE session_key = ?", (session_key,))
            return None

        return user_id
    except Exception as e:
        log.error(f"Error validating session: {e}")
        return None


def get_user_role(user_id, database: Database = None):
    """
    Get the role of a user.

    :param user_id: User ID
    :param database: Database connection
    :return: User role or None if user not found
    """
    if database:
        db = database
    else:
        db = Database().get_instance()

    try:
        # Search for the user in the database
        result = db.query("SELECT role FROM user WHERE id = ?", (user_id,))
        if result:
            # Return the user's role if one was found
            return result[0][0]

        return None
    except Exception as e:
        log.error(f"Error getting user role: {e}")
        return None


def logout(session_key, database: Database = None):
    """
    Log out a user by deleting their session.

    :param session_key: Session key
    :param database: Database connection
    :return: True if successful, False otherwise
    """
    if database:
        db = database
    else:
        db = Database().get_instance()

    try:
        # Delete the session key from the database
        db.query("DELETE FROM session_key WHERE session_key = ?", (session_key,))
        log.info(f"User logged out: {session_key[:8]}...")
        return True
    except Exception as e:
        log.error(f"Error logging out: {e}")
        return False


def require_auth(database: Database = None, required_role=None) -> bool:
    """
    Check if current user is authenticated and has required role.

    :param database: Database connection
    :param required_role: Role required to access the page (optional)
    :return: True if authenticated with required role, False otherwise
    """
    if 'session_key' not in st.session_state or not st.session_state['session_key']:
        return False

    # Check if the database instance is provided, otherwise fetch the instance
    if database:
        db = database
    else:
        db = Database().get_instance()

    # Validate the session key
    user_id = validate_session(st.session_state['session_key'], db)
    if not user_id:
        return False

    # Check if the user has the required role
    if required_role:
        user_role = get_user_role(user_id, db)
        if user_role != required_role:
            log.warning(f"User {user_id} with role {user_role} tried to access a {required_role} page he doesn't have access to.")
            return False

    return True
