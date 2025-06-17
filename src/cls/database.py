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
    Manage SQLite database interactions, including connecting, querying, and managing client and audit case data.

    This class operates as a singleton to ensure only one connection to the database exists throughout the
    application's lifecycle. It provides methods to execute SQL queries, insert data, and retrieve specific
    records or datasets, including clients and active audit cases. It ensures that required database tables
    exist and handles errors gracefully during database interactions.

    Attributes:
    :ivar _path: The file path to the SQLite database used for establishing the connection.
    :type _path: str
    :ivar _conn: Represents the SQLite database connection object. Set to None if no connection exists.
    :type _conn: sqlite3.Connection | None
    :ivar cursor: Represents the SQLite database cursor object. Used for executing SQL queries.
    :type cursor: sqlite3.Cursor | None
    """
    def __init__(self, db_path: str = "./.filesystem/database.db"):
        """
        Initializes and configures the database connection.

        This class is responsible for establishing a connection to the database
        specified by the provided file path. It sets up the connection and
        initializes the cursor to enable database operations. The default
        database path is set to './.filesystem/database.db'.

        .. note::

           The connection to the database is established immediately upon
           initialization.

        :param db_path: The file path to the SQLite database.
        :type db_path: str
        """
        log.debug("Initializing database connection...")
        self._path = db_path
        self._conn = None
        self.cursor = None
        self.connect()
        log.info("Database initialized.")

    def __del__(self):
        """
        Handles the cleanup and closing of resources when the object is destroyed.

        This special method ensures that the proper disposal of resources is performed
        as part of the object's lifecycle. Once the object is no longer in use and is
        subject to garbage collection, this method is called to release any held
        resources, such as open connections or files, and perform additional cleanup
        operations, if necessary. The additional logging provides useful insights about
        the destruction process for debugging purposes.
        """
        self.close()
        log.debug("Database object destroyed.")

    def connect(self):
        """
        Establishes a connection to the SQLite database and ensures necessary setup is performed.

        This method attempts to connect to the SQLite database located at the specified path.
        If the directory of the database path does not exist, it will create the required directory.
        After establishing the connection, it initializes the cursor and verifies the presence of
        required tables in the database. If there is an error during the connection process, it
        logs the error and raises an exception.

        :raises sqlite3.Error: If an error occurs while attempting to connect to the database.
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
        Closes the database connection if it is currently open and resets
        associated resources. If no connection is open, logs a warning.
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
        Verifies the existence of required tables in the SQLite database. If the required
        tables are not present, an error is logged and a RuntimeError is raised. The method
        also logs debug information when all required tables are found. By default, a
        predefined list of required tables is used if none is provided.

        :param required_tables: List of table names that are required to exist in the
            database. If not provided, a default list of table names will be used.
        :type required_tables: list[str]
        :raises RuntimeError: If any of the required tables is missing in the database.
        :raises sqlite3.Error: If an SQLite database error occurs during the table
            verification process.
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
        Executes the provided SQL query using the cursor associated with the database
        connection. This function executes the query with or without parameters and
        retrieves all rows returned by the executed query. It also logs detailed
        debug-level information about the query execution and error handling.

        :param query: The SQL query string to execute.
        :type query: str
        :param params: A sequence of parameters to bind to the SQL query.
            If None, the query is executed without binding parameters. Defaults to None.
        :type params: Optional[Union[tuple, list]]
        :return: A list of tuples representing the rows fetched from the query
            result, a list for non-tuple outputs, or None if results are unavailable.
        :rtype: Union[list[tuple], list, None]
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
        Inserts a new record into the database and returns the ID of the last inserted row.
        The method executes the given SQL `query` with optional `params`, commits the transaction,
        and retrieves the ID of the last inserted row. If the operation fails, it rolls back
        the transaction and raises an exception. Logs the query and parameters for debugging
        purposes.

        :param query: The SQL insert query to be executed.
        :type query: str
        :param params: Optional sequence or mapping to be bound to the query, default is None.
        :type params: Optional[Any]
        :return: The ID of the last inserted row.
        :rtype: int
        :raises sqlite3.Error: If an error occurs during query execution or committing the transaction.
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
        Fetch client data from the database and return it as a pandas DataFrame.

        This method executes an SQL query to retrieve information about clients
        from the `client` table in the database. It includes various fields such as
        `id`, `institute`, `bafin_id`, contact details, and other attributes related
        to the client. The query results are then converted into a pandas DataFrame.
        If there's an error during the query execution, an empty DataFrame is returned.

        :return: DataFrame containing client data or an empty DataFrame if an
            error occurred during retrieval.
        :rtype: pd.DataFrame
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
        Retrieves active audit cases from the database, filtering by client IDs if
        provided, and returns the results as a pandas DataFrame. Audit cases are
        considered active if their stage is less than 5.

        :param client_ids: List of client IDs to filter the query. If None, no filter
                           is applied. If an empty list is provided, an empty
                           DataFrame is returned.
        :type client_ids: list[int]
        :return: A pandas DataFrame containing the active audit cases. Columns in
                 the DataFrame include case details such as case_id, client_id,
                 stage, created_at, last_updated_at, and client-specific details like
                 institute, address, and contact information.
        :rtype: pd.DataFrame
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
        Fetches user information from the database based on the provided email address.
        This method performs a database query to retrieve user details, including the
        user's ID, email, role, and creation date. The email address is matched in a
        case-insensitive manner.

        :param email: The email address of the user to be retrieved. It is matched
            against the `username_email` column in the database table.
        :type email: str
        :return: A dictionary containing user details if the email exists in the
            database. The dictionary includes the user's `id`, `email`, `role`,
            and `created_at`. If the email is not found, or in case of an error,
            it returns `None`.
        :rtype: dict | None
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
        Fetch a client record from the database using their BaFin ID.

        This method queries the database for a client whose record matches
        the provided BaFin ID. If a matching record is found, the method
        returns a dictionary containing the client's details such as ID,
        institute, address, city, and contact information. If no match
        is found or an error occurs, the method returns None.

        :param bafin_id: The BaFin ID of the client to be searched for.
        :type bafin_id: int
        :return: A dictionary containing client details if a match is
                 found, otherwise None.
        :rtype: dict | None
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
        Executes a given SQL migration script using the database connection and cursor objects.
        This method takes the input SQL script, splits it into individual statements,
        executes them sequentially, commits the changes to the database on success,
        or rolls back the transaction in case of an error.

        :param migration_sql: The SQL migration script to be executed. This can consist of multiple SQL
                              statements separated by semicolons.
        :type migration_sql: str
        :return: A boolean indicating whether the migration execution was successful.
        :rtype: bool
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
