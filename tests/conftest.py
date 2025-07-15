"""
Pytest configuration and fixtures for the RPA Document Fetcher test suite.
"""
import pytest
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import after adding to path
from cls.database import Database
from cls.mailclient import MailClient
from cls.singleton import SingletonMeta


@pytest.fixture(scope="session", autouse=True)
def test_environment():
    """Configure test environment using pre-initialized database."""
    # Load test environment variables
    os.environ["DEV_MODE"] = "true"
    os.environ["DB_PATH"] = os.environ.get("DB_PATH", "test_db.sqlite")
    os.environ["MOCK_EMAIL_DIR"] = "example_mails/"
    os.environ["LOG_LEVEL"] = "WARNING"

    # Ensure example_mails directory exists
    Path("example_mails").mkdir(exist_ok=True)

    yield

    # Cleanup is handled by GitHub Actions


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test to ensure isolation."""
    # Clear all singleton instances
    SingletonMeta._instances = {}
    yield
    # Clear again after test
    SingletonMeta._instances = {}


@pytest.fixture(scope="function")
def db():
    """Provide a clean database instance for each test."""
    # Get database instance (will be recreated due to reset_singletons)
    database = Database.get_instance()

    # Begin transaction for rollback capability
    conn = database.get_connection()
    conn.execute("BEGIN")

    yield database

    # Rollback any changes made during the test
    try:
        conn.rollback()
    except:
        pass
    finally:
        conn.close()


@pytest.fixture(scope="function")
def clean_db(db):
    """Provide database with cleaned transaction tables."""
    with db.get_connection() as conn:
        # Clear only transaction data, keep reference data
        conn.execute("DELETE FROM audit_case")
        conn.execute("DELETE FROM document")
        conn.execute("DELETE FROM document_data")
        conn.execute("DELETE FROM user_session")
        # Reset audit trail except system entries
        conn.execute("DELETE FROM audit_trail WHERE user_id != 0")
        conn.commit()

    return db


@pytest.fixture
def mock_email_client():
    """Return mock email client (automatically used in DEV_MODE).

    The mock client expects emails in pickle format (test_mail_*.pickle)
    in the MOCK_EMAIL_DIR directory, which is created by email_downloader.py.
    """
    client = MailClient.get_instance()
    # In DEV_MODE, this should automatically use mock_imaplib
    return client


@pytest.fixture
def sample_user(clean_db):
    """Create a test user."""
    conn = clean_db.get_connection()
    cursor = conn.execute(
        """INSERT INTO user (username, password_hash, email, role, is_active)
           VALUES (?, ?, ?, ?, ?)""",
        ("test_user", "hashed_password", "test@example.com", "auditor", 1)
    )
    user_id = cursor.lastrowid
    conn.commit()

    return {
        "id": user_id,
        "username": "test_user",
        "email": "test@example.com",
        "role": "auditor"
    }


@pytest.fixture
def sample_client(clean_db):
    """Create a test client."""
    conn = clean_db.get_connection()
    cursor = conn.execute(
        """INSERT INTO client (
            client_name, email, financial_year_start, financial_year_end,
            revenue_value, expenditure_value, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            "Test Client Corp", "client@example.com",
            "2024-01-01", "2024-12-31",
            1000000.00, 800000.00, 1
        )
    )
    client_id = cursor.lastrowid
    conn.commit()

    return {
        "id": client_id,
        "name": "Test Client Corp",
        "email": "client@example.com"
    }


@pytest.fixture
def sample_audit_case(clean_db, sample_client, sample_user):
    """Create a test audit case."""
    conn = clean_db.get_connection()
    cursor = conn.execute(
        """INSERT INTO audit_case (
            client_id, stage, assigned_to, created_by, reminder_sent
        ) VALUES (?, ?, ?, ?, ?)""",
        (sample_client["id"], 1, sample_user["id"], sample_user["id"], 0)
    )
    case_id = cursor.lastrowid
    conn.commit()

    return {
        "id": case_id,
        "client_id": sample_client["id"],
        "stage": 1,
        "assigned_to": sample_user["id"]
    }


@pytest.fixture
def temp_pdf_file():
    """Create a temporary PDF file for testing."""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
        # Write a minimal PDF header
        f.write(b"%PDF-1.4\n")
        f.write(b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n")
        f.write(b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n")
        f.write(b"xref\n0 3\n0000000000 65535 f\n")
        f.write(b"0000000009 00000 n\n0000000058 00000 n\n")
        f.write(b"trailer<</Size 3/Root 1 0 R>>\n")
        f.write(b"startxref\n109\n%%EOF\n")
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        os.unlink(temp_path)
    except:
        pass


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit for testing UI components."""
    import unittest.mock as mock

    # Create mock streamlit module
    mock_st = mock.MagicMock()

    # Mock session state
    mock_st.session_state = {}

    # Mock common streamlit functions
    mock_st.title = mock.MagicMock()
    mock_st.write = mock.MagicMock()
    mock_st.error = mock.MagicMock()
    mock_st.success = mock.MagicMock()
    mock_st.warning = mock.MagicMock()
    mock_st.info = mock.MagicMock()
    mock_st.sidebar = mock.MagicMock()
    mock_st.columns = mock.MagicMock(return_value=[mock.MagicMock(), mock.MagicMock()])
    mock_st.button = mock.MagicMock(return_value=False)
    mock_st.text_input = mock.MagicMock(return_value="")
    mock_st.selectbox = mock.MagicMock(return_value=None)

    # Patch streamlit import
    with mock.patch.dict('sys.modules', {'streamlit': mock_st}):
        yield mock_st


# Markers for conditional test execution
requires_ocr = pytest.mark.skipif(
    not shutil.which("tesseract"),
    reason="Tesseract OCR not installed"
)

requires_imap_secrets = pytest.mark.skipif(
    not all([
        os.environ.get("IMAP_HOST"),
        os.environ.get("IMAP_USER"),
        os.environ.get("IMAP_PASSWORD")
    ]),
    reason="IMAP credentials not available (fork PR or no secrets configured)"
)

slow_test = pytest.mark.skipif(
    os.environ.get("SKIP_SLOW_TESTS", "").lower() == "true",
    reason="Skipping slow tests"
)
