"""
This module holds security-related functions for the application.
"""
import os
import hashlib
import secrets
import logging
import string
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
    Retrieve the IP address of the client making a request.

    This function retrieves the client IP address by accessing the current
    script runtime context and fetching client information from its session.
    If the script run context or session information is unavailable, or if
    any error occurs during the process, a default value of 'unknown' is
    returned. Errors encountered during the retrieval process are logged
    for debugging purposes.

    :return: The client IP address or 'unknown' if it cannot be retrieved.
    :rtype: str
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
    Checks if the specified IP address has exceeded the allowed number of login attempts
    within a defined time window. This is used to prevent brute force login attempts by
    monitoring failed login activity. If the login attempts exceed the threshold, the
    function returns True, otherwise False.

    :param ip_address: The IP address to check for failed login attempts.
    :type ip_address: str
    :param database: Optional database instance. If not provided, a default instance is fetched.
    :type database: Database or None
    :param max_attempts: Maximum allowed failed login attempts before blocking the IP.
    :type max_attempts: int
    :param window_minutes: Time window in minutes to consider failed login attempts.
    :type window_minutes: int
    :return: A boolean indicating whether the IP address has exceeded the login attempt limit.
    :rtype: bool
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
    Records a failed login attempt in the database with the given IP address and username.

    This function logs a failed login attempt by inserting a record into the
    `login_attempts` table of a database. If the `ip_address` is 'unknown', it
    does not proceed. The function can optionally use a provided database
    instance; otherwise, it fetches a default instance of the database.

    :param ip_address: The IP address from where the login attempt was made.
    :type ip_address: str
    :param username: The username provided during the failed login attempt.
    :type username: str
    :param database: An optional database instance to record the login attempt.
                     If not provided, a default database instance is retrieved.
    :type database: Database, optional
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
    Records a successful login attempt in the database. If necessary, it also performs
    cleanup of older login attempt records to maintain the table size within a manageable
    limit. Older records beyond a cutoff period (30 days) are deleted. This function logs
    a message indicating the successful addition of a new record or captures any errors
    encountered during the process.

    :param ip_address: The IP address of the user who successfully logged in.
    :type ip_address: str
    :param user_id: The unique identifier of the user who successfully logged in.
    :type user_id: str
    :param database: An optional instance of the Database class to use for operations.
        If not provided, a new instance is fetched or initialized.
    :type database: Database, optional
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
    Generate a secure session key.

    This function generates a secure random session key
    using the `secrets.token_hex` method. The length of the
    generated key can be customized by specifying a value
    for the `length` parameter (default is 32).

    :param length: The length of the generated session key.
    :type length: int
    :return: A randomly generated hexadecimal session key.
    :rtype: str
    """
    return secrets.token_hex(length)


def hash_password(password, salt=None) -> tuple[str, str]:
    """
    Hashes a given password using PBKDF2-HMAC-SHA256 along with a salt. If no salt
    is provided, generates a new random salt. The hashed password and the salt are
    returned as hexadecimal strings.

    Defaults to 100,000 iterations for the hashing process.

    :param password: The password to be hashed. Accepts a string or bytes.
    :type password: str or bytes
    :param salt: A cryptographic salt in hexadecimal string format or bytes.
                 If not provided, a 256-bit random salt will be generated.
    :type salt: str or bytes or None
    :return: A tuple containing the hashed password as a hexadecimal string and the
             salt as a hexadecimal string.
    :rtype: tuple[str, str]
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
    Verifies whether the provided password generates the same hash as the stored hash
    by using the stored salt.

    :param stored_hash: The precomputed hash of the password to be verified.
    :type stored_hash: str
    :param stored_salt: The salt value used when generating the stored hash, in hex
        string format.
    :type stored_salt: str
    :param provided_password: The password provided by the user to be checked.
    :type provided_password: str
    :return: A boolean value indicating whether the provided password matches the
        stored hash after hashing with the stored salt.
    :rtype: bool
    """
    # Convert hex string to bytes
    salt = bytes.fromhex(stored_salt)

    # Hash the provided password with the stored salt
    new_hash, _ = hash_password(provided_password, salt)

    # Compare the new hash with the stored hash and return the result
    return new_hash == stored_hash


def create_session(user_id, database: Database = None, session_duration_hours=1):
    """
    Generates a new session for a given user, stores it in the database, and returns the session key.

    :param user_id: The ID of the user for whom the session is to be created.
    :type user_id: int
    :param database: Optional database instance to use for interacting with the session table. If not provided,
        the function will create or fetch a singleton instance.
    :type database: Database, optional
    :param session_duration_hours: The number of hours for which the session will be valid. Defaults to 1 hour.
    :type session_duration_hours: int
    :return: The generated session key if the session is created successfully, otherwise None.
    :rtype: str or None
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
    Validates a provided session key against the database to determine its
    validity. Checks include verifying the existence of the session key and
    whether it has expired. If the session key is expired, it will be removed
    from the database.

    :param session_key: The session key to validate.
    :type session_key: str
    :param database: Optional database instance. If not provided, a default
                     instance will be used.
    :type database: Database, optional
    :return: The user ID associated with the session key if valid, otherwise None.
    :rtype: Union[int, None]
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
    Retrieves the role associated with a specific user ID from a database. If the
    database is not provided, a default database instance will be used. The method
    queries the database for the role associated with the user ID and returns it
    if found. Returns None if the user ID is not found or if an error occurs.

    :param user_id: The unique identifier of the user whose role is being queried.
    :type user_id: int
    :param database: An optional database instance to use for querying. If not
        specified, a default database instance will be used.
    :type database: Database, optional
    :return: The role associated with the user ID if found, otherwise None.
    :rtype: str or None
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
    Logs out a user by removing the specified session key from the database.

    This function attempts to delete the provided session key from the
    database to effectively log out the user. If a custom database instance
    is provided, it will use that; otherwise, it will use the default
    singleton database instance.

    :param session_key: The session key of the user to be logged out.
    :type session_key: str
    :param database: Optional database instance to be used for logging out.
    :type database: Database, optional
    :return: True if the session key is successfully removed, False otherwise.
    :rtype: bool
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
    Checks if a user is authenticated and authorized based on the session key,
    database validation, and required role. If a valid session key is found in
    the session state and the user meets the required role criteria (if specified),
    authentication is granted. Otherwise, it is denied.

    Provides functionality to validate the user's session using the provided
    or default database instance, and queries the associated user role when
    necessary to match the required role.

    :param database: The `Database` instance to be used for session validation
        and role querying.
    :type database: Database, optional
    :param required_role: The role required for authorization. If specified, the
        function will ensure that the user's role matches the given role.
    :type required_role: Any, optional
    :return: A boolean indicating if the user is authenticated and authorized.
    :rtype: bool
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


def generate_secure_password(length: int = 12) -> str:
    """
    Generates a secure and random password of a given length. The generated password
    will include at least one lowercase letter, one uppercase letter, one digit,
    and one special character. The remaining characters will be randomly selected
    from all available characters, and the order will be shuffled to ensure
    unpredictability.

    :param length: The total length of the password to be generated. Must be greater
                   than or equal to 4 to ensure the inclusion of one character from
                   each required set (lowercase, uppercase, digit, special).
    :type length: int
    :return: A randomly generated password string that fulfills all necessary
             security requirements.
    :rtype: str
    """
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*"

    # Ensure password has at least one character from each set
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]

    # Fill the rest of the password length with random characters from all sets
    all_characters = lowercase + uppercase + digits + special
    for _ in range(length - 4):
        password.append(secrets.choice(all_characters))

    # Shuffle the password list to avoid predictable patterns
    secrets.SystemRandom().shuffle(password)

    return ''.join(password)
