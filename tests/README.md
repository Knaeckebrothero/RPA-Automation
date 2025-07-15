# Testing Guide for RPA-Document-Fetcher

This guide provides comprehensive information on testing the RPA-Document-Fetcher application. It is intended for developers who are new to the project and need to understand how to run, write, and maintain tests.

## Quick Start

To run all tests immediately:

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run tests with coverage
pytest --cov=src tests/
```

## Test Organization

Tests are organized in the following directory structure:

```
tests/
├── conftest.py                  # Shared fixtures
├── README.md                    # This guide
├── unit/                        # Unit tests
│   ├── cls/                     # Tests for cls module
│   │   ├── test_database.py     # Database class tests
│   │   ├── test_document.py     # Document class tests
│   │   └── ...
│   ├── processing/              # Tests for processing module
│   │   ├── test_detect.py
│   │   ├── test_files.py
│   │   └── test_ocr.py
│   ├── ui/                      # Tests for ui module
│   │   ├── test_navbar.py
│   │   ├── test_pages.py
│   │   └── ...
│   └── workflow/                # Tests for workflow module
│       ├── test_audit.py
│       ├── test_excel_import.py
│       └── test_security.py
└── integration/                 # Integration tests
    ├── test_document_workflow.py
    └── test_email_processing.py
```

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test the interaction between components

## Running Tests

### Running All Tests

```bash
pytest
```

### Running Tests by Category

```bash
# Run all unit tests
pytest tests/unit/

# Run all integration tests
pytest tests/integration/

# Run tests for a specific module
pytest tests/unit/cls/
pytest tests/unit/processing/
pytest tests/unit/ui/
pytest tests/unit/workflow/
```

### Running Specific Test Files

```bash
# Run tests in a specific file
pytest tests/unit/cls/test_database.py

# Run a specific test class
pytest tests/unit/cls/test_database.py::TestDatabase

# Run a specific test method
pytest tests/unit/cls/test_database.py::TestDatabase::test_database_initialization
```

### Running Tests with Coverage

```bash
# Generate coverage report for all tests
pytest --cov=src tests/

# Generate detailed HTML coverage report
pytest --cov=src --cov-report=html tests/

# Generate coverage for a specific module
pytest --cov=src.cls tests/unit/cls/
```

### Running Tests with Verbose Output

```bash
pytest -v
```

### Running Tests with Print Statements

```bash
pytest -s
```

## Writing New Tests

### Basic Test Structure

Tests in this project follow the pytest framework. Here's a basic structure for a test file:

```python
"""
Unit tests for the [Component] class.

This module contains tests for the [Component] class functionality.
"""
import pytest
from unittest.mock import patch, MagicMock

from module.path import Component

class TestComponent:
    """Test suite for the Component class."""

    def test_component_initialization(self):
        """Test that Component initializes correctly."""
        component = Component()
        assert component.attribute == expected_value

    @patch('external.dependency')
    def test_component_method(self, mock_dependency):
        """Test a method that has external dependencies."""
        mock_dependency.return_value = mock_value

        component = Component()
        result = component.method()

        assert result == expected_result
        mock_dependency.assert_called_once_with(expected_args)
```

### Using Fixtures

Fixtures are a powerful feature of pytest that allow you to set up preconditions for your tests:

```python
@pytest.fixture
def sample_component():
    """Create a sample component for testing."""
    return Component(param1="value1", param2="value2")

def test_component_method(sample_component):
    """Test using the fixture."""
    result = sample_component.method()
    assert result == expected_result
```

### Testing Different Types of Components

#### Testing Database Operations

```python
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

#### Testing UI Components

```python
@patch('streamlit.sidebar')
def test_navbar_render(mock_sidebar):
    """Test navbar rendering."""
    navbar = Navbar()
    navbar.render()

    # Verify that the sidebar methods were called
    mock_sidebar.title.assert_called_once_with("Navigation")
    assert mock_sidebar.button.call_count >= 1
```

#### Testing Document Processing

```python
def test_document_processing(sample_document_content, sample_document_attributes):
    """Test document processing."""
    document = Document(content=sample_document_content, attributes=sample_document_attributes)
    result = document.process()

    assert result is True
    assert document.get_attributes('processed') is True
```

### Testing Error Handling

```python
def test_error_handling():
    """Test that errors are handled correctly."""
    component = Component()

    with pytest.raises(ValueError) as excinfo:
        component.method_that_raises_error()

    assert "Expected error message" in str(excinfo.value)
```

## Test Fixtures

The project uses a variety of fixtures defined in `conftest.py` to simplify test setup. Here are some of the most useful fixtures:

### Database Fixtures

