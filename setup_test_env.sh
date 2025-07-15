# Setup script for local test environment

echo "Setting up test environment..."

# Load credentials from existing .env file
if [ -f .env ]; then
    echo "Loading credentials from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Override with test-specific settings
export DEV_MODE=true
export DB_PATH=test_db.sqlite
export MOCK_EMAIL_DIR=example_mails/
export LOG_LEVEL=WARNING
export CI=true

# Create example_mails directory
mkdir -p example_mails

# Initialize test database
echo "Initializing test database..."
python db_init.py
python app_init.py

# Download test emails if credentials are available
if [ ! -z "$IMAP_HOST" ] && [ ! -z "$IMAP_USER" ] && [ ! -z "$IMAP_PASSWORD" ]; then
    echo "Downloading test emails..."
    python email_downloader.py --num-emails 5 --output-dir example_mails --manifest
else
    echo "No IMAP credentials found, skipping email download"
fi

echo "Test environment setup complete!"
echo ""
echo "Run tests with: pytest"
echo "Run specific tests with: pytest tests/unit/"
echo "Run with coverage: pytest --cov=src"