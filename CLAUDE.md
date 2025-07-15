# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Start the main application
streamlit run src/main.py

# Initialize the application (first time setup)
python app_init.py

# Initialize database
python db_init.py
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src tests/

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only

# Run specific test file
pytest tests/unit/cls/test_database.py

# Run specific test with verbose output
pytest -v tests/unit/cls/test_database.py::TestDatabase::test_database_initialization
```

### GitHub Actions Testing
The repository includes automated testing via GitHub Actions that runs on push/PR to `main` and `develop` branches.

**Optional GitHub Secrets for enhanced testing:**
If you want to test with real email data, add these secrets to your GitHub repository:
- `IMAP_HOST`: Your email server host
- `IMAP_PORT`: Email server port (usually 993)
- `IMAP_USER`: Your email username
- `IMAP_PASSWORD`: Your email password (use app password for Gmail)
- `INBOX`: Your inbox name

The workflow will automatically download example emails if credentials are provided, otherwise it uses mock data.

### Dependencies
```bash
# Install all dependencies (includes testing)
pip install -r requirements.txt
```

### Linting and Code Quality
```bash
# No linting tools are currently configured in requirements
# Consider adding: pylint, black, isort, mypy for code quality
```

### Important Notes on pytest
Since pytest 7.0+, the `pytest-pythonpath` plugin is obsolete. The project uses the built-in `pythonpath` configuration in `pytest.ini` instead.

## Architecture Overview

This is a Python-based RPA (Robotic Process Automation) document fetcher that automates yearly auditing processes. The application connects to email inboxes, retrieves PDF documents, uses OCR to extract text and tabular data, and automatically compares extracted values against database records.

### Core Architecture

The application follows a modular architecture with clear separation of concerns:

- **cls/**: Core business logic classes (Database, Document, Mailclient, AccessControl, Config)
- **processing/**: Document processing utilities (OCR, detection, file operations)
- **ui/**: Streamlit-based web interface components
- **workflow/**: Business workflow logic (audit, security, Excel import)

### Key Components

1. **Database Layer** (`cls/database.py`): SQLite-based data persistence with audit trails
2. **Document Processing** (`cls/document.py`, `processing/`): PDF processing with OCR using EasyOCR/Tesseract
3. **Email Integration** (`cls/mailclient.py`): IMAP-based email fetching with mock support for development
4. **Access Control** (`cls/accesscontrol.py`): Role-based (admin, auditor, inspector) and resource-based permissions
5. **Web Interface** (`ui/`): Streamlit-based UI with multi-page navigation
6. **Workflow Engine** (`workflow/audit.py`): 5-stage audit process workflow

### Database Schema

Key tables include:
- `client`: Client information and financial data
- `audit_case`: Active audit cases and their stages (1-5)
- `document`: Document tracking and processing status
- `user`: User accounts with role-based access
- `user_client_access`: Granular user-to-client permissions

### Processing Workflow

1. **Stage 1**: Document reception from email
2. **Stage 2**: Data verification via OCR comparison
3. **Stage 3**: Certificate generation for verified documents
4. **Stage 4**: Process completion
5. **Stage 5**: Archiving

### Configuration

The application uses multiple configuration layers:
- Environment variables (`.env` file)
- Configuration file (`src/config.cfg`)
- Dynamic settings via web interface

### Development Mode

Set `DEV_MODE=true` in `.env` to use mock email data from `example_mails/` directory instead of connecting to real IMAP servers.

## Important Implementation Details

### Singleton Pattern
Database and Mailclient use singleton pattern accessed via `get_instance()` method.

### OCR Integration
Uses both EasyOCR and Tesseract with GPU acceleration support. Text extraction patterns defined in `src/regex_patterns.json`.

### Security
- Session-based authentication with IP tracking
- Login attempt monitoring
- Comprehensive audit logging
- Role-based access control with resource-level permissions

### Testing Strategy
- Unit tests for individual components
- Integration tests for workflow processes
- Extensive mocking of external dependencies (database, email, OCR)
- Shared fixtures in `tests/conftest.py`

### File Structure
```
src/
├── cls/                    # Core classes
├── processing/            # Document processing
├── ui/                    # Web interface
├── workflow/              # Business logic
├── main.py               # Application entry point
├── schema.sql            # Database schema
└── config.cfg            # Configuration file
```

## Notes for Development

- Application entry point is `src/main.py`
- Database initialization scripts are in root directory (`db_init.py`, `app_init.py`)
- Test data and examples are in `examples/` directory
- Docker deployment configuration in `deployment/` directory
- OCR requires Tesseract system installation for full functionality
- Email processing supports both live IMAP and mock data for development
- The `.gitignore` file excludes runtime data, logs, and local configuration files
- When running tests in CI/CD, the workflow handles database initialization automatically