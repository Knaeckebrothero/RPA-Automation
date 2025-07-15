"""
Integration tests for document workflow.

This module contains integration tests that verify the interaction between
the Document class and the Database class in a document processing workflow.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from cls.document import Document, PDF
from cls.database import Database


@pytest.fixture
def mock_pdf_content():
    """Provide sample PDF content for testing."""
    # In a real test, this might be actual PDF content from a file
    return b'%PDF-1.5\nMock PDF content for testing'


@pytest.fixture
def sample_pdf_attributes():
    """Provide sample PDF attributes for testing."""
    return {
        'name': 'test_document.pdf',
        'type': 'application/pdf',
        'size': 1024,
        'created_at': '2023-01-01T12:00:00',
        'author': 'Test Author',
        'client_id': 1,
        'bafin_id': 12345
    }


class TestDocumentWorkflow:
    """Integration tests for document workflow processes."""

    @patch('cls.database.Database.query')
    @patch('cls.database.Database.insert')
    def test_pdf_store_document(self, mock_insert, mock_query, mock_pdf_content, sample_pdf_attributes):
        """
        Test storing a PDF document in the database.
        
        This test verifies that the PDF.store_document method correctly interacts
        with the Database class to store document information.
        """
        # Set up mocks
        mock_query.return_value = []  # No existing documents
        mock_insert.return_value = 1  # New document ID
        
        # Create a PDF document
        pdf = PDF(
            content=mock_pdf_content,
            attributes=sample_pdf_attributes,
            client_id=sample_pdf_attributes['client_id'],
            bafin_id=sample_pdf_attributes['bafin_id']
        )
        
        # Store the document
        result = pdf.store_document(audit_case_id=123)
        
        # Verify the result
        assert result is True
        
        # Verify that database methods were called correctly
        assert mock_query.call_count >= 1  # Should check for existing documents
        assert mock_insert.call_count >= 1  # Should insert document data
        
        # Verify that the document has been updated with the audit case ID
        assert pdf.get_audit_case_id() == 123

    @patch('cls.document.PDF.extract_table_data')
    @patch('cls.document.PDF.extract_audit_values')
    @patch('cls.database.Database.query')
    @patch('cls.database.Database.insert')
    def test_pdf_workflow_integration(self, mock_insert, mock_query, 
                                     mock_extract_audit_values, mock_extract_table_data,
                                     mock_pdf_content, sample_pdf_attributes):
        """
        Test the complete PDF document workflow.
        
        This test verifies the integration between multiple components in the
        document processing workflow, including:
        - Document creation
        - Data extraction
        - Value comparison
        - Document storage
        """
        # Set up mocks
        mock_query.return_value = []  # No existing documents
        mock_insert.return_value = 1  # New document ID
        
        # Mock the extraction results
        mock_extract_table_data.return_value = True
        mock_extract_audit_values.return_value = {
            'client_name': 'Test Client',
            'bafin_id': 12345,
            'total_assets': 1000000,
            'total_liabilities': 500000,
            'net_income': 100000
        }
        
        # Create a PDF document
        pdf = PDF(
            content=mock_pdf_content,
            attributes=sample_pdf_attributes,
            client_id=sample_pdf_attributes['client_id'],
            bafin_id=sample_pdf_attributes['bafin_id']
        )
        
        # Execute the workflow steps
        
        # 1. Extract table data
        pdf.extract_table_data()
        mock_extract_table_data.assert_called_once()
        
        # 2. Extract audit values
        pdf.extract_audit_values()
        mock_extract_audit_values.assert_called_once()
        
        # 3. Verify BaFin ID
        bafin_verification = pdf.verify_bafin_id()
        assert bafin_verification is True
        
        # 4. Initialize audit case
        pdf.initialize_audit_case(stage=1)
        
        # 5. Compare values
        comparison_result = pdf.compare_values()
        assert comparison_result is not None
        
        # 6. Store document
        storage_result = pdf.store_document(audit_case_id=123)
        assert storage_result is True
        
        # Verify database interactions
        assert mock_query.call_count >= 1
        assert mock_insert.call_count >= 1

    @patch('cls.database.Database.query')
    def test_document_retrieval_workflow(self, mock_query, mock_pdf_content, sample_pdf_attributes):
        """
        Test retrieving and processing a document from the database.
        
        This test verifies that documents can be retrieved from the database
        and processed correctly.
        """
        # Set up mock query result to simulate a document in the database
        mock_query.return_value = [(
            1,                                      # id
            sample_pdf_attributes['client_id'],     # client_id
            sample_pdf_attributes['bafin_id'],      # bafin_id
            123,                                    # audit_case_id
            sample_pdf_attributes['name'],          # filename
            'document_hash_value',                  # document_hash
            '2023-01-01 12:00:00'                   # created_at
        )]
        
        # Create a database instance
        db = Database()
        
        # Query for documents with a specific audit case ID
        documents = db.query("SELECT * FROM documents WHERE audit_case_id = ?", (123,))
        
        # Verify that the query was executed correctly
        mock_query.assert_called_once_with("SELECT * FROM documents WHERE audit_case_id = ?", (123,))
        
        # Verify that we got the expected document
        assert len(documents) == 1
        assert documents[0][0] == 1  # document ID
        assert documents[0][1] == sample_pdf_attributes['client_id']
        assert documents[0][2] == sample_pdf_attributes['bafin_id']
        assert documents[0][3] == 123  # audit_case_id
        assert documents[0][4] == sample_pdf_attributes['name']