"""
Shared pytest fixtures for the RPA-Document-Fetcher test suite.

This file contains fixtures that can be used across multiple test files.
"""
import os
import pytest
import sqlite3
import base64
import numpy as np
from unittest.mock import MagicMock, patch

# Add the src directory to the Python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_sqlite_connection():
    """
    Create a mock SQLite connection and cursor for database testing.

    Returns:
        tuple: (mock_connection, mock_cursor)
    """
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


@pytest.fixture
def sample_document_content():
    """
    Provide sample document content for testing.

    Returns:
        bytes: Sample document content
    """
    return b'Sample document content for testing'


@pytest.fixture
def sample_document_attributes():
    """
    Provide sample document attributes for testing.

    Returns:
        dict: Sample document attributes
    """
    return {
        'name': 'test_document.pdf',
        'type': 'application/pdf',
        'size': 1024,
        'created_at': '2023-01-01T12:00:00',
        'author': 'Test Author'
    }


@pytest.fixture
def sample_pdf_content():
    """
    Provide sample PDF content for testing.

    Returns:
        bytes: Sample PDF content with PDF header
    """
    return b'%PDF-1.5\nSample PDF content for testing'


@pytest.fixture
def sample_pdf_attributes():
    """
    Provide sample PDF attributes for testing.

    Returns:
        dict: Sample PDF attributes
    """
    return {
        'filename': 'test_document.pdf',
        'content_type': 'application/pdf',
        'size': 1024,
        'created_at': '2023-01-01T12:00:00',
        'author': 'Test Author',
        'BaFin-ID': 12345,
        'client_id': 1,
        'email_id': 100
    }


@pytest.fixture
def mock_database():
    """
    Create a mock Database instance for testing.

    Returns:
        MagicMock: Mock Database instance
    """
    with patch('cls.database.Database') as mock_db_class:
        db_instance = MagicMock()
        mock_db_class.return_value = db_instance
        db_instance.get_instance.return_value = db_instance

        # Set up common query responses
        db_instance.query.side_effect = lambda query, params=None: {
            "SELECT id FROM client WHERE bafin_id = ?": [(1,)] if params and params[0] == 12345 else [],
            "SELECT stage FROM audit_case WHERE client_id = ?": [(1,)] if params and params[0] == 1 else [],
            "SELECT id FROM audit_case WHERE client_id = ?": [(123,)] if params and params[0] == 1 else [],
            "SELECT document_path FROM document WHERE document_hash = ? AND audit_case_id = ?": [] 
        }.get(query, [])

        yield db_instance


@pytest.fixture
def mock_ocr_reader():
    """
    Create a mock OCR reader for testing.

    Returns:
        MagicMock: Mock OCR reader
    """
    mock = MagicMock()
    mock.readtext.return_value = [
        ([[0, 0], [100, 0], [100, 30], [0, 30]], "Sample OCR Text", 0.95)
    ]
    return mock


@pytest.fixture
def mock_cv2():
    """
    Create a mock cv2 module for testing.

    Returns:
        MagicMock: Mock cv2 module
    """
    with patch('cv2.cvtColor', return_value=np.zeros((100, 100, 3), dtype=np.uint8)), \
         patch('cv2.boundingRect', return_value=(0, 0, 100, 30)), \
         patch('cv2.contourArea', return_value=3000):
        yield


@pytest.fixture
def mock_detect_module():
    """
    Create a mock detect module for testing.

    Returns:
        MagicMock: Mock detect module
    """
    with patch('processing.detect.normalize_image_resolution', return_value=np.zeros((100, 100, 3), dtype=np.uint8)), \
         patch('processing.detect.tables', return_value=[np.array([[[0, 0]], [[100, 0]], [[100, 30]], [[0, 30]]])]), \
         patch('processing.detect.rows', return_value=[(0, 30)]), \
         patch('processing.detect.cells', return_value=[(0, 100)]), \
         patch('processing.detect.bafin_id', return_value=12345):
        yield


@pytest.fixture
def mock_ocr_cell():
    """
    Create a mock ocr_cell function for testing.

    Returns:
        MagicMock: Mock ocr_cell function
    """
    with patch('processing.ocr.ocr_cell', return_value="Sample OCR Text"):
        yield


@pytest.fixture
def mock_get_images_from_pdf():
    """
    Create a mock get_images_from_pdf function for testing.

    Returns:
        MagicMock: Mock get_images_from_pdf function
    """
    with patch('processing.files.get_images_from_pdf', return_value=[MagicMock()]):
        yield


@pytest.fixture
def mock_environment_variables():
    """
    Set up mock environment variables for testing.

    This fixture uses pytest's monkeypatch to set environment variables
    that are commonly used in the application.
    """
    env_vars = {
        'IMAP_HOST': 'test.mail.server',
        'IMAP_PORT': '993',
        'IMAP_USER': 'test@example.com',
        'IMAP_PASSWORD': 'test_password',
        'INBOX': 'INBOX',
        'SMTP_HOST': 'test.smtp.server',
        'SMTP_PORT': '587',
        'LOG_LEVEL_CONSOLE': '20',
        'LOG_LEVEL_FILE': '10',
        'LOG_PATH': './logs',
        'DEV_MODE': 'true',
        'EXAMPLE_MAIL_PATH': './example_mails'
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_imap_connection():
    """
    Create a mock IMAP connection for email testing.

    Returns:
        MagicMock: Mock IMAP connection
    """
    mock = MagicMock()
    mock.login.return_value = ('OK', [b'Login successful'])
    mock.select.return_value = ('OK', [b'1'])
    mock.search.return_value = ('OK', [b'1 2 3'])
    mock.fetch.return_value = ('OK', [(b'1', b'EMAIL_DATA')])
    return mock


@pytest.fixture
def mock_smtp_connection():
    """
    Create a mock SMTP connection for email sending testing.

    Returns:
        MagicMock: Mock SMTP connection
    """
    mock = MagicMock()
    mock.login.return_value = None  # SMTP login doesn't return anything on success
    mock.sendmail.return_value = {}  # Empty dict indicates success
    return mock
