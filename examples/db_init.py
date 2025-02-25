"""
Initialization script for the application database.

This script initializes the SQLite database by:
1. Creating the database file if it doesn't exist
2. Creating or updating the tables structure
3. Inserting example data if the database is empty

Usage:
    python db_init.py [--db-path PATH] [--schema-path PATH] [--data-path PATH]
"""
import argparse
import logging
import os
import sqlite3
import sys


def setup_logging():
    """
    Set up logging configuration.
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
    """
    parser = argparse.ArgumentParser(description='Initialize the SQLite database.')
    parser.add_argument(
        '--db-path',
        default='./.filesystem/database.db',
        help='Path to the SQLite database file (default: ./.filesystem/database.db)'
    )
    parser.add_argument(
        '--schema-path',
        default='./src/cfg/schema.sql',
        help='Path to the schema SQL file (default: ./src/cfg/schema.sql)'
    )
    parser.add_argument(
        '--data-path',
        default='./examples/insert_example_data.sql',
        help='Path to the data insertion SQL file (default: ./examples/insert_example_data.sql)'
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
    """
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        return True
    return False


def execute_sql_file(conn, filepath, logger):
    """
    Execute SQL commands from a file.
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


def initialize_database(db_path, schema_path, data_path, force_reset, logger):
    """
    Initialize the database with schema and example data.
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

        if count == 0:
            # Execute data insertion SQL
            if not execute_sql_file(conn, data_path, logger):
                logger.error("Failed to insert example data")
                conn.close()
                return False
            logger.info("Inserted example data")
        else:
            logger.info(f"Skipped data insertion because client table already has {count} records")

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

    if not os.path.exists(args.schema_path):
        logger.error(f"Schema file not found: {args.schema_path}")
        return 1

    if not os.path.exists(args.data_path):
        logger.error(f"Data file not found: {args.data_path}")
        return 1

    success = initialize_database(
        args.db_path,
        args.schema_path,
        args.data_path,
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