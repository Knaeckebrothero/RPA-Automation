"""
This module holds the database class.
"""
import sqlite3
import logging
import json

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
        self._insert_example_data()
        log.info("Database initialized.")

    def __del__(self):
        self.close()

    def connect(self):
        """
        Attempt to connect to the database.
        """
        try:
            self._conn = sqlite3.connect(self._path, check_same_thread=False)
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
                email TEXT NOT NULL,
                p033 INTEGER,
                p034 INTEGER,
                p035 INTEGER,
                p036 INTEGER,
                ab2s1n01 INTEGER,
                ab2s1n02 INTEGER,
                ab2s1n03 INTEGER,
                ab2s1n04 INTEGER,
                ab2s1n05 INTEGER,
                ab2s1n06 INTEGER,
                ab2s1n07 INTEGER,
                ab2s1n08 INTEGER,
                ab2s1n09 INTEGER,
                ab2s1n10 INTEGER,
                ab2s1n11 INTEGER,
                ratio FLOAT
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

    def _insert_example_data(self):
        """
        Insert data from a JSON file into the companies table.
        """
        try:
            # Check if the table is empty
            if not self.cursor.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 0:
                log.debug("Company table already contains data, skipping example data insertion.")
                return

            # Load the example data from a JSON file
            with open('./.filesystem/examples.json', 'r') as f:
                examples = json.load(f)

            # Insert the example data into the companies table
            for company in examples:
                # Map JSON data to the columns in the table
                self.cursor.execute("""
                INSERT INTO companies (
                    institut, bafin_id, address, city, contact_person,
                    phone, fax, email, 
                    p033, p034, p035, p036,
                    ab2s1n01, ab2s1n02, ab2s1n03, ab2s1n04, ab2s1n05,
                    ab2s1n06, ab2s1n07, ab2s1n08, ab2s1n09, ab2s1n10,
                    ab2s1n11, 
                    ratio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    company["Institut"], company["ID"], company["Adresse"], company["PLZ/Ort"],
                    company["Ansprechpartner"], company["Telefon"], company["Fax"], company["Mail"],
                    int(company["N1"].replace(".", "")), int(company["N2"].replace(".", "")),
                    int(company["N3"].replace(".", "")), int(company["N4"].replace(".", "")),
                    int(company["N6"].replace(".", "")), int(company["N7"].replace(".", "")),
                    int(company["N8"].replace(".", "")), int(company["N9"].replace(".", "")),
                    int(company["N10"].replace(".", "")), int(company["N11"].replace(".", "")),
                    int(company["N12"].replace(".", "")), int(company["N13"].replace(".", "")),
                    int(company["N14"].replace(".", "")), int(company["N15"].replace(".", "")),
                    int(company["N16"].replace(".", "")),
                    float(company["N18"].replace(".", "").replace(",", ".")),
                ))

            self._conn.commit()
            log.info("Example data inserted into companies table.")
        except sqlite3.Error as e:
            log.error(f"Error inserting example data: {e}")
        except Exception as e:
            log.error(f"Unexpected error: {e}")

    def query(self, query: str) -> list[tuple]:
        """
        Execute a query on the database.
        The difference is that this method does not do a commit.

        :param query: The query to execute.
        :return: The result of the query as a list of tuples
        """
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            log.error(f"Error executing query: {e}")
            return []

    def insert(self, insert_query: str) -> bool:
        """
        Execute an insert query on the database.
        The difference is that this method does not do a fetchall.

        :param insert_query: The insert query to execute.
        :return: True if the query was successful, False otherwise.
        """
        try:
            self.cursor.execute(insert_query)
            self._conn.commit()
            return True
        except sqlite3.Error as e:
            log.error(f"Error executing query: {e}")
            return False
