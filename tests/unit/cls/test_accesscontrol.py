"""
Unit tests for the AccessControl class.

This module contains tests for the AccessControl class functionality, including
role-based permissions, client access management, and error handling.
"""
from unittest.mock import patch, MagicMock

from cls.accesscontrol import AccessControl


class TestAccessControl:
    """Test suite for the AccessControl class."""

    def test_can_access_feature(self):
        """Test checking if a role can access a specific feature."""
        # Test admin access to various features
        assert AccessControl.can_access_feature('admin', 'settings') is True
        assert AccessControl.can_access_feature('admin', 'user_management') is True
        assert AccessControl.can_access_feature('admin', 'nonexistent_feature') is False
        
        # Test inspector access
        assert AccessControl.can_access_feature('inspector', 'view_assigned_cases') is True
        assert AccessControl.can_access_feature('inspector', 'edit_assigned_cases') is True
        assert AccessControl.can_access_feature('inspector', 'user_management') is False
        
        # Test auditor access
        assert AccessControl.can_access_feature('auditor', 'view_assigned_cases') is True
        assert AccessControl.can_access_feature('auditor', 'settings') is False
        
        # Test invalid role
        assert AccessControl.can_access_feature('invalid_role', 'settings') is False
        
        # Test None role
        assert AccessControl.can_access_feature(None, 'settings') is False

    @patch('cls.database.Database')
    def test_can_access_client_as_admin(self, mock_db_class):
        """Test checking if an admin can access a client."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Test admin access (should always return True without querying the database)
        result = AccessControl.can_access_client(1, 100, user_role='admin', database=mock_db)
        
        # Verify the result
        assert result is True
        
        # Verify that no database query was made for client access
        mock_db.query.assert_not_called()

    @patch('cls.database.Database')
    def test_can_access_client_with_explicit_access(self, mock_db_class):
        """Test checking if a user with explicit access can access a client."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database query to return a result (indicating access)
        mock_db.query.return_value = [(1,)]
        
        # Test user access with explicit permission
        result = AccessControl.can_access_client(2, 100, user_role='inspector', database=mock_db)
        
        # Verify the result
        assert result is True
        
        # Verify that the database was queried for client access
        mock_db.query.assert_called_once()

    @patch('cls.database.Database')
    def test_can_access_client_without_access(self, mock_db_class):
        """Test checking if a user without access cannot access a client."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database query to return an empty result (indicating no access)
        mock_db.query.return_value = []
        
        # Test user access without permission
        result = AccessControl.can_access_client(3, 100, user_role='inspector', database=mock_db)
        
        # Verify the result
        assert result is False
        
        # Verify that the database was queried for client access
        mock_db.query.assert_called_once()

    @patch('cls.database.Database')
    def test_can_access_client_fetch_role(self, mock_db_class):
        """Test checking if a user can access a client when role is not provided."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database queries
        # First query gets the user role
        # Second query checks for client access
        mock_db.query.side_effect = [
            [('inspector',)],  # User role query result
            []                 # Client access query result (empty = no access)
        ]
        
        # Test user access without providing role
        result = AccessControl.can_access_client(4, 100, database=mock_db)
        
        # Verify the result
        assert result is False
        
        # Verify that the database was queried twice
        assert mock_db.query.call_count == 2

    @patch('cls.database.Database')
    def test_can_access_client_user_not_found(self, mock_db_class):
        """Test checking if a non-existent user can access a client."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database query to return an empty result (user not found)
        mock_db.query.return_value = []
        
        # Test access for non-existent user
        result = AccessControl.can_access_client(999, 100, database=mock_db)
        
        # Verify the result
        assert result is False
        
        # Verify that the database was queried for the user
        mock_db.query.assert_called_once()

    @patch('cls.database.Database')
    def test_get_accessible_clients_as_admin(self, mock_db_class):
        """Test getting accessible clients for an admin."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database query to return a list of clients
        mock_db.query.return_value = [(1,), (2,), (3,)]
        
        # Test getting accessible clients for admin
        result = AccessControl.get_accessible_clients(1, user_role='admin', database=mock_db)
        
        # Verify the result
        assert result == [1, 2, 3]
        
        # Verify that the database was queried for all clients
        mock_db.query.assert_called_once_with("SELECT id FROM client")

    @patch('cls.database.Database')
    def test_get_accessible_clients_for_user(self, mock_db_class):
        """Test getting accessible clients for a regular user."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database query to return a list of accessible clients
        mock_db.query.return_value = [(100,), (200,)]
        
        # Test getting accessible clients for a regular user
        result = AccessControl.get_accessible_clients(2, user_role='inspector', database=mock_db)
        
        # Verify the result
        assert result == [100, 200]
        
        # Verify that the database was queried for user's accessible clients
        mock_db.query.assert_called_once()

    @patch('cls.database.Database')
    def test_get_accessible_clients_fetch_role(self, mock_db_class):
        """Test getting accessible clients when role is not provided."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database queries
        # First query gets the user role
        # Second query gets the accessible clients
        mock_db.query.side_effect = [
            [('inspector',)],     # User role query result
            [(100,), (200,)]      # Accessible clients query result
        ]
        
        # Test getting accessible clients without providing role
        result = AccessControl.get_accessible_clients(2, database=mock_db)
        
        # Verify the result
        assert result == [100, 200]
        
        # Verify that the database was queried twice
        assert mock_db.query.call_count == 2

    @patch('cls.database.Database')
    def test_get_accessible_clients_user_not_found(self, mock_db_class):
        """Test getting accessible clients for a non-existent user."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database query to return an empty result (user not found)
        mock_db.query.return_value = []
        
        # Test getting accessible clients for non-existent user
        result = AccessControl.get_accessible_clients(999, database=mock_db)
        
        # Verify the result
        assert result == []
        
        # Verify that the database was queried for the user
        mock_db.query.assert_called_once()

    @patch('cls.database.Database')
    def test_grant_client_access_new(self, mock_db_class):
        """Test granting a user access to a client."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database queries
        # First query checks if access already exists
        # Second query inserts the new access
        mock_db.query.return_value = []  # No existing access
        mock_db.insert.return_value = 1  # Insert successful
        
        # Test granting access
        result = AccessControl.grant_client_access(2, 100, granted_by=1, database=mock_db)
        
        # Verify the result
        assert result is True
        
        # Verify that the database was queried and insert was called
        mock_db.query.assert_called_once()
        mock_db.insert.assert_called_once()

    @patch('cls.database.Database')
    def test_grant_client_access_existing(self, mock_db_class):
        """Test granting a user access to a client they already have access to."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database query to return a result (indicating existing access)
        mock_db.query.return_value = [(1,)]
        
        # Test granting access when it already exists
        result = AccessControl.grant_client_access(2, 100, database=mock_db)
        
        # Verify the result
        assert result is True
        
        # Verify that the database was queried but insert was not called
        mock_db.query.assert_called_once()
        mock_db.insert.assert_not_called()

    @patch('cls.database.Database')
    def test_grant_client_access_error(self, mock_db_class):
        """Test granting a user access to a client with a database error."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database query to raise an exception
        mock_db.query.side_effect = Exception("Database error")
        
        # Test granting access with a database error
        result = AccessControl.grant_client_access(2, 100, database=mock_db)
        
        # Verify the result
        assert result is False
        
        # Verify that the database was queried
        mock_db.query.assert_called_once()

    @patch('cls.database.Database')
    def test_revoke_client_access(self, mock_db_class):
        """Test revoking a user's access to a client."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Test revoking access
        result = AccessControl.revoke_client_access(2, 100, database=mock_db)
        
        # Verify the result
        assert result is True
        
        # Verify that the database was queried
        mock_db.query.assert_called_once()

    @patch('cls.database.Database')
    def test_revoke_client_access_error(self, mock_db_class):
        """Test revoking a user's access to a client with a database error."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database query to raise an exception
        mock_db.query.side_effect = Exception("Database error")
        
        # Test revoking access with a database error
        result = AccessControl.revoke_client_access(2, 100, database=mock_db)
        
        # Verify the result
        assert result is False
        
        # Verify that the database was queried
        mock_db.query.assert_called_once()

    @patch('cls.database.Database')
    def test_get_user_client_access(self, mock_db_class):
        """Test getting a user's client access records."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database query to return access records
        mock_db.query.return_value = [
            (100, "Company A", "BF12345", "2023-01-01", "admin@example.com"),
            (200, "Company B", "BF67890", "2023-01-02", "admin@example.com")
        ]
        
        # Test getting user client access
        result = AccessControl.get_user_client_access(2, database=mock_db)
        
        # Verify the result
        assert len(result) == 2
        assert result[0]['client_id'] == 100
        assert result[0]['institute'] == "Company A"
        assert result[0]['bafin_id'] == "BF12345"
        assert result[0]['granted_at'] == "2023-01-01"
        assert result[0]['granted_by'] == "admin@example.com"
        
        # Verify that the database was queried
        mock_db.query.assert_called_once()

    @patch('cls.database.Database')
    def test_get_user_client_access_no_records(self, mock_db_class):
        """Test getting client access records for a user with no access."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the database query to return no records
        mock_db.query.return_value = []
        
        # Test getting user client access with no records
        result = AccessControl.get_user_client_access(2, database=mock_db)
        
        # Verify the result
        assert result == []
        
        # Verify that the database was queried
        mock_db.query.assert_called_once()

    @patch('cls.database.Database')
    @patch.object(AccessControl, 'grant_client_access')
    def test_bulk_grant_access(self, mock_grant, mock_db_class):
        """Test granting access to multiple users and clients in bulk."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the grant_client_access method to return True
        mock_grant.return_value = True
        
        # Test bulk granting access
        assignments = [
            {'user_id': 1, 'client_id': 100},
            {'user_id': 2, 'client_id': 200},
            {'user_id': 3, 'client_id': 300}
        ]
        result = AccessControl.bulk_grant_access(assignments, granted_by=1, database=mock_db)
        
        # Verify the result
        assert result['success_count'] == 3
        assert len(result['errors']) == 0
        
        # Verify that grant_client_access was called for each assignment
        assert mock_grant.call_count == 3

    @patch('cls.database.Database')
    @patch.object(AccessControl, 'grant_client_access')
    def test_bulk_grant_access_with_errors(self, mock_grant, mock_db_class):
        """Test bulk granting access with some failures."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Mock the grant_client_access method to return True for some and False for others
        mock_grant.side_effect = [True, False, True]
        
        # Test bulk granting access with some failures
        assignments = [
            {'user_id': 1, 'client_id': 100},
            {'user_id': 2, 'client_id': 200},
            {'user_id': 3, 'client_id': 300}
        ]
        result = AccessControl.bulk_grant_access(assignments, database=mock_db)
        
        # Verify the result
        assert result['success_count'] == 2
        assert len(result['errors']) == 1
        
        # Verify that grant_client_access was called for each assignment
        assert mock_grant.call_count == 3

    @patch('cls.database.Database')
    @patch.object(AccessControl, 'grant_client_access')
    def test_bulk_grant_access_invalid_assignments(self, mock_grant, mock_db_class):
        """Test bulk granting access with invalid assignments."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Test bulk granting access with invalid assignments
        assignments = [
            {'user_id': 1, 'client_id': 100},
            {'user_id': None, 'client_id': 200},
            {'user_id': 3, 'client_id': None},
            {'wrong_key': 'wrong_value'}
        ]
        result = AccessControl.bulk_grant_access(assignments, database=mock_db)
        
        # Verify the result
        assert result['success_count'] == 1
        assert len(result['errors']) == 3
        
        # Verify that grant_client_access was called only for valid assignments
        mock_grant.assert_called_once()