"""
This module holds the database class.
"""
import os
import sqlite3
import logging
import pandas as pd

# Custom imports
from cls.singleton import Singleton


# Set up logging
log  = logging.getLogger(__name__)


class Database(Singleton):
    """
    The Database class represents the database and acts as a middleman.
    It implements the Singleton pattern to ensure only one connection is active.
    """
    def __init__(self, db_path: str = "./.filesystem/database.db"):
        """
        Initialize the database connection.

        :param db_path: Path to the SQLite database file. If None, uses the default path.
        """
        log.debug("Initializing database connection...")
        self._path = db_path
        self._conn = None
        self.cursor = None
        self.connect()
        log.info("Database initialized.")

    def __del__(self):
        """
        Clean up resources when the object is garbage collected.
        """
        self.close()
        log.debug("Database object destroyed.")

    def connect(self):
        """
        Attempt to connect to the database.

        :raises sqlite3.Error: If connection to the database fails.
        """
        try:
            # Ensure directory exists
            directory = os.path.dirname(self._path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                log.debug(f"Created directory for database: {directory}")

            # Connect to the database
            self._conn = sqlite3.connect(self._path, check_same_thread=False)
            self.cursor = self._conn.cursor()
            log.debug(f"Connected to database at: {self._path}")

            # Verify that required tables exist
            self._verify_tables()
        except sqlite3.Error as e:
            log.error(f"Error connecting to database: {e}")
            raise

    def close(self):
        """
        Attempt to close the database connection.
        """
        if self._conn:
            self._conn.close()
            self._conn = None
            self.cursor = None
            log.debug("Database connection closed.")
        else:
            log.warning("No database connection to close.")

    def _verify_tables(self, required_tables: list[str] = None):
        """
        Verify that the required tables exist correctly in the database.

        :param required_tables: A list of table names that should exist in the database.
        :raises RuntimeError: If the required tables don't exist.
        """
        if required_tables is None:
            required_tables = ['client', 'audit_case', 'user', 'session_key', 'user_client_access']

        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in self.cursor.fetchall()]

            missing_tables = [table for table in required_tables if table not in existing_tables]
            if missing_tables:
                log.error(f"Required tables are missing: {missing_tables}")
                log.error("Please run the database initialization script first!")
                raise RuntimeError(f"Required tables are missing: {missing_tables}")
            else:
                log.debug(f"All required tables exist: {required_tables}")

        except sqlite3.Error as e:
            log.error(f"Error verifying tables: {e}")
            raise

    def query(self, query: str, params=None) -> list[tuple] | list | None:
        """
        Execute a query on the database.
        This method doesn't commit changes to the database.

        :param query: The SQL query to execute.
        :param params: Parameters to use with the query (optional).
        :return: The result of the query as a list of tuples. Each tuple represents a record, with each element
         representing a column value. If only one column was queried, the tuples will collapse into a single value
          and the method will return a list of values. If the query returns no records, an empty list is returned.
        :raises sqlite3.Error: If the query execution fails.
        """
        try:
            if params:
                log.debug(f"Executing query: {query} with params: {params}")
                self.cursor.execute(query, params)
            else:
                log.debug(f"Executing query: {query}")
                self.cursor.execute(query)

            result = self.cursor.fetchall()
            log.debug(f"Query returned {len(result)} records")
            return result
        except sqlite3.Error as e:
            log.error(f"Error executing query: {e}")
            log.debug(f"Query was: {query}")
            if params:
                log.debug(f"Params were: {params}")
            raise

    def insert(self, query: str, params=None) -> int:
        """
        Execute an insert query on the database.
        This method commits changes to the database.

        :param query: The SQL insert query to execute.
        :param params: Parameters to use with the query (optional).
        :return: The ID of the last inserted row.
        :raises sqlite3.Error: If the query execution fails.
        """
        try:
            if params:
                log.debug(f"Executing insert: {query} with params: {params}")
                self.cursor.execute(query, params)
            else:
                log.debug(f"Executing insert: {query}")
                self.cursor.execute(query)
            self._conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            log.error(f"Error executing insert: {e}")
            log.debug(f"Query was: {query}")
            if params:
                log.debug(f"Params were: {params}")
            self._conn.rollback()
            raise

    def get_clients(self) -> pd.DataFrame:
        """
        This method returns all clients from the database.

        :return: A pandas DataFrame with all clients.
        """
        try:
            query = """
                    SELECT
                        id, institute, bafin_id, address, city, contact_person,
                        phone, fax, email, p033, p034, p035, p036,
                        ab2s1n01, ab2s1n02, ab2s1n03, ab2s1n04, ab2s1n05,
                        ab2s1n06, ab2s1n07, ab2s1n08, ab2s1n09, ab2s1n10,
                        ab2s1n11, ratio
                    FROM client \
                    """

            # Get column names
            self.cursor.execute(f"PRAGMA table_info(client)")
            columns = [row[1] for row in self.cursor.fetchall()]

            # Execute query
            data = self.query(query)

            # Create DataFrame
            return pd.DataFrame(data, columns=columns)

        except sqlite3.Error as e:
            log.error(f"Error fetching clients: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error

    def get_active_client_cases(self, client_ids: list[int] = None) -> pd.DataFrame:
        """
        This method returns all active audit cases by joining the audit_case table with the client table.
        An active case is defined as one where the stage is less than 5.

        :param client_ids: Optional list of client IDs to filter by (for access control)
        :return: A pandas DataFrame with active audit cases and their associated client information.
        """
        try:
            # Base query
            query = """
                    SELECT
                        a.id AS case_id,
                        a.client_id,
                        a.email_id,
                        a.stage,
                        a.created_at,
                        a.last_updated_at,
                        a.comments,
                        c.institute,
                        c.bafin_id,
                        c.address,
                        c.city,
                        c.contact_person,
                        c.phone,
                        c.fax,
                        c.email
                    FROM
                        audit_case a
                            JOIN
                        client c ON a.client_id = c.id
                    WHERE
                        a.stage < 5 \
                    """

            # Add client ID filter if provided
            params = []
            if client_ids is not None:
                if not client_ids:  # Empty list means no access
                    log.info("No accessible clients provided, returning empty DataFrame")
                    return pd.DataFrame()

                placeholders = ','.join(['?' for _ in client_ids])
                query += f" AND a.client_id IN ({placeholders})"
                params.extend(client_ids)

            query += " ORDER BY a.last_updated_at DESC"

            # Execute query
            data = self.query(query, params if params else None)

            # Define column names for the DataFrame
            columns = [
                'case_id', 'client_id', 'email_id', 'stage', 'created_at', 'last_updated_at',
                'comments', 'institute', 'bafin_id', 'address', 'city', 'contact_person',
                'phone', 'fax', 'email'
            ]

            # Create DataFrame
            df = pd.DataFrame(data, columns=columns)

            # Convert timestamp strings to datetime objects for better handling
            if not df.empty:
                df['created_at'] = pd.to_datetime(df['created_at'])
                df['last_updated_at'] = pd.to_datetime(df['last_updated_at'])

            log.info(f"Retrieved {len(df)} active audit cases")
            return df

        except sqlite3.Error as e:
            log.error(f"Error fetching active audit cases: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error

    def get_user_by_email(self, email: str) -> dict | None:
        """
        Get user information by email address.

        :param email: The email address to search for
        :return: Dictionary with user information or None if not found
        """
        try:
            result = self.query("""
                                SELECT id, username_email, role, created_at
                                FROM user
                                WHERE LOWER(username_email) = LOWER(?)
                                """, (email,))

            if result:
                return {
                    'id': result[0][0],
                    'email': result[0][1],
                    'role': result[0][2],
                    'created_at': result[0][3]
                }
            return None

        except sqlite3.Error as e:
            log.error(f"Error fetching user by email: {e}")
            return None

    def get_client_by_bafin_id(self, bafin_id: int) -> dict | None:
        """
        Get client information by BaFin ID.

        :param bafin_id: The BaFin ID to search for
        :return: Dictionary with client information or None if not found
        """
        try:
            result = self.query("""
                                SELECT id, institute, bafin_id, address, city,
                                       contact_person, phone, fax, email
                                FROM client
                                WHERE bafin_id = ?
                                """, (bafin_id,))

            if result:
                return {
                    'id': result[0][0],
                    'institute': result[0][1],
                    'bafin_id': result[0][2],
                    'address': result[0][3],
                    'city': result[0][4],
                    'contact_person': result[0][5],
                    'phone': result[0][6],
                    'fax': result[0][7],
                    'email': result[0][8]
                }
            return None

        except sqlite3.Error as e:
            log.error(f"Error fetching client by BaFin ID: {e}")
            return None

    def execute_migration(self, migration_sql: str) -> bool:
        """
        Execute a migration SQL script.

        :param migration_sql: The SQL script to execute
        :return: True if successful, False otherwise
        """
        try:
            # Split the SQL script by semicolons to handle multiple statements
            statements = [s.strip() for s in migration_sql.split(';') if s.strip()]

            for statement in statements:
                self.cursor.execute(statement)

            self._conn.commit()
            log.info("Migration executed successfully")
            return True

        except sqlite3.Error as e:
            log.error(f"Error executing migration: {e}")
            self._conn.rollback()
            return False
