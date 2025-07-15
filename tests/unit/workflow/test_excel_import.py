"""
Unit tests for the excel_import workflow module.

This module contains tests for the ExcelImporter class and its methods for
importing audit season data from Excel files.
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
from io import BytesIO

from src.workflow.excel_import import ExcelImporter


class TestExcelImporter:
    """Test suite for the ExcelImporter class."""

    def test_init(self):
        """Test ExcelImporter initialization."""
        # Setup & Execute
        importer = ExcelImporter()

        # Assert
        assert importer.db is not None
        assert importer.results == {'success': [], 'errors': []}

    @patch('src.workflow.excel_import.Database')
    def test_init_with_database(self, mock_db_class):
        """Test ExcelImporter initialization with a provided database."""
        # Setup
        mock_db = MagicMock()

        # Execute
        importer = ExcelImporter(database=mock_db)

        # Assert
        assert importer.db is mock_db
        assert importer.results == {'success': [], 'errors': []}

    @patch('pandas.read_excel')
    @patch('src.workflow.excel_import.ExcelImporter._process_row')
    @patch('src.workflow.excel_import.ExcelImporter.validate_excel_structure')
    def test_import_audit_season_with_valid_data(self, mock_validate, mock_process_row, mock_read_excel):
        """Test importing audit season with valid data."""
        # Setup
        mock_df = pd.DataFrame({
            'Client Name': ['Test Client 1', 'Test Client 2'],
            'BaFin ID': ['12345', '67890'],
            'Contact Email': ['test1@example.com', 'test2@example.com'],
            'Auditor Name': ['Auditor 1', 'Auditor 2'],
            'Auditor Email': ['auditor1@example.com', 'auditor2@example.com'],
            'Auditor Role': ['primary', 'secondary']
        })
        mock_read_excel.return_value = mock_df
        mock_validate.return_value = True
        mock_process_row.side_effect = [None, None]  # No errors

        # Execute
        importer = ExcelImporter()
        result = importer.import_audit_season('test.xlsx', granted_by=1)

        # Assert
        assert result == {'success': [], 'errors': []}
        mock_validate.assert_called_once()
        assert mock_process_row.call_count == 2

    @patch('pandas.read_excel')
    @patch('src.workflow.excel_import.ExcelImporter.validate_excel_structure')
    def test_import_audit_season_with_invalid_structure(self, mock_validate, mock_read_excel):
        """Test importing audit season with invalid Excel structure."""
        # Setup
        mock_validate.return_value = False

        # Execute
        importer = ExcelImporter()
        with pytest.raises(ValueError) as excinfo:
            importer.import_audit_season('test.xlsx', granted_by=1)

        # Assert
        assert "Invalid Excel structure" in str(excinfo.value)
        mock_validate.assert_called_once()
        mock_read_excel.assert_not_called()

    @patch('src.workflow.excel_import.ExcelImporter._find_or_create_user')
    @patch('src.workflow.excel_import.Database')
    def test_process_row_success(self, mock_db_class, mock_find_user):
        """Test processing a row successfully."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = []  # No existing client
        mock_db.insert.side_effect = [1, 2]  # client_id, audit_case_id

        mock_find_user.return_value = {'id': 3, 'email': 'auditor@example.com'}

        row = pd.Series({
            'Client Name': 'Test Client',
            'BaFin ID': '12345',
            'Contact Email': 'client@example.com',
            'Auditor Name': 'Test Auditor',
            'Auditor Email': 'auditor@example.com',
            'Auditor Role': 'primary'
        })

        # Execute
        importer = ExcelImporter(database=mock_db)
        importer._process_row(row, 0, granted_by=1)

        # Assert
        assert len(importer.results['success']) == 1
        assert len(importer.results['errors']) == 0
        mock_db.insert.assert_called()
        mock_find_user.assert_called_once()

    @patch('src.workflow.excel_import.ExcelImporter._find_or_create_user')
    @patch('src.workflow.excel_import.Database')
    def test_process_row_existing_client(self, mock_db_class, mock_find_user):
        """Test processing a row with an existing client."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = [(1,)]  # Existing client
        mock_db.insert.return_value = 2  # audit_case_id

        mock_find_user.return_value = {'id': 3, 'email': 'auditor@example.com'}

        row = pd.Series({
            'Client Name': 'Test Client',
            'BaFin ID': '12345',
            'Contact Email': 'client@example.com',
            'Auditor Name': 'Test Auditor',
            'Auditor Email': 'auditor@example.com',
            'Auditor Role': 'primary'
        })

        # Execute
        importer = ExcelImporter(database=mock_db)
        importer._process_row(row, 0, granted_by=1)

        # Assert
        assert len(importer.results['success']) == 1
        assert len(importer.results['errors']) == 0
        mock_db.insert.assert_called_once()  # Only insert audit_case
        mock_find_user.assert_called_once()

    @patch('src.workflow.excel_import.ExcelImporter._find_or_create_user')
    @patch('src.workflow.excel_import.Database')
    def test_process_row_error(self, mock_db_class, mock_find_user):
        """Test processing a row with an error."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.side_effect = Exception("Database error")

        row = pd.Series({
            'Client Name': 'Test Client',
            'BaFin ID': '12345',
            'Contact Email': 'client@example.com',
            'Auditor Name': 'Test Auditor',
            'Auditor Email': 'auditor@example.com',
            'Auditor Role': 'primary'
        })

        # Execute
        importer = ExcelImporter(database=mock_db)
        importer._process_row(row, 0, granted_by=1)

        # Assert
        assert len(importer.results['success']) == 0
        assert len(importer.results['errors']) == 1
        assert "Database error" in importer.results['errors'][0]
        mock_find_user.assert_not_called()

    @patch('workflow.excel_import.ExcelImporter._find_user')
    @patch('workflow.excel_import.ExcelImporter._generate_username')
    @patch('workflow.excel_import.sec.generate_secure_password')
    @patch('workflow.excel_import.sec.hash_password')
    @patch('workflow.excel_import.AccessControl')
    @patch('workflow.excel_import.Database')
    def test_find_or_create_user_new(self, mock_db_class, mock_ac, mock_hash, 
                                    mock_gen_pwd, mock_gen_user, mock_find_user):
        """Test finding or creating a user when the user doesn't exist."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db

        mock_find_user.return_value = None  # User not found
        mock_gen_user.return_value = "testuser"
        mock_gen_pwd.return_value = "password123"
        mock_hash.return_value = ("hashed_password", "salt")
        mock_db.insert.return_value = 1  # user_id

        # Execute
        importer = ExcelImporter(database=mock_db)
        result = importer._find_or_create_user("test@example.com", "primary", 0)

        # Assert
        assert result['id'] == 1
        assert result['email'] == "test@example.com"
        mock_find_user.assert_called_once_with("test@example.com")
        mock_gen_user.assert_called_once()
        mock_gen_pwd.assert_called_once()
        mock_hash.assert_called_once_with("password123")
        mock_db.insert.assert_called_once()

    @patch('workflow.excel_import.ExcelImporter._find_user')
    @patch('workflow.excel_import.Database')
    def test_find_or_create_user_existing(self, mock_db_class, mock_find_user):
        """Test finding or creating a user when the user exists."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db

        mock_find_user.return_value = {'id': 1, 'email': 'test@example.com', 'role': 'primary'}

        # Execute
        importer = ExcelImporter(database=mock_db)
        result = importer._find_or_create_user("test@example.com", "primary", 0)

        # Assert
        assert result['id'] == 1
        assert result['email'] == "test@example.com"
        mock_find_user.assert_called_once_with("test@example.com")
        mock_db.insert.assert_not_called()

    def test_generate_username(self):
        """Test generating a username from a name."""
        # Setup & Execute
        importer = ExcelImporter()
        username = importer._generate_username("John Doe")

        # Assert
        assert username.startswith("jdoe")
        assert "@example.com" in username

    @patch('workflow.excel_import.Database')
    def test_find_user(self, mock_db_class):
        """Test finding a user by email."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = [(1, "test@example.com", "primary")]

        # Execute
        importer = ExcelImporter(database=mock_db)
        result = importer._find_user("test@example.com")

        # Assert
        assert result['id'] == 1
        assert result['email'] == "test@example.com"
        assert result['role'] == "primary"
        mock_db.query.assert_called_once()

    @patch('workflow.excel_import.Database')
    def test_find_user_not_found(self, mock_db_class):
        """Test finding a user that doesn't exist."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = []

        # Execute
        importer = ExcelImporter(database=mock_db)
        result = importer._find_user("nonexistent@example.com")

        # Assert
        assert result is None
        mock_db.query.assert_called_once()

    def test_get_results(self):
        """Test getting the results of an import operation."""
        # Setup
        importer = ExcelImporter()
        importer.results = {
            'success': ['Success 1', 'Success 2'],
            'errors': ['Error 1']
        }

        # Execute
        result = importer._get_results()

        # Assert
        assert result == importer.results
        assert len(result['success']) == 2
        assert len(result['errors']) == 1

    @patch('pandas.read_excel')
    def test_validate_excel_structure_valid(self, mock_read_excel):
        """Test validating a valid Excel structure."""
        # Setup
        mock_df = pd.DataFrame({
            'Client Name': ['Test'],
            'BaFin ID': ['12345'],
            'Contact Email': ['test@example.com'],
            'Auditor Name': ['Auditor'],
            'Auditor Email': ['auditor@example.com'],
            'Auditor Role': ['primary']
        })
        mock_read_excel.return_value = mock_df

        # Execute
        result = ExcelImporter.validate_excel_structure('test.xlsx')

        # Assert
        assert result is True
        mock_read_excel.assert_called_once()

    @patch('pandas.read_excel')
    def test_validate_excel_structure_invalid(self, mock_read_excel):
        """Test validating an invalid Excel structure."""
        # Setup
        mock_df = pd.DataFrame({
            'Client Name': ['Test'],
            'BaFin ID': ['12345'],
            # Missing required columns
        })
        mock_read_excel.return_value = mock_df

        # Execute
        result = ExcelImporter.validate_excel_structure('test.xlsx')

        # Assert
        assert result is False
        mock_read_excel.assert_called_once()
