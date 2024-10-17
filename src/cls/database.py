"""
This module holds the database class.
"""
import sqlite3
import logging

# Custom imports
from cls.singleton import Singleton


# Set up logging
log  = logging.getLogger(__name__)


class Database(Singleton):
    """
    The Database class represents the database and acts as a middleman.
    """
    _path = "./.filesystem/database.db"

    def __init__(self):
        log.debug("Initializing...")
        self._conn = None
        self.cursor = None
        self.connect()
        self._ensure_tables_exist()
        log.info("Database initialized.")

    def __del__(self):
        self.close()

    def connect(self):
        """
        Attempt to connect to the database.
        """
        try:
            self._conn = sqlite3.connect(self._path)
            self.cursor = self._conn.cursor()
            log.debug("Connected to database.")
        except sqlite3.Error as e:
            log.error(f"Error connecting to database: {e}")

    def close(self):
        """
        Attempt to close the database connection.
        """
        if self._conn:
            self._conn.close()
            log.debug("Database connection closed.")
        else:
            log.warning("No database connection to close.")

    def _ensure_tables_exist(self):
        """
        Ensure that all required tables exist in the database.
        Make sure the companies table is created first,
        as the status table has a foreign key constraint on it.
        """
        try:
            self._create_companies_table()
            self._create_status_table()
            log.debug("All required tables are ensured to exist.")
        except sqlite3.Error as e:
            log.error(f"Error ensuring tables exist: {e}")

    def _create_companies_table(self):
        """
        Create the companies table if it does not exist.
        """
        try:
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                institut TEXT,
                bafin_id INTEGER NOT NULL,
                address TEXT,
                city TEXT,
                contact_person TEXT,
                phone TEXT,
                fax TEXT,
                email TEXT NOT NULL
            );
            """)
            self._conn.commit()
            log.debug("Companies table created or already exists.")
        except sqlite3.Error as e:
            log.error(f"Error creating companies table: {e}")

    def _create_status_table(self):
        """
        Create the status table if it does not exist.
        """
        try:
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                email_id INTEGER NOT NULL,
                
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                comment TEXT,
                
                FOREIGN KEY (company_id) REFERENCES companies(id)
            );
            """)
            self._conn.commit()
            log.debug("Status table created or already exists.")
        except sqlite3.Error as e:
            log.error(f"Error creating status table: {e}")

    def query(self, query: str) -> list:
        """
        Execute a query on the database.
        """
        try:
            self.cursor.execute(query)
            self._conn.commit()
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            log.error(f"Error executing query: {e}")
            return []
