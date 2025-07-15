# Unit Testing Guide for RPA-Document-Fetcher

This guide outlines a comprehensive approach to implementing unit tests for the RPA-Document-Fetcher application to achieve 70% code coverage.

## Table of Contents
1. [Introduction](#introduction)
2. [Testing Framework](#testing-framework)
3. [Test Directory Structure](#test-directory-structure)
4. [Components to Test](#components-to-test)
5. [Testing Strategy](#testing-strategy)
6. [Example Test Implementations](#example-test-implementations)
7. [Coverage Measurement](#coverage-measurement)
8. [Continuous Integration](#continuous-integration)

## Introduction

The RPA-Document-Fetcher application currently lacks unit tests. This guide provides a roadmap for implementing tests to achieve 70% code coverage, focusing on the most critical components of the application.

## Testing Framework

### Recommended Tools
- **pytest**: Primary testing framework
- **pytest-cov**: For measuring code coverage
- **pytest-mock**: For mocking dependencies
- **pytest-env**: For environment variable management during tests

### Installation
Add these dependencies to a new `requirements-dev.txt` file:

```
pytest==7.4.0
pytest-cov==4.1.0
pytest-mock==3.11.1
pytest-env==1.0.1
```

Install with:
```bash
pip install -r requirements-dev.txt
```

## Test Directory Structure

Create the following directory structure for tests:

```
tests/
├── conftest.py                  # Shared fixtures
├── unit/
│   ├── cls/                     # Tests for cls module
│   │   ├── test_database.py
│   │   ├── test_document.py
│   │   ├── test_mailclient.py
│   │   └── test_singleton.py
│   ├── processing/              # Tests for processing module
│   │   ├── test_detect.py
│   │   ├── test_files.py
│   │   └── test_ocr.py
│   ├── ui/                      # Tests for ui module
│   │   ├── test_expander_stages.py
│   │   ├── test_navbar.py
│   │   ├── test_pages.py
│   │   └── test_visuals.py
│   └── workflow/                # Tests for workflow module
│       ├── test_audit.py
│       ├── test_excel_import.py
│       └── test_security.py
└── integration/                 # Integration tests
    ├── test_document_workflow.py
    └── test_email_processing.py
```

## Components to Test

To achieve 70% code coverage, focus on testing these key components:

### High Priority (Core Functionality)
1. **Database Operations** (`cls/database.py`)
   - Connection management
   - Query execution
   - Data retrieval methods

2. **Document Processing** (`cls/document.py`)
   - Document class functionality
   - PDF class functionality
   - Document attribute management

3. **Email Client** (`cls/mailclient.py`)
   - Email retrieval
   - Attachment handling
   - Email sending

4. **Processing Modules**
   - OCR functionality (`processing/ocr.py`)
   - File operations (`processing/files.py`)
   - Detection algorithms (`processing/detect.py`)

### Medium Priority
1. **Workflow Management**
   - Audit workflows (`workflow/audit.py`)
   - Security and authentication (`workflow/security.py`)
   - Excel import functionality (`workflow/excel_import.py`)

2. **Singleton Pattern** (`cls/singleton.py`)
   - Instance management
   - Inheritance behavior

### Lower Priority (UI Components)
1. **UI Components**
   - Navigation (`ui/navbar.py`)
   - Page rendering (`ui/pages.py`)
   - Visual components (`ui/visuals.py`)
   - Expander stages (`ui/expander_stages.py`)

## Testing Strategy

### 1. Unit Testing Approach

#### Mocking External Dependencies
- Use `pytest-mock` to mock database connections, file operations, and external APIs
- Create fixture files for test data
- Use environment variables to control test behavior

#### Test Isolation
- Each test should be independent and not rely on the state from other tests
- Use fixtures to set up and tear down test environments

### 2. Test Categories

#### Functional Tests
- Test that functions return expected results for given inputs
- Verify error handling and edge cases

#### Behavioral Tests
- Test that components interact correctly
- Verify that side effects occur as expected

#### Regression Tests
- Test specific bug fixes to prevent regressions

### 3. Testing Priorities

1. **First Phase**: Core functionality (Database, Document, Mailclient)
2. **Second Phase**: Processing modules and Workflow components
3. **Third Phase**: UI components and integration tests

## Example Test Implementations

### Example 1: Testing Database Connection

```python
# tests/unit/cls/test_database.py
import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from cls.database import Database

@pytest.fixture
def mock_sqlite_connection():
    """Mock SQLite connection for testing."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor

def test_database_initialization():
    """Test that Database initializes with correct default path."""
    db = Database()
    assert db._db_path.endswith('database.db')
    assert db._connection is None

@patch('sqlite3.connect')
def test_database_connect(mock_connect, mock_sqlite_connection):
    """Test database connection."""
    conn, cursor = mock_sqlite_connection
    mock_connect.return_value = conn
    
    db = Database()
    db.connect()
    
    mock_connect.assert_called_once()
    assert db._connection is not None

@patch('sqlite3.connect')
def test_database_query(mock_connect, mock_sqlite_connection):
    """Test database query execution."""
    conn, cursor = mock_sqlite_connection
    mock_connect.return_value = conn
    cursor.fetchall.return_value = [('result1',), ('result2',)]
    
    db = Database()
    result = db.query("SELECT * FROM test_table")
    
    cursor.execute.assert_called_once_with("SELECT * FROM test_table", None)
    assert len(result) == 2
    assert result[0][0] == 'result1'
```

### Example 2: Testing Document Class

```python
# tests/unit/cls/test_document.py
import pytest
import os
import json
from unittest.mock import patch, mock_open
from cls.document import Document

@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    content = b'Sample document content'
    attributes = {'name': 'test_doc', 'type': 'text'}
    return Document(content=content, attributes=attributes)

def test_document_initialization(sample_document):
    """Test document initialization with attributes."""
    assert sample_document.get_content() == b'Sample document content'
    assert sample_document.get_attributes('name') == 'test_doc'
    assert sample_document.get_attributes('type') == 'text'

def test_document_add_attributes(sample_document):
    """Test adding attributes to a document."""
    sample_document.add_attributes({'size': 100, 'author': 'Test Author'})
    assert sample_document.get_attributes('size') == 100
    assert sample_document.get_attributes('author') == 'Test Author'
    assert sample_document.get_attributes('name') == 'test_doc'  # Original attribute preserved

@patch('builtins.open', new_callable=mock_open)
def test_document_save_to_file(mock_file, sample_document):
    """Test saving document to a file."""
    sample_document.save_to_file('test_path.txt')
    mock_file.assert_called_once_with('test_path.txt', 'wb')
    mock_file().write.assert_called_once_with(b'Sample document content')
```

### Example 3: Testing Mailclient

```python
# tests/unit/cls/test_mailclient.py
import pytest
from unittest.mock import patch, MagicMock
from cls.mailclient import Mailclient, HTMLTextExtractor

@pytest.fixture
def mock_imap():
    """Mock IMAP connection for testing."""
    mock = MagicMock()
    mock.login.return_value = ('OK', [b'Login successful'])
    mock.select.return_value = ('OK', [b'1'])
    return mock

@patch('cls.mailclient.IMAP4_SSL')
def test_mailclient_connect(mock_imap_class, mock_imap):
    """Test mailclient connection."""
    mock_imap_class.return_value = mock_imap
    
    client = Mailclient(imap_server='test.server.com', imap_port=993, 
                        username='test@example.com', password='password')
    client.connect('test.server.com', 993)
    
    mock_imap_class.assert_called_once_with('test.server.com', 993)
    assert client._connection is not None

@patch('cls.mailclient.IMAP4_SSL')
def test_mailclient_login(mock_imap_class, mock_imap):
    """Test mailclient login."""
    mock_imap_class.return_value = mock_imap
    
    client = Mailclient(imap_server='test.server.com', imap_port=993)
    client.connect('test.server.com', 993)
    result = client.login('test@example.com', 'password')
    
    mock_imap.login.assert_called_once_with('test@example.com', 'password')
    assert result == ('OK', [b'Login successful'])

def test_html_text_extractor():
    """Test HTML text extraction."""
    html = "<html><body><p>Test paragraph</p><div>Test div</div></body></html>"
    extractor = HTMLTextExtractor()
    text = extractor.extract_text_from_html(html)
    assert "Test paragraph" in text
    assert "Test div" in text
```

## Coverage Measurement

### Running Tests with Coverage

Use pytest-cov to measure code coverage:

```bash
pytest --cov=src tests/
```

For a detailed HTML report:

```bash
pytest --cov=src --cov-report=html tests/
```

### Coverage Targets

To achieve 70% overall coverage:
- Aim for 80-90% coverage of core components (database.py, document.py, mailclient.py)
- Aim for 70-80% coverage of processing modules
- Aim for 50-60% coverage of workflow modules
- Aim for 40-50% coverage of UI components

## Continuous Integration

### GitHub Actions Configuration

Create a GitHub Actions workflow to run tests automatically:

```yaml
# .github/workflows/tests.yml
name: Run Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    - name: Run tests
      run: |
        pytest --cov=src tests/
    - name: Upload coverage report
      uses: codecov/codecov-action@v3
```

## Conclusion

Implementing this testing strategy will provide a solid foundation for ensuring the reliability and maintainability of the RPA-Document-Fetcher application. By focusing on the core components first and gradually expanding test coverage, the team can achieve the 70% code coverage goal while maximizing the value of the testing effort.