@echo off
REM Setup script for local test environment on Windows

echo Setting up test environment...

REM Set test-specific environment variables
set DEV_MODE=true
set DB_PATH=test_db.sqlite
set MOCK_EMAIL_DIR=example_mails/
set LOG_LEVEL=WARNING
set CI=true

REM Create example_mails directory
if not exist example_mails mkdir example_mails

REM Initialize test database
echo Initializing test database...
python db_init.py
python app_init.py

REM Download test emails if credentials are available
if defined IMAP_HOST if defined IMAP_USER if defined IMAP_PASSWORD (
    echo Downloading test emails...
    python email_downloader.py --num-emails 5 --output-dir example_mails --manifest
) else (
    echo No IMAP credentials found, skipping email download
)

echo Test environment setup complete!
echo.
echo Run tests with: pytest
echo Run specific tests with: pytest tests\unit\
echo Run with coverage: pytest --cov=src