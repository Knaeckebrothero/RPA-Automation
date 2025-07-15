"""
Unit tests for the PDF class.

This module contains tests for the PDF class functionality, including
initialization, table data extraction, audit value extraction, and document storage.
"""
import os
import json
import pytest
import numpy as np
from unittest.mock import patch, mock_open, MagicMock, ANY

from cls.document import PDF


class TestPDF:
    """Test suite for the PDF class."""

    def test_pdf_initialization(self, sample_pdf_content, sample_pdf_attributes):
        """Test PDF initialization with content and attributes."""
        pdf = PDF(
            content=sample_pdf_content,
            attributes=sample_pdf_attributes,
            email_id=sample_pdf_attributes['email_id'],
            client_id=sample_pdf_attributes['client_id'],
            bafin_id=sample_pdf_attributes['BaFin-ID']
        )
        
        assert pdf.get_content() == sample_pdf_content
        assert pdf.get_attributes() == sample_pdf_attributes
        assert pdf.email_id == sample_pdf_attributes['email_id']
        assert pdf.client_id == sample_pdf_attributes['client_id']
        assert pdf.bafin_id == sample_pdf_attributes['BaFin-ID']
        assert pdf.document_hash is not None
        assert pdf._audit_values is None
        assert pdf._signature_page_index is None

    def test_pdf_initialization_with_audit_values(self, sample_pdf_content, sample_pdf_attributes):
        """Test PDF initialization with audit values."""
        audit_values = {
            'p033': 1000,
            'p034': 2000,
            'raw_p033': '1,000',
            'raw_p034': '2,000'
        }
        
        pdf = PDF(
            content=sample_pdf_content,
            attributes=sample_pdf_attributes,
            email_id=sample_pdf_attributes['email_id'],
            client_id=sample_pdf_attributes['client_id'],
            bafin_id=sample_pdf_attributes['BaFin-ID'],
            audit_values=audit_values
        )
        
        assert pdf._audit_values == audit_values

    def test_pdf_str_representation(self, sample_pdf_content, sample_pdf_attributes):
        """Test the string representation of a PDF."""
        pdf = PDF(
            content=sample_pdf_content,
            attributes=sample_pdf_attributes,
            email_id=sample_pdf_attributes['email_id'],
            client_id=sample_pdf_attributes['client_id'],
            bafin_id=sample_pdf_attributes['BaFin-ID']
        )
        
        str_repr = str(pdf)
        
        assert "PDF" in str_repr
        assert str(sample_pdf_attributes['email_id']) in str_repr
        assert str(sample_pdf_attributes['client_id']) in str_repr
        assert str(sample_pdf_attributes['BaFin-ID']) in str_repr

    def test_get_serializable_data(self, sample_pdf_content, sample_pdf_attributes):
        """Test the _get_serializable_data method."""
        pdf = PDF(
            content=sample_pdf_content,
            attributes=sample_pdf_attributes
        )
        
        data = pdf._get_serializable_data()
        
        assert data['document_type'] == 'PDF'
        assert data['attributes'] == sample_pdf_attributes
        assert 'content_path' in data
        assert '_audit_values' not in data  # Should not be included if None

    def test_get_serializable_data_with_audit_values(self, sample_pdf_content, sample_pdf_attributes):
        """Test the _get_serializable_data method with audit values."""
        audit_values = {
            'p033': 1000,
            'p034': 2000
        }
        
        pdf = PDF(
            content=sample_pdf_content,
            attributes=sample_pdf_attributes,
            audit_values=audit_values
        )
        
        data = pdf._get_serializable_data()
        
        assert data['_audit_values'] == audit_values

    @patch('processing.files.get_images_from_pdf')
    @patch('processing.ocr.create_ocr_reader')
    @patch('processing.ocr.ocr_cell')
    @patch('cv2.cvtColor')
    @patch('processing.detect.normalize_image_resolution')
    @patch('processing.detect.tables')
    @patch('processing.detect.rows')
    @patch('processing.detect.cells')
    def test_extract_table_data(
        self, mock_cells, mock_rows, mock_tables, mock_normalize, 
        mock_cvtColor, mock_ocr_cell, mock_create_ocr_reader, 
        mock_get_images_from_pdf, sample_pdf_content, sample_pdf_attributes
    ):
        """Test the extract_table_data method."""
        # Set up mocks
        mock_image = MagicMock()
        mock_get_images_from_pdf.return_value = [mock_image]
        
        mock_ocr_reader = MagicMock()
        mock_create_ocr_reader.return_value = mock_ocr_reader
        
        mock_normalize.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Create a mock contour
        mock_contour = np.array([[[0, 0]], [[100, 0]], [[100, 30]], [[0, 30]]])
        mock_tables.return_value = [mock_contour]
        
        mock_rows.return_value = [(0, 30)]
        mock_cells.return_value = [(0, 100)]
        mock_ocr_cell.return_value = "Sample OCR Text"
        
        # Create a PDF instance
        pdf = PDF(content=sample_pdf_content, attributes=sample_pdf_attributes)
        
        # Call the method
        pdf.extract_table_data()
        
        # Verify the mocks were called correctly
        mock_get_images_from_pdf.assert_called_once_with(sample_pdf_content)
        mock_create_ocr_reader.assert_called_once_with(language='de')
        mock_normalize.assert_called_once()
        mock_tables.assert_called_once()
        mock_rows.assert_called_once()
        mock_cells.assert_called_once()
        mock_ocr_cell.assert_called_once()

    def test_determine_signature_page_empty_data(self, sample_pdf_content, sample_pdf_attributes):
        """Test _determine_signature_page with empty data."""
        pdf = PDF(content=sample_pdf_content, attributes=sample_pdf_attributes)
        
        pdf._determine_signature_page([])
        
        assert pdf._signature_page_index == -1

    def test_determine_signature_page_with_two_tables(self, sample_pdf_content, sample_pdf_attributes):
        """Test _determine_signature_page with pages having two tables."""
        pdf = PDF(content=sample_pdf_content, attributes=sample_pdf_attributes)
        
        page_data = [
            {
                'page_index': 0,
                'num_tables': 2,
                'total_area': 6000,
                'max_area': 4000,
                'min_area': 2000
            },
            {
                'page_index': 1,
                'num_tables': 2,
                'total_area': 5000,
                'max_area': 3000,
                'min_area': 2000
            }
        ]
        
        pdf._determine_signature_page(page_data)
        
        # Should select the last page with two tables
        assert pdf._signature_page_index == 1

    def test_determine_signature_page_largest_smallest_tables(self, sample_pdf_content, sample_pdf_attributes):
        """Test _determine_signature_page with a page having both largest and smallest tables."""
        pdf = PDF(content=sample_pdf_content, attributes=sample_pdf_attributes)
        
        page_data = [
            {
                'page_index': 0,
                'num_tables': 2,
                'total_area': 6000,
                'max_area': 5000,
                'min_area': 1000
            },
            {
                'page_index': 1,
                'num_tables': 3,
                'total_area': 7000,
                'max_area': 4000,
                'min_area': 1500
            }
        ]
        
        pdf._determine_signature_page(page_data)
        
        # Should select the page with both largest and smallest tables
        assert pdf._signature_page_index == 0

    def test_determine_signature_page_default_to_largest(self, sample_pdf_content, sample_pdf_attributes):
        """Test _determine_signature_page defaulting to the page with the largest table."""
        pdf = PDF(content=sample_pdf_content, attributes=sample_pdf_attributes)
        
        page_data = [
            {
                'page_index': 0,
                'num_tables': 1,
                'total_area': 3000,
                'max_area': 3000,
                'min_area': 3000
            },
            {
                'page_index': 1,
                'num_tables': 1,
                'total_area': 5000,
                'max_area': 5000,
                'min_area': 5000
            }
        ]
        
        pdf._determine_signature_page(page_data)
        
        # Should select the page with the largest table
        assert pdf._signature_page_index == 1

    @patch('processing.detect.bafin_id')
    def test_process_row_data_multiple_cells(self, mock_bafin_id, sample_pdf_content, sample_pdf_attributes):
        """Test _process_row_data with multiple cells."""
        pdf = PDF(content=sample_pdf_content, attributes=sample_pdf_attributes)
        
        row_data = ["Key1", "Key2", "Value"]
        pdf._process_row_data(row_data)
        
        # Should add "Key1 Key2" as key and "Value" as value
        assert pdf.get_attributes("Key1 Key2") == "Value"

    @patch('processing.detect.bafin_id')
    def test_process_row_data_single_cell_with_colon(self, mock_bafin_id, sample_pdf_content, sample_pdf_attributes):
        """Test _process_row_data with a single cell containing a colon."""
        pdf = PDF(content=sample_pdf_content, attributes=sample_pdf_attributes)
        
        row_data = ["Key: Value"]
        pdf._process_row_data(row_data)
        
        # Should split at the colon and add "Key" as key and "Value" as value
        assert pdf.get_attributes("Key") == "Value"

    @patch('processing.detect.bafin_id')
    def test_process_row_data_single_cell_too_long(self, mock_bafin_id, sample_pdf_content, sample_pdf_attributes):
        """Test _process_row_data with a single cell that's too long."""
        pdf = PDF(content=sample_pdf_content, attributes=sample_pdf_attributes)
        
        # Create a cell with more than 100 characters
        row_data = ["A" * 101]
        pdf._process_row_data(row_data)
        
        # Should skip the row and not add any attributes
        assert pdf.get_attributes("A") is None

    @patch('processing.detect.bafin_id')
    def test_process_row_data_extract_bafin_id(self, mock_bafin_id, sample_pdf_content):
        """Test _process_row_data extracting a BaFin ID."""
        # Create a PDF without a BaFin ID
        pdf = PDF(content=sample_pdf_content)
        
        # Set up the mock to return a BaFin ID
        mock_bafin_id.return_value = 12345
        
        # Mock the verify_bafin_id method to return a client ID
        with patch.object(pdf, 'verify_bafin_id', return_value=1):
            row_data = ["Some text with BaFin ID"]
            pdf._process_row_data(row_data)
            
            # Should extract the BaFin ID and add it to attributes
            assert pdf.bafin_id == 12345
            assert pdf.get_attributes("BaFin-ID") == 12345

    @patch('cls.database.Database')
    def test_verify_bafin_id(self, mock_db_class, sample_pdf_content, sample_pdf_attributes):
        """Test verify_bafin_id method."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.return_value.get_instance.return_value = mock_db
        mock_db.query.return_value = [(1,)]  # Return a client ID
        
        # Create a PDF without a BaFin ID
        pdf = PDF(content=sample_pdf_content)
        
        # Call the method
        result = pdf.verify_bafin_id(12345)
        
        # Verify the result
        assert result == 1
        assert pdf.bafin_id == 12345
        assert pdf.client_id == 1
        assert pdf.get_attributes("BaFin-ID") == 12345
        assert pdf.get_attributes("client_id") == 1

    @patch('cls.database.Database')
    def test_verify_bafin_id_not_found(self, mock_db_class, sample_pdf_content):
        """Test verify_bafin_id when BaFin ID is not found in database."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.return_value.get_instance.return_value = mock_db
        mock_db.query.return_value = []  # No client found
        
        # Create a PDF without a BaFin ID
        pdf = PDF(content=sample_pdf_content)
        
        # Call the method
        result = pdf.verify_bafin_id(12345)
        
        # Verify the result
        assert result is None
        assert pdf.get_attributes("BaFin-ID") is None

    @patch('cls.database.Database')
    def test_initialize_audit_case(self, mock_db_class, sample_pdf_content, sample_pdf_attributes):
        """Test initialize_audit_case method."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.return_value.get_instance.return_value = mock_db
        mock_db.query.return_value = [(1,)]  # Return a client ID
        mock_db.insert.return_value = 123  # Return an audit case ID
        
        # Create a PDF with a BaFin ID
        pdf = PDF(
            content=sample_pdf_content,
            bafin_id=sample_pdf_attributes['BaFin-ID'],
            email_id=sample_pdf_attributes['email_id']
        )
        
        # Call the method
        result = pdf.initialize_audit_case(stage=2)
        
        # Verify the result
        assert result == 123
        mock_db.query.assert_called_once_with("SELECT id FROM client WHERE bafin_id = ? ", (sample_pdf_attributes['BaFin-ID'],))
        mock_db.insert.assert_called_once()

    @patch('cls.database.Database')
    def test_initialize_audit_case_no_client(self, mock_db_class, sample_pdf_content, sample_pdf_attributes):
        """Test initialize_audit_case when no client is found."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.return_value.get_instance.return_value = mock_db
        mock_db.query.return_value = []  # No client found
        
        # Create a PDF with a BaFin ID
        pdf = PDF(
            content=sample_pdf_content,
            bafin_id=sample_pdf_attributes['BaFin-ID'],
            email_id=sample_pdf_attributes['email_id']
        )
        
        # Call the method
        result = pdf.initialize_audit_case()
        
        # Verify the result
        assert result is None
        mock_db.insert.assert_not_called()

    @patch('cls.database.Database')
    def test_get_audit_stage(self, mock_db_class, sample_pdf_content, sample_pdf_attributes):
        """Test get_audit_stage method."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.return_value.get_instance.return_value = mock_db
        mock_db.query.side_effect = [
            [(1,)],  # First call for client ID
            [(2,)]   # Second call for stage
        ]
        
        # Create a PDF with a BaFin ID
        pdf = PDF(
            content=sample_pdf_content,
            bafin_id=sample_pdf_attributes['BaFin-ID']
        )
        
        # Call the method
        result = pdf.get_audit_stage()
        
        # Verify the result
        assert result == 2

    @patch('cls.database.Database')
    def test_get_audit_case_id(self, mock_db_class, sample_pdf_content, sample_pdf_attributes):
        """Test get_audit_case_id method."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.return_value.get_instance.return_value = mock_db
        mock_db.query.side_effect = [
            [(1,)],    # First call for client ID
            [(123,)]   # Second call for audit case ID
        ]
        
        # Create a PDF with a BaFin ID
        pdf = PDF(
            content=sample_pdf_content,
            bafin_id=sample_pdf_attributes['BaFin-ID']
        )
        
        # Call the method
        result = pdf.get_audit_case_id()
        
        # Verify the result
        assert result == 123
        assert pdf.audit_case_id == 123
        assert pdf.get_attributes("audit_case_id") == 123

    @patch('cls.database.Database')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.join')
    @patch('os.makedirs')
    def test_store_document(self, mock_makedirs, mock_join, mock_open, mock_db_class, 
                           sample_pdf_content, sample_pdf_attributes):
        """Test store_document method."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.return_value.get_instance.return_value = mock_db
        mock_db.query.return_value = []  # No existing document
        
        # Set up the mock path
        mock_join.return_value = "test/path/document.pdf"
        
        # Create a PDF
        pdf = PDF(
            content=sample_pdf_content,
            attributes=sample_pdf_attributes,
            email_id=sample_pdf_attributes['email_id']
        )
        
        # Mock the _generate_document_hash method
        with patch.object(pdf, '_generate_document_hash', return_value=True):
            # Call the method
            result = pdf.store_document(audit_case_id=123)
            
            # Verify the result
            assert result is True
            mock_db.query.assert_called_once()
            mock_db.insert.assert_called_once()
            mock_open.assert_called()

    @patch('cls.database.Database')
    def test_store_document_existing(self, mock_db_class, sample_pdf_content, sample_pdf_attributes):
        """Test store_document when document already exists."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.return_value.get_instance.return_value = mock_db
        mock_db.query.return_value = [("existing/path.pdf",)]  # Existing document
        
        # Create a PDF with a document hash
        pdf = PDF(
            content=sample_pdf_content,
            attributes=sample_pdf_attributes,
            document_hash="test_hash"
        )
        
        # Call the method
        result = pdf.store_document(audit_case_id=123)
        
        # Verify the result
        assert result is True
        mock_db.insert.assert_not_called()

    @patch('builtins.open', new_callable=mock_open)
    def test_extract_audit_values(self, mock_open, sample_pdf_content, sample_pdf_attributes):
        """Test extract_audit_values method."""
        # Create mock JSON data for regex patterns
        mock_json_data = {
            "p033": [".*total assets.*", ".*assets.*total.*"],
            "p034": [".*total liabilities.*", ".*liabilities.*total.*"]
        }
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_json_data)
        
        # Create a PDF with attributes that should match the patterns
        attributes = sample_pdf_attributes.copy()
        attributes.update({
            "Total Assets": "1,000,000",
            "Total Liabilities": "500,000"
        })
        
        pdf = PDF(
            content=sample_pdf_content,
            attributes=attributes
        )
        
        # Call the method
        result = pdf.extract_audit_values()
        
        # Verify the result
        assert "p033" in result
        assert "p034" in result
        assert "raw_p033" in result
        assert "raw_p034" in result
        assert result["raw_p033"] == "1,000,000"
        assert result["raw_p034"] == "500,000"

    @patch('cls.database.Database')
    def test_compare_values(self, mock_db_class, sample_pdf_content, sample_pdf_attributes):
        """Test compare_values method."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.return_value.get_instance.return_value = mock_db
        
        # Mock the query result with client data
        client_data = [1]  # Client ID
        for i in range(15):
            client_data.append(i * 1000)  # Add 15 values for the fields
        
        mock_db.query.return_value = [tuple(client_data)]
        
        # Create a PDF with a BaFin ID and audit values
        pdf = PDF(
            content=sample_pdf_content,
            bafin_id=sample_pdf_attributes['BaFin-ID'],
            audit_values={
                "p033": 0,
                "p034": 1000,
                "p035": 2000,
                "p036": 3000,
                "ab2s1n01": 4000,
                "ab2s1n02": 5000,
                "ab2s1n03": 6000,
                "ab2s1n04": 7000,
                "ab2s1n05": 8000,
                "ab2s1n06": 9000,
                "ab2s1n07": 10000,
                "ab2s1n08": 11000,
                "ab2s1n09": 12000,
                "ab2s1n10": 13000,
                "ab2s1n11": 14000,
                "raw_p033": "0",
                "raw_p034": "1,000",
                "raw_p035": "2,000"
            }
        )
        
        # Call the method
        result = pdf.compare_values()
        
        # Verify the result
        assert result is True
        assert pdf._audit_values["match_percentage"] == 100.0
        assert pdf._audit_values["matched_required_fields"] == 15
        assert pdf._audit_values["total_required_fields"] == 15

    @patch('cls.database.Database')
    def test_compare_values_with_mismatches(self, mock_db_class, sample_pdf_content, sample_pdf_attributes):
        """Test compare_values method with mismatches."""
        # Set up the mock database
        mock_db = MagicMock()
        mock_db_class.return_value.get_instance.return_value = mock_db
        
        # Mock the query result with client data
        client_data = [1]  # Client ID
        for i in range(15):
            client_data.append(i * 1000)  # Add 15 values for the fields
        
        mock_db.query.return_value = [tuple(client_data)]
        
        # Create a PDF with a BaFin ID and audit values with some mismatches
        pdf = PDF(
            content=sample_pdf_content,
            bafin_id=sample_pdf_attributes['BaFin-ID'],
            audit_values={
                "p033": 0,
                "p034": 1000,
                "p035": 9999,  # Mismatch
                "p036": 3000,
                "ab2s1n01": 4000,
                "ab2s1n02": 5000,
                "ab2s1n03": 9999,  # Mismatch
                "ab2s1n04": 7000,
                "ab2s1n05": 8000,
                "ab2s1n06": 9000,
                "ab2s1n07": 10000,
                "ab2s1n08": 11000,
                "ab2s1n09": 12000,
                "ab2s1n10": 13000,
                "ab2s1n11": 14000,
                "raw_p033": "0",
                "raw_p034": "1,000",
                "raw_p035": "9,999"
            }
        )
        
        # Call the method
        result = pdf.compare_values()
        
        # Verify the result
        assert result is False
        assert pdf._audit_values["match_percentage"] < 100.0
        assert pdf._audit_values["matched_required_fields"] == 13
        assert pdf._audit_values["total_required_fields"] == 15
        assert pdf._audit_values["mismatched_fields"] == 2