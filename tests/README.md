# RPA Document Fetcher - Test Suite

This directory contains the test suite for the RPA Document Fetcher application.

## Test Structure

```
tests/
├── unit/              # Unit tests for individual components
├── integration/       # Integration tests requiring multiple components
├── conftest.py       # Shared pytest fixtures and configuration
├── download_test_emails.py  # Script to download test emails
└── README.md         # This file
```

## Running Tests

### Local Development

1. **Basic test run:**
   ```bash
   pytest
   ```

2. **Run only unit tests:**
   ```bash
   pytest tests/unit/
   ```

3. **Run with coverage:**
   ```bash
   pytest --cov=src --cov-report=html
   ```

4. **Run specific test file:**
   ```bash
   pytest tests/unit/cls/test_database.py
   ```

5. **Run tests matching pattern:**
   ```bash
   pytest -k "test_email"
   ```

### CI/CD Pipeline

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests targeting these branches
- Manual workflow dispatch

## Test Fixtures

The following fixtures are available in `conftest.py`:

### Database Fixtures
- `db`: Provides a database instance with transaction rollback
- `clean_db`: Database with cleared transaction tables
- `sample_user`: Creates a test user
- `sample_client`: Creates a test client
- `sample_audit_case`: Creates a test audit case with dependencies

### Email Fixtures
- `mock_email_client`: Returns the mock email client (auto-enabled in DEV_MODE)

### File Fixtures
- `temp_pdf_file`: Creates a temporary PDF file for testing

### UI Fixtures
- `mock_streamlit`: Mocks Streamlit for UI component testing

## Test Markers

Use these markers to conditionally run tests:

```python
@pytest.mark.requires_ocr       # Skip if Tesseract not installed
@pytest.mark.requires_imap_secrets  # Skip if IMAP credentials not available
@pytest.mark.slow_test         # Skip if SKIP_SLOW_TESTS=true
```

## Environment Variables

The test suite uses these environment variables:

### Test Configuration (set automatically):
- `DEV_MODE=true` - Enables mock services
- `DB_PATH=test_db.sqlite` - Test database location
- `MOCK_EMAIL_DIR=example_mails/` - Directory for mock emails
- `CI=true` - Set by GitHub Actions in CI environment

### Credentials (from your .env file or GitHub Secrets):
- `IMAP_HOST` - IMAP server hostname
- `IMAP_USER` - IMAP username
- `IMAP_PASSWORD` - IMAP password
- `INBOX` - Inbox name (default: INBOX)

## GitHub Actions Setup

### 1. Add Repository Secrets

Go to Settings → Secrets and variables → Actions → New repository secret:

- `IMAP_HOST`: Your IMAP server (e.g., imap.gmail.com)
- `IMAP_USER`: Your email address
- `IMAP_PASSWORD`: Your email password (use app password for Gmail)
- `INBOX`: (Optional) Inbox name if not "INBOX"

### 2. Initial Setup

The workflow automatically:
1. Installs system dependencies (Tesseract)
2. Installs Python dependencies
3. Initializes test database using `db_init.py` and `app_init.py`
4. Downloads test emails (if secrets available)
5. Runs tests

## Writing Tests

### Example Unit Test

```python
def test_database_operation(clean_db, sample_client):
    """Test database operations with fixtures."""
    # clean_db provides a clean database
    # sample_client provides test data
    
    result = clean_db.get_client(sample_client["id"])
    assert result["name"] == "Test Client Corp"
```

### Example Integration Test

```python
@pytest.mark.requires_imap_secrets
def test_email_processing():
    """Test requiring real email connection."""
    # This test only runs when IMAP credentials are available
    pass
```

### Mocking External Services

```python
def test_with_mock(mocker):
    """Test using pytest-mock."""
    mock_ocr = mocker.patch('src.processing.ocr.extract_text')
    mock_ocr.return_value = "Test text"
    
    # Your test code here
```

## Troubleshooting

### Tests fail with "Database not initialized"
- Ensure `db_init.py` and `app_init.py` run before tests
- Check that `DB_PATH` environment variable is set correctly

### OCR tests skipped
- Install Tesseract: `sudo apt-get install tesseract-ocr`
- Or use the `@pytest.mark.requires_ocr` marker

### Integration tests skipped in PR
- This is expected for PRs from forks (no access to secrets)
- Tests will run fully on push to main/develop branches

### Mock emails not found
- Ensure `example_mails/` directory exists
- Run `python email_downloader.py --output-dir example_mails` with credentials
- Check that pickle files are created (test_mail_*.pickle)