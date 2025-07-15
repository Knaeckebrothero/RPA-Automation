"""
Unit tests for the Database class.

This module contains tests for the Database class functionality, including
connection management, query execution, and data retrieval methods.
"""
import os
import pytest
import sqlite3
from unittest.mock import patch, MagicMock, mock_open

from cls.database import Database


class TestDatabase:
    """Test suite for the Database class."""

    def test_database_initialization(self):
        """Test that Database initializes with correct default path."""
        db = Database()
        assert db._db_path.endswith('database.db')
        assert db._connection is None

    def test_database_custom_path(self):
        """Test that Database accepts a custom path."""
        custom_path = "./custom/path/database.db"
        db = Database(db_path=custom_path)
        assert db._db_path == custom_path

    @patch('sqlite3.connect')
    def test_database_connect(self, mock_connect, mock_sqlite_connection):
        """Test database connection."""
        conn, cursor = mock_sqlite_connection
        mock_connect.return_value = conn
        
        db = Database()
        db.connect()
        
        mock_connect.assert_called_once()
        assert db._connection is not None

    @patch('sqlite3.connect')
    def test_database_connect_error(self, mock_connect):
        """Test database connection error handling."""
        mock_connect.side_effect = sqlite3.Error("Connection error")
        
        db = Database()
        with pytest.raises(Exception) as excinfo:
            db.connect()
        
        assert "Failed to connect to database" in str(excinfo.value)

    def test_database_close(self, mock_sqlite_connection):
        """Test database connection closing."""
        conn, _ = mock_sqlite_connection
        
        db = Database()
        db._connection = conn
        db.close()
        
        conn.close.assert_called_once()
        assert db._connection is None

    def test_database_close_no_connection(self):
        """Test closing when no connection exists."""
        db = Database()
        db._connection = None
        # Should not raise an exception
        db.close()

    @patch('sqlite3.connect')
    def test_database_query(self, mock_connect, mock_sqlite_connection):
        """Test database query execution."""
        conn, cursor = mock_sqlite_connection
        mock_connect.return_value = conn
        cursor.fetchall.return_value = [('result1',), ('result2',)]
        
        db = Database()
        result = db.query("SELECT * FROM test_table")
        
        cursor.execute.assert_called_once_with("SELECT * FROM test_table", None)
        assert len(result) == 2
        assert result[0][0] == 'result1'

    @patch('sqlite3.connect')
    def test_database_query_with_params(self, mock_connect, mock_sqlite_connection):
        """Test database query with parameters."""
        conn, cursor = mock_sqlite_connection
        mock_connect.return_value = conn
        cursor.fetchall.return_value = [('specific_result',)]
        
        db = Database()
        result = db.query("SELECT * FROM test_table WHERE id = ?", (1,))
        
        cursor.execute.assert_called_once_with("SELECT * FROM test_table WHERE id = ?", (1,))
        assert len(result) == 1
        assert result[0][0] == 'specific_result'

    @patch('sqlite3.connect')
    def test_database_query_error(self, mock_connect, mock_sqlite_connection):
        """Test database query error handling."""
        conn, cursor = mock_sqlite_connection
        mock_connect.return_value = conn
        cursor.execute.side_effect = sqlite3.Error("Query error")
        
        db = Database()
        with pytest.raises(Exception) as excinfo:
            db.query("SELECT * FROM test_table")
        
        assert "Error executing query" in str(excinfo.value)

    @patch('sqlite3.connect')
    def test_database_insert(self, mock_connect, mock_sqlite_connection):
        """Test database insert operation."""
        conn, cursor = mock_sqlite_connection
        mock_connect.return_value = conn
        cursor.lastrowid = 1
        
        db = Database()
        result = db.insert("INSERT INTO test_table (name) VALUES (?)", ("test_name",))
        
        cursor.execute.assert_called_once_with("INSERT INTO test_table (name) VALUES (?)", ("test_name",))
        conn.commit.assert_called_once()
        assert result == 1

    @patch('sqlite3.connect')
    def test_database_insert_error(self, mock_connect, mock_sqlite_connection):
        """Test database insert error handling."""
        conn, cursor = mock_sqlite_connection
        mock_connect.return_value = conn
        cursor.execute.side_effect = sqlite3.Error("Insert error")
        
        db = Database()
        with pytest.raises(Exception) as excinfo:
            db.insert("INSERT INTO test_table (name) VALUES (?)", ("test_name",))
        
        assert "Error executing insert" in str(excinfo.value)
        conn.rollback.assert_called_once()

    @patch('sqlite3.connect')
    def test_database_get_clients(self, mock_connect, mock_sqlite_connection):
        """Test get_clients method."""
        conn, cursor = mock_sqlite_connection
        mock_connect.return_value = conn
        
        # Mock the query result for clients
        cursor.fetchall.return_value = [
            (1, 'Client 1', '12345', '67890', 'client1@example.com'),
            (2, 'Client 2', '23456', '78901', 'client2@example.com')
        ]
        
        db = Database()
        clients = db.get_clients()
        
        assert len(clients) == 2
        assert clients[0]['id'] == 1
        assert clients[0]['name'] == 'Client 1'
        assert clients[1]['id'] == 2
        assert clients[1]['name'] == 'Client 2'

    @patch('sqlite3.connect')
    def test_database_get_user_by_email(self, mock_connect, mock_sqlite_connection):
        """Test get_user_by_email method."""
        conn, cursor = mock_sqlite_connection
        mock_connect.return_value = conn
        
        # Mock the query result for user
        cursor.fetchone.return_value = (1, 'test@example.com', 'hashed_password', 'admin')
        
        db = Database()
        user = db.get_user_by_email('test@example.com')
        
        assert user is not None
        assert user['id'] == 1
        assert user['email'] == 'test@example.com'
        assert user['role'] == 'admin'

    @patch('sqlite3.connect')
    def test_database_get_user_by_email_not_found(self, mock_connect, mock_sqlite_connection):
        """Test get_user_by_email when user not found."""
        conn, cursor = mock_sqlite_connection
        mock_connect.return_value = conn
        
        # Mock the query result for no user found
        cursor.fetchone.return_value = None
        
        db = Database()
        user = db.get_user_by_email('nonexistent@example.com')
        
        assert user is None

    @patch('sqlite3.connect')
    def test_database_verify_tables(self, mock_connect, mock_sqlite_connection):
        """Test _verify_tables method."""
        conn, cursor = mock_sqlite_connection
        mock_connect.return_value = conn
        
        # Mock the query result for table names
        cursor.fetchall.return_value = [('users',), ('clients',), ('documents',)]
        
        db = Database()
        # Should not raise an exception if all required tables exist
        db._verify_tables(['users', 'clients'])
        
        # Should raise an exception if a required table is missing
        with pytest.raises(Exception) as excinfo:
            db._verify_tables(['users', 'missing_table'])
        
        assert "Required table 'missing_table' not found" in str(excinfo.value)