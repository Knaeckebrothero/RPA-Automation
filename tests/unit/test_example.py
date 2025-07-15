"""
Example test file showing how to use the test fixtures.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_database_connection(db):
    """Test that we can connect to the database."""
    # The db fixture provides a database instance
    assert db is not None

    # Test a simple query
    with db.get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM user")
        count = cursor.fetchone()[0]
        assert count >= 0  # At least no errors


def test_create_audit_case(sample_audit_case, clean_db):
    """Test creating an audit case using fixtures."""
    # sample_audit_case fixture creates all necessary data
    assert sample_audit_case["id"] > 0
    assert sample_audit_case["stage"] == 1

    # Verify it was created in the database
    with clean_db.get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM audit_case WHERE id = ?",
            (sample_audit_case["id"],)
        )
        row = cursor.fetchone()
        assert row is not None


def test_mock_email_client(mock_email_client):
    """Test that mock email client works in DEV_MODE."""
    # In DEV_MODE, this should use mock_imaplib
    assert mock_email_client is not None

    # The mock should be configured to read from example_mails/
    # You can test email fetching here


@pytest.mark.requires_ocr
def test_ocr_functionality():
    """Test that requires OCR - will be skipped if Tesseract not installed."""
    import pytesseract
    # Your OCR test here
    assert True


@pytest.mark.requires_imap_secrets
def test_real_email_connection():
    """Test that requires real IMAP credentials - skipped in fork PRs."""
    import os
    host = os.environ.get("IMAP_HOST")
    assert host is not None
    # Your real email test here


def test_with_mocked_dependencies(mocker):
    """Example of using pytest-mock to mock external dependencies."""
    # Mock the OCR function
    mock_ocr = mocker.patch('src.processing.ocr.extract_text')
    mock_ocr.return_value = "Mocked OCR text"

    # Now when your code calls extract_text, it gets the mocked response
    from src.processing.ocr import extract_text
    result = extract_text("dummy.pdf")
    assert result == "Mocked OCR text"
    mock_ocr.assert_called_once_with("dummy.pdf")


def test_file_processing_with_temp_files(temp_pdf_file):
    """Example using the temp_pdf_file fixture."""
    import os

    # temp_pdf_file provides a path to a temporary PDF
    assert os.path.exists(temp_pdf_file)
    assert temp_pdf_file.endswith('.pdf')

    # Use the file in your test
    # The file will be automatically cleaned up after the test
