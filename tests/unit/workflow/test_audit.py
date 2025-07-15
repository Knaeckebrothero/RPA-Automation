"""
Unit tests for the audit workflow module.

This module contains tests for the audit workflow functionality, including
email processing, audit case management, and certificate generation.
"""
from unittest.mock import patch, MagicMock
import pandas as pd
import os

from workflow.audit import (
    get_emails, assess_emails, process_audit_case, fetch_new_emails,
    generate_certificate, get_client_info, get_document_info,
    update_audit_case, send_document_confirmation_email
)


class TestAuditWorkflow:
    """Test suite for the audit workflow module."""

    @patch('src.workflow.audit.Database')
    def test_get_emails(self, mock_db_class):
        """Test retrieving emails from the database."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = [
            (1, 'test@example.com', 'Test Subject', '2023-01-01', 0),
            (2, 'test2@example.com', 'Test Subject 2', '2023-01-02', 0)
        ]

        # Execute
        result = get_emails()

        # Assert
        assert len(result) == 2
        assert result.iloc[0]['id'] == 1
        assert result.iloc[0]['sender'] == 'test@example.com'
        assert result.iloc[1]['id'] == 2
        assert result.iloc[1]['sender'] == 'test2@example.com'
        mock_db.query.assert_called_once()

    @patch('src.workflow.audit.Database')
    def test_get_emails_with_excluded_ids(self, mock_db_class):
        """Test retrieving emails with excluded IDs."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = [
            (2, 'test2@example.com', 'Test Subject 2', '2023-01-02', 0)
        ]

        # Execute
        result = get_emails(excluded_ids=[1])

        # Assert
        assert len(result) == 1
        assert result.iloc[0]['id'] == 2
        mock_db.query.assert_called_once()

    @patch('src.workflow.audit.process_audit_case')
    def test_assess_emails_with_valid_email(self, mock_process):
        """Test assessing emails with a valid email."""
        # Setup
        emails_df = pd.DataFrame({
            'id': [1],
            'sender': ['test@example.com'],
            'subject': ['Test Subject'],
            'date': ['2023-01-01'],
            'processed': [0]
        })
        mock_process.return_value = True

        # Execute
        result = assess_emails(emails_df)

        # Assert
        assert result == 1
        mock_process.assert_called_once()

    @patch('src.workflow.audit.process_audit_case')
    def test_assess_emails_with_invalid_email(self, mock_process):
        """Test assessing emails with an invalid email."""
        # Setup
        emails_df = pd.DataFrame({
            'id': [1],
            'sender': ['invalid@example.com'],
            'subject': ['Invalid Subject'],
            'date': ['2023-01-01'],
            'processed': [0]
        })
        mock_process.side_effect = Exception("Invalid email")

        # Execute
        result = assess_emails(emails_df)

        # Assert
        assert result == 0
        mock_process.assert_called_once()

    @patch('src.workflow.audit.PDF')
    @patch('src.workflow.audit.Database')
    def test_process_audit_case(self, mock_db_class, mock_pdf_class):
        """Test processing an audit case."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_pdf = MagicMock()
        mock_pdf_class.return_value = mock_pdf
        mock_pdf.store_document.return_value = 123
        mock_pdf.extract_audit_values.return_value = {'key': 'value'}
        mock_pdf.extract_table_data.return_value = [['data']]
        mock_pdf.check_document_completeness.return_value = True
        mock_pdf.check_for_signature.return_value = True
        mock_pdf.compare_values.return_value = True

        # Execute
        result = process_audit_case(mock_pdf)

        # Assert
        assert result is True
        mock_pdf.store_document.assert_called_once()
        mock_pdf.extract_audit_values.assert_called_once()
        mock_pdf.extract_table_data.assert_called_once()
        mock_pdf.check_document_completeness.assert_called_once()
        mock_pdf.check_for_signature.assert_called_once()
        mock_pdf.compare_values.assert_called_once()

    @patch('src.workflow.audit.get_emails')
    @patch('src.workflow.audit.assess_emails')
    def test_fetch_new_emails(self, mock_assess, mock_get_emails):
        """Test fetching new emails."""
        # Setup
        mock_get_emails.return_value = pd.DataFrame({
            'id': [1, 2],
            'sender': ['test@example.com', 'test2@example.com'],
            'subject': ['Test Subject', 'Test Subject 2'],
            'date': ['2023-01-01', '2023-01-02'],
            'processed': [0, 0]
        })
        mock_assess.return_value = 2

        # Execute
        result = fetch_new_emails()

        # Assert
        assert result == 2
        mock_get_emails.assert_called_once()
        mock_assess.assert_called_once()

    @patch('src.workflow.audit.os.path.exists')
    @patch('src.workflow.audit.os.makedirs')
    @patch('src.workflow.audit.get_client_info')
    @patch('src.workflow.audit.get_document_info')
    @patch('src.workflow.audit.update_audit_case')
    @patch('src.workflow.audit.Database')
    def test_generate_certificate(self, mock_db_class, mock_update, mock_get_doc, 
                                 mock_get_client, mock_makedirs, mock_exists):
        """Test generating a certificate."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_exists.return_value = False
        mock_get_client.return_value = {
            'name': 'Test Client',
            'bafin_id': '12345'
        }
        mock_get_doc.return_value = {
            'document_path': 'path/to/document.pdf',
            'document_hash': 'hash123'
        }

        # Execute
        result = generate_certificate(123)

        # Assert
        assert result is not None
        assert os.path.basename(result).startswith('certificate_')
        assert os.path.basename(result).endswith('.pdf')
        mock_get_client.assert_called_once_with(123, mock_db)
        mock_get_doc.assert_called_once_with(123, mock_db)
        mock_update.assert_called_once()

    @patch('src.workflow.audit.Database')
    def test_get_client_info(self, mock_db_class):
        """Test getting client information."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = [(1, 'Test Client', '12345', 'test@example.com')]

        # Execute
        result = get_client_info(123, mock_db)

        # Assert
        assert result['id'] == 1
        assert result['name'] == 'Test Client'
        assert result['bafin_id'] == '12345'
        assert result['email'] == 'test@example.com'
        mock_db.query.assert_called_once()

    @patch('src.workflow.audit.Database')
    def test_get_document_info(self, mock_db_class):
        """Test getting document information."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = [(1, 'path/to/document.pdf', 'hash123', '2023-01-01')]

        # Execute
        result = get_document_info(123, mock_db)

        # Assert
        assert result['id'] == 1
        assert result['document_path'] == 'path/to/document.pdf'
        assert result['document_hash'] == 'hash123'
        assert result['created_at'] == '2023-01-01'
        mock_db.query.assert_called_once()

    @patch('src.workflow.audit.Database')
    def test_update_audit_case(self, mock_db_class):
        """Test updating an audit case."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db

        # Execute
        update_audit_case(123, 'path/to/certificate.pdf', mock_db)

        # Assert
        mock_db.query.assert_called_once()

    @patch('src.workflow.audit.Mailclient')
    @patch('src.workflow.audit.Database')
    def test_send_document_confirmation_email(self, mock_db_class, mock_mail_class):
        """Test sending a document confirmation email."""
        # Setup
        mock_db = MagicMock()
        mock_db_class.get_instance.return_value = mock_db
        mock_db.query.return_value = [(1, 'Test Client', 'test@example.com')]

        mock_mail = MagicMock()
        mock_mail_class.get_instance.return_value = mock_mail

        mock_document = MagicMock()
        mock_document.audit_case_id = 123
        mock_document.attributes = {'filename': 'test.pdf'}

        # Execute
        send_document_confirmation_email(mock_document, mock_db)

        # Assert
        mock_db.query.assert_called_once()
        mock_mail.send_email.assert_called_once()
