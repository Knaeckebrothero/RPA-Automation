"""
Unit tests for the mock_imaplib.py module.

This module contains tests for the mock IMAP implementation used for testing
email functionality without connecting to a real IMAP server.
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import socket
import pickle
import os

from mock_imaplib import MockIMAP4_SSL


class TestMockImaplib:
    """Test suite for the mock_imaplib.py module."""

    @pytest.fixture
    def valid_credentials(self):
        """Provide valid mock credentials."""
        return {
            'host': 'right.host.com',
            'port': 993,
            'user': 'right@example.com',
            'password': 'right_password',
            'mailbox': 'right_mailbox'
        }

    @pytest.fixture
    def mock_emails(self):
        """Create mock email data."""
        return [
            {
                'id': '1',
                'sender': 'sender1@example.com',
                'subject': 'Test Email 1',
                'date': 'Mon, 01 Jan 2024 10:00:00 +0000',
                'content': 'Test content 1',
                'attachments': []
            },
            {
                'id': '2',
                'sender': 'sender2@example.com',
                'subject': 'Test Email 2',
                'date': 'Tue, 02 Jan 2024 11:00:00 +0000',
                'content': 'Test content 2',
                'attachments': [b'PDF content']
            }
        ]

    def test_init_with_correct_credentials(self, valid_credentials):
        """Test initialization with correct host and port."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        
        assert mock_imap.host == valid_credentials['host']
        assert mock_imap.port == valid_credentials['port']
        assert mock_imap.state == 'NONAUTH'
        assert mock_imap.selected_mailbox is None

    def test_init_with_wrong_host(self, valid_credentials):
        """Test initialization with wrong host raises error."""
        with pytest.raises(socket.gaierror) as exc_info:
            MockIMAP4_SSL('wrong.host.com', valid_credentials['port'])
        
        assert exc_info.value.errno == 11001
        assert "getaddrinfo failed" in str(exc_info.value)

    def test_init_with_wrong_port(self, valid_credentials):
        """Test initialization with wrong port raises error."""
        with pytest.raises(socket.gaierror) as exc_info:
            MockIMAP4_SSL(valid_credentials['host'], 999)
        
        assert exc_info.value.errno == 11001
        assert "getaddrinfo failed" in str(exc_info.value)

    def test_init_with_both_wrong(self):
        """Test initialization with both wrong host and port."""
        with pytest.raises(socket.gaierror) as exc_info:
            MockIMAP4_SSL('wrong.host.com', 999)
        
        assert exc_info.value.errno == 11001

    @patch('mock_imaplib.MockIMAP4_SSL._add_test_emails')
    def test_login_success(self, mock_add_emails, valid_credentials):
        """Test successful login with correct credentials."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        
        result = mock_imap.login(valid_credentials['user'], valid_credentials['password'])
        
        assert result == ('OK', [b'Logged in'])
        assert mock_imap.state == 'AUTH'
        mock_add_emails.assert_called_once()

    def test_login_wrong_username(self, valid_credentials):
        """Test login with wrong username."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        
        result = mock_imap.login('wrong@example.com', valid_credentials['password'])
        
        assert result == ('NO', [b'Invalid credentials'])
        assert mock_imap.state == 'NONAUTH'

    def test_login_wrong_password(self, valid_credentials):
        """Test login with wrong password."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        
        result = mock_imap.login(valid_credentials['user'], 'wrong_password')
        
        assert result == ('NO', [b'Invalid credentials'])
        assert mock_imap.state == 'NONAUTH'

    def test_select_mailbox_authenticated(self, valid_credentials):
        """Test selecting mailbox when authenticated."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap.state = 'AUTH'  # Simulate authenticated state
        
        result = mock_imap.select(valid_credentials['mailbox'])
        
        assert result == ('OK', [b'2'])  # Assuming 2 emails
        assert mock_imap.selected_mailbox == valid_credentials['mailbox']

    def test_select_mailbox_unauthenticated(self, valid_credentials):
        """Test selecting mailbox when not authenticated."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        
        result = mock_imap.select(valid_credentials['mailbox'])
        
        assert result == ('NO', [b'Not authenticated'])
        assert mock_imap.selected_mailbox is None

    def test_select_wrong_mailbox(self, valid_credentials):
        """Test selecting wrong mailbox."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap.state = 'AUTH'
        
        result = mock_imap.select('wrong_mailbox')
        
        assert result == ('NO', [b'Mailbox does not exist'])
        assert mock_imap.selected_mailbox is None

    def test_search_with_mailbox_selected(self, valid_credentials, mock_emails):
        """Test searching emails with mailbox selected."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap.state = 'AUTH'
        mock_imap.selected_mailbox = valid_credentials['mailbox']
        mock_imap._emails = mock_emails
        
        result = mock_imap.search(None, 'ALL')
        
        assert result == ('OK', [b'1 2'])

    def test_search_no_mailbox_selected(self, valid_credentials):
        """Test searching emails without mailbox selected."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap.state = 'AUTH'
        
        result = mock_imap.search(None, 'ALL')
        
        assert result == ('NO', [b'No mailbox selected'])

    def test_fetch_email_success(self, valid_credentials, mock_emails):
        """Test fetching email successfully."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap.state = 'AUTH'
        mock_imap.selected_mailbox = valid_credentials['mailbox']
        mock_imap._emails = mock_emails
        
        result = mock_imap.fetch('1', '(RFC822)')
        
        assert result[0] == 'OK'
        assert b'1 (RFC822' in result[1][0][0]
        assert b'From: sender1@example.com' in result[1][0][1]
        assert b'Subject: Test Email 1' in result[1][0][1]

    def test_fetch_nonexistent_email(self, valid_credentials, mock_emails):
        """Test fetching non-existent email."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap.state = 'AUTH'
        mock_imap.selected_mailbox = valid_credentials['mailbox']
        mock_imap._emails = mock_emails
        
        result = mock_imap.fetch('999', '(RFC822)')
        
        assert result == ('NO', [b'Message does not exist'])

    def test_fetch_no_mailbox_selected(self, valid_credentials):
        """Test fetching email without mailbox selected."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap.state = 'AUTH'
        
        result = mock_imap.fetch('1', '(RFC822)')
        
        assert result == ('NO', [b'No mailbox selected'])

    def test_logout(self, valid_credentials):
        """Test logout functionality."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap.state = 'AUTH'
        
        result = mock_imap.logout()
        
        assert result == ('OK', [b'Logged out'])
        assert mock_imap.state == 'LOGOUT'

    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.load')
    @patch('os.path.exists')
    def test_add_test_emails_from_pickle(self, mock_exists, mock_pickle_load, mock_file, valid_credentials):
        """Test loading test emails from pickle file."""
        mock_exists.return_value = True
        mock_pickle_load.return_value = [
            {'id': '1', 'content': 'Pickled email 1'},
            {'id': '2', 'content': 'Pickled email 2'}
        ]
        
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap._add_test_emails()
        
        # Verify pickle file was loaded
        mock_file.assert_called_once_with('example_mails/mock_emails.pkl', 'rb')
        mock_pickle_load.assert_called_once()
        
        # Verify emails were loaded
        assert len(mock_imap._emails) == 2
        assert mock_imap._emails[0]['content'] == 'Pickled email 1'

    @patch('os.path.exists')
    def test_add_test_emails_no_pickle_file(self, mock_exists, valid_credentials):
        """Test adding test emails when pickle file doesn't exist."""
        mock_exists.return_value = False
        
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        
        # Should raise NotImplementedError as per the TODO in the code
        with pytest.raises(NotImplementedError):
            mock_imap._add_test_emails()

    def test_email_with_attachment(self, valid_credentials):
        """Test email with attachment in fetch response."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap.state = 'AUTH'
        mock_imap.selected_mailbox = valid_credentials['mailbox']
        
        # Create email with attachment
        email_with_attachment = {
            'id': '1',
            'sender': 'sender@example.com',
            'subject': 'Email with PDF',
            'date': 'Wed, 03 Jan 2024 12:00:00 +0000',
            'content': 'See attached',
            'attachments': [b'%PDF-1.5 mock pdf content']
        }
        mock_imap._emails = [email_with_attachment]
        
        result = mock_imap.fetch('1', '(RFC822)')
        
        assert result[0] == 'OK'
        # Verify attachment is included in response
        assert b'attachment' in result[1][0][1]
        assert b'%PDF-1.5' in result[1][0][1]

    def test_state_transitions(self, valid_credentials):
        """Test proper state transitions during operations."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        
        # Initial state
        assert mock_imap.state == 'NONAUTH'
        
        # After successful login
        mock_imap.login(valid_credentials['user'], valid_credentials['password'])
        assert mock_imap.state == 'AUTH'
        
        # After logout
        mock_imap.logout()
        assert mock_imap.state == 'LOGOUT'

    def test_multiple_email_ids_in_search(self, valid_credentials):
        """Test search returns multiple email IDs."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap.state = 'AUTH'
        mock_imap.selected_mailbox = valid_credentials['mailbox']
        mock_imap._emails = [
            {'id': '1', 'content': 'Email 1'},
            {'id': '2', 'content': 'Email 2'},
            {'id': '3', 'content': 'Email 3'}
        ]
        
        result = mock_imap.search(None, 'ALL')
        
        assert result == ('OK', [b'1 2 3'])

    def test_empty_mailbox_search(self, valid_credentials):
        """Test search on empty mailbox."""
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        mock_imap.state = 'AUTH'
        mock_imap.selected_mailbox = valid_credentials['mailbox']
        mock_imap._emails = []
        
        result = mock_imap.search(None, 'ALL')
        
        assert result == ('OK', [b''])

    @patch('pickle.load')
    @patch('builtins.open', side_effect=Exception("File error"))
    @patch('os.path.exists')
    def test_add_test_emails_file_error(self, mock_exists, mock_file, mock_pickle, valid_credentials):
        """Test handling file errors when loading test emails."""
        mock_exists.return_value = True
        
        mock_imap = MockIMAP4_SSL(valid_credentials['host'], valid_credentials['port'])
        
        # Should raise the file error
        with pytest.raises(Exception) as exc_info:
            mock_imap._add_test_emails()
        
        assert "File error" in str(exc_info.value)