```python
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
```

### Document Fixtures

```python
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
```

### Processing Fixtures

```python
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
```

### Email Fixtures

```python
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
```

## Best Practices

### Test Isolation

Each test should be independent and not rely on the state from other tests. Use fixtures to set up and tear down test environments.

```python
# Good: Test is isolated and uses fixtures
def test_isolated_example(mock_database):
    # Test uses a fresh mock_database for each test
    result = process_data(mock_database)
    assert result is True

# Bad: Test depends on global state
global_db = None

def setup_module():
    global global_db
    global_db = Database()

def test_non_isolated_example():
    # Test depends on global_db being set up correctly
    result = process_data(global_db)
    assert result is True
```

### Mocking External Dependencies

Use `pytest-mock` to mock database connections, file operations, and external APIs:

```python
@patch('requests.get')
def test_api_call(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'key': 'value'}

    result = call_api()

    assert result == {'key': 'value'}
    mock_get.assert_called_once_with('https://api.example.com/endpoint')
```

### Test Naming Conventions

- Test files should be named `test_*.py`
- Test classes should be named `Test*`
- Test methods should be named `test_*`
- Test method names should clearly describe what is being tested

```python
# Good: Clear test names
def test_database_connection_succeeds():
    # Test code

def test_database_connection_fails_with_invalid_credentials():
    # Test code

# Bad: Unclear test names
def test_db_conn():
    # Test code

def test_db_conn_2():
    # Test code
```

### Comprehensive Testing

Tests should cover:

1. **Normal Operation**: Test that functions work correctly with valid inputs
2. **Edge Cases**: Test boundary conditions and special cases
3. **Error Handling**: Test that errors are handled correctly

```python
# Testing normal operation
def test_divide_normal():
    assert divide(10, 2) == 5

# Testing edge cases
def test_divide_edge_cases():
    assert divide(0, 5) == 0
    assert divide(-10, 2) == -5
    assert divide(10, -2) == -5

# Testing error handling
def test_divide_by_zero():
    with pytest.raises(ValueError) as excinfo:
        divide(10, 0)
    assert "Cannot divide by zero" in str(excinfo.value)
```

## Troubleshooting

### Common Issues and Solutions

#### Tests Failing Due to Import Errors

**Issue**: `ModuleNotFoundError: No module named 'module_name'`

**Solution**: 
- Ensure that the project root is in your Python path
- Check that you've installed all required dependencies
- Make sure you're running tests from the project root

```python
# Add this to conftest.py if not already present
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
```

#### Tests Failing Due to Missing Fixtures

**Issue**: `fixture 'fixture_name' not found`

**Solution**:
- Check that the fixture is defined in `conftest.py` or in the test file
- Ensure that the fixture name is spelled correctly
- Make sure the fixture is accessible to the test (in the same file or in conftest.py)

#### Tests Failing Due to Mocking Issues

**Issue**: `AssertionError: Expected 'mock_method' to have been called once. Called 0 times.`

**Solution**:
- Check that you're mocking the correct path
- Ensure that the mock is set up before the code under test is executed
- Verify that the code under test is actually calling the method you're mocking

```python
# Correct way to mock a method
@patch('module.Class.method')  # Use the full import path
def test_example(mock_method):
    # Test code that calls module.Class.method
    mock_method.assert_called_once()

# Incorrect way to mock a method
@patch('Class.method')  # Incomplete path
def test_example(mock_method):
    # This won't work if the code imports from module.Class
    mock_method.assert_called_once()
```

#### Tests Running Slowly

**Issue**: Tests take a long time to run

**Solution**:
- Use mocks to avoid actual network calls, database operations, or file I/O
- Run only the tests you need using pytest's filtering options
- Use pytest-xdist to run tests in parallel: `pytest -n auto`

#### Tests Failing Intermittently

**Issue**: Tests sometimes pass and sometimes fail

**Solution**:
- Check for race conditions or timing issues
- Ensure tests are properly isolated and don't depend on each other
- Look for external dependencies that might be unreliable
- Add more logging to identify the issue: `pytest -v --log-cli-level=DEBUG`

### Getting Help

If you're still having trouble with tests, you can:

1. Check the pytest documentation: https://docs.pytest.org/
2. Look at existing test files for examples
3. Ask for help from other team members
4. Add detailed logging to your tests to understand what's happening

## Conclusion

Testing is a critical part of maintaining the RPA-Document-Fetcher application. By following the guidelines in this document, you can write effective tests that help ensure the reliability and maintainability of the codebase.

Remember that tests should be:
- Fast
- Independent
- Repeatable
- Self-validating
- Thorough

Happy testing!
