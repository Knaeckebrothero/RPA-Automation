"""
Initialization script for the application database.

This script initializes the SQLite database by:
1. Creating the database file if it doesn't exist
2. Creating or updating the tables structure
3. Inserting example data if the database is empty
4. Creating default users if they don't exist

Usage:
    python db_init.py [--db-path PATH] [--schema-path PATH] [--data-path PATH]
"""
import json
import argparse
import logging
import os
import sqlite3
import sys
import hashlib


def setup_logging():
    """
    Set up logging configuration.

    :return: Logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def parse_args():
    """
    Parse command line arguments.

    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Initialize the SQLite database.')
    parser.add_argument(
        '--db-path',
        default='./.filesystem/database.db',
        help='Path to the SQLite database file (default: ./.filesystem/database.db)'
    )
    parser.add_argument(
        '--schema-path',
        default='./src/schema.sql',
        help='Path to the schema SQL file (default: ./src/schema.sql)'
    )
    parser.add_argument(
        '--json-path',
        default='./examples/examples.json',
        help='Path to the JSON file with example data (default: ./examples/examples.json)'
    )
    parser.add_argument(
        '--force-reset',
        action='store_true',
        help='Force reset the database (warning: this will delete all existing data)'
    )
    return parser.parse_args()


def ensure_directory_exists(path):
    """
    Ensure the directory for the given file path exists.

    :param path: File path
    :return: True if directory was created, False if it already exists
    """
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        return True
    return False


def execute_sql_file(conn, filepath, logger):
    """
    Execute SQL commands from a file.

    :param conn: SQLite connection
    :param filepath: Path to the SQL file
    :param logger: Logger instance
    :return: True if successful, False otherwise
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as sql_file:
            sql_script = sql_file.read()
            conn.executescript(sql_script)
            conn.commit()
            logger.info(f"Successfully executed SQL from {filepath}")
            return True
    except sqlite3.Error as e:
        logger.error(f"SQLite error while executing {filepath}: {e}")
        conn.rollback()
    except IOError as e:
        logger.error(f"I/O error while reading {filepath}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while executing {filepath}: {e}")
        conn.rollback()
    return False


# This function is a duplicate of the one in workflow.security, make sure to keep them in sync!
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


def insert_default_users(conn, logger):
    """
    Insert default admin and auditor users if they don't exist.

    :param conn: SQLite connection
    :param logger: Logger instance
    :return: True if successful, False otherwise
    """
    try:
        cursor = conn.cursor()

        # Check if users already exist
        cursor.execute("SELECT COUNT(*) FROM user")
        count = cursor.fetchone()[0]

        if count == 0:
            logger.info("Creating default users...")

            # Create admin user
            admin_pass, admin_salt = hash_password("admin123")
            cursor.execute("""
                INSERT INTO user (username_email, password_hash, password_salt, role)
                VALUES (?, ?, ?, ?)
            """, ("admin@example.com", admin_pass, admin_salt, "admin"))

            # Create auditor user
            auditor_pass, auditor_salt = hash_password("auditor123")
            cursor.execute("""
                INSERT INTO user (username_email, password_hash, password_salt, role)
                VALUES (?, ?, ?, ?)
            """, ("auditor@example.com", auditor_pass, auditor_salt, "auditor"))

            # Create inspector user
            auditor_pass, auditor_salt = hash_password("inspector123")
            cursor.execute("""
                INSERT INTO user (username_email, password_hash, password_salt, role)
                VALUES (?, ?, ?, ?)
            """, ("inspector@example.com", auditor_pass, auditor_salt, "inspector"))

            conn.commit()
            logger.info("Default users created: admin, auditor and inspector")
            return True
        else:
            logger.info(f"Users already exist ({count} users found), skipping default user creation")
            return True

    except Exception as e:
        logger.error(f"Error creating default users: {e}")
        if conn:
            conn.rollback()
        return False


def insert_json_data(conn, json_filepath, logger):
    """
    Insert data from a JSON file into the database.
    The JSON file should contain a list of client objects with properties that map to database columns.

    :param conn: SQLite connection
    :param json_filepath: Path to the JSON file
    :param logger: Logger instance
    :return: True if successful, False otherwise
    """
    try:
        with open(json_filepath, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)

        # Check if the data is a list
        if not isinstance(data, list):
            logger.error(f"JSON data is not a list. Found type: {type(data)}")
            return False

        cursor = conn.cursor()
        records_inserted = 0

        # Begin transaction for faster inserts
        conn.execute('BEGIN TRANSACTION')

        for item in data:
            try:
                # Handle number formatting (replace commas with dots for decimal numbers)
                # N18 is the ratio field
                ratio_str = str(item.get('N18', '0'))
                ratio = ratio_str.replace(',', '.')
                try:
                    ratio = float(ratio)
                except ValueError:
                    ratio = 0.0
                    logger.warning(f"Could not convert ratio value '{ratio_str}' to float for record {item.get('ID', 'unknown')}")

                # Extract city and zip from combined field if present
                plz_ort = item.get('PLZ/Ort', '')
                if isinstance(plz_ort, str) and ' ' in plz_ort:
                    # Extract the first part as zip code and the rest as city
                    parts = plz_ort.split(' ', 1)
                    city = parts[1] if len(parts) > 1 else ''
                else:
                    city = plz_ort

                # Safe conversion for numeric fields
                def safe_int(value, default=0):
                    try:
                        # Remove thousands separators (dots) and convert to int
                        if isinstance(value, str):
                            value = value.replace('.', '')
                        return int(value)
                    except (ValueError, TypeError):
                        return default

                # Insert data into the client table
                cursor.execute("""
                INSERT INTO client (
                    institute, bafin_id, address, city, contact_person,
                    phone, fax, email, 
                    p033, p034, p035, p036,
                    ab2s1n01, ab2s1n02, ab2s1n03, ab2s1n04, ab2s1n05,
                    ab2s1n06, ab2s1n07, ab2s1n08, ab2s1n09, ab2s1n10,
                    ab2s1n11, ratio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get('Institut', ''),
                    safe_int(item.get('ID', 0)),
                    item.get('Adresse', ''),
                    city,
                    item.get('Ansprechpartner', ''),
                    item.get('Telefon', ''),
                    item.get('Fax', ''),
                    item.get('Mail', ''),
                    safe_int(item.get('N1', 0)),
                    safe_int(item.get('N2', 0)),
                    safe_int(item.get('N3', 0)),
                    safe_int(item.get('N4', 0)),
                    safe_int(item.get('N6', 0)),
                    safe_int(item.get('N7', 0)),
                    safe_int(item.get('N8', 0)),
                    safe_int(item.get('N9', 0)),
                    safe_int(item.get('N10', 0)),
                    safe_int(item.get('N11', 0)),
                    safe_int(item.get('N12', 0)),
                    safe_int(item.get('N13', 0)),
                    safe_int(item.get('N14', 0)),
                    safe_int(item.get('N15', 0)),
                    safe_int(item.get('N16', 0)),
                    ratio
                ))
                records_inserted += 1

                # Log progress for large datasets
                if records_inserted % 50 == 0:
                    logger.info(f"Inserted {records_inserted} records so far...")

            except (sqlite3.Error, ValueError) as e:
                logger.warning(f"Error inserting record {item.get('ID', 'unknown')}: {e}")

        # Commit the transaction
        conn.commit()
        logger.info(f"Successfully inserted {records_inserted} records from JSON")
        return records_inserted > 0

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON file {json_filepath}: {e}")
        return False
    except IOError as e:
        logger.error(f"I/O error while reading JSON file {json_filepath}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while inserting JSON data: {e}")
        conn.rollback()
        return False


