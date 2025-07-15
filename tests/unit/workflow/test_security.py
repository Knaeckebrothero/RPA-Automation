"""
Unit tests for the security workflow module.

This module contains tests for the security-related functions, including
authentication, session management, and password handling.
"""
import pytest
from unittest.mock import patch, MagicMock
import os
import hashlib
import secrets
from datetime import datetime, timedelta

import workflow.security as security


class TestSecurity:
    """Test suite for the security workflow module."""

    @patch('workflow.security.get_script_run_ctx')
    def test_get_client_ip(self, mock_get_ctx):
        """Test getting client IP address."""
        # Setup
        mock_ctx = MagicMock()
        mock_ctx.session_id = "test_session"
        mock_get_ctx.return_value = mock_ctx
        
        # Execute
        result = security.get_client_ip()
        
        # Assert
        assert result == "127.0.0.1"  # Default IP for testing
        mock_get_ctx.assert_called_once()

    @patch('workflow.security.get_script_run_ctx')
    def test_get_client_ip_no_context(self, mock_get_ctx):
        """Test getting client IP address when no context is available."""
        # Setup
        mock_get_ctx.return_value = None
        
        # Execute
        result = security.get_client_ip()
        
        # Assert
        assert result == "unknown"
        mock_get_ctx.assert_called_once()

    @patch('workflow.security.Database')
    def test_check_login_attempts_no_attempts(self, mock_db_class):
        """Test checking login attempts when there are no previous attempts."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = []  # No previous attempts
        
        # Execute
        result = security.check_login_attempts("127.0.0.1")
        
        # Assert
        assert result is True
        mock_db.query.assert_called_once()

    @patch('workflow.security.Database')
    def test_check_login_attempts_below_limit(self, mock_db_class):
        """Test checking login attempts when attempts are below the limit."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        # 3 attempts in the last 15 minutes (below default limit of 5)
        mock_db.query.return_value = [
            (1, "127.0.0.1", "user1", (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")),
            (2, "127.0.0.1", "user1", (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")),
            (3, "127.0.0.1", "user2", (datetime.now() - timedelta(minutes=12)).strftime("%Y-%m-%d %H:%M:%S"))
        ]
        
        # Execute
        result = security.check_login_attempts("127.0.0.1")
        
        # Assert
        assert result is True
        mock_db.query.assert_called_once()

    @patch('workflow.security.Database')
    def test_check_login_attempts_at_limit(self, mock_db_class):
        """Test checking login attempts when attempts are at the limit."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        # 5 attempts in the last 15 minutes (at default limit of 5)
        mock_db.query.return_value = [
            (1, "127.0.0.1", "user1", (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")),
            (2, "127.0.0.1", "user1", (datetime.now() - timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M:%S")),
            (3, "127.0.0.1", "user2", (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "127.0.0.1", "user3", (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")),
            (5, "127.0.0.1", "user1", (datetime.now() - timedelta(minutes=14)).strftime("%Y-%m-%d %H:%M:%S"))
        ]
        
        # Execute
        result = security.check_login_attempts("127.0.0.1")
        
        # Assert
        assert result is False
        mock_db.query.assert_called_once()

    @patch('workflow.security.Database')
    def test_record_failed_attempt(self, mock_db_class):
        """Test recording a failed login attempt."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Execute
        security.record_failed_attempt("127.0.0.1", "testuser")
        
        # Assert
        mock_db.insert.assert_called_once()
        # Check that the first argument to insert is the expected SQL query
        assert "INSERT INTO login_attempts" in mock_db.insert.call_args[0][0]
        # Check that the second argument contains the IP and username
        assert "127.0.0.1" in mock_db.insert.call_args[0][1]
        assert "testuser" in mock_db.insert.call_args[0][1]

    @patch('workflow.security.Database')
    def test_record_successful_login(self, mock_db_class):
        """Test recording a successful login."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Execute
        security.record_successful_login("127.0.0.1", 1)
        
        # Assert
        mock_db.insert.assert_called_once()
        # Check that the first argument to insert is the expected SQL query
        assert "INSERT INTO login_history" in mock_db.insert.call_args[0][0]
        # Check that the second argument contains the IP and user_id
        assert "127.0.0.1" in mock_db.insert.call_args[0][1]
        assert 1 in mock_db.insert.call_args[0][1]

    def test_generate_session_key(self):
        """Test generating a session key."""
        # Execute
        key1 = security.generate_session_key()
        key2 = security.generate_session_key()
        
        # Assert
        assert len(key1) == 32  # Default length
        assert key1 != key2  # Keys should be unique
        
        # Test with custom length
        key3 = security.generate_session_key(length=64)
        assert len(key3) == 64

    def test_hash_password(self):
        """Test hashing a password."""
        # Execute
        hashed, salt = security.hash_password("password123")
        
        # Assert
        assert hashed is not None
        assert salt is not None
        assert hashed != "password123"  # Password should be hashed
        
        # Test with provided salt
        hashed2, salt2 = security.hash_password("password123", salt)
        assert hashed2 == hashed  # Same password + same salt = same hash
        assert salt2 == salt

    def test_verify_password(self):
        """Test verifying a password."""
        # Setup
        password = "password123"
        hashed, salt = security.hash_password(password)
        
        # Execute & Assert
        assert security.verify_password(hashed, salt, password) is True
        assert security.verify_password(hashed, salt, "wrongpassword") is False

    @patch('workflow.security.generate_session_key')
    @patch('workflow.security.Database')
    def test_create_session(self, mock_db_class, mock_gen_key):
        """Test creating a user session."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_gen_key.return_value = "test_session_key"
        
        # Execute
        result = security.create_session(1)
        
        # Assert
        assert result == "test_session_key"
        mock_db.insert.assert_called_once()
        mock_gen_key.assert_called_once()

    @patch('workflow.security.Database')
    def test_validate_session_valid(self, mock_db_class):
        """Test validating a valid session."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        # Session that expires in the future
        future_time = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        mock_db.query.return_value = [(1, future_time)]
        
        # Execute
        result = security.validate_session("test_session_key")
        
        # Assert
        assert result == 1  # Should return user_id
        mock_db.query.assert_called_once()

    @patch('workflow.security.Database')
    def test_validate_session_expired(self, mock_db_class):
        """Test validating an expired session."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        # Session that expired in the past
        past_time = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        mock_db.query.return_value = [(1, past_time)]
        
        # Execute
        result = security.validate_session("test_session_key")
        
        # Assert
        assert result is None  # Should return None for expired session
        mock_db.query.assert_called_once()
        mock_db.query.assert_called_with("DELETE FROM sessions WHERE session_key = ?", ("test_session_key",))

    @patch('workflow.security.Database')
    def test_validate_session_not_found(self, mock_db_class):
        """Test validating a session that doesn't exist."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = []  # No session found
        
        # Execute
        result = security.validate_session("nonexistent_key")
        
        # Assert
        assert result is None
        mock_db.query.assert_called_once()

    @patch('workflow.security.Database')
    def test_get_user_role(self, mock_db_class):
        """Test getting a user's role."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = [("admin",)]
        
        # Execute
        result = security.get_user_role(1)
        
        # Assert
        assert result == "admin"
        mock_db.query.assert_called_once()

    @patch('workflow.security.Database')
    def test_get_user_role_not_found(self, mock_db_class):
        """Test getting a role for a user that doesn't exist."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = []
        
        # Execute
        result = security.get_user_role(999)
        
        # Assert
        assert result is None
        mock_db.query.assert_called_once()

    @patch('workflow.security.Database')
    def test_logout(self, mock_db_class):
        """Test logging out a user."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        
        # Execute
        security.logout("test_session_key")
        
        # Assert
        mock_db.query.assert_called_once_with("DELETE FROM sessions WHERE session_key = ?", ("test_session_key",))

    @patch('workflow.security.validate_session')
    @patch('workflow.security.get_user_role')
    def test_require_auth_valid(self, mock_get_role, mock_validate):
        """Test require_auth with a valid session."""
        # Setup
        mock_validate.return_value = 1  # Valid user_id
        mock_get_role.return_value = "admin"
        
        # Mock st.session_state
        with patch('workflow.security.st.session_state', {'session_key': 'test_key'}):
            # Execute
            result = security.require_auth(required_role="admin")
            
            # Assert
            assert result == 1
            mock_validate.assert_called_once_with('test_key')
            mock_get_role.assert_called_once_with(1)

    @patch('workflow.security.validate_session')
    def test_require_auth_invalid_session(self, mock_validate):
        """Test require_auth with an invalid session."""
        # Setup
        mock_validate.return_value = None  # Invalid session
        
        # Mock st.session_state
        with patch('workflow.security.st.session_state', {'session_key': 'test_key'}):
            # Execute
            result = security.require_auth()
            
            # Assert
            assert result is None
            mock_validate.assert_called_once_with('test_key')

    @patch('workflow.security.validate_session')
    @patch('workflow.security.get_user_role')
    def test_require_auth_insufficient_role(self, mock_get_role, mock_validate):
        """Test require_auth with insufficient role."""
        # Setup
        mock_validate.return_value = 1  # Valid user_id
        mock_get_role.return_value = "user"  # Lower role than required
        
        # Mock st.session_state
        with patch('workflow.security.st.session_state', {'session_key': 'test_key'}):
            # Execute
            result = security.require_auth(required_role="admin")
            
            # Assert
            assert result is None
            mock_validate.assert_called_once_with('test_key')
            mock_get_role.assert_called_once_with(1)

    def test_generate_secure_password(self):
        """Test generating a secure password."""
        # Execute
        password1 = security.generate_secure_password()
        password2 = security.generate_secure_password()
        
        # Assert
        assert len(password1) == 12  # Default length
        assert password1 != password2  # Passwords should be unique
        
        # Test with custom length
        password3 = security.generate_secure_password(length=20)
        assert len(password3) == 20
        
        # Check that password contains at least one of each required character type
        def has_required_chars(password):
            has_lower = any(c.islower() for c in password)
            has_upper = any(c.isupper() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for c in password)
            return has_lower and has_upper and has_digit and has_special
        
        assert has_required_chars(password1)