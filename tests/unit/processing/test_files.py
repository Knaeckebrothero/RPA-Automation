"""
Unit tests for the files module.

This module contains tests for file processing functionality, including
PDF manipulation, document conversion, and certificate generation.
"""
import os
import io
import pytest
import numpy as np
import datetime
from unittest.mock import patch, MagicMock, mock_open

from processing.files import (
    get_images_from_pdf,
    create_certificate_from_template,
    convert_docx_to_pdf,
    extract_first_page,
    combine_pdfs
)


class TestFiles:
    """Test suite for the files module."""

    @patch('fitz.open')
    def test_get_images_from_pdf_with_images(self, mock_fitz_open):
        """Test extracting images from a PDF that contains images."""
        # Set up mock PDF document
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_image_list = [
            {'xref': 1, 'width': 100, 'height': 100, 'colorspace': 3},
            {'xref': 2, 'width': 200, 'height': 200, 'colorspace': 3}
        ]

        # Configure mocks
        mock_fitz_open.return_value = mock_doc
        mock_doc.page_count = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_page.get_images.return_value = mock_image_list

        # Mock the extract_image method to return image data
        mock_doc.extract_image.side_effect = [
            {'image': b'image1_data'},
            {'image': b'image2_data'}
        ]

        # Call the function
        result = get_images_from_pdf(b'sample_pdf_bytes')

        # Verify the result
        assert len(result) == 2
        mock_fitz_open.assert_called_once()
        mock_page.get_images.assert_called_once()
        assert mock_doc.extract_image.call_count == 2

    @patch('fitz.open')
    def test_get_images_from_pdf_no_images(self, mock_fitz_open):
        """Test extracting images from a PDF that contains no images."""
        # Set up mock PDF document
        mock_doc = MagicMock()
        mock_page = MagicMock()

        # Configure mocks
        mock_fitz_open.return_value = mock_doc
        mock_doc.page_count = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_page.get_images.return_value = []  # No images

        # Call the function
        result = get_images_from_pdf(b'sample_pdf_bytes')

        # Verify the result
        assert len(result) == 0
        mock_fitz_open.assert_called_once()
        mock_page.get_images.assert_called_once()
        mock_doc.extract_image.assert_not_called()

    @patch('fitz.open')
    def test_get_images_from_pdf_multiple_pages(self, mock_fitz_open):
        """Test extracting images from a multi-page PDF."""
        # Set up mock PDF document
        mock_doc = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()

        # Configure mocks
        mock_fitz_open.return_value = mock_doc
        mock_doc.page_count = 2
        mock_doc.__getitem__.side_effect = [mock_page1, mock_page2]

        # Page 1 has one image, page 2 has two images
        mock_page1.get_images.return_value = [{'xref': 1, 'width': 100, 'height': 100, 'colorspace': 3}]
        mock_page2.get_images.return_value = [
            {'xref': 2, 'width': 200, 'height': 200, 'colorspace': 3},
            {'xref': 3, 'width': 300, 'height': 300, 'colorspace': 3}
        ]

        # Mock the extract_image method to return image data
        mock_doc.extract_image.side_effect = [
            {'image': b'image1_data'},
            {'image': b'image2_data'},
            {'image': b'image3_data'}
        ]

        # Call the function
        result = get_images_from_pdf(b'sample_pdf_bytes')

        # Verify the result
        assert len(result) == 3
        mock_fitz_open.assert_called_once()
        assert mock_page1.get_images.call_count == 1
        assert mock_page2.get_images.call_count == 1
        assert mock_doc.extract_image.call_count == 3

    @patch('docx.Document')
    @patch('processing.files.datetime')
    @patch('builtins.open', new_callable=mock_open)
    def test_create_certificate_from_template(self, mock_file, mock_datetime, mock_document_class):
        """Test creating a certificate from a template."""
        # Set up mocks
        mock_doc = MagicMock()
        mock_document_class.return_value = mock_doc
        mock_datetime.datetime.now.return_value = datetime.datetime(2023, 1, 1)
        mock_datetime.datetime.strftime.return_value = "January 1, 2023"

        # Mock document elements
        mock_paragraphs = [MagicMock(), MagicMock(), MagicMock()]
        mock_doc.paragraphs = mock_paragraphs

        # Client info for the certificate
        client_info = {
            'name': 'Test Client',
            'address': '123 Test St',
            'city': 'Test City',
            'bafin_id': '12345'
        }

        # Call the function
        result = create_certificate_from_template(client_info, 100)

        # Verify the result
        assert result is not None
        mock_document_class.assert_called_once()
        # Check that the document was saved
        mock_doc.save.assert_called_once()
        # Verify file operations
        mock_file.assert_called()

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_convert_docx_to_pdf_success(self, mock_exists, mock_run):
        """Test successful conversion of DOCX to PDF."""
        # Set up mocks
        mock_exists.return_value = True  # PDF file exists after conversion
        mock_run.return_value = MagicMock(returncode=0)  # Successful conversion

        # Call the function
        docx_path = 'test_document.docx'
        result = convert_docx_to_pdf(docx_path)

        # Verify the result
        assert result == 'test_document.pdf'
        mock_run.assert_called_once()
        mock_exists.assert_called_once()

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('processing.files.logging')
    def test_convert_docx_to_pdf_failure(self, mock_logging, mock_exists, mock_run):
        """Test failed conversion of DOCX to PDF."""
        # Set up mocks
        mock_exists.return_value = False  # PDF file doesn't exist after conversion
        mock_run.return_value = MagicMock(returncode=1)  # Failed conversion

        # Call the function
        docx_path = 'test_document.docx'
        result = convert_docx_to_pdf(docx_path)

        # Verify the result
        assert result is None
        mock_run.assert_called_once()
        mock_exists.assert_called_once()
        # Check that error was logged
        mock_logging.error.assert_called()

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('processing.files.logging')
    def test_convert_docx_to_pdf_exception(self, mock_logging, mock_exists, mock_run):
        """Test exception handling during DOCX to PDF conversion."""
        # Set up mocks
        mock_run.side_effect = Exception("Conversion error")

        # Call the function
        docx_path = 'test_document.docx'
        result = convert_docx_to_pdf(docx_path)

        # Verify the result
        assert result is None
        mock_run.assert_called_once()
        # Check that error was logged
        mock_logging.error.assert_called()

    @patch('fitz.open')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_extract_first_page(self, mock_makedirs, mock_exists, mock_fitz_open):
        """Test extracting the first page from a document."""
        # Set up mocks
        mock_doc = MagicMock()
        mock_fitz_open.return_value = mock_doc
        mock_exists.return_value = False  # Output directory doesn't exist

        # Call the function
        document_path = 'test_document.pdf'
        audit_case_id = 100
        result = extract_first_page(document_path, audit_case_id)

        # Verify the result
        assert result is not None
        mock_fitz_open.assert_called_once_with(document_path)
        mock_exists.assert_called_once()
        mock_makedirs.assert_called_once()
        # Check that the document was saved
        mock_doc.select.assert_called_once_with([0])  # Select first page
        mock_doc.save.assert_called_once()

    @patch('fitz.open')
    @patch('os.path.exists')
    @patch('processing.files.logging')
    def test_extract_first_page_exception(self, mock_logging, mock_exists, mock_fitz_open):
        """Test exception handling during first page extraction."""
        # Set up mocks
        mock_fitz_open.side_effect = Exception("Extraction error")
        mock_exists.return_value = True  # Output directory exists

        # Call the function
        document_path = 'test_document.pdf'
        audit_case_id = 100
        result = extract_first_page(document_path, audit_case_id)

        # Verify the result
        assert result is None
        mock_fitz_open.assert_called_once_with(document_path)
        # Check that error was logged
        mock_logging.error.assert_called()

    @patch('fitz.open')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_combine_pdfs(self, mock_makedirs, mock_exists, mock_fitz_open):
        """Test combining multiple PDFs into one."""
        # Set up mocks
        mock_doc = MagicMock()
        mock_source_doc = MagicMock()
        mock_fitz_open.side_effect = [mock_doc, mock_source_doc, mock_source_doc, mock_source_doc]
        mock_exists.return_value = False  # Output directory doesn't exist

        # Call the function
        certificate_path = 'certificate.pdf'
        first_page_path = 'first_page.pdf'
        terms_path = 'terms.pdf'
        audit_case_id = 100
        result = combine_pdfs(certificate_path, first_page_path, terms_path, audit_case_id)

        # Verify the result
        assert result is not None
        assert mock_fitz_open.call_count == 4  # One for output, three for input PDFs
        mock_exists.assert_called_once()
        mock_makedirs.assert_called_once()
        # Check that pages were inserted
        assert mock_doc.insert_pdf.call_count == 3
        # Check that the document was saved
        mock_doc.save.assert_called_once()

    @patch('fitz.open')
    @patch('os.path.exists')
    @patch('processing.files.logging')
    def test_combine_pdfs_exception(self, mock_logging, mock_exists, mock_fitz_open):
        """Test exception handling during PDF combination."""
        # Set up mocks
        mock_fitz_open.side_effect = Exception("Combination error")
        mock_exists.return_value = True  # Output directory exists

        # Call the function
        certificate_path = 'certificate.pdf'
        first_page_path = 'first_page.pdf'
        terms_path = 'terms.pdf'
        audit_case_id = 100
        result = combine_pdfs(certificate_path, first_page_path, terms_path, audit_case_id)

        # Verify the result
        assert result is None
        mock_fitz_open.assert_called_once()
        # Check that error was logged
        mock_logging.error.assert_called()