def initialize_database(db_path, schema_path, json_path, force_reset, logger):
    """
    Initialize the database with schema and example data.

    :param db_path: Path to the SQLite database file
    :param schema_path: Path to the SQL schema file
    :param json_path: Path to the JSON file with example data
    :param force_reset: If True, delete existing database and recreate it
    :param logger: Logger instance
    :return: True if successful, False otherwise
    """
    if ensure_directory_exists(db_path):
        logger.info(f"Created directory for database at {os.path.dirname(db_path)}")

    # If force reset and file exists, delete it
    if force_reset and os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.warning(f"Forced reset: Deleted existing database at {db_path}")
        except OSError as e:
            logger.error(f"Failed to delete existing database: {e}")
            return False

    # Connect to the database
    try:
        conn = sqlite3.connect(db_path)
        logger.info(f"Connected to database at {db_path}")
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        return False

    try:
        # Execute schema SQL
        if not execute_sql_file(conn, schema_path, logger):
            logger.error("Failed to initialize database schema")
            conn.close()
            return False

        # Check if client table is empty
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM client")
        count = cursor.fetchone()[0]

        # Insert data from JSON file
        if count == 0:
            if not insert_json_data(conn, json_path, logger):
                logger.error("Failed to insert example data from JSON")
                conn.close()
                return False
            logger.info("Inserted example data from JSON")
        else:
            logger.info(f"Skipped data insertion because client table already has {count} records")

        # Insert default users if they don't exist
        if not insert_default_users(conn, logger):
            logger.error("Failed to insert default users")
            conn.close()
            return False

        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"Database has tables: {[table[0] for table in tables]}")

        conn.close()
        logger.info("Database initialization completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        conn.close()
        return False


def main():
    logger = setup_logging()
    args = parse_args()

    logger.info("Starting database initialization")

    # Check if the database path is valid
    if not os.path.exists(args.schema_path):
        logger.error(f"Schema file not found: {args.schema_path}")
        return 1

    # Check if the JSON data path is valid
    if not os.path.exists(args.json_path):
        logger.error(f"JSON data file not found: {args.json_path}")
        return 1

    # Initialize the database
    success = initialize_database(
        args.db_path,
        args.schema_path,
        args.json_path,
        args.force_reset,
        logger
    )

    if success:
        logger.info("Database initialized successfully!")
        return 0
    else:
        logger.error("Database initialization failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